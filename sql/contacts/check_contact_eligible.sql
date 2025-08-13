-- Returns TRUE if contact is eligible to receive emails
-- $1: contact_id
SELECT (
  COALESCE(tc.unsubscribed, FALSE) = FALSE
  AND COALESCE(tc.is_buyer, FALSE) = FALSE
  AND NOT EXISTS (
    SELECT 1 FROM tbl_contact_tags ctu
    JOIN tbl_tags tu ON ctu.tag_id = tu.id
    WHERE ctu.contact_id = tc.id AND LOWER(TRIM(tu.tag_name)) = 'unsubscribed'
  )
  AND NOT EXISTS (
    SELECT 1 FROM tbl_contact_tags ctb
    JOIN tbl_tags tb ON ctb.tag_id = tb.id
    WHERE ctb.contact_id = tc.id AND LOWER(TRIM(tb.tag_name)) IN ('bounce','bouncy')
  )
) AS ok
FROM tbl_contacts tc
WHERE tc.id = $1;
