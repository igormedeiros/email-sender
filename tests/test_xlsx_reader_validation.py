import pytest
import pandas as pd
from pathlib import Path
from email_sender.utils.xlsx_reader import XLSXReader

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

class TestDataValidation:
    def test_nonexistent_file_raises_error(self):
        with pytest.raises(FileNotFoundError):
            XLSXReader("nonexistent.xlsx")

    def test_invalid_file_raises_error(self, tmp_path):
        invalid_file = tmp_path / "invalid.xlsx"
        invalid_file.touch()
        with pytest.raises(Exception):
            XLSXReader(str(invalid_file))

    def test_missing_email_column_raises_error(self, tmp_path):
        file_path = tmp_path / "invalid.xlsx"
        df = pd.DataFrame({'wrong_column': ['test@example.com']})
        df.to_excel(file_path, index=False)
        with pytest.raises(ValueError):
            XLSXReader(str(file_path))

class TestRecordCounting:
    @pytest.fixture(autouse=True)
    def setup(self, mock_excel_file):
        self.reader = XLSXReader(mock_excel_file)

    def test_counts_only_valid_emails(self):
        assert self.reader.total_records == 1

    def test_ignores_sent_emails(self):
        self.reader.mark_as_sent("user1@test.com")
        assert self.reader.total_records == 0

class TestDataFormatting:
    @pytest.fixture(autouse=True)
    def setup(self, mock_excel_file):
        self.reader = XLSXReader(mock_excel_file)
        self.batch = next(self.reader.get_batches())

    def test_email_is_converted_to_lowercase(self):
        assert self.batch[0]["email"] == "user1@test.com"

    def test_non_email_fields_are_preserved(self):
        assert self.batch[0]["name"] == "User 1"

class TestFlagManagement:
    @pytest.fixture(autouse=True)
    def setup(self, mock_excel_file):
        self.reader = XLSXReader(mock_excel_file)

    def test_clear_sent_flags_clears_sent_status(self):
        self.reader.clear_sent_flags()
        assert all(self.reader.df['enviado'] == '')

    def test_clear_sent_flags_with_clear_all_clears_failed_status(self):
        self.reader.clear_sent_flags(clear_all=True)
        assert all(self.reader.df['falhou'] == '')

    def test_clear_sent_flags_without_clear_all_preserves_failed_status(self):
        original_failed = self.reader.df['falhou'].copy()
        self.reader.clear_sent_flags(clear_all=False)
        assert (self.reader.df['falhou'] == original_failed).all()