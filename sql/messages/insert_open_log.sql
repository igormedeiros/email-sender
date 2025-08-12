-- Source: n8n/_email______Abriu_email.json -> "log que abriu a mensagem"
-- Variables: $('Webhook').item.json.query.contact_id, $('Webhook').item.json.query.message_id, client IP
INSERT INTO tbl_message_logs (contact_id, message_id, event_type, event_timestamp, ip_address)
VALUES (
    '{{ $('Webhook').item.json.query.contact_id }}',
    '{{ $('Webhook').item.json.query.message_id }}',
    'opened',
    NOW(),
    '{{ $json.headers["x-forwarded-for"] || $json.ip }}'
)
ON CONFLICT (contact_id, message_id, event_type) DO NOTHING;
