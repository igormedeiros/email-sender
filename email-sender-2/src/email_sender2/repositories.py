from __future__ import annotations

from typing import Optional, Iterable

import psycopg

from .domain import Event, Message, Contact
from .db import Db


class EventsRepo:
    def __init__(self, db: Db) -> None:
        self._db = db

    def get_active_event(self) -> Optional[Event]:
        sql = """
        SELECT sympla_id, event_name, event_start_date, event_end_date,
               city, state, place_name, event_link, detail
        FROM tbl_events
        WHERE is_active = TRUE
        LIMIT 1
        """
        with self._db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                row = cur.fetchone()
                if not row:
                    return None
                return Event(
                    id=row[0],
                    name=row[1],
                    start_date=row[2],
                    end_date=row[3],
                    city=row[4],
                    state=row[5],
                    place_name=row[6],
                    link=row[7],
                    detail_markdown=row[8],
                )


class ContactsRepo:
    def __init__(self, db: Db) -> None:
        self._db = db

    def select_recipients_for_message(self, message_id: int, test_mode: bool) -> Iterable[Contact]:
        sql = """
        SELECT tc.id, tc.email, tc.unsubscribed
        FROM tbl_contacts AS tc
        WHERE tc.email IS NOT NULL AND tc.email <> ''
          AND tc.is_buyer = FALSE
          AND tc.unsubscribed = FALSE
          AND NOT EXISTS (
            SELECT 1 FROM tbl_contact_tags ctb JOIN tbl_tags t ON ctb.tag_id = t.id
            WHERE ctb.contact_id = tc.id AND LOWER(TRIM(t.tag_name)) = 'unsubscribed'
          )
          AND NOT EXISTS (
            SELECT 1 FROM tbl_contact_tags ctb JOIN tbl_tags t ON ctb.tag_id = t.id
            WHERE ctb.contact_id = tc.id AND LOWER(TRIM(t.tag_name)) = 'bounce'
          )
          AND NOT EXISTS (
            SELECT 1 FROM tbl_contact_tags ctb JOIN tbl_tags t ON ctb.tag_id = t.id
            WHERE ctb.contact_id = tc.id AND LOWER(TRIM(t.tag_name)) = 'buyer_s2c5f20'
          )
          AND (
             (%(is_test)s = TRUE AND EXISTS (
                SELECT 1 FROM tbl_contact_tags ctb_t JOIN tbl_tags t_t ON ctb_t.tag_id = t_t.id
                WHERE ctb_t.contact_id = tc.id AND LOWER(TRIM(t_t.tag_name)) = 'test'
             ))
             OR
             (%(is_test)s = FALSE AND NOT EXISTS (
                SELECT 1 FROM tbl_contact_tags ctb_t JOIN tbl_tags t_t ON ctb_t.tag_id = t_t.id
                WHERE ctb_t.contact_id = tc.id AND LOWER(TRIM(t_t.tag_name)) = 'test'
             ))
          )
          AND NOT EXISTS (
            SELECT 1 FROM tbl_message_logs tmsl
            WHERE tmsl.contact_id = tc.id AND tmsl.message_id = %(msg_id)s
          )
          AND EXISTS (
            SELECT 1 FROM tbl_messages tm
            WHERE tm.id = %(msg_id)s AND tm.processed = FALSE
          )
        ORDER BY tc.id ASC
        """
        params = {"is_test": test_mode, "msg_id": message_id}
        with self._db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                for row in cur.fetchall():
                    yield Contact(id=row[0], email=row[1], unsubscribed=row[2])


class MessagesRepo:
    def __init__(self, db: Db) -> None:
        self._db = db

    def create_message(self, subject: str, event_id: str) -> Message:
        sql = """
        INSERT INTO tbl_messages (subject, internal_name, event_id)
        VALUES (%(subject)s,
                CONCAT('[', (SELECT state FROM tbl_events WHERE sympla_id=%(event_id)s LIMIT 1), ' ',
                       TO_CHAR(NOW(), 'MM-YYYY'), '] Envio ', COALESCE((SELECT MAX(id) + 1 FROM tbl_messages), 1)),
                %(event_id)s)
        RETURNING id, subject, processed
        """
        params = {"subject": subject, "event_id": event_id}
        with self._db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                conn.commit()
                return Message(id=row[0], subject=row[1], processed=row[2])

    def mark_processed(self, message_id: int) -> None:
        with self._db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE tbl_messages SET processed=TRUE WHERE id=%s", (message_id,))
                conn.commit()
