-- Source: n8n/_email_______Bounces.json -> "Update Records"
-- Variables: $json.email
INSERT INTO tbl_contact_tags (contact_id, tag_id, assigned_at)
VALUES (
    (SELECT id FROM tbl_contacts WHERE email = '{{ $json.email }}'),
    1, -- 'Bounce'
    NOW()
)
ON CONFLICT (contact_id, tag_id) DO NOTHING;
