-- Source: n8n/_email______Clicou_no_Link_Webhook_Evento_Atual.json -> "log que clicou na mensagem"
-- Variables: $('Webhook').item.json.query.contact_id, message_id, url, ip, user-agent
INSERT INTO tbl_message_logs (contact_id, message_id, event_type, event_timestamp, details, ip_address, user_agent)
VALUES (
    '{{ $('Webhook').item.json.query.contact_id }}',
    '{{ $('Webhook').item.json.query.message_id }}',
    'clicked',
    NOW(),
    '{{ $('Webhook').item.json.query.url }}',
    '{{ $json.headers["x-forwarded-for"] || $json.ip }}',
    '{{ $json.headers["user-agent"] }}'
)
ON CONFLICT (contact_id, message_id, event_type, details) DO NOTHING;
