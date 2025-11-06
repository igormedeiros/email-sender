"""
Testes unitários para o módulo de banco de dados.
"""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import psycopg
import pytest

from src.email_sender.config import Config
from src.email_sender.db import Database, _load_sql_file, _prepare_sql


class TestDatabaseHelpers:
    """Testes para funções auxiliares do módulo db."""

    def test_load_sql_file_exists(self, temp_dir):
        """Testa carregamento de arquivo SQL existente."""
        sql_content = "SELECT * FROM test_table;"
        sql_file = temp_dir / "test.sql"
        sql_file.write_text(sql_content)

        result = _load_sql_file(str(sql_file))
        assert result == sql_content

    def test_load_sql_file_not_exists(self):
        """Testa erro ao carregar arquivo SQL inexistente."""
        with pytest.raises(FileNotFoundError):
            _load_sql_file("/nonexistent/file.sql")

    def test_prepare_sql_simple(self):
        """Testa preparação de SQL simples."""
        sql = "SELECT * FROM users WHERE id = $1"
        params = (123,)

        prepared_sql, expanded_params = _prepare_sql(sql, params)
        assert prepared_sql == "SELECT * FROM users WHERE id = %s"
        assert expanded_params == (123,)

    def test_prepare_sql_multiple_params(self):
        """Testa preparação de SQL com múltiplos parâmetros."""
        sql = "SELECT * FROM users WHERE id = $1 AND name = $2"
        params = (123, "John")

        prepared_sql, expanded_params = _prepare_sql(sql, params)
        assert prepared_sql == "SELECT * FROM users WHERE id = %s AND name = %s"
        assert expanded_params == (123, "John")

    def test_prepare_sql_repeated_params(self):
        """Testa preparação de SQL com parâmetros repetidos."""
        sql = "SELECT * FROM users WHERE id = $1 OR parent_id = $1"
        params = (123,)

        prepared_sql, expanded_params = _prepare_sql(sql, params)
        assert prepared_sql == "SELECT * FROM users WHERE id = %s OR parent_id = %s"
        assert expanded_params == (123, 123)

    def test_prepare_sql_no_params(self):
        """Testa preparação de SQL sem parâmetros."""
        sql = "SELECT * FROM users"

        prepared_sql, expanded_params = _prepare_sql(sql, ())
        assert prepared_sql == "SELECT * FROM users"
        assert expanded_params == ()

    def test_prepare_sql_comments_stripped(self):
        """Testa que comentários são removidos do SQL."""
        sql = """
        -- This is a comment
        SELECT * FROM users -- inline comment
        WHERE id = $1 /* block comment */
        """

        prepared_sql, expanded_params = _prepare_sql(sql, (123,))
        # Comments should be stripped
        assert "--" not in prepared_sql
        assert "/*" not in prepared_sql
        assert "*/" not in prepared_sql
        assert prepared_sql.strip() == "SELECT * FROM users WHERE id = %s"


