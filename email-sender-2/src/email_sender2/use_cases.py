from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .config import AppConfig
from .db import Db
from .repositories import EventsRepo, MessagesRepo, ContactsRepo


@dataclass
class CreateMessageAndSelectRecipients:
    cfg: AppConfig

    def run(self, subject: str) -> tuple[int, Iterable[tuple[int, str]]]:
        """Creates a message for the active event and selects recipients.

        Returns: (message_id, iterable of (contact_id, email))
        """
        db = Db(self.cfg)
        events = EventsRepo(db)
        msgs = MessagesRepo(db)
        contacts = ContactsRepo(db)

        active = events.get_active_event()
        if not active:
            raise RuntimeError("Nenhum evento ativo encontrado.")

        message = msgs.create_message(subject=subject, event_id=active.id)

        is_test = (self.cfg.environment == "test")
        recipients = ((c.id, c.email) for c in contacts.select_recipients_for_message(message.id, is_test))
        return message.id, recipients
