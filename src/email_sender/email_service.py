import logging
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

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
            'errors': [],
            'sent_emails': [],  # Lista de emails enviados com sucesso
            'failed_emails': []  # Lista de emails que falharam
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
            
            # 2. VALIDAR MENSAGEM E BUSCAR ASSUNTO
            message_subject = None
            try:
                log.info(f"[STEP 2] Validando mensagem {message_id}...")
                check_msg_path = "sql/messages/check_message_valid.sql"
                msg_exists = self.db.fetch_one(check_msg_path, [message_id])
                
                if not msg_exists:
                    log.warning(f"[STEP 2] ❌ Mensagem {message_id} não existe ou já foi processada")
                    result['errors'].append(f"Message {message_id} invalid or processed")
                    return result
                
                # Buscar assunto da mensagem
                log.debug(f"[STEP 2] Buscando assunto da configuração...")
                content_config = self.config.content_config
                message_subject = content_config.get('email', {}).get('subject', 'Sem assunto')
                
                # Carregar template HTML
                log.debug(f"[STEP 2] Carregando template HTML...")
                template_path = self.config.email_config.get('template_path', 'config/templates/email.html')
                try:
                    message_html = Path(template_path).read_text(encoding='utf-8')
                    
                    # Processar placeholders do template com dados do content_config
                    log.debug(f"[STEP 2] Processando placeholders...")
                    evento = content_config.get('evento', {})
                    promocao = content_config.get('promocao', {})
                    
                    # Substituir placeholders
                    message_html = message_html.replace('{data_evento}', evento.get('data', ''))
                    message_html = message_html.replace('{cidade}', evento.get('cidade', ''))
                    message_html = message_html.replace('{link_evento}', evento.get('link', ''))
                    message_html = message_html.replace('{uf}', evento.get('uf', ''))
                    message_html = message_html.replace('{local}', evento.get('local', ''))
                    message_html = message_html.replace('{horario}', evento.get('horario', ''))
                    
                    # Desconto parágrafo
                    desconto = promocao.get('desconto', '')
                    if desconto:
                        desconto_para = f"<p><strong>🎉 DESCONTO ESPECIAL: {desconto} OFF!</strong> Use o cupom <strong>{evento.get('cupom', '')}</strong> para garantir esse preço exclusivo.</p>"
                    else:
                        desconto_para = ""
                    message_html = message_html.replace('{desconto_paragrafo}', desconto_para)
                    
                except Exception as e:
                    log.warning(f"[STEP 2] Erro ao processar template: {e}")
                    message_html = '<p>Sem conteúdo</p>'
                
                log.info(f"[STEP 2] ✅ Mensagem validada (subject: {message_subject[:50] if message_subject else 'N/A'}...)")
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
            
            # Rastreamento de progresso
            start_time = time.time()
            last_progress_update = 0
            
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
                    # Em TESTE mode, permitir reenvio (is_test_mode=True)
                    if not is_test_mode:  # Se PRODUÇÃO (is_test_mode=False)
                        try:
                            check_query_path = "sql/messages/check_email_already_sent.sql"
                            already_sent = self.db.fetch_one(check_query_path, [contact_id, message_id])
                            
                            if already_sent:
                                continue
                        except Exception as e:
                            log.warning(f"Erro ao verificar duplicata: {type(e).__name__}: {e}")
                    
                    # ENVIAR EMAIL
                    try:
                        if not dry_run:
                            log.info(f"📧 {email}")
                            self.smtp.send_email(
                                to_email=email,
                                subject=message_subject or 'Sem assunto',
                                content=message_html or '<p>Sem conteúdo</p>',
                                is_html=True
                            )
                            log.info(f"[STEP 5.{i}] ✅ Email enviado para {email}")
                        else:
                            log.info(f"🔄 [DRY-RUN] {email}")
                        
                        # Marcar em memória
                        self._sent_contacts.add(contact_id)
                        
                        # Registrar no BD
                        try:
                            insert_log_path = "sql/messages/insert_message_sent_log.sql"
                            self.db.execute(insert_log_path, [contact_id, message_id])
                        except Exception as e:
                            log.warning(f"Erro ao registrar log: {type(e).__name__}: {e}")
                        
                        result['sent'] += 1
                        result['sent_emails'].append(email)
                        
                    except Exception as e:
                        log.error(f"❌ {email} - {type(e).__name__}: {str(e)}")
                        result['failed'] += 1
                        result['failed_emails'].append({'email': email, 'error': str(e)})
                        result['errors'].append(f"{email}: {str(e)}")
                    
                    # PAUSA ENTRE LOTES + PROGRESSO
                    if (i + 1) % batch_size == 0 and i + 1 < len(contacts):
                        # Calcular progresso
                        elapsed = time.time() - start_time
                        processed = i + 1
                        percentage = (processed / len(contacts)) * 100
                        avg_time_per_email = elapsed / processed if processed > 0 else 0
                        remaining_emails = len(contacts) - processed
                        estimated_remaining_secs = remaining_emails * avg_time_per_email
                        
                        # Formatar tempo restante
                        if estimated_remaining_secs > 60:
                            time_str = f"{estimated_remaining_secs/60:.1f}m"
                        else:
                            time_str = f"{estimated_remaining_secs:.0f}s"
                        
                        log.info(f"[STEP 5] 📊 {processed}/{len(contacts)} ({percentage:.1f}%) | ⏱️  ~{time_str} restantes | aguardando {batch_delay}s...")
                        time.sleep(batch_delay)
                
                except Exception as e:
                    log.error(f"[STEP 5.{i}] ❌ Erro no loop: {type(e).__name__}: {e}")
                    result['errors'].append(f"Loop error at {i}: {str(e)}")
            
            # 6. FINALIZAR
            total_time = time.time() - start_time
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
            
            # Log final com tempo total
            if total_time > 60:
                time_display = f"{total_time/60:.1f}m"
            else:
                time_display = f"{total_time:.1f}s"
            
            log.info(f"[SUCCESS] Envio concluído: {result['sent']} enviados, {result['failed']} falhas em {time_display}")
            
            # Gerar relatório em arquivo
            self._generate_report(result, total_time)
            
            return result
            
        except Exception as e:
            log.error(f"[ERROR] Erro geral: {type(e).__name__}: {e}")
            import traceback
            log.error(f"[ERROR] Traceback:\n{traceback.format_exc()}")
            result['errors'].append(str(e))
            return result
    
    def _generate_report(self, result: Dict[str, Any], total_time: float) -> None:
        """Gera relatório de envio em arquivo txt."""
        try:
            # Criar diretório de relatórios se não existir
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            
            # Nome do arquivo com timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = reports_dir / f"email_report_{timestamp}.txt"
            
            # Formatar tempo
            if total_time > 60:
                time_display = f"{total_time/60:.1f}m ({total_time:.1f}s)"
            else:
                time_display = f"{total_time:.1f}s"
            
            # Gerar conteúdo do relatório
            lines = [
                "=" * 80,
                "RELATÓRIO DE ENVIO DE EMAILS",
                "=" * 80,
                f"\nData/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                f"Tempo total: {time_display}",
                f"\nResumo:",
                f"  Total processado: {result['total_processed']}",
                f"  Enviados com sucesso: {result['sent']}",
                f"  Falhas: {result['failed']}",
                f"  Taxa de sucesso: {(result['sent'] / result['total_processed'] * 100):.1f}%" if result['total_processed'] > 0 else "  Taxa de sucesso: N/A",
                "\n" + "=" * 80,
                "EMAILS ENVIADOS COM SUCESSO",
                "=" * 80,
            ]
            
            if result['sent_emails']:
                for email in result['sent_emails']:
                    lines.append(f"  ✓ {email}")
            else:
                lines.append("  Nenhum email enviado.")
            
            lines.extend([
                "\n" + "=" * 80,
                "EMAILS COM FALHA",
                "=" * 80,
            ])
            
            if result['failed_emails']:
                for item in result['failed_emails']:
                    lines.append(f"  ✗ {item['email']}")
                    lines.append(f"    Erro: {item['error']}")
                    lines.append("")
            else:
                lines.append("  Nenhuma falha.")
            
            lines.append("\n" + "=" * 80)
            
            # Escrever arquivo
            report_content = "\n".join(lines)
            report_file.write_text(report_content, encoding='utf-8')
            
            log.info(f"Relatório salvo em: {report_file}")
            
        except Exception as e:
            log.error(f"Erro ao gerar relatório: {type(e).__name__}: {e}")

