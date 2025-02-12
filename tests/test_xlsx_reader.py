import pytest
import pandas as pd
from unittest.mock import Mock, patch, mock_open
from email_sender.utils.xlsx_reader import XLSXReader
from pathlib import Path

@pytest.fixture
def mock_dataframe():
    return pd.DataFrame({
        'email': ['User1@test.com', 'user2@test.com', 'USER3@test.com'],
        'name': ['User 1', 'User 2', 'User 3'],
        'enviado': ['', 'ok', ''],
        'falhou': ['', '', 'ok']
    })

@pytest.fixture
def mock_excel_file(tmp_path, mock_dataframe):
    xlsx_file = tmp_path / "test.xlsx"
    mock_dataframe.to_excel(xlsx_file, index=False)
    return str(xlsx_file)

@patch('pandas.DataFrame.to_excel')  # Mock the save operation
def test_xlsx_reader_total_records(mock_to_excel, mock_excel_file):
    reader = XLSXReader(mock_excel_file)
    assert reader.total_records == 1  # Only one record not marked as sent/failed
    mock_to_excel.assert_not_called()

@patch('pandas.DataFrame.to_excel')  # Mock the save operation
def test_xlsx_reader_batch_size(mock_to_excel, mock_excel_file):
    reader = XLSXReader(mock_excel_file, batch_size=2)
    batches = list(reader.get_batches())
    
    assert len(batches) == 1  # Only one batch because only one email is not sent/failed
    assert len(batches[0]) == 1  # First batch has 1 record
    mock_to_excel.assert_not_called()

@patch('pandas.DataFrame.to_excel')  # Mock the save operation
def test_xlsx_reader_data_content(mock_to_excel, mock_excel_file):
    reader = XLSXReader(mock_excel_file)
    batch = next(reader.get_batches())
    
    # Verifica se o email foi convertido para minúsculas
    assert batch[0]["email"] == "user1@test.com"
    assert batch[0]["name"] == "User 1"
    mock_to_excel.assert_not_called()

@patch('pandas.DataFrame.to_excel')  # Mock the save operation
def test_xlsx_reader_mark_as_sent(mock_to_excel, mock_excel_file):
    reader = XLSXReader(mock_excel_file)
    reader.mark_as_sent("user1@test.com")
    
    # Verify the DataFrame was updated
    assert reader.df.loc[reader.df['email'] == 'user1@test.com', 'enviado'].iloc[0] == 'ok'
    mock_to_excel.assert_called_once()

@patch('pandas.DataFrame.to_excel')  # Mock the save operation
def test_xlsx_reader_mark_as_failed(mock_to_excel, mock_excel_file):
    reader = XLSXReader(mock_excel_file)
    reader.mark_as_failed("user1@test.com")
    
    # Verify the DataFrame was updated
    assert reader.df.loc[reader.df['email'] == 'user1@test.com', 'falhou'].iloc[0] == 'ok'
    mock_to_excel.assert_called_once()

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