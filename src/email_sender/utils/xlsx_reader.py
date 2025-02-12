import pandas as pd
import logging
from typing import List, Dict, Generator
from pathlib import Path

log = logging.getLogger("email_sender")

class XLSXReader:
    def __init__(self, file_path: str, batch_size: int = 100):
        self.file_path = file_path
        self.batch_size = batch_size
        
        if not Path(file_path).exists():
            raise FileNotFoundError(f"XLSX file not found: {file_path}")
            
        try:
            self.df = pd.read_excel(file_path)
            
            if 'email' not in self.df.columns:
                raise ValueError("XLSX file must contain an 'email' column")
                
            # Convertendo emails para minúsculas
            self.df['email'] = self.df['email'].str.lower()
            
            # Preenchendo valores NaN com string vazia
            if 'enviado' not in self.df.columns:
                self.df['enviado'] = ''
            else:
                self.df['enviado'] = self.df['enviado'].fillna('')
                
            if 'falhou' not in self.df.columns:
                self.df['falhou'] = ''
            else:
                self.df['falhou'] = self.df['falhou'].fillna('')
                
            log.info(f"Successfully loaded {len(self.df)} records from {file_path}")
            
        except Exception as e:
            log.error(f"Error loading XLSX file {file_path}: {str(e)}")
            raise

    def get_batches(self) -> Generator[List[Dict], None, None]:
        try:
            # Filtra apenas emails não enviados
            df_to_send = self.df[
                (self.df['enviado'] != 'ok') & 
                (self.df['falhou'] != 'ok')
            ]
            total_rows = len(df_to_send)
            if total_rows == 0:
                log.info("No emails found to send. Current status:")
                log.info(f"Total records in file: {len(self.df)}")
                log.info(f"Already sent: {len(self.df[self.df['enviado'] == 'ok'])}")
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
            df_to_send = self.df[
                (self.df['enviado'] != 'ok') & 
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
                self.df.to_excel(self.file_path, index=False)
                log.debug(f"Marked {email} as sent")
            else:
                log.warning(f"Email {email} not found in spreadsheet")
        except Exception as e:
            log.error(f"Error marking email {email} as sent: {str(e)}")
            raise

    def mark_as_failed(self, email: str) -> None:
        try:
            idx = self.df[self.df['email'] == email.lower()].index
            if len(idx) > 0:
                self.df.loc[idx, 'falhou'] = 'ok'
                self.df.to_excel(self.file_path, index=False)
                log.debug(f"Marked {email} as failed")
            else:
                log.warning(f"Email {email} not found in spreadsheet")
        except Exception as e:
            log.error(f"Error marking email {email} as failed: {str(e)}")
            raise

    def clear_sent_flags(self) -> None:
        try:
            self.df['enviado'] = ''
            self.df['falhou'] = ''
            self.df = self.df.fillna('')
            self.df.to_excel(self.file_path, index=False)
            log.info("Cleared all sent and failed flags")
        except Exception as e:
            log.error(f"Error clearing flags: {str(e)}")
            raise