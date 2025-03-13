import smtplib
import csv
import os
import logging
import pandas as pd
import time
import ssl
import socket
import re
import shutil
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Any
from contextlib import contextmanager
from datetime import datetime
import signal

from src.config import Config
from src.utils.csv_reader import CSVReader

log = logging.getLogger("email_sender")

class EmailService:
    def __init__(self, config: Config):
        self.config = config

    def _extract_email_address(self, sender: str) -> str:
        """Extract email address from sender string format 'Name | Company <email@domain.com>'"""
        match = re.search(r'<([^>]+)>', sender)
        return match.group(1) if match else sender

    @contextmanager
    def _create_smtp_connection(self):
        retry_attempts = self.config.smtp_config.get("retry_attempts", 3)
        retry_delay = self.config.smtp_config.get("retry_delay", 5)
        timeout = self.config.smtp_config.get("send_timeout", 10)
        last_exception = None
        smtp = None

        for attempt in range(retry_attempts):
            try:
                if attempt > 0:
                    log.info(f"Tentativa {attempt + 1} de {retry_attempts} de conectar ao SMTP...")
                
                smtp = smtplib.SMTP(
                    self.config.smtp_config["host"],
                    self.config.smtp_config["port"],
                    timeout=timeout
                )
                
                if self.config.smtp_config["use_tls"]:
                    smtp.starttls()
                    
                smtp.login(
                    self.config.smtp_config["username"],
                    self.config.smtp_config["password"]
                )
                
                break
            except Exception as e:
                last_exception = e
                if smtp:
                    try:
                        smtp.close()
                    except:
                        pass
                if attempt < retry_attempts - 1 and retry_delay > 0:
                    log.error(f"Falha na conexão SMTP: {str(e)}")
                    time.sleep(retry_delay)
                smtp = None
        
        if smtp is None:
            raise Exception(f"Falha ao conectar ao servidor SMTP após {retry_attempts} tentativas: {str(last_exception)}")

        try:
            yield smtp
        finally:
            try:
                smtp.quit()
            except:
                try:
                    smtp.close()
                except:
                    pass

    def _create_message(self, to_email: str, subject: str, content: str, is_html: bool = False) -> MIMEMultipart:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        sender_email = self._extract_email_address(self.config.email_config["sender"])
        message["From"] = self.config.email_config["sender"]
        message["Reply-To"] = sender_email
        message["Return-Path"] = sender_email
        message["To"] = to_email
        
        # Se não for HTML, envia como texto simples
        if not is_html:
            text_part = MIMEText(content, "plain", "utf-8")
            message.attach(text_part)
        # Se for HTML, envia a parte HTML e também uma versão em texto simples convertida
        else:
            # Versão texto simples - versão básica sem formatação
            text_content = re.sub(r'<.*?>', '', content)
            text_content = re.sub(r'\s+', ' ', text_content)
            text_part = MIMEText(text_content, "plain", "utf-8")
            message.attach(text_part)
            
            # Versão HTML
            html_part = MIMEText(content, "html", "utf-8")
            message.attach(html_part)
            
        return message

    def _read_template(self, template_path: str) -> str:
        with open(template_path, 'r', encoding='utf-8') as file:
            return file.read()

    def _format_template(self, template: str, recipient: Dict) -> str:
        """Format template with recipient data."""
        # Substituir parâmetros do formato {param}
        result = template
        for key, value in recipient.items():
            placeholder = '{' + key + '}'
            result = result.replace(placeholder, str(value))
        return result

    def send_batch(self, recipients: List[Dict], content: str, subject: str, is_html: bool = False) -> None:
        try:
            log.info(f"Iniciando envio em lote para {len(recipients)} destinatários")
            log.info(f"Modo HTML: {'Sim' if is_html else 'Não'}")
            
            with self._create_smtp_connection() as smtp:
                for recipient in recipients:
                    try:
                        # Formatar o conteúdo com os dados do destinatário
                        formatted_content = self._format_template(content, recipient)
                        
                        # Criar a mensagem
                        message = self._create_message(
                            to_email=recipient["email"],
                            subject=subject,
                            content=formatted_content,
                            is_html=is_html
                        )
                        
                        # Log de debug antes do envio
                        log.info(f"📧 {recipient['email']}")
                        
                        # Enviar a mensagem
                        try:
                            smtp.send_message(message)
                            log.info(f"✅ {recipient['email']}")
                        except smtplib.SMTPException as smtp_error:
                            log.error(f"❌ {recipient['email']}")
                            raise smtp_error
                        except Exception as send_error:
                            log.error(f"❌ {recipient['email']}")
                            raise send_error
                            
                    except smtplib.SMTPServerDisconnected:
                        # Se a conexão foi perdida, tenta reconectar e reenviar este email
                        log.warning("Conexão SMTP perdida. Tentando reconectar...")
                        with self._create_smtp_connection() as new_smtp:
                            new_smtp.send_message(message)
                    except Exception as e:
                        # Outros erros devem ser propagados
                        log.error(f"Erro no processamento do destinatário {recipient['email']}: {str(e)}")
                        raise e
        except Exception as e:
            log.error(f"Erro no envio em lote: {str(e)}")
            raise

    # Novas funções refatoradas a partir do CLI

    def load_unsubscribed_emails(self, unsubscribe_file: str = "data/descadastros.csv") -> List[str]:
        """Carrega a lista de emails descadastrados do arquivo CSV"""
        try:
            if not os.path.exists(unsubscribe_file):
                log.warning(f"Arquivo de descadastros {unsubscribe_file} não encontrado.")
                return []
                
            try:
                # Primeiro tenta ler como CSV com cabeçalho
                df = pd.read_csv(unsubscribe_file)
                if 'email' in df.columns:
                    return df['email'].str.lower().tolist()
                else:
                    # Se não tiver coluna 'email', assume que a primeira coluna contém emails
                    return df.iloc[:, 0].str.lower().tolist()
            except Exception as e:
                # Se falhar na leitura CSV, tenta ler como texto linha por linha
                log.warning(f"Erro ao ler CSV de descadastros, tentando como texto: {str(e)}")
                with open(unsubscribe_file, 'r', encoding='utf-8') as file:
                    emails = []
                    for line in file:
                        email = line.strip().split(',')[0]  # Pega apenas a primeira parte antes da vírgula
                        if email and email.lower() != 'email':  # Ignora cabeçalho e linhas vazias
                            emails.append(email.lower())
                    return emails
        except Exception as e:
            log.warning(f"Erro ao carregar emails descadastrados: {str(e)}.")
            return []

    def register_failed_email(self, email: str, reason: str = None, file_path: str = "data/emails_falharam.csv"):
        """
        Registra um email que falhou no envio em um arquivo CSV.
        
        Args:
            email: Email que falhou no envio
            reason: Motivo da falha (opcional)
            file_path: Caminho para o arquivo CSV (padrão: data/emails_falharam.csv)
        """
        # Garante que o diretório existe
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Data e hora atual
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Verifica se o arquivo existe
        file_exists = os.path.isfile(file_path)
        
        # Abre o arquivo em modo append
        with open(file_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            
            # Escreve o cabeçalho se o arquivo não existir
            if not file_exists:
                writer.writerow(['email', 'data', 'motivo'])
            
            # Escreve o email com data e motivo
            writer.writerow([email, timestamp, reason or "Falha no envio"])
            
        log.info(f"Email {email} registrado em {file_path}")

    def sync_unsubscribed_emails(self, csv_path: str, unsubscribe_file: str) -> int:
        """
        Sincroniza a lista de emails descadastrados com o arquivo principal.
        
        Args:
            csv_path: Caminho para o arquivo CSV principal
            unsubscribe_file: Caminho para o arquivo CSV de descadastros
            
        Returns:
            Número de emails marcados como descadastrados
        """
        try:
            log.info(f"Sincronizando lista de descadastros {unsubscribe_file} com {csv_path}...")
            
            # Verificar se os arquivos existem
            if not Path(csv_path).exists():
                log.error(f"Arquivo principal {csv_path} não encontrado.")
                return 0
                
            if not Path(unsubscribe_file).exists():
                log.warning(f"Arquivo de descadastros {unsubscribe_file} não encontrado.")
                return 0
                
            # Otimização: Usar sets para operações mais rápidas
            unsubscribed = set()
            
            # Lê lista de descadastros de forma eficiente 
            try:
                # Tenta primeiro ler como CSV com cabeçalho
                df_unsubscribed = pd.read_csv(unsubscribe_file, sep=None, engine='python', low_memory=False)
                if 'email' in df_unsubscribed.columns:
                    unsubscribed = set(df_unsubscribed['email'].astype(str).str.lower().dropna())
                else:
                    # Se não tiver coluna 'email', tenta ler a primeira coluna
                    unsubscribed = set(df_unsubscribed.iloc[:, 0].astype(str).str.lower().dropna())
            except Exception as e:
                # Se falhar, tenta ler linha por linha como texto
                log.warning(f"Tentando ler arquivo como texto simples: {str(e)}")
                with open(unsubscribe_file, 'r', encoding='utf-8') as file:
                    for line in file:
                        email = line.strip().lower()
                        if email and not email.startswith('email'):
                            unsubscribed.add(email)
                
            if not unsubscribed:
                log.warning(f"Nenhum email encontrado na lista de descadastros.")
                return 0
                
            log.info(f"Encontrados {len(unsubscribed)} emails descadastrados.")
            
            # Atualiza o arquivo principal - carregando por chunks para maior eficiência com arquivos grandes
            try:
                df = pd.read_csv(csv_path, sep=None, engine='python')
                
                # Verificar se a coluna 'email' existe
                if 'email' not in df.columns:
                    log.error(f"Coluna 'email' não encontrada no arquivo {csv_path}")
                    return 0
                
                # Garantir que a coluna 'descadastro' existe
                if 'descadastro' not in df.columns:
                    df['descadastro'] = ''
                
                # Determinar quais emails existem no CSV principal
                existing_emails = set(df['email'].astype(str).str.lower())
                
                # Marcar emails como descadastrados
                df['descadastro'] = df['email'].astype(str).str.lower().isin(unsubscribed).map({True: 'S', False: ''})
                
                # Calcular estatísticas
                total_blacklisted = len(df[df['descadastro'] == 'S'])
                update_count = total_blacklisted
                
                # Salvar o arquivo atualizado
                df.to_csv(csv_path, index=False)
                
                log.info(f"✅ Sincronização concluída! {update_count} emails atualizados.")
                return update_count
            except Exception as e:
                log.error(f"Erro ao processar arquivo CSV principal: {str(e)}")
                raise
                
        except Exception as e:
            log.error(f"Erro ao sincronizar emails descadastrados: {str(e)}")
            raise

    def send_test_email(self, recipient: str) -> bool:
        """
        Envia um email de teste para verificar a conexão com o servidor SMTP.
        
        Args:
            recipient: Endereço de email do destinatário de teste
            
        Returns:
            True se o email foi enviado com sucesso, False caso contrário
        """
        try:
            # Usar subject do arquivo email.yaml
            email_subject = self.config.content_config.get("email", {}).get("subject", "SMTP Test Email")
            
            message = "This is a test email from the email-sender application."
            
            with self._create_smtp_connection() as smtp:
                test_message = self._create_message(
                    to_email=recipient,
                    subject=email_subject,
                    content=message
                )
                smtp.send_message(test_message)
                
            return True
        except Exception as e:
            log.error(f"Erro ao enviar email de teste: {str(e)}")
            raise

    def create_backup(self, file_path: str) -> str:
        """
        Cria um backup do arquivo CSV.
        
        Args:
            file_path: Caminho para o arquivo CSV a ser copiado
            
        Returns:
            Caminho para o arquivo de backup criado
        """
        try:
            # Verificar se o arquivo existe
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Arquivo para backup não encontrado: {file_path}")
                
            # Criar diretório de backup se não existir
            backup_dir = Path("backup")
            backup_dir.mkdir(exist_ok=True)
            
            # Gerar nome do arquivo de backup
            file_name = Path(file_path).name
            backup_path = backup_dir / f"{file_name}.bak"
            
            # Copiar o arquivo
            shutil.copy2(file_path, backup_path)
            
            log.info(f"Backup criado: {backup_path}")
            return str(backup_path)
        except Exception as e:
            log.error(f"Erro ao criar backup: {str(e)}")
            raise

    def clear_sent_flags(self, csv_file: str) -> int:
        """
        Limpa as flags 'enviado' e 'falhou' no arquivo CSV para permitir o reenvio de emails.
        
        Args:
            csv_file: Caminho para o arquivo CSV
            
        Returns:
            Número de registros com flags limpas
        """
        try:
            if not Path(csv_file).exists():
                raise FileNotFoundError(f"Arquivo CSV não encontrado: {csv_file}")
            
            # Criar backup do arquivo antes de modificá-lo
            backup_path = self.create_backup(csv_file)
            log.info(f"Backup do arquivo criado em: {backup_path}")
                
            # Carrega o arquivo CSV
            df = pd.read_csv(csv_file)
            
            # Contador para registros modificados
            modified_count = 0
            
            # Limpa o flag 'enviado'
            if 'enviado' in df.columns:
                modified_count += len(df[df['enviado'] == 'ok'])
                df['enviado'] = ''
                
            # Limpa o flag 'falhou'
            if 'falhou' in df.columns:
                modified_count += len(df[df['falhou'] == 'ok'])
                df['falhou'] = ''
                
            # Salva o arquivo atualizado
            df.to_csv(csv_file, index=False)
            
            return modified_count
        except Exception as e:
            log.error(f"Erro ao limpar flags de envio: {str(e)}")
            raise

    def process_email_template(self, template_path: str, recipient: Dict, email_subject: str) -> str:
        """
        Processa o template HTML, substituindo as variáveis pelos valores do destinatário.
        
        Args:
            template_path: Caminho para o arquivo de template HTML
            recipient: Dicionário com os dados do destinatário
            email_subject: Assunto do email
            
        Returns:
            HTML formatado
        """
        try:
            # Carrega o template HTML
            with open(template_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            
            # Primeiro substituir os campos obrigatórios
            html_content = html_content.replace("{unsubscribe_url}", self.config.content_config.get("urls", {}).get("unsubscribe", ""))
            html_content = html_content.replace("{subscribe_url}", self.config.content_config.get("urls", {}).get("subscribe", ""))
            html_content = html_content.replace("{email}", recipient['email'])
            
            # Substituir variáveis do evento
            html_content = html_content.replace("{link_evento}", self.config.content_config.get("evento", {}).get("link", ""))
            html_content = html_content.replace("{data_evento}", self.config.content_config.get("evento", {}).get("data", ""))
            html_content = html_content.replace("{cidade}", self.config.content_config.get("evento", {}).get("cidade", ""))
            html_content = html_content.replace("{local}", self.config.content_config.get("evento", {}).get("local", ""))
            
            # Processar parágrafo condicional de desconto
            desconto_paragrafo = ""
            if "promocao" in self.config.content_config and "desconto" in self.config.content_config["promocao"]:
                desconto_valor = self.config.content_config["promocao"]["desconto"]
                desconto_paragrafo = f"""
                <div style="background-color: #e9f2fa; border-left: 4px solid #0066CC; padding: 15px; margin: 20px 0; border-radius: 4px;">
                    <p style="margin: 0; font-size: 1.1em;">
                        <strong style="color: #0066CC;">OFERTA ESPECIAL:</strong> Estamos oferecendo <strong style="color: #0066CC; font-size: 1.15em;">{desconto_valor} de desconto</strong> 
                        no treinamento para quem está recebendo este email.
                    </p>
                    <p style="margin: 10px 0 0 0;">
                        Não é necessário digitar nenhum código promocional – ele já está aplicado e o 
                        desconto é aplicado automaticamente no link acima.
                    </p>
                </div>
                """
            html_content = html_content.replace("{desconto_paragrafo}", desconto_paragrafo)
            
            # Substituir campos de conteúdo dinâmico da configuração
            for key, value in self.config.content_config.items():
                placeholder = f"{{{key}}}"
                if placeholder in html_content:
                    html_content = html_content.replace(placeholder, str(value))
            
            # Verificar todos os campos nas chaves de formatação {campo}
            placeholders = re.findall(r'\{([^}]+)\}', html_content)
            
            # Substituir campos extras se existirem no destinatário
            for placeholder in placeholders:
                if placeholder in recipient:
                    value = recipient[placeholder]
                    html_content = html_content.replace(f"{{{placeholder}}}", str(value))
                else:
                    html_content = html_content.replace(f"{{{placeholder}}}", "")
            
            return html_content
        except Exception as e:
            log.error(f"Erro ao processar template: {str(e)}")
            raise

    def generate_report(self, start_time: float, end_time: float, total_sent: int, successful: int, failed: int) -> Dict[str, Any]:
        """
        Gera um relatório do processo de envio de emails.
        
        Args:
            start_time: Timestamp de início do envio
            end_time: Timestamp de fim do envio
            total_sent: Total de emails tentados
            successful: Total de emails enviados com sucesso
            failed: Total de emails com falha
            
        Returns:
            Dicionário com os dados do relatório e nome do arquivo
        """
        duration = end_time - start_time
        avg_time = duration/total_sent if total_sent > 0 else 0
        
        # Calcular horas e minutos
        horas = int(duration // 3600)
        minutos = int((duration % 3600) // 60)
        segundos = int(duration % 60)
        
        report = f"""Relatório de Envio de Emails
Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
-----------------------------------------
Total de emails tentados: {total_sent}
Enviados com sucesso: {successful}
Falhas: {failed}
Tempo total: {duration:.2f} segundos ({horas}h {minutos}min {segundos}s)
Tempo médio por email: {avg_time:.2f} segundos
"""
        # Ensure reports directory exists
        Path("reports").mkdir(exist_ok=True)
        
        # Nome do arquivo de relatório
        report_file = f"email_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Save report in reports directory
        report_path = Path("reports") / report_file
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return {
            "report": report,
            "report_file": report_file,
            "duration": duration,
            "avg_time": avg_time,
            "total_sent": total_sent,
            "successful": successful,
            "failed": failed,
            "duracao_formatada": f"{horas}h {minutos}min {segundos}s"
        }

    def remove_duplicates(self, csv_file: str, column: str = "email", keep: str = "first", output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Remove linhas duplicadas de um arquivo CSV baseado em uma coluna específica.
        
        Args:
            csv_file: Caminho para o arquivo CSV a ser processado
            column: Coluna a ser usada para identificar duplicados (padrão: 'email')
            keep: Qual ocorrência manter ('first' ou 'last', padrão: 'first')
            output_file: Arquivo de saída. Se não especificado, substitui o original
            
        Returns:
            Dicionário com resultados do processamento
        """
        try:
            log.info(f"Removendo duplicados do arquivo {csv_file} baseado na coluna '{column}'...")
            
            # Verificar se o arquivo existe
            if not Path(csv_file).exists():
                raise FileNotFoundError(f"Arquivo {csv_file} não encontrado")
            
            # Carregar o arquivo CSV
            try:
                # Tentar determinar automaticamente o delimitador
                df = pd.read_csv(csv_file, sep=None, engine='python')
            except Exception as e:
                raise ValueError(f"Erro ao ler o arquivo CSV: {str(e)}")
            
            # Verificar se a coluna existe
            if column not in df.columns:
                raise ValueError(f"Coluna '{column}' não encontrada no arquivo CSV")
            
            # Contar registros antes da remoção
            total_antes = len(df)
            
            # Remover duplicados
            df_without_duplicates = df.drop_duplicates(subset=[column], keep=keep)
            
            # Contar registros após a remoção
            total_depois = len(df_without_duplicates)
            duplicados_removidos = total_antes - total_depois
            
            # Determinar o arquivo de saída
            if not output_file:
                # Se não foi especificado, faz backup do original e substitui
                backup_dir = Path("backup")
                backup_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = backup_dir / f"{Path(csv_file).stem}_{timestamp}.csv"
                
                # Criar backup
                shutil.copy2(csv_file, backup_file)
                log.info(f"Backup criado em: {backup_file}")
                
                # Salvar no arquivo original
                output_path = csv_file
            else:
                # Usar o arquivo de saída especificado
                output_path = output_file
                backup_file = None
            
            # Salvar o arquivo sem duplicados
            df_without_duplicates.to_csv(output_path, index=False)
            
            # Preparar resultado
            result = {
                "status": "success",
                "total_antes": total_antes,
                "total_depois": total_depois,
                "duplicados_removidos": duplicados_removidos,
                "output_file": str(output_path),
                "backup_file": str(backup_file) if backup_file else None
            }
            
            # Log do resultado
            if duplicados_removidos > 0:
                log.info(f"{duplicados_removidos} duplicados removidos com sucesso!")
            else:
                log.info(f"Nenhum duplicado encontrado para a coluna '{column}'.")
                
            return result
                
        except Exception as e:
            log.error(f"Erro ao remover duplicados: {str(e)}")
            raise

    def process_email_sending(self, csv_file: str = None, template: str = "", skip_unsubscribed_sync: bool = False, is_test_mode: bool = True) -> Dict[str, Any]:
        """
        Processa o envio de emails em lote.
        
        Args:
            csv_file: Caminho para o arquivo CSV (opcional, usa o da configuração se não fornecido)
            template: Caminho para o arquivo de template HTML
            skip_unsubscribed_sync: Se deve pular a sincronização de emails descadastrados
            is_test_mode: Se deve usar o modo de teste
            
        Returns:
            Dicionário com os resultados do envio
        """
        try:
            # Verificar configurações SMTP
            log.info(f"Servidor SMTP: {self.config.smtp_config['host']}:{self.config.smtp_config['port']}")
            log.info(f"Usuário SMTP: {self.config.smtp_config['username']}")
            
            # Determinar qual arquivo usar com base no modo
            if is_test_mode:
                test_emails_file = self.config.email_config.get("test_emails_file", "data/test_emails.csv")
                csv_path = test_emails_file
                log.info(f"MODO TESTE: Usando arquivo de teste {test_emails_file}")
            else:
                csv_path = csv_file or self.config.email_config["csv_file"]
                log.info(f"MODO PRODUÇÃO: Usando arquivo principal {csv_path}")
                
            # Usar subject do arquivo email.yaml
            email_subject = self.config.content_config.get("email", {}).get("subject", "Sem assunto")
            log.info(f"Assunto do email: {email_subject}")
            
            # Sincronizar lista de descadastros antes de enviar (a menos que seja explicitamente ignorado)
            # Só sincroniza no modo produção
            if not skip_unsubscribed_sync and not is_test_mode:
                unsubscribe_file = self.config.email_config.get("unsubscribe_file", "data/descadastros.csv")
                self.sync_unsubscribed_emails(csv_path, unsubscribe_file)
            
            csv_reader = CSVReader(csv_path, self.config.email_config["batch_size"])
            
            # Ensure template has .html extension
            if not template.endswith('.html'):
                template += '.html'
                
            # Check if the template exists in the provided path or in templates/ directory
            template_path = Path(template)
            if not template_path.exists():
                root_template_path = Path("templates") / template_path.name
                if root_template_path.exists():
                    template_path = root_template_path
                else:
                    raise FileNotFoundError(f"Template file not found: {template}")
            else:
                template_path = template_path.resolve()

            total_records = csv_reader.total_records
            if total_records == 0:
                log.warning("Nenhum email para enviar!")
                return {"status": "no_emails", "total_records": 0}
                
            log.info(f"Iniciando processo de envio de emails HTML...")
            
            # Verificar total de emails no arquivo
            total_emails_in_file = len(csv_reader.df)
            unsubscribed_count = 0
            
            # Verificar total de emails descadastrados se a coluna existir
            if 'descadastro' in csv_reader.df.columns:
                unsubscribed_count = len(csv_reader.df[csv_reader.df['descadastro'] == 'S'])
                
            already_sent = len(csv_reader.df[csv_reader.df['enviado'] == 'ok'])
            failed_count = len(csv_reader.df[csv_reader.df['falhou'] == 'ok'])
            
            # Mostrar estatísticas
            log.info(f"Total de emails na lista: {total_emails_in_file}")
            log.info(f"Emails válidos para envio: {total_records}")
            
            if unsubscribed_count > 0:
                log.info(f"Emails descadastrados (ignorados): {unsubscribed_count}")
                
            if already_sent > 0:
                log.info(f"Emails já enviados: {already_sent}")
                
            if failed_count > 0:
                log.info(f"Emails que falharam: {failed_count}")
                
            # Configurações
            start_time = time.time()
            successful = 0
            failed = 0
            current_record = 0
            batch_delay = self.config.email_config.get("batch_delay", 60)
            retry_attempts = self.config.email_config.get("retry_attempts", 5)
            retry_delay = self.config.email_config.get("retry_delay", 60)
            send_timeout = self.config.email_config.get("send_timeout", 10)
            
            # Carregar lista de emails descadastrados
            unsubscribed = self.load_unsubscribed_emails()
            
            try:
                # Configurar alarm para timeout
                class TimeoutException(Exception):
                    pass
                
                def timeout_handler(signum, frame):
                    raise TimeoutException
                
                signal.signal(signal.SIGALRM, timeout_handler)
                
                for batch in csv_reader.get_batches():
                    batch_successful = []  # Keep track of successful sends in this batch
                    batch_failed = 0  # Count failures in this batch
                    
                    for recipient in batch:
                        if recipient['email'].lower() in unsubscribed:
                            # Emails descadastrados são silenciosamente ignorados
                            continue
                        
                        attempts = 0
                        while attempts < retry_attempts:
                            try:
                                log.info(f"📧 {recipient['email']}")
                                signal.alarm(send_timeout)  # Set timeout for email sending
                                
                                # Processar o template
                                html_content = self.process_email_template(template_path, recipient, email_subject)
                                
                                # Enviar o email
                                self.send_batch([recipient], html_content, email_subject, is_html=True)
                                log.info(f"✅ {recipient['email']}")
                                
                                signal.alarm(0)  # Reset the alarm
                                successful += 1
                                batch_successful.append(recipient['email'])  # Add to successful list
                                break
                            except TimeoutException:
                                log.error(f"❌ {recipient['email']}")
                                self.register_failed_email(recipient['email'], "Timeout ao enviar email")
                                failed += 1
                                batch_failed += 1
                                break
                            except Exception as e:
                                attempts += 1
                                if attempts >= retry_attempts:
                                    log.error(f"❌ {recipient['email']}")
                                    self.register_failed_email(recipient['email'], f"Erro após {retry_attempts} tentativas: {str(e)}")
                                    failed += 1
                                    batch_failed += 1
                                else:
                                    log.warning(f"⚠️ {recipient['email']} - Tentativa {attempts}/{retry_attempts}")
                                    if retry_delay > 0:  # Only sleep if delay is greater than 0
                                        time.sleep(retry_delay)
                        
                        signal.alarm(0)  # Ensure the alarm is reset after processing
                        current_record += 1
                        
                        # Progress indication every 50 emails
                        if current_record % 50 == 0:
                            percentage = (current_record / total_records) * 100
                            log.info(f"Progresso: {current_record}/{total_records} emails processados ({percentage:.1f}%)")
                    
                    # Mark all successful emails in this batch before delay
                    for email in batch_successful:
                        csv_reader.mark_as_sent(email)
                    
                    # Summary after each batch
                    batch_size = len(batch_successful) + batch_failed
                    batch_success_rate = (len(batch_successful) / batch_size) * 100 if batch_size > 0 else 0
                    total_success_rate = (successful / current_record) * 100 if current_record > 0 else 0
                    remaining = total_records - current_record
                    
                    log.info("\nResumo do lote atual:")
                    log.info(f"✓ Enviados neste lote: {len(batch_successful)}")
                    log.info(f"✗ Falhas neste lote: {batch_failed}")
                    log.info(f"Taxa de sucesso do lote: {batch_success_rate:.1f}%")
                    log.info("\nResumo geral:")
                    log.info(f"✓ Total enviados: {successful}")
                    log.info(f"✗ Total falhas: {failed}")
                    log.info(f"Taxa de sucesso geral: {total_success_rate:.1f}%")
                    log.info(f"Faltam: {remaining} emails\n")
                    
                    # Delay between batches
                    if batch_delay > 0 and remaining > 0:  # Only sleep if delay is greater than 0 and there are more emails
                        log.info(f"Aguardando {batch_delay} segundos antes do próximo lote...")
                        time.sleep(batch_delay)

            except KeyboardInterrupt:
                log.warning("\nProcesso interrompido pelo usuário.")
                log.info("Salvando progresso...")
                # The CSVReader will handle the safe shutdown
            finally:
                # Reset signal handler
                signal.alarm(0)
            
            end_time = time.time()
            
            # Gerar relatório
            report_data = self.generate_report(start_time, end_time, total_records, successful, failed)
            
            return report_data
        
        except Exception as e:
            log.error(f"Erro no processo de envio de emails: {str(e)}")
            error_message = str(e)
            
            # Marcar todos os emails como falhados
            try:
                # Tenta obter os emails do CSV reader
                if 'csv_reader' in locals() and csv_reader is not None:
                    for batch in csv_reader.get_batches():
                        for recipient in batch:
                            self.register_failed_email(recipient['email'], f"Falha de conexão com o servidor: {error_message}")
                            log.error(f"Marcando {recipient['email']} como falha devido a erro: {error_message}")
            except Exception as inner_e:
                log.error(f"Erro ao registrar emails como falha: {str(inner_e)}")
            
            # Gerar um relatório simplificado para evitar o erro 'report_file'
            report_file = f"email_report_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            report_path = os.path.join("reports", report_file)
            
            # Garantir que o diretório de relatórios existe
            os.makedirs("reports", exist_ok=True)
            
            # Criar um relatório mínimo
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"Relatório de Erro\n")
                f.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write("-----------------------------------------\n")
                f.write(f"Erro: {error_message}\n")
            
            return {
                "status": "error", 
                "error": error_message,
                "report_file": report_file,
                "report": f"Erro: {error_message}"
            }