-- Select recipients for a message
-- Params: is_test_mode (boolean), message_id (integer)
-- Protections: Excludes unsubscribed, bounce, buyers and already sent

WITH excluded_by_column AS (
    -- Contatos que têm unsubscribed=TRUE ou is_buyer=TRUE na tabela principal
    SELECT id FROM tbl_contacts 
    WHERE unsubscribed = TRUE OR is_buyer = TRUE
),
excluded_by_tag AS (
    -- Contatos com tags que devem ser excluídos
    SELECT DISTINCT ctg.contact_id
    FROM tbl_contact_tags ctg
    INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
    WHERE LOWER(tg.tag_name) IN ('unsubscribed', 'bounce', 'bouncy', 'buyer_s2c5f20', 'invalid', 'problem')
),
test_contacts AS (
    -- Contatos com tag 'test'
    SELECT DISTINCT ctg.contact_id
    FROM tbl_contact_tags ctg
    INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
    WHERE LOWER(tg.tag_name) = 'test'
)
SELECT DISTINCT
    tc.id,
    tc.email
FROM tbl_contacts tc
WHERE
    -- ✅ Filter: Test mode vs production
    (
        ($1 = TRUE AND tc.id IN (SELECT contact_id FROM test_contacts))
        OR
        ($1 = FALSE AND tc.id NOT IN (SELECT contact_id FROM test_contacts))
    )
    
    AND tc.email IS NOT NULL 
    AND tc.email <> ''
    
    AND tc.id NOT IN (SELECT id FROM excluded_by_column)
    
    AND tc.id NOT IN (SELECT contact_id FROM excluded_by_tag)
    
    AND (
        tc.id NOT IN (
            SELECT DISTINCT contact_id
            FROM tbl_message_logs
            WHERE message_id = $2 AND event_type = 'sent'
        )
        OR $1 = TRUE
    )
    
    AND EXISTS (
        SELECT 1 FROM tbl_messages 
        WHERE id = $2 AND processed = FALSE
    )
    
ORDER BY tc.id ASC;

