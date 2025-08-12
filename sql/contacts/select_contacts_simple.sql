-- Select contacts for simple send flow, excluding unsubscribed and bounces
-- $1: last_success_contact_id (int)
SELECT tc.id, tc.email
FROM tbl_contacts tc
WHERE tc.email IS NOT NULL AND tc.email <> ''
  AND COALESCE(tc.unsubscribed, FALSE) = FALSE
  AND COALESCE(tc.is_bounce, FALSE) = FALSE
  AND NOT EXISTS (
    SELECT 1
    FROM tbl_contact_tags ctb
    JOIN tbl_tags t ON ctb.tag_id = t.id
    WHERE ctb.contact_id = tc.id AND LOWER(TRIM(t.tag_name)) = 'bounce'
  )
  AND tc.id > $1
ORDER BY tc.id ASC;
