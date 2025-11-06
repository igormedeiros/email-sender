import logging
import time
from typing import Dict, Any

from .config import Config
from .smtp_manager import SmtpManager
from .db import Database

log = logging.getLogger("email_sender")


class EmailService:
    """Serviço de envio de emails SIMPLIFICADO seguindo princípios KISS."""
    
    def __init__(self, config: Config, db: Database, smtp: SmtpManager):
        self.config = config
        self.db = db
        self.smtp = smtp
        self._sent_contacts = set()

    def send_batch(self, message_id: int, dry_run: bool = False) -> Dict[str, Any]:
        """
        Envia emails em lote de forma simples e direta.

        Args:
            message_id: ID da mensagem a ser enviada (não usado por enquanto)
            dry_run: Se True, não envia emails de verdade

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
            log.info(f"Iniciando envio (dry_run={dry_run})")
            
            # 1. Conectar ao banco
            self.db.connect()
            
            # 2. Buscar contatos com tag 'Test' (simples!)
            contacts = self.db._conn.execute('''
                SELECT DISTINCT tc.id, tc.email 
                FROM tbl_contacts tc 
                JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id 
                JOIN tbl_tags tg ON ctg.tag_id = tg.id 
                WHERE LOWER(tg.tag_name) = 'test'
                AND tc.email IS NOT NULL
                AND tc.email <> ''
                AND tc.unsubscribed = FALSE
                LIMIT 1000
            ''').fetchall()
            
            if not contacts:
                log.warning("Nenhum contato encontrado")
                return result
            
            log.info(f"Encontrados {len(contacts)} contatos")
            
            # 3. Conectar SMTP
            self.smtp.connect()
            
            # 4. Enviar para cada contato
            batch_size = self.config.email_config.get('batch_size', 200)
            batch_delay = self.config.email_config.get('batch_delay', 5)
            
            for i, contact in enumerate(contacts):
                contact_id = contact[0]
                email = contact[1]
                result['total_processed'] += 1
                
                # Pular se já enviou
                if contact_id in self._sent_contacts:
                    continue
                
                try:
                    # Enviar!
                    if not dry_run:
                        self.smtp.send_email(
                            to_email=email,
                            subject="Teste - Treineinsite",
                            content="<p>Email de teste</p>",
                            is_html=True
                        )
                    
                    self._sent_contacts.add(contact_id)
                    result['sent'] += 1
                    log.info(f"✅ {email}")
                    
                except Exception as e:
                    result['failed'] += 1
                    result['errors'].append(f"{email}: {str(e)}")
                    log.error(f"❌ {email}: {e}")
                
                # Pausa entre lotes
                if (i + 1) % batch_size == 0 and i + 1 < len(contacts):
                    log.info(f"Aguardando {batch_delay}s...")
                    time.sleep(batch_delay)
            
            # 5. Desconectar
            self.smtp.disconnect()
            log.info(f"✅ Envio concluído: {result['sent']} enviados, {result['failed']} falhas")
            
            return result
            
        except Exception as e:
            log.error(f"Erro: {e}")
            result['errors'].append(str(e))
            return result
