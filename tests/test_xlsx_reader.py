import pytest
import pandas as pd
from unittest.mock import Mock, patch, mock_open, ANY
from email_sender.utils.xlsx_reader import XLSXReader
from pathlib import Path
import signal
import os
import time

@pytest.fixture
def mock_dataframe():
    return pd.DataFrame({
        'email': ['User1@test.com', 'user2@test.com', 'USER3@test.com', 'user4@test.com'],
        'name': ['User 1', 'User 2', 'User 3', 'User 4'],
        'enviado': ['', 'ok', '', 'ok'],
        'falhou': ['', '', 'ok', '']
    })

@pytest.fixture
def mock_excel_file(tmp_path, mock_dataframe):
    xlsx_file = tmp_path / "test.xlsx"
    mock_dataframe.to_excel(xlsx_file, index=False)
    return str(xlsx_file)

@pytest.fixture(autouse=True)
def cleanup_files(tmp_path):
    yield
    # Clean up any temporary files after each test
    for file in tmp_path.glob("*.xlsx*"):
        try:
            file.unlink()
        except:
            pass

@patch('signal.signal')  # Mock signal registration
@patch('shutil.copy2')  # Mock backup creation
@patch('pandas.DataFrame.to_excel')  # Mock the save operation
@patch('os.replace')  # Mock atomic rename
@patch('os.remove')  # Mock file removal
def test_xlsx_reader_atomic_save(mock_remove, mock_replace, mock_to_excel, mock_copy, mock_signal, mock_excel_file):
    reader = XLSXReader(mock_excel_file)
    with patch('os.path.exists', return_value=True):  # Simulate temp file exists
        reader.mark_as_sent("user1@test.com")
        mock_to_excel.assert_called_once_with(ANY, index=False, engine='openpyxl')
        mock_replace.assert_called_once()
        reader.cleanup()

@patch('signal.signal')
@patch('shutil.copy2')
@patch('pandas.DataFrame.to_excel')
@patch('os.replace')
@patch('time.time')
def test_xlsx_reader_periodic_save(mock_time, mock_replace, mock_to_excel, mock_copy, mock_signal, mock_excel_file):
    # Simulate time passing for periodic save
    mock_time.side_effect = [0, 301, 302]  # First call returns 0, second call returns time > save_interval
    
    reader = XLSXReader(mock_excel_file)
    reader.mark_as_sent("user1@test.com")
    
    # Verify periodic save was triggered
    assert mock_to_excel.call_count >= 1
    assert mock_replace.call_count >= 1

@patch('signal.signal')
@patch('shutil.copy2')
@patch('pandas.DataFrame.to_excel')
@patch('os.replace')
def test_xlsx_reader_handles_interruption(mock_replace, mock_to_excel, mock_copy, mock_signal, mock_excel_file):
    reader = XLSXReader(mock_excel_file)
    
    # Simulate SIGINT
    signal_handler = mock_signal.call_args[0][1]  # Get the registered signal handler
    with pytest.raises(SystemExit):
        signal_handler(signal.SIGINT, None)
    
    # Verify safe shutdown was attempted
    assert mock_to_excel.call_count >= 1
    assert mock_replace.call_count >= 1

@patch('signal.signal')
@patch('shutil.copy2')
@patch('pandas.DataFrame.to_excel')
@patch('os.replace')
def test_xlsx_reader_save_failure_restores_backup(mock_replace, mock_to_excel, mock_copy, mock_signal, mock_excel_file):
    mock_to_excel.side_effect = Exception("Save failed")
    reader = XLSXReader(mock_excel_file)
    
    reader.mark_as_sent("user1@test.com")
    
    # Verify backup was restored
    assert mock_copy.call_count >= 1  # Initial backup + restore

@patch('signal.signal')
@patch('shutil.copy2')
@patch('os.remove')
@patch('os.path.exists')
def test_xlsx_reader_creates_backup(mock_exists, mock_remove, mock_copy, mock_signal, mock_excel_file):
    mock_exists.return_value = True
    reader = XLSXReader(mock_excel_file)
    mock_copy.assert_called_once_with(mock_excel_file, f"{mock_excel_file}.bak")
    reader.cleanup()
    mock_remove.assert_called_once()

@patch('signal.signal')
@patch('shutil.copy2')
@patch('os.remove')
@patch('os.path.exists')
def test_xlsx_reader_cleanup_on_exit(mock_exists, mock_remove, mock_copy, mock_signal, mock_excel_file):
    mock_exists.return_value = True
    reader = XLSXReader(mock_excel_file)
    backup_path = f"{mock_excel_file}.bak"
    reader.cleanup()
    mock_remove.assert_called_once()

@patch('pandas.DataFrame.to_excel')  # Mock the save operation
def test_xlsx_reader_total_records(mock_to_excel, mock_excel_file):
    reader = XLSXReader(mock_excel_file)
    # Should only count records where enviado is empty and falhou is not 'ok'
    assert reader.total_records == 1  # Only User1 is not sent and not failed
    mock_to_excel.assert_not_called()

@patch('pandas.DataFrame.to_excel')  # Mock the save operation
def test_xlsx_reader_batch_size(mock_to_excel, mock_excel_file):
    reader = XLSXReader(mock_excel_file, batch_size=2)
    batches = list(reader.get_batches())
    
    assert len(batches) == 1  # Only one batch because only one email is valid
    assert len(batches[0]) == 1  # First batch has 1 record (User1)
    mock_to_excel.assert_not_called()

