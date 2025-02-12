import pytest
import pandas as pd
from email_sender.utils.csv_reader import CSVReader

@pytest.fixture
def sample_csv_file(tmp_path):
    df = pd.DataFrame({
        'email': ['user1@test.com', 'user2@test.com', 'user3@test.com'],
        'name': ['User 1', 'User 2', 'User 3']
    })
    csv_file = tmp_path / "test.csv"
    df.to_csv(csv_file, index=False)
    return str(csv_file)

def test_csv_reader_total_records(sample_csv_file):
    reader = CSVReader(sample_csv_file)
    assert reader.total_records == 3

def test_csv_reader_batch_size(sample_csv_file):
    reader = CSVReader(sample_csv_file, batch_size=2)
    batches = list(reader.get_batches())
    
    assert len(batches) == 2
    assert len(batches[0]) == 2  # First batch has 2 records
    assert len(batches[1]) == 1  # Second batch has 1 record

def test_csv_reader_data_content(sample_csv_file):
    reader = CSVReader(sample_csv_file)
    batch = next(reader.get_batches())
    
    assert batch[0]["email"] == "user1@test.com"
    assert batch[0]["name"] == "User 1"