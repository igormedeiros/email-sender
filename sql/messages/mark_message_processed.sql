-- Source: n8n/_email_______Sending_Emails_PROD (1).json -> "Postgres" (mark processed)
-- Variables: $('messageContents').item.json.messageId
UPDATE tbl_messages
SET processed = TRUE
WHERE id = '{{ $('messageContents').item.json.messageId }}';
