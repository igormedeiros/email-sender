import pytest
import pandas as pd
from unittest.mock import patch, ANY
from email_sender.utils.xlsx_reader import XLSXReader
import signal
import os

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

class TestAtomicSave:
    @patch('signal.signal')
    @patch('shutil.copy2')
    @patch('pandas.DataFrame.to_excel')
    @patch('os.replace')
    @patch('os.remove')
    def test_calls_to_excel(self, mock_remove, mock_replace, mock_to_excel, mock_copy, mock_signal, mock_excel_file):
        reader = XLSXReader(mock_excel_file)
        with patch('os.path.exists', return_value=True):
            reader.mark_as_sent("user1@test.com")
            mock_to_excel.assert_called_once_with(ANY, index=False, engine='openpyxl')

    @patch('signal.signal')
    @patch('shutil.copy2')
    @patch('pandas.DataFrame.to_excel')
    @patch('os.replace')
    @patch('os.remove')
    def test_performs_atomic_rename(self, mock_remove, mock_replace, mock_to_excel, mock_copy, mock_signal, mock_excel_file):
        reader = XLSXReader(mock_excel_file)
        with patch('os.path.exists', return_value=True):
            reader.mark_as_sent("user1@test.com")
            mock_replace.assert_called_once()

class TestPeriodicSave:
    @patch('signal.signal')
    @patch('shutil.copy2')
    @patch('pandas.DataFrame.to_excel')
    @patch('os.replace')
    @patch('time.time')
    def test_triggers_to_excel(self, mock_time, mock_replace, mock_to_excel, mock_copy, mock_signal, mock_excel_file):
        mock_time.side_effect = [0, 301, 302]
        reader = XLSXReader(mock_excel_file)
        reader.mark_as_sent("user1@test.com")
        assert mock_to_excel.call_count >= 1

    @patch('signal.signal')
    @patch('shutil.copy2')
    @patch('pandas.DataFrame.to_excel')
    @patch('os.replace')
    @patch('time.time')
    def test_performs_atomic_rename(self, mock_time, mock_replace, mock_to_excel, mock_copy, mock_signal, mock_excel_file):
        mock_time.side_effect = [0, 301, 302]
        reader = XLSXReader(mock_excel_file)
        reader.mark_as_sent("user1@test.com")
        assert mock_replace.call_count >= 1

class TestInterruption:
    @patch('signal.signal')
    @patch('shutil.copy2')
    @patch('pandas.DataFrame.to_excel')
    @patch('os.replace')
    def test_raises_system_exit(self, mock_replace, mock_to_excel, mock_copy, mock_signal, mock_excel_file):
        reader = XLSXReader(mock_excel_file)
        signal_handler = mock_signal.call_args[0][1]
        with pytest.raises(SystemExit):
            signal_handler(signal.SIGINT, None)

    @patch('signal.signal')
    @patch('shutil.copy2')
    @patch('pandas.DataFrame.to_excel')
    @patch('os.replace')
    def test_triggers_save(self, mock_replace, mock_to_excel, mock_copy, mock_signal, mock_excel_file):
        reader = XLSXReader(mock_excel_file)
        signal_handler = mock_signal.call_args[0][1]
        try:
            signal_handler(signal.SIGINT, None)
        except SystemExit:
            pass
        assert mock_to_excel.call_count >= 1

class TestSaveFailure:
    @patch('signal.signal')
    @patch('shutil.copy2')
    @patch('pandas.DataFrame.to_excel')
    @patch('os.replace')
    def test_creates_backup(self, mock_replace, mock_to_excel, mock_copy, mock_signal, mock_excel_file):
        mock_to_excel.side_effect = Exception("Save failed")
        reader = XLSXReader(mock_excel_file)
        reader.mark_as_sent("user1@test.com")
        assert mock_copy.call_count >= 1

class TestBackupManagement:
    @patch('signal.signal')
    @patch('shutil.copy2')
    @patch('os.remove')
    @patch('os.path.exists')
    def test_initialization_creates_backup(self, mock_exists, mock_remove, mock_copy, mock_signal, mock_excel_file):
        mock_exists.return_value = True
        reader = XLSXReader(mock_excel_file)
        mock_copy.assert_called_once_with(mock_excel_file, f"{mock_excel_file}.bak")

    @patch('signal.signal')
    @patch('shutil.copy2')
    @patch('os.remove')
    @patch('os.path.exists')
    def test_cleanup_removes_backup(self, mock_exists, mock_remove, mock_copy, mock_signal, mock_excel_file):
        mock_exists.return_value = True
        reader = XLSXReader(mock_excel_file)
        reader.cleanup()
        mock_remove.assert_called_once()