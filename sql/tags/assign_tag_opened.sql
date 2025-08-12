-- Source: n8n/_email______Abriu_email.json -> "TAG: abriu email"
-- Variables: $('Webhook').item.json.query.contact_id
INSERT INTO tbl_contact_tags (contact_id, tag_id, assigned_at)
VALUES (
    '{{ $('Webhook').item.json.query.contact_id }}',
    6,
    NOW()
)
ON CONFLICT (contact_id, tag_id) DO NOTHING;
