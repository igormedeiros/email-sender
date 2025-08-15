-- Source: Marca um contato com a tag 'problem' quando há falhas de envio
-- Parameterized: $1 is the contact email
INSERT INTO tbl_contact_tags (contact_id, tag_id, assigned_at)
SELECT 
    tc.id,
    (SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'problem' LIMIT 1),
    NOW()
FROM tbl_contacts tc
WHERE LOWER(TRIM(tc.email)) = LOWER(TRIM($1))
  AND EXISTS (SELECT 1 FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'problem')
ON CONFLICT (contact_id, tag_id) DO NOTHING;