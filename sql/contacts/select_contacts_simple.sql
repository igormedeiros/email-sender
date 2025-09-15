-- Select contacts for simple send flow, excluding unsubscribed and bounces
-- $1: last_success_contact_id (int)
SELECT tc.id, tc.email
FROM tbl_contacts tc
WHERE tc.email IS NOT NULL AND tc.email <> ''
  AND COALESCE(tc.unsubscribed, FALSE) = FALSE
  AND NOT EXISTS (
    SELECT 1
    FROM tbl_contact_tags ctu
    JOIN tbl_tags tu ON ctu.tag_id = tu.id
    WHERE ctu.contact_id = tc.id AND LOWER(TRIM(tu.tag_name)) = 'unsubscribed'
  )
  AND NOT EXISTS (
    SELECT 1
    FROM tbl_contact_tags ctb
    JOIN tbl_tags t ON ctb.tag_id = t.id
    WHERE ctb.contact_id = tc.id AND LOWER(TRIM(t.tag_name)) IN ('bounce','bouncy')
  )
  -- Prevent contacts who have already received any email from being selected again
  AND NOT EXISTS (
    SELECT 1
    FROM tbl_message_logs tml
    WHERE tml.contact_id = tc.id AND tml.event_type = 'sent'
  )
  AND tc.id > $1
ORDER BY tc.id ASC;
