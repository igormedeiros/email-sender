-- Parameterized version
-- $1: contact_id (int)
-- $2: message_id (int)
-- $3: status text (optional)
-- $4: details text (optional)
INSERT INTO tbl_message_logs (contact_id, message_id, event_type, event_timestamp, status, details)
VALUES ($1, $2, 'sent', NOW(), $3, $4);
