-- Source: n8n/_email_____Unsubscribe.json -> "Unsubscribe email"
-- Variables: $json.query.email
UPDATE tbl_contacts
SET
    unsubscribed = TRUE,
    updated_at = NOW()
WHERE email = '{{ $json.query.email }}';
