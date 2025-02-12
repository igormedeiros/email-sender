import pytest
import pandas as pd
from src.email_sender.utils.xlsx_reader import XLSXReader

@pytest.fixture
def sample_xlsx_file(tmp_path):
    data = {
        'email': ['user1@test.com', 'user2@test.com', 'user3@test.com'],
        'name': ['User 1', 'User 2', 'User 3']
    }
    df = pd.DataFrame(data)
    xlsx_file = tmp_path / "test.xlsx"
    df.to_excel(xlsx_file, index=False)
    return str(xlsx_file)

def test_xlsx_reader_total_records(sample_xlsx_file):
    reader = XLSXReader(sample_xlsx_file)
    assert reader.total_records == 3

def test_xlsx_reader_batch_size(sample_xlsx_file):
    reader = XLSXReader(sample_xlsx_file, batch_size=2)
    batches = list(reader.get_batches())
    
    assert len(batches) == 2
    assert len(batches[0]) == 2  # First batch has 2 records
    assert len(batches[1]) == 1  # Second batch has 1 record

def test_xlsx_reader_data_content(sample_xlsx_file):
    reader = XLSXReader(sample_xlsx_file)
    batch = next(reader.get_batches())
    
    assert batch[0]["email"] == "user1@test.com"
    assert batch[0]["name"] == "User 1"