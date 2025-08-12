from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    username: str
    password: str
    use_tls: bool


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


class AppConfig:
    def __init__(self) -> None:
        # Environment mode
        environment = os.getenv("ENVIRONMENT", "test").strip().lower()
        if environment not in {"test", "prod", "production"}:
            environment = "test"
        self._environment = environment

        # SMTP
        self._smtp = SmtpConfig(
            host=os.getenv("SMTP_HOST", ""),
            port=int(os.getenv("SMTP_PORT", "587")),
            username=os.getenv("SMTP_USERNAME", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"},
        )

        # Postgres
        self._pg = PostgresConfig(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            user=os.getenv("PGUSER", "postgres"),
            password=os.getenv("PGPASSWORD", ""),
            database=os.getenv("PGDATABASE", "postgres"),
        )

    @property
    def environment(self) -> str:
        return "prod" if self._environment in {"prod", "production"} else "test"

    @property
    def smtp(self) -> SmtpConfig:
        return self._smtp

    @property
    def postgres(self) -> PostgresConfig:
        return self._pg