@patch('pandas.DataFrame.to_excel')  # Mock the save operation
def test_xlsx_reader_data_content(mock_to_excel, mock_excel_file):
    reader = XLSXReader(mock_excel_file)
    batch = next(reader.get_batches())
    
    # Should only get User1 as it's the only one not sent and not failed
    assert batch[0]["email"] == "user1@test.com"  # Should be lowercase
    assert batch[0]["name"] == "User 1"
    mock_to_excel.assert_not_called()

@patch('pandas.DataFrame.to_excel')  # Mock the save operation
def test_xlsx_reader_mark_as_sent(mock_to_excel, mock_excel_file):
    reader = XLSXReader(mock_excel_file)
    with patch('os.replace') as mock_replace:
        reader.mark_as_sent("user1@test.com")
        assert mock_to_excel.call_count == 1
        assert mock_replace.call_count == 1

@patch('pandas.DataFrame.to_excel')  # Mock the save operation
def test_xlsx_reader_mark_as_failed(mock_to_excel, mock_excel_file):
    reader = XLSXReader(mock_excel_file)
    with patch('os.replace') as mock_replace:
        reader.mark_as_failed("user1@test.com")
        assert mock_to_excel.call_count == 1
        assert mock_replace.call_count == 1

@patch('pandas.DataFrame.to_excel')  # Mock the save operation
def test_xlsx_reader_clear_sent_flags(mock_to_excel, mock_excel_file):
    reader = XLSXReader(mock_excel_file)
    reader.clear_sent_flags()
    
    # Verify all flags were cleared
    assert all(reader.df['enviado'] == '')
    assert all(reader.df['falhou'] == '')
    mock_to_excel.assert_called_once()

def test_xlsx_reader_file_not_found():
    with pytest.raises(FileNotFoundError):
        XLSXReader("nonexistent.xlsx")

def test_xlsx_reader_invalid_file(tmp_path):
    # Create an empty file
    invalid_file = tmp_path / "invalid.xlsx"
    invalid_file.touch()
    
    with pytest.raises(Exception):
        XLSXReader(str(invalid_file))

@patch('pandas.DataFrame.to_excel')  # Mock the save operation
def test_xlsx_reader_only_processes_empty_enviado(mock_to_excel, mock_excel_file):
    reader = XLSXReader(mock_excel_file)
    all_batches = list(reader.get_batches())
    all_emails = [item['email'] for batch in all_batches for item in batch]
    
    # Should only contain User1, as it's the only one with empty 'enviado' and not failed
    assert len(all_emails) == 1
    assert 'user1@test.com' in all_emails
    assert 'user2@test.com' not in all_emails  # Already sent
    assert 'user3@test.com' not in all_emails  # Failed
    assert 'user4@test.com' not in all_emails  # Already sent

import pytest
import pandas as pd
import os
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

def test_xlsx_reader_initialization(sample_xlsx):
    reader = XLSXReader(sample_xlsx)
    assert reader.total_records == 1  # Only one email should be available to send

def test_get_batches(sample_xlsx):
    reader = XLSXReader(sample_xlsx, batch_size=2)
    batches = list(reader.get_batches())
    assert len(batches) == 1
    assert len(batches[0]) == 1
    assert batches[0][0]['email'] == 'test1@example.com'

def test_mark_as_sent(sample_xlsx):
    reader = XLSXReader(sample_xlsx)
    reader.mark_as_sent('test1@example.com')
    assert reader.total_records == 0

def test_mark_as_failed(sample_xlsx):
    reader = XLSXReader(sample_xlsx)
    reader.mark_as_failed('test1@example.com')
    assert reader.total_records == 0

def test_clear_sent_flags(sample_xlsx):
    reader = XLSXReader(sample_xlsx)
    reader.clear_sent_flags(clear_all=False)  # Preserve failed status
    assert reader.total_records == 2  # test2@example.com was marked as failed

def test_backup_creation(sample_xlsx):
    reader = XLSXReader(sample_xlsx)
    assert Path(f"{sample_xlsx}.bak").exists()

def test_case_insensitive_email(sample_xlsx):
    reader = XLSXReader(sample_xlsx)
    reader.mark_as_sent('TEST1@EXAMPLE.COM')
    assert reader.total_records == 0

def test_invalid_file():
    with pytest.raises(FileNotFoundError):
        XLSXReader("nonexistent.xlsx")

def test_missing_email_column(tmp_path):
    file_path = tmp_path / "invalid.xlsx"
    df = pd.DataFrame({'wrong_column': ['test@example.com']})
    df.to_excel(file_path, index=False)
    
    with pytest.raises(ValueError):
        XLSXReader(str(file_path))

def test_cleanup(sample_xlsx):
    reader = XLSXReader(sample_xlsx)
    backup_path = f"{sample_xlsx}.bak"
    assert Path(backup_path).exists()
    reader.cleanup()
    assert not Path(backup_path).exists()

@pytest.mark.parametrize("email,expected_records", [
    ("test1@example.com", 0),
    ("nonexistent@example.com", 1),
])
def test_mark_as_sent_different_emails(sample_xlsx, email, expected_records):
    reader = XLSXReader(sample_xlsx)
    reader.mark_as_sent(email)
    assert reader.total_records == expected_records

@patch('signal.signal')
@patch('shutil.copy2')
@patch('pandas.read_excel')
@patch('os.remove')
@patch('os.path.exists')
def test_xlsx_reader_restores_on_error(mock_exists, mock_remove, mock_read_excel, mock_copy, mock_signal, mock_excel_file):
    mock_exists.return_value = True
    mock_read_excel.side_effect = Exception("Test error")
    with pytest.raises(Exception):
        XLSXReader(mock_excel_file)
    mock_copy.assert_called_once()
    mock_remove.assert_called_once()