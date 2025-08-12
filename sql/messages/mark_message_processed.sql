-- Parameterized version
-- $1: message_id (int)
UPDATE tbl_messages SET processed = TRUE WHERE id = $1;
