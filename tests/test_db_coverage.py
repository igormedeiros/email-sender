"""Additional tests for database module to improve coverage."""

import pytest
import tempfile
from unittest.mock import patch, MagicMock
from email_sender.db import Database, _prepare_sql, _load_sql_file, _strip_sql_comments
from pathlib import Path


def test_load_sql_file():
    """Test _load_sql_file function."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write("SELECT * FROM test_table;")
        sql_path = Path(f.name)
    
    try:
        content = _load_sql_file(sql_path)
        assert content == "SELECT * FROM test_table;"
    finally:
        sql_path.unlink()


def test_load_sql_file_not_found():
    """Test _load_sql_file function with non-existent file."""
    with pytest.raises(FileNotFoundError):
        _load_sql_file("/nonexistent/file.sql")


def test_strip_sql_comments():
    """Test _strip_sql_comments function."""
    sql_with_comments = """
    -- This is a single line comment
    SELECT * FROM test_table; /* This is a block comment */
    -- Another single line comment
    WHERE id = 1;
    """
    
    cleaned_sql = _strip_sql_comments(sql_with_comments)
    # Should remove comments but preserve SQL
    assert "-- This is a single line comment" not in cleaned_sql
    assert "/* This is a block comment */" not in cleaned_sql
    assert "SELECT * FROM test_table;" in cleaned_sql
    assert "WHERE id = 1;" in cleaned_sql


def test_prepare_sql():
    """Test _prepare_sql function."""
    sql_text = "SELECT * FROM test_table WHERE id = $1 AND name = $2;"
    params = ["123", "test_name"]
    
    prepared_sql, expanded_params = _prepare_sql(sql_text, params)
    
    # Should convert $1, $2 to %s
    assert prepared_sql == "SELECT * FROM test_table WHERE id = %s AND name = %s;"
    assert expanded_params == ("123", "test_name")


def test_prepare_sql_with_n8n_placeholder():
    """Test _prepare_sql function with n8n placeholder."""
    sql_text = "SELECT * FROM test_table WHERE email = {{ $json.query.email }};"
    params = ["test@example.com"]
    
    prepared_sql, expanded_params = _prepare_sql(sql_text, params)
    
    # Should convert n8n placeholder to %s
    assert prepared_sql == "SELECT * FROM test_table WHERE email = %s;"
    assert expanded_params == ("test@example.com",)


def test_prepare_sql_with_mixed_placeholders():
    """Test _prepare_sql function with mixed placeholders."""
    sql_text = "SELECT * FROM test_table WHERE id = $1 AND email = {{ $json.query.email }} AND name = $2;"
    # According to current implementation:
    # $1 (index 1) gets params[0] = "123"
    # $2 (index 2) gets params[1] = "test_name"
    # {{ $json.query.email }} gets params[2] = "test@example.com" (taken from tail)
    params = ["123", "test_name", "test@example.com"]
    
    prepared_sql, expanded_params = _prepare_sql(sql_text, params)
    
    # Should convert both $n and n8n placeholders to %s
    assert prepared_sql == "SELECT * FROM test_table WHERE id = %s AND email = %s AND name = %s;"
    # Current implementation ordering:
    assert expanded_params == ("123", "test_name", "test@example.com")


def test_database_initialization():
    """Test Database class initialization."""
    mock_config = MagicMock()
    mock_config.postgres_config = {
        "host": "localhost",
        "port": 5432,
        "user": "testuser",
        "password": "testpass",
        "database": "testdb"
    }
    
    db = Database(mock_config)
    assert db._config == mock_config
    assert db._conn is None


def test_database_context_manager():
    """Test Database context manager."""
    mock_config = MagicMock()
    mock_config.postgres_config = {
        "host": "localhost",
        "port": 5432,
        "user": "testuser",
        "password": "testpass",
        "database": "testdb"
    }
    
    with patch('psycopg.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.close = MagicMock()
        
        with Database(mock_config) as db:
            assert db._conn is not None
        
        # Should close connection when exiting context
        mock_conn.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])