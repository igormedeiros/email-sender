import pandas as pd
from typing import List, Dict, Generator

class XLSXReader:
    def __init__(self, file_path: str, batch_size: int = 100):
        self.file_path = file_path
        self.batch_size = batch_size
        self.df = pd.read_excel(file_path, usecols=['email'])

    def get_batches(self) -> Generator[List[Dict], None, None]:
        total_rows = len(self.df)
        for i in range(0, total_rows, self.batch_size):
            batch = self.df.iloc[i:i + self.batch_size].to_dict('records')
            yield batch

    @property
    def total_records(self) -> int:
        return len(self.df)