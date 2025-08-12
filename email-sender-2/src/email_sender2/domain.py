from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Event:
    id: str  # sympla_id
    name: str
    start_date: str
    end_date: str
    city: str
    state: str
    place_name: str
    link: Optional[str]
    detail_markdown: Optional[str]


@dataclass(frozen=True)
class Message:
    id: int
    subject: str
    processed: bool


@dataclass(frozen=True)
class Contact:
    id: int
    email: str
    unsubscribed: bool
