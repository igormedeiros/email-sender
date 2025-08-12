-- Source: n8n/_email______Clicou_no_Link_Webhook_Evento_Atual.json -> "TAG: Clicked_email"
-- Variables: $('Webhook').item.json.query.contact_id
INSERT INTO tbl_contact_tags (contact_id, tag_id, assigned_at)
VALUES (
    '{{ $('Webhook').item.json.query.contact_id }}',
    7,
    NOW()
)
ON CONFLICT (contact_id, tag_id) DO NOTHING;
