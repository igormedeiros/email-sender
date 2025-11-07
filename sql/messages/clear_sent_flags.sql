-- Clear sent flags for message reenvio
-- Params: $1 = message_id
-- Purpose: Delete all sent logs for a message to allow reenvio in production mode

DELETE FROM tbl_message_logs 
WHERE message_id = $1 AND event_type = 'sent';
