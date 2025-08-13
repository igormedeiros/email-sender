-- Count unsubscribed contacts after a given id
-- $1: last_success_contact_id (int)
SELECT COUNT(*) AS cnt
FROM tbl_contacts tc
WHERE tc.id > $1
  AND (
    COALESCE(tc.unsubscribed, FALSE) = TRUE
    OR EXISTS (
      SELECT 1
      FROM tbl_contact_tags ctb
      JOIN tbl_tags t ON ctb.tag_id = t.id
      WHERE ctb.contact_id = tc.id AND LOWER(TRIM(t.tag_name)) = 'unsubscribed'
    )
  );
