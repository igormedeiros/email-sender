-- Select recipients for a message, parameterized
-- $1: boolean is_test_mode
-- $2: integer message_id
SELECT
    tc.id,
    tc.email
FROM
    tbl_contacts AS tc
WHERE
    tc.email IS NOT NULL AND tc.email <> ''
    AND tc.is_buyer = FALSE
    AND tc.unsubscribed = FALSE
    AND NOT EXISTS (
        SELECT 1
        FROM tbl_contact_tags AS ctb
        JOIN tbl_tags AS t ON ctb.tag_id = t.id
        WHERE ctb.contact_id = tc.id AND LOWER(TRIM(t.tag_name)) = 'unsubscribed'
    )
    AND NOT EXISTS (
        SELECT 1
        FROM tbl_contact_tags AS ctb
        JOIN tbl_tags AS t ON ctb.tag_id = t.id
        WHERE ctb.contact_id = tc.id AND LOWER(TRIM(t.tag_name)) = 'bounce'
    )
    AND NOT EXISTS (
        SELECT 1
        FROM tbl_contact_tags AS ctb
        JOIN tbl_tags AS t ON ctb.tag_id = t.id
        WHERE ctb.contact_id = tc.id AND LOWER(TRIM(t.tag_name)) = 'buyer_s2c5f20'
    )
    AND (
        ($1 = TRUE AND EXISTS (
            SELECT 1
            FROM tbl_contact_tags AS ctb_t
            JOIN tbl_tags AS t_t ON ctb_t.tag_id = t_t.id
            WHERE ctb_t.contact_id = tc.id AND LOWER(TRIM(t_t.tag_name)) = 'test'
        ))
        OR
        ($1 = FALSE AND NOT EXISTS (
            SELECT 1
            FROM tbl_contact_tags AS ctb_t
            JOIN tbl_tags AS t_t ON ctb_t.tag_id = t_t.id
            WHERE ctb_t.contact_id = tc.id AND LOWER(TRIM(t_t.tag_name)) = 'test'
        ))
    )
    AND NOT EXISTS (
        SELECT 1
        FROM tbl_message_logs AS tmsl
        WHERE tmsl.contact_id = tc.id AND tmsl.message_id = $2
    )
    AND EXISTS (
        SELECT 1 FROM tbl_messages tm WHERE tm.id = $2 AND tm.processed = FALSE
    )
ORDER BY tc.id ASC;
