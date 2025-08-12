-- Source: n8n/_email_______Sending_Emails_PROD (1).json -> "Load Contacts"
-- Variables (n8n): {{$json.messageId}}, $('SessionInfo').item.json.test
SELECT
    tc.id,
    tc.email
FROM
    tbl_contacts AS tc
WHERE
    tc.email IS NOT NULL AND tc.email <> ''
    AND tc.is_buyer = FALSE
    AND tc.unsubscribed = FALSE

    -- Contato NÃO deve ter a tag 'Unsubscribed'
    AND NOT EXISTS (
        SELECT 1
        FROM tbl_contact_tags AS ctb
        JOIN tbl_tags AS t ON ctb.tag_id = t.id
        WHERE ctb.contact_id = tc.id AND LOWER(TRIM(t.tag_name)) = 'unsubscribed'
    )
    -- Contato NÃO deve ter a tag 'Bounce'
    AND NOT EXISTS (
        SELECT 1
        FROM tbl_contact_tags AS ctb
        JOIN tbl_tags AS t ON ctb.tag_id = t.id
        WHERE ctb.contact_id = tc.id AND LOWER(TRIM(t.tag_name)) = 'bounce'
    )
    -- Contato NÃO deve ter a tag 'buyer_s2c5f20'
    AND NOT EXISTS (
        SELECT 1
        FROM tbl_contact_tags AS ctb
        JOIN tbl_tags AS t ON ctb.tag_id = t.id
        WHERE ctb.contact_id = tc.id AND LOWER(TRIM(t.tag_name)) = 'buyer_s2c5f20'
    )

    -- Verificação da tag 'Test' (depende do modo de sessão)
    AND (
        ( {{ $('SessionInfo').item.json.test }} = TRUE AND EXISTS (
            SELECT 1
            FROM tbl_contact_tags AS ctb_t
            JOIN tbl_tags AS t_t ON ctb_t.tag_id = t_t.id
            WHERE ctb_t.contact_id = tc.id AND LOWER(TRIM(t_t.tag_name)) = 'test'
        ) )
        OR
        ( {{ $('SessionInfo').item.json.test }} = FALSE AND NOT EXISTS (
            SELECT 1
            FROM tbl_contact_tags AS ctb_t
            JOIN tbl_tags AS t_t ON ctb_t.tag_id = t_t.id
            WHERE ctb_t.contact_id = tc.id AND LOWER(TRIM(t_t.tag_name)) = 'test'
        ) )
    )

    -- Contato NÃO recebeu esta mensagem específica
    AND NOT EXISTS (
        SELECT 1
        FROM tbl_message_sent_logs AS tmsl
        WHERE
            tmsl.contact_id = tc.id
            AND tmsl.message_id = {{ $json.messageId }}
    )
    -- Mensagem atual ainda não está processada
    AND EXISTS (
        SELECT 1
        FROM tbl_messages AS tm
        WHERE
            tm.id = {{ $json.messageId }}
            AND tm.processed = FALSE
    )
ORDER BY
    tc.id ASC;
