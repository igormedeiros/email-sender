import pandas as pd
import logging
from typing import List, Dict, Generator
from pathlib import Path
import signal
import sys
import shutil
import time
import os
from datetime import datetime

log = logging.getLogger("email_sender")

class XLSXReader:
    def __init__(self, file_path: str, batch_size: int = 100):
        self.file_path = file_path
        self.batch_size = batch_size
        self.backup_path = f"{file_path}.bak"
        self.last_save = time.time()
        self.save_interval = 300  # Save every 5 minutes
        
        # Criar backup da planilha antes de começar
        try:
            shutil.copy2(file_path, self.backup_path)
            log.info(f"Backup created: {self.backup_path}")
        except Exception as e:
            log.error(f"Failed to create backup: {str(e)}")
            raise
        
        # Registrar handler para SIGINT
        self._setup_signal_handlers()
        
        if not Path(file_path).exists():
            raise FileNotFoundError(f"XLSX file not found: {file_path}")
            
        try:
            self.df = pd.read_excel(file_path)
            
            if 'email' not in self.df.columns:
                raise ValueError("XLSX file must contain an 'email' column")
                
            if 'enviado' not in self.df.columns:
                self.df['enviado'] = ''
            else:
                self.df['enviado'] = self.df['enviado'].fillna('')
                
            if 'falhou' not in self.df.columns:
                self.df['falhou'] = ''
            else:
                self.df['falhou'] = self.df['falhou'].fillna('')
                
            # Convertendo emails para minúsculas apenas onde enviado está vazio
            mask = self.df['enviado'] == ''
            self.df.loc[mask, 'email'] = self.df.loc[mask, 'email'].str.lower()
                
            log.info(f"Successfully loaded {len(self.df)} records from {file_path}")
            
        except Exception as e:
            log.error(f"Error loading XLSX file {file_path}: {str(e)}")
            self._restore_backup()
            if os.path.exists(file_path):
                os.remove(file_path)
            raise

    def _atomic_save(self, temp_path: str, final_path: str):
        """Salva o arquivo de forma atômica usando rename"""
        try:
            self.df.to_excel(temp_path, index=False, engine='openpyxl')
            os.replace(temp_path, final_path)
            self.last_save = time.time()
            return True
        except Exception as e:
            log.error(f"Error during atomic save: {str(e)}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            return False

    def _should_save(self) -> bool:
        """Check if it's time to save based on the interval"""
        current_time = time.time()
        if current_time - self.last_save >= self.save_interval:
            self.last_save = current_time
            return True
        return False

    def _periodic_save(self):
        """Save the spreadsheet periodically"""
        if self._should_save():
            temp_path = f"{self.file_path}.temp.xlsx"
            if self._atomic_save(temp_path, self.file_path):
                log.debug(f"Auto-saved at {datetime.now().strftime('%H:%M:%S')}")

    def _setup_signal_handlers(self):
        """Configure signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            if signum == signal.SIGINT:
                log.warning("\nReceived SIGINT (Ctrl+C). Saving changes and restoring if needed...")
                self._safe_shutdown()
                sys.exit(1)
        
        signal.signal(signal.SIGINT, signal_handler)

    def _safe_shutdown(self):
        """Ensure safe shutdown and data preservation"""
        try:
            if hasattr(self, 'df'):
                temp_path = f"{self.file_path}.temp.xlsx"
                if self._atomic_save(temp_path, self.file_path):
                    log.info("Changes saved successfully before exit")
                else:
                    self._restore_backup()
            else:
                self._restore_backup()
        except Exception as e:
            log.error(f"Error during shutdown: {str(e)}")
            self._restore_backup()

    def _restore_backup(self):
        """Restaura o backup se algo der errado"""
        try:
            if Path(self.backup_path).exists():
                shutil.copy2(self.backup_path, self.file_path)
                log.info(f"Restored from backup: {self.backup_path}")
        except Exception as e:
            log.error(f"Failed to restore backup: {str(e)}")
            raise

    def cleanup(self):
        """Cleanup backup file"""
        try:
            if os.path.exists(self.backup_path):
                os.remove(self.backup_path)
                log.debug("Backup file removed")
        except Exception as e:
            log.error(f"Error removing backup file: {str(e)}")

    def __del__(self):
        """Ensure cleanup on object destruction"""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during object destruction

    def get_batches(self) -> Generator[List[Dict], None, None]:
        try:
            # Filtra apenas emails onde enviado está vazio e não está marcado como falha
            df_to_send = self.df[
                (self.df['enviado'] == '') & 
                (self.df['falhou'] != 'ok')
            ]
            total_rows = len(df_to_send)
            if (total_rows == 0):
                log.info("No emails found to send. Current status:")
                log.info(f"Total records in file: {len(self.df)}")
                log.info(f"Already sent: {len(self.df[self.df['enviado'] == 'ok'])}")
                log.info(f"Not sent (empty): {len(self.df[self.df['enviado'] == ''])}")
                log.info(f"Failed: {len(self.df[self.df['falhou'] == 'ok'])}")
                
            for i in range(0, total_rows, self.batch_size):
                batch = df_to_send.iloc[i:i + self.batch_size].to_dict('records')
                yield batch
                
        except Exception as e:
            log.error(f"Error getting batch of emails: {str(e)}")
            raise

    @property
    def total_records(self) -> int:
        try:
            # Mantém a lógica original: conta apenas registros não enviados e não falhados
            df_to_send = self.df[
                (self.df['enviado'] == '') & 
                (self.df['falhou'] != 'ok')
            ]
            return len(df_to_send)
        except Exception as e:
            log.error(f"Error counting records: {str(e)}")
            raise

    def mark_as_sent(self, email: str) -> None:
        try:
            idx = self.df[self.df['email'] == email.lower()].index
            if len(idx) > 0:
                self.df.loc[idx, 'enviado'] = 'ok'
                # Force save after marking
                temp_path = f"{self.file_path}.temp.xlsx"
                self._atomic_save(temp_path, self.file_path)
                log.debug(f"Marked {email} as sent")
            else:
                log.warning(f"Email {email} not found in spreadsheet")
        except Exception as e:
            log.error(f"Error marking email {email} as sent: {str(e)}")
            self._restore_backup()
            raise

    def mark_as_failed(self, email: str) -> None:
        try:
            idx = self.df[self.df['email'] == email.lower()].index
            if len(idx) > 0:
                self.df.loc[idx, 'falhou'] = 'ok'
                # Force save after marking
                temp_path = f"{self.file_path}.temp.xlsx"
                self._atomic_save(temp_path, self.file_path)
                log.debug(f"Marked {email} as failed")
            else:
                log.warning(f"Email {email} not found in spreadsheet")
        except Exception as e:
            log.error(f"Error marking email {email} as failed: {str(e)}")
            self._restore_backup()
            raise

    def clear_sent_flags(self) -> None:
        try:
            # Create a backup before clearing flags
            shutil.copy2(self.file_path, self.backup_path)
            
            # Limpar todas as flags
            self.df['enviado'] = ''
            self.df['falhou'] = ''
            self.df = self.df.fillna('')
            self.df.to_excel(self.file_path, index=False)
            log.info("Cleared all flags")
        except Exception as e:
            log.error(f"Error clearing flags: {str(e)}")
            self._restore_backup()
            raise