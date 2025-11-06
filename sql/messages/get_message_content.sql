-- Get full message content for sending
-- $1: message_id
-- Returns: id, subject, html_body

SELECT id, subject, html_body
FROM tbl_messages 
WHERE id = $1
LIMIT 1;
