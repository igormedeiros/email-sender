from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

import psycopg

from .config import AppConfig


@dataclass
class Db:
    cfg: AppConfig

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        conn = psycopg.connect(
            host=self.cfg.postgres.host,
            port=self.cfg.postgres.port,
            user=self.cfg.postgres.user,
            password=self.cfg.postgres.password,
            dbname=self.cfg.postgres.database,
        )
        try:
            yield conn
        finally:
            conn.close()
