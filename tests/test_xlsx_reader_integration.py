import pytest
import pandas as pd
from pathlib import Path
from email_sender.utils.xlsx_reader import XLSXReader

@pytest.fixture
def sample_xlsx(tmp_path):
    """Create a sample XLSX file for testing"""
    file_path = tmp_path / "test.xlsx"
    df = pd.DataFrame({
        'email': ['test1@example.com', 'test2@example.com', 'test3@example.com'],
        'enviado': ['', '', 'ok'],
        'falhou': ['', 'ok', '']
    })
    df.to_excel(file_path, index=False)
    return str(file_path)

def test_initialization_with_real_file(sample_xlsx):
    reader = XLSXReader(sample_xlsx)
    assert reader.total_records == 1

def test_batches_with_real_file(sample_xlsx):
    reader = XLSXReader(sample_xlsx, batch_size=2)
    batches = list(reader.get_batches())
    assert len(batches[0]) == 1

def test_mark_as_sent_with_real_file(sample_xlsx):
    reader = XLSXReader(sample_xlsx)
    reader.mark_as_sent('test1@example.com')
    assert reader.total_records == 0

def test_mark_as_failed_with_real_file(sample_xlsx):
    reader = XLSXReader(sample_xlsx)
    reader.mark_as_failed('test1@example.com')
    assert reader.total_records == 0

def test_clear_flags_preserves_failed_status_with_real_file(sample_xlsx):
    reader = XLSXReader(sample_xlsx)
    reader.clear_sent_flags(clear_all=False)
    assert reader.total_records == 2

def test_backup_file_is_created(sample_xlsx):
    reader = XLSXReader(sample_xlsx)
    assert Path(f"{sample_xlsx}.bak").exists()

def test_case_insensitive_email_handling(sample_xlsx):
    reader = XLSXReader(sample_xlsx)
    reader.mark_as_sent('TEST1@EXAMPLE.COM')
    assert reader.total_records == 0

def test_backup_cleanup(sample_xlsx):
    reader = XLSXReader(sample_xlsx)
    backup_path = f"{sample_xlsx}.bak"
    reader = XLSXReader(sample_xlsx)
    assert Path(backup_path).exists()
    reader.cleanup()
    assert not Path(backup_path).exists()

@pytest.mark.parametrize("email,expected_records", [
    ("test1@example.com", 0),
    ("nonexistent@example.com", 1),
])
def test_mark_as_sent_with_different_emails(sample_xlsx, email, expected_records):
    reader = XLSXReader(sample_xlsx)
    reader.mark_as_sent(email)
    assert reader.total_records == expected_records