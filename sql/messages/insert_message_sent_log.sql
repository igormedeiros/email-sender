-- Source: n8n/_email_______Sending_Emails_PROD (1).json -> "SET enviado = true"
-- Variables: contact_id from Load Contacts, messageId, SMTP response
INSERT INTO tbl_message_logs (contact_id, message_id, event_type, event_timestamp, status, details)
VALUES (
    '{{ $('Load Contacts').item.json.id }}',
    '{{ $('messageContents').item.json.messageId }}',
    'sent',
    NOW(),
    '{{ $('Send Email').item.json.response }}',
    NULL
);