class TestDatabase:
    """Testes para a classe Database."""

    def test_database_initialization(self, mock_config):
        """Testa inicialização da classe Database."""
        db = Database(mock_config)
        assert db._config == mock_config
        assert db._conn is None

    @patch('psycopg.connect')
    def test_database_connect(self, mock_connect, mock_config, mock_db_connection):
        """Testa conexão com o banco."""
        mock_conn, mock_cursor = mock_db_connection
        mock_connect.return_value = mock_conn

        db = Database(mock_config)
        db.connect()

        assert db._conn == mock_conn
        mock_connect.assert_called_once()

    @patch('psycopg.connect')
    def test_database_connect_already_connected(self, mock_connect, mock_config, mock_db_connection):
        """Testa que connect() não faz nada se já conectado."""
        mock_conn, mock_cursor = mock_db_connection
        mock_connect.return_value = mock_conn

        db = Database(mock_config)
        db._conn = mock_conn

        db.connect()

        # connect() não deve ser chamado novamente
        mock_connect.assert_not_called()

    @patch('psycopg.connect')
    def test_database_close(self, mock_connect, mock_config, mock_db_connection):
        """Testa fechamento da conexão."""
        mock_conn, mock_cursor = mock_db_connection
        mock_connect.return_value = mock_conn

        db = Database(mock_config)
        db._conn = mock_conn

        db.close()

        mock_conn.close.assert_called_once()
        assert db._conn is None

    @patch('psycopg.connect')
    def test_database_close_no_connection(self, mock_connect, mock_config):
        """Testa fechamento quando não há conexão."""
        db = Database(mock_config)
        db._conn = None

        # Não deve dar erro
        db.close()

    @patch('psycopg.connect')
    def test_database_context_manager(self, mock_connect, mock_config, mock_db_connection):
        """Testa uso como context manager."""
        mock_conn, mock_cursor = mock_db_connection
        mock_connect.return_value = mock_conn

        db = Database(mock_config)

        with db as db_instance:
            assert db_instance == db
            assert db._conn == mock_conn

        mock_conn.close.assert_called_once()

    @patch('psycopg.connect')
    def test_database_fetch_one_success(self, mock_connect, mock_config, mock_db_connection):
        """Testa fetch_one com sucesso."""
        mock_conn, mock_cursor = mock_db_connection
        mock_connect.return_value = mock_conn

        # Mock do resultado
        mock_row = {"id": 1, "name": "Test"}
        mock_cursor.fetchone.return_value = mock_row

        db = Database(mock_config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("SELECT * FROM test_table WHERE id = $1")
            sql_file = f.name

        try:
            result = db.fetch_one(sql_file, (1,))

            assert result == mock_row
            mock_cursor.execute.assert_called_once()
        finally:
            Path(sql_file).unlink()

    @patch('psycopg.connect')
    def test_database_fetch_one_no_results(self, mock_connect, mock_config, mock_db_connection):
        """Testa fetch_one sem resultados."""
        mock_conn, mock_cursor = mock_db_connection
        mock_connect.return_value = mock_conn

        mock_cursor.fetchone.return_value = None

        db = Database(mock_config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("SELECT * FROM test_table WHERE id = $1")
            sql_file = f.name

        try:
            result = db.fetch_one(sql_file, (999,))

            assert result is None
            mock_cursor.execute.assert_called_once()
        finally:
            Path(sql_file).unlink()

    @patch('psycopg.connect')
    def test_database_fetch_one_error(self, mock_connect, mock_config, mock_db_connection):
        """Testa fetch_one com erro."""
        mock_conn, mock_cursor = mock_db_connection
        mock_connect.return_value = mock_conn

        mock_cursor.execute.side_effect = Exception("Database error")

        db = Database(mock_config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("SELECT * FROM test_table WHERE id = $1")
            sql_file = f.name

        try:
            with pytest.raises(RuntimeError, match="DB fetch_one failed"):
                db.fetch_one(sql_file, (1,))
        finally:
            Path(sql_file).unlink()

    @patch('psycopg.connect')
    def test_database_fetch_all_success(self, mock_connect, mock_config, mock_db_connection):
        """Testa fetch_all com sucesso."""
        mock_conn, mock_cursor = mock_db_connection
        mock_connect.return_value = mock_conn

        # Mock dos resultados
        mock_rows = [{"id": 1, "name": "Test1"}, {"id": 2, "name": "Test2"}]
        mock_cursor.fetchall.return_value = mock_rows

        db = Database(mock_config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("SELECT * FROM test_table")
            sql_file = f.name

        try:
            result = db.fetch_all(sql_file)

            assert result == mock_rows
            mock_cursor.execute.assert_called_once()
        finally:
            Path(sql_file).unlink()

    @patch('psycopg.connect')
    def test_database_execute_success(self, mock_connect, mock_config, mock_db_connection):
        """Testa execute com sucesso."""
        mock_conn, mock_cursor = mock_db_connection
        mock_connect.return_value = mock_conn

        mock_cursor.rowcount = 5

        db = Database(mock_config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("INSERT INTO test_table (name) VALUES ($1)")
            sql_file = f.name

        try:
            result = db.execute(sql_file, ("Test",))

            assert result == 5
            mock_cursor.execute.assert_called_once()
        finally:
            Path(sql_file).unlink()

    @patch('psycopg.connect')
    def test_database_execute_error(self, mock_connect, mock_config, mock_db_connection):
        """Testa execute com erro."""
        mock_conn, mock_cursor = mock_db_connection
        mock_connect.return_value = mock_conn

        mock_cursor.execute.side_effect = Exception("Insert error")

        db = Database(mock_config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("INSERT INTO test_table (name) VALUES ($1)")
            sql_file = f.name

        try:
            with pytest.raises(RuntimeError, match="DB execute failed"):
                db.execute(sql_file, ("Test",))
        finally:
            Path(sql_file).unlink()

    @patch('psycopg.connect')
    def test_database_no_connection_error(self, mock_config):
        """Testa erro quando não há conexão estabelecida."""
        db = Database(mock_config)
        # Não chama connect()

        with pytest.raises(RuntimeError, match="Database connection not established"):
            db._require_conn()
