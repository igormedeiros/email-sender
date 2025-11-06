import logging
import time
from typing import Dict, Any

from .config import Config
from .smtp_manager import SmtpManager
from .db import Database

log = logging.getLogger("email_sender")


class EmailService:
    """Serviço de envio de emails com proteções contra spam."""
    
    def __init__(self, config: Config, db: Database, smtp: SmtpManager):
        self.config = config
        self.db = db
        self.smtp = smtp
        self._sent_contacts = set()

    def send_batch(self, message_id: int, dry_run: bool = False, is_test_mode: bool = True) -> Dict[str, Any]:
        """
        Envia emails em lote com proteções:
        1. Não envia para descadastrados
        2. Não envia para bounces
        3. Não envia 2x para o mesmo contato
        4. Controla duplicatas em memória

        Args:
            message_id: ID da mensagem a ser enviada
            dry_run: Se True, não envia de verdade
            is_test_mode: Se True, apenas contatos com tag 'Test' (padrão: True)

        Returns:
            Dict com estatísticas do envio
        """
        result = {
            'sent': 0,
            'failed': 0,
            'total_processed': 0,
            'errors': []
        }
        
        try:
            log.info(f"[START] send_batch: message_id={message_id}, dry_run={dry_run}")
            
            # 1. CONECTAR AO BANCO
            try:
                log.info("[STEP 1] Conectando ao banco de dados...")
                self.db.connect()
                log.info("[STEP 1] ✅ Banco conectado")
            except Exception as e:
                log.error(f"[STEP 1] ❌ Erro: {type(e).__name__}: {e}")
                result['errors'].append(f"DB connect: {str(e)}")
                return result
            
            # 2. VALIDAR MENSAGEM
            try:
                log.info(f"[STEP 2] Validando mensagem {message_id}...")
                check_msg_path = "sql/messages/check_message_valid.sql"
                msg_exists = self.db.fetch_one(check_msg_path, [message_id])
                
                if not msg_exists:
                    log.warning(f"[STEP 2] ❌ Mensagem {message_id} não existe ou já foi processada")
                    result['errors'].append(f"Message {message_id} invalid or processed")
                    return result
                
                log.info(f"[STEP 2] ✅ Mensagem validada")
            except Exception as e:
                log.error(f"[STEP 2] ❌ Erro: {type(e).__name__}: {e}")
                result['errors'].append(f"Message check: {str(e)}")
                return result
            
            # 3. BUSCAR CONTATOS ELEGÍVEIS
            try:
                if is_test_mode:
                    log.info("[STEP 3] Buscando contatos elegíveis (tag 'Test' apenas)...")
                else:
                    log.info("[STEP 3] Buscando contatos elegíveis (PRODUÇÃO - TODOS)...")
                query_path = "sql/contacts/select_recipients_for_message.sql"
                # is_test_mode = TRUE = apenas contatos com tag 'Test'
                # is_test_mode = FALSE = TODOS os contatos elegíveis
                contacts = self.db.fetch_all(query_path, [is_test_mode, message_id])
                log.info(f"[STEP 3] ✅ Encontrados {len(contacts)} contatos")
            except Exception as e:
                log.error(f"[STEP 3] ❌ Erro: {type(e).__name__}: {e}")
                result['errors'].append(f"Fetch contacts: {str(e)}")
                return result
            
            if not contacts:
                log.warning("[STEP 3] ⚠️  Nenhum contato encontrado")
                return result
            
            # 4. CONECTAR SMTP
            try:
                log.info("[STEP 4] Conectando ao SMTP...")
                self.smtp.connect()
                log.info("[STEP 4] ✅ SMTP conectado")
            except Exception as e:
                log.error(f"[STEP 4] ❌ Erro: {type(e).__name__}: {e}")
                result['errors'].append(f"SMTP connect: {str(e)}")
                return result
            
            # 5. ENVIAR EMAILS
            batch_size = self.config.email_config.get('batch_size', 200)
            batch_delay = self.config.email_config.get('batch_delay', 5)
            
            log.info(f"[STEP 5] Iniciando envio de {len(contacts)} emails (batch_size={batch_size})...")
            
            for i, contact_data in enumerate(contacts):
                try:
                    # Extrair dados (pode ser dict ou tupla)
                    if isinstance(contact_data, dict):
                        contact_id = contact_data.get('id')
                        email = contact_data.get('email')
                    else:
                        contact_id, email = contact_data
                    
                    log.debug(f"[STEP 5.{i}] Processando: id={contact_id}, email={email}")
                    result['total_processed'] += 1
                    
                    # PROTEÇÃO 1: Verificar memória (duplicata nesta sessão)
                    if contact_id in self._sent_contacts:
                        log.debug(f"[STEP 5.{i}] ⏭️  Já enviado nesta sessão")
                        continue
                    
                    # PROTEÇÃO 2: Verificar BD (já enviado antes?) - APENAS em PRODUÇÃO
                    # Em TESTE mode, permitir reenvio (dry_run=True significa TESTE)
                    if not dry_run:  # Se PRODUÇÃO (dry_run=False)
                        try:
                            log.debug(f"[STEP 5.{i}] Verificando BD...")
                            check_query_path = "sql/messages/check_email_already_sent.sql"
                            already_sent = self.db.fetch_one(check_query_path, [contact_id, message_id])
                            
                            if already_sent:
                                log.debug(f"[STEP 5.{i}] ⏭️  Já enviado antes")
                                continue
                        except Exception as e:
                            log.warning(f"[STEP 5.{i}] Erro ao verificar: {type(e).__name__}: {e}")
                    else:
                        log.debug(f"[STEP 5.{i}] ℹ️  TESTE mode - ignorando deduplicação BD")
                    
                    # ENVIAR EMAIL
                    try:
                        if not dry_run:
                            log.debug(f"[STEP 5.{i}] 📧 Enviando email...")
                            self.smtp.send_email(
                                to_email=email,
                                subject="Test Email",
                                content="<p>Test message</p>",
                                is_html=True
                            )
                            log.info(f"[STEP 5.{i}] ✅ Email enviado para {email}")
                        else:
                            log.info(f"[STEP 5.{i}] 🔄 [DRY-RUN] {email}")
                        
                        # Marcar em memória
                        self._sent_contacts.add(contact_id)
                        
                        # Registrar no BD
                        try:
                            insert_log_path = "sql/messages/insert_message_sent_log.sql"
                            self.db.execute(insert_log_path, [contact_id, message_id])
                            log.debug(f"[STEP 5.{i}] 📝 Log registrado")
                        except Exception as e:
                            log.warning(f"[STEP 5.{i}] Erro ao registrar log: {type(e).__name__}: {e}")
                        
                        result['sent'] += 1
                        
                    except Exception as e:
                        log.error(f"[STEP 5.{i}] ❌ Erro ao enviar: {type(e).__name__}: {e}")
                        result['failed'] += 1
                        result['errors'].append(f"{email}: {str(e)}")
                    
                    # PAUSA ENTRE LOTES
                    if (i + 1) % batch_size == 0 and i + 1 < len(contacts):
                        log.info(f"[STEP 5] 📊 {i + 1}/{len(contacts)} enviados, aguardando {batch_delay}s...")
                        time.sleep(batch_delay)
                
                except Exception as e:
                    log.error(f"[STEP 5.{i}] ❌ Erro no loop: {type(e).__name__}: {e}")
                    result['errors'].append(f"Loop error at {i}: {str(e)}")
            
            # 6. FINALIZAR
            try:
                log.info("[STEP 6] Marcando mensagem como processada...")
                mark_path = "sql/messages/mark_message_processed.sql"
                self.db.execute(mark_path, [message_id])
                log.info("[STEP 6] ✅ Mensagem marcada")
            except Exception as e:
                log.warning(f"[STEP 6] Erro: {type(e).__name__}: {e}")
            
            # DESCONECTAR
            try:
                self.smtp.disconnect()
                log.info("[DONE] SMTP desconectado")
            except Exception as e:
                log.warning(f"[DONE] Erro ao desconectar: {type(e).__name__}: {e}")
            
            log.info(f"[SUCCESS] Envio concluído: {result['sent']} enviados, {result['failed']} falhas")
            return result
            
        except Exception as e:
            log.error(f"[ERROR] Erro geral: {type(e).__name__}: {e}")
            import traceback
            log.error(f"[ERROR] Traceback:\n{traceback.format_exc()}")
            result['errors'].append(str(e))
            return result
