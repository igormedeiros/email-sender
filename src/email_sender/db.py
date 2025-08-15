from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Optional

import psycopg
from psycopg.rows import dict_row

from .config import Config


def _load_sql_file(sql_path: str | Path) -> str:
    path_obj = Path(sql_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")
    return path_obj.read_text(encoding="utf-8")


_DOLLAR_PARAM_PATTERN = re.compile(r"\$([1-9][0-9]*)")
_N8N_EMAIL_PATTERN = re.compile(r"\{\{\s*\$json\.query\.email\s*\}\}")


def _strip_sql_comments(sql_text: str) -> str:
    """Remove single-line (--) and block (/* */) comments from SQL text."""
    # Remove block comments first (non-greedy)
    no_block = re.sub(r"/\*.*?\*/", "", sql_text, flags=re.DOTALL)
    # Remove single-line comments
    no_line = re.sub(r"--.*?$", "", no_block, flags=re.MULTILINE)
    return no_line


def _prepare_sql(sql_text: str, params: Iterable[Any]) -> tuple[str, tuple[Any, ...]]:
    """Prepare SQL by converting $1-style placeholders to %s and expanding params.

    This preserves the ability to reference the same positional parameter multiple
    times in the SQL (e.g., $2 appearing several times) by duplicating the value
    in the parameters sequence to match the number of placeholders.
    """
    # Strip comments to avoid counting placeholders in comments
    clean_sql = _strip_sql_comments(sql_text)
    # First, capture the order of $n placeholders as they appear (in clean SQL)
    occurrences = [int(m.group(1)) for m in _DOLLAR_PARAM_PATTERN.finditer(clean_sql)]

    # Also treat the n8n inline email placeholder as an extra positional parameter
    # by substituting it with a synthetic $ index after the existing ones.
    # Count how many n8n placeholders exist so we can expand params accordingly if used.
    n8n_count = len(list(_N8N_EMAIL_PATTERN.finditer(clean_sql)))

    # Build the %s-based SQL: replace n8n first (becomes %s), then $n -> %s
    sql_text_percent = _N8N_EMAIL_PATTERN.sub("%s", clean_sql)
    sql_text_percent = _DOLLAR_PARAM_PATTERN.sub("%s", sql_text_percent)

    # Expand parameters according to the occurrences
    original_params = tuple(params)
    expanded_params: list[Any] = []
    if occurrences:
        for idx in occurrences:
            param_pos = idx - 1
            if param_pos < 0 or param_pos >= len(original_params):
                raise ValueError(
                    f"SQL expects parameter ${idx} but only {len(original_params)} were provided"
                )
            expanded_params.append(original_params[param_pos])
    # Append n8n inline parameters if present (assume they are provided at the end of the params list)
    if n8n_count > 0:
        # For simplicity, take additional params from the tail beyond the max index in occurrences
        max_idx = max(occurrences) if occurrences else 0
        extra_params = original_params[max_idx: max_idx + n8n_count]
        if len(extra_params) != n8n_count:
            raise ValueError(
                f"SQL expects {n8n_count} inline parameters from n8n template but only {len(extra_params)} were provided"
            )
        expanded_params.extend(extra_params)

    # If there were no $n occurrences and no n8n placeholders, keep params as-is
    if not occurrences and n8n_count == 0:
        expanded_params = list(original_params)

    return sql_text_percent, tuple(expanded_params)


class Database:
    """Lightweight helper around psycopg for running queries from sql/ files."""

    def __init__(self, config: Config):
        self._config = config
        self._conn: Optional[psycopg.Connection] = None

    def connect(self) -> None:
        if self._conn is not None:
            return
        pg = self._config.postgres_config
        self._conn = psycopg.connect(
            host=pg["host"],
            port=pg["port"],
            user=pg["user"],
            password=pg["password"],
            dbname=pg["database"],
            row_factory=dict_row,
            autocommit=True,  # Usar autocommit para evitar transações pendentes
        )

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def __enter__(self) -> "Database":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._conn is None:
            return
        if exc is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self.close()

    def _require_conn(self) -> psycopg.Connection:
        if self._conn is None:
            raise RuntimeError(
                "Database connection not established. Call connect() or use 'with Database(config) as db:' context manager."
            )
        return self._conn

    # Query helpers
    def fetch_one(self, sql_file_path: str | Path, params: Iterable[Any] = ()) -> Optional[dict[str, Any]]:
        sql_raw = _load_sql_file(sql_file_path)
        sql_text, expanded = _prepare_sql(sql_raw, params)
        cur = self._require_conn().cursor()
        try:
            cur.execute(sql_text, expanded)
            row = cur.fetchone()
            return row if row is not None else None
        except Exception as e:
            # Add rich context to the error to help troubleshoot
            raise RuntimeError(
                f"DB fetch_one failed for {sql_file_path} with params={expanded}: {e}"
            ) from e
        finally:
            cur.close()

    def fetch_all(self, sql_file_path: str | Path, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        sql_raw = _load_sql_file(sql_file_path)
        sql_text, expanded = _prepare_sql(sql_raw, params)
        cur = self._require_conn().cursor()
        try:
            cur.execute(sql_text, expanded)
            rows = cur.fetchall()
            return list(rows)
        except Exception as e:
            raise RuntimeError(
                f"DB fetch_all failed for {sql_file_path} with params={expanded}: {e}"
            ) from e
        finally:
            cur.close()

    def execute(self, sql_file_path: str | Path, params: Iterable[Any] = ()) -> int:
        sql_raw = _load_sql_file(sql_file_path)
        sql_text, expanded = _prepare_sql(sql_raw, params)
        cur = self._require_conn().cursor()
        try:
            cur.execute(sql_text, expanded)
            return cur.rowcount
        except Exception as e:
            raise RuntimeError(
                f"DB execute failed for {sql_file_path} with params={expanded}: {e}"
            ) from e
        finally:
            cur.close()
