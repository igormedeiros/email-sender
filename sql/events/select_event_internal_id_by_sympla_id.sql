-- Returns the internal numeric id for a given sympla_id (text)
-- $1: sympla_id text
SELECT id
FROM tbl_events
WHERE sympla_id = $1
LIMIT 1;
