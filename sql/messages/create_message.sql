-- Parameterized version
-- $1: subject text
-- $2: state text (ex: 'SP')
-- $3: month number text (ex: '05')
-- $4: year text (ex: '2025')
-- $5: event_id text
INSERT INTO tbl_messages (subject, internal_name, event_id)
VALUES (
    $1::text,
    CONCAT('[', $2::text, ' ', $3::text, '-', $4::text, '] Envio ', COALESCE((SELECT MAX(id) + 1 FROM tbl_messages), 1)),
    CASE WHEN ($5)::text ~ '^[0-9]+' THEN ($5)::int ELSE NULL END
)
RETURNING id, subject, processed;
