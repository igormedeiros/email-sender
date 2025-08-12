import types

from email_sender.db import Database, _prepare_sql


class FakeConfig:
    def __init__(self):
        self._pg = {"host": "h", "port": 5432, "user": "u", "password": "p", "database": "d"}
    @property
    def postgres_config(self):
        return self._pg


class DummyCursor:
    def __init__(self):
        self.queries = []
        self._rows = [{"id": 1}]
        self.rowcount = 1
    def execute(self, sql, params):
        self.queries.append((sql, params))
    def fetchone(self):
        return self._rows[0]
    def fetchall(self):
        return self._rows
    def close(self):
        pass

class DummyConn:
    def __init__(self):
        self._cur = DummyCursor()
        self.committed = False
        self.rolled = False
        self.closed = False
    def cursor(self):
        return self._cur
    def commit(self):
        self.committed = True
    def rollback(self):
        self.rolled = True
    def close(self):
        self.closed = True


def test_database_context_and_helpers(monkeypatch, tmp_path):
    # Create sample SQL file
    sqlp = tmp_path / "q.sql"
    sqlp.write_text("SELECT * FROM t WHERE id=$1 AND email={{ $json.query.email }}", encoding="utf-8")

    # Patch psycopg.connect to return DummyConn
    import email_sender.db as db_mod
    monkeypatch.setattr(db_mod.psycopg, "connect", lambda **k: DummyConn())

    db = Database(FakeConfig())
    with db as dbc:
        row = dbc.fetch_one(str(sqlp), (5, "a@b.com"))
        assert row["id"] == 1
        rows = dbc.fetch_all(str(sqlp), (5, "a@b.com"))
        assert len(rows) == 1
        count = dbc.execute(str(sqlp), (5, "a@b.com"))
        assert count == 1
