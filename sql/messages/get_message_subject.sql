-- Get message subject for sending
-- $1: message_id
-- Returns: subject

SELECT subject
FROM tbl_messages 
WHERE id = $1
LIMIT 1;
