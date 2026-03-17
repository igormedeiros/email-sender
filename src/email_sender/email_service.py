import logging
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, TaskProgressColumn
from rich.console import Console

from .config import Config
from .smtp_manager import SmtpManager
from .db import Database

log = logging.getLogger("email_sender")
console = Console()


class EmailService:
    """Serviço de envio de emails com proteções contra spam."""
    
    def __init__(self, config: Config, db: Database, smtp: SmtpManager):
        self.config = config
        self.db = db
        self.smtp = smtp
        self._sent_contacts = set()

    def send_batch(self, message_id: int, dry_run: bool = False, is_test_mode: bool = True, target_email: str = None) -> Dict[str, Any]:
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
            target_email: Se fornecido, envia apenas para este email

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
        
        is_single_target_mode = target_email is not None
        
        try:
            log.info(f"[START] send_batch: message_id={message_id}, dry_run={dry_run}, is_test_mode={is_test_mode}, target_email={target_email}")
            
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
                if is_test_mode:
                    # Em modo de teste, apenas verificar se a mensagem existe, ignorando o status 'processed'
                    msg_exists = self.db.fetch_one("sql/messages/check_message_exists.sql", [message_id])
                else:
                    # Em modo de produção, usar a validação completa
                    check_msg_path = "sql/messages/check_message_valid.sql"
                    msg_exists = self.db.fetch_one(check_msg_path, [message_id])
                
                if not msg_exists:
                    log.warning(f"[STEP 2] ❌ Mensagem {message_id} não existe ou não está pronta para envio")
                    result['errors'].append(f"Message {message_id} invalid or not ready")
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
                if is_single_target_mode:
                    log.info(f"[STEP 3] Buscando contato específico: {target_email}...")
                    query_path = "sql/contacts/select_contact_by_email.sql"
                    contacts = self.db.fetch_all(query_path, [target_email])
                elif is_test_mode:
                    log.info("[STEP 3] Buscando contatos elegíveis (tag 'Test' apenas, modo de teste)...")
                    query_path = "sql/contacts/select_recipients_for_message_test_mode.sql"
                    contacts = self.db.fetch_all(query_path, [True, message_id])
                else:
                    log.info("[STEP 3] Buscando contatos elegíveis (PRODUÇÃO - TODOS)...")
                    query_path = "sql/contacts/select_recipients_for_message.sql"
                    contacts = self.db.fetch_all(query_path, [False, message_id])
                
                log.info(f"[STEP 3] ✅ Encontrados {len(contacts)} contatos")
            except Exception as e:
                log.error(f"[STEP 3] ❌ Erro: {type(e).__name__}: {e}")
                result['errors'].append(f"Fetch contacts: {str(e)}")
                return result
            
            if not contacts:
                log.warning("[STEP 3] ⚠️  Nenhum contato encontrado")
                return result
            
            # 3.5 PRÉ-CARREGAR DUPLICATAS EM MEMÓRIA (OTIMIZAÇÃO CRÍTICA)
            # ⚡ Carregar TODOS os contatos já-enviados UMA VEZ
            # Isso evita N queries SQL durante o envio (gargalo principal!)
            already_sent_contact_ids = set()
            is_production_run = not is_test_mode and not is_single_target_mode
            if is_production_run:
                try:
                    log.info("[STEP 3.5] Pré-carregando duplicatas em memória (OTIMIZAÇÃO)...")
                    check_all_sent_path = "sql/messages/check_all_emails_already_sent.sql"
                    all_sent_logs = self.db.fetch_all(check_all_sent_path, [message_id])
                    already_sent_contact_ids = {row['contact_id'] for row in all_sent_logs}
                    log.info(f"[STEP 3.5] ✅ {len(already_sent_contact_ids)} contatos já-enviados em memória")
                except Exception as e:
                    log.warning(f"[STEP 3.5] ⚠️  Erro ao pré-carregar: {e}")
            
            # 3.6 DESCONECTAR BANCO ANTES DO ENVIO
            # ⚡ OTIMIZAÇÃO CRÍTICA: Liberar conexão de BD
            # Não precisamos de BD durante o envio SMTP (que é O gargalo)
            try:
                log.info("[STEP 3.6] Desconectando BD para liberar recursos durante envio...")
                self.db.close()
                log.info("[STEP 3.6] ✅ BD desconectado (reconectará ao final)")
            except Exception as e:
                log.warning(f"[STEP 3.6] Erro ao desconectar BD: {e}")
            
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
            
            # Usar barra de progresso Rich
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task(
                    f"[cyan]Enviando {len(contacts)} emails...",
                    total=len(contacts)
                )
                
                start_time = time.time()
                
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
                            progress.advance(task)
                            continue
                        
                        # PROTEÇÃO 2: Verificar BD (já enviado antes?) - APENAS em PRODUÇÃO
                        # Em TESTE mode, permitir reenvio (is_test_mode=True)
                        # ⚡ OTIMIZAÇÃO CRÍTICA: Usar pré-carregamento em memória (O(1) lookup, sem queries!)
                        if is_production_run and contact_id in already_sent_contact_ids:
                            log.debug(f"[STEP 5.{i}] ⏭️  Já enviado (verificação em memória)")
                            progress.advance(task)
                            continue
                        
                        # ENVIAR EMAIL (sem acesso a BD durante envio!)
                        try:
                            if not dry_run:
                                self.smtp.send_email(
                                    to_email=email,
                                    subject=message_subject or 'Sem assunto',
                                    content=message_html or '<p>Sem conteúdo</p>',
                                    is_html=True
                                )
                                log.debug(f"[STEP 5.{i}] ✅ Email enviado para {email}")
                            else:
                                log.debug(f"🔄 [DRY-RUN] {email}")
                            
                            # Marcar em memória (sem query!)
                            self._sent_contacts.add(contact_id)
                            
                            result['sent'] += 1
                            result['sent_emails'].append({'id': contact_id, 'email': email})
                            
                        except Exception as e:
                            log.error(f"❌ {email} - {type(e).__name__}: {str(e)}")
                            result['failed'] += 1
                            result['failed_emails'].append({'email': email, 'error': str(e)})
                            result['errors'].append(f"{email}: {str(e)}")
                        
                        # Atualizar barra de progresso
                        progress.advance(task)
                        
                        # PAUSA ENTRE LOTES
                        if (i + 1) % batch_size == 0 and i + 1 < len(contacts):
                            time.sleep(batch_delay)
                    
                    except Exception as e:
                        log.error(f"[STEP 5.{i}] ❌ Erro no loop: {type(e).__name__}: {e}")
                        result['errors'].append(f"Loop error at {i}: {str(e)}")
                        progress.advance(task)
            
            # 6. FINALIZAR ENVIO SMTP
            total_time = time.time() - start_time
            
            # DESCONECTAR SMTP
            try:
                self.smtp.disconnect()
                log.info("[STEP 6] ✅ SMTP desconectado")
            except Exception as e:
                log.warning(f"[STEP 6] Erro ao desconectar SMTP: {type(e).__name__}: {e}")
            
            # 7. RECONECTAR BD E FAZER BATCH UPDATE
            # ⚡ OTIMIZAÇÃO: Fazer TODOS os UPDATEs de uma vez (batch)
            try:
                log.info("[STEP 7] Reconectando ao BD para gravação em batch...")
                self.db.connect()
                log.info("[STEP 7] ✅ BD reconectado")
            except Exception as e:
                log.error(f"[STEP 7] ❌ Erro ao reconectar BD: {type(e).__name__}: {e}")
                result['errors'].append(f"DB reconnect failed: {str(e)}")
                # Continuar mesmo se falhar, para gerar relatório
            
            # 7.1 REGISTRAR EMAILS COM SUCESSO (batch)
            try:
                if result['sent'] > 0 and self.db._conn and not is_test_mode: # Não registrar logs em modo de teste
                    log.info(f"[STEP 7.1] Registrando {result['sent']} emails enviados em batch...")
                    insert_log_path = "sql/messages/insert_message_sent_log_batch.sql"
                    
                    # Preparar dados para batch
                    batch_data = [(item['id'], message_id) for item in result['sent_emails']]
                    
                    # Executar batch insert
                    for contact_id, msg_id in batch_data:
                        self.db.execute("sql/messages/insert_message_sent_log.sql", [contact_id, msg_id])
                    
                    log.info(f"[STEP 7.1] ✅ {result['sent']} registros de sucesso gravados")
                elif is_test_mode:
                    log.info("[STEP 7.1] ℹ️  Não registrando logs de envio (modo de teste)")
            except Exception as e:
                log.warning(f"[STEP 7.1] Erro ao registrar sucessos: {type(e).__name__}: {e}")
                result['errors'].append(f"Insert success logs failed: {str(e)}")
            
            # 7.2 MARCAR MENSAGEM COMO PROCESSADA
            try:
                if self.db._conn and not is_test_mode: # Adicionar condição para não marcar como processada em modo de teste
                    log.info("[STEP 7.2] Marcando mensagem como processada...")
                    mark_path = "sql/messages/mark_message_processed.sql"
                    self.db.execute(mark_path, [message_id])
                    log.info("[STEP 7.2] ✅ Mensagem marcada")
                elif is_test_mode:
                    log.info("[STEP 7.2] ℹ️  Mensagem NÃO marcada como processada (modo de teste)")
            except Exception as e:
                log.warning(f"[STEP 7.2] Erro ao marcar mensagem: {type(e).__name__}: {e}")
            
            # 7.3 REGISTRAR EMAILS COM FALHA (para relatório)
            if result['failed'] > 0:
                log.info(f"[STEP 7.3] Relatório contém {result['failed']} emails com falha")
                log.info(f"[STEP 7.3] ℹ️  Falhas estão documentadas no relatório para análise manual")
            
            # Desconectar BD ao final
            try:
                self.db.close()
            except:
                pass
            
            # Log final com tempo total
            if total_time > 60:
                time_display = f"{total_time/60:.1f}m"
            else:
                time_display = f"{total_time:.1f}s"
            
            log.info(f"[SUCCESS] Envio concluído: {result['sent']} enviados, {result['failed']} falhas em {time_display}")
            
            # Gerar relatório em arquivo (com lista de falhas para análise)
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
                for item in result['sent_emails']:
                    # Lidar com dict ou string
                    email = item['email'] if isinstance(item, dict) else item
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

