-- Check if message was already sent to contact
-- $1: integer contact_id
-- $2: integer message_id
SELECT id, event_type
FROM tbl_message_logs
WHERE contact_id = $1
  AND message_id = $2
  AND event_type = 'sent'
LIMIT 1;