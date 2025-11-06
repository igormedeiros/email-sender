-- Select recipients for a message - VERSÃO OTIMIZADA
-- Usa subconsultas em vez de múltiplos JOINs para evitar multiplicação de linhas
-- $1: boolean is_test_mode
-- $2: integer message_id

WITH excluded_contacts AS (
    -- Encontrar contatos que devem ser excluídos (descadastrados, bounce, etc)
    SELECT DISTINCT tc.id
    FROM tbl_contacts tc
    LEFT JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
    LEFT JOIN tbl_tags tg ON ctg.tag_id = tg.id
    WHERE tg.tag_name IN ('unsubscribed', 'bounce', 'bouncy', 'buyer_s2c5f20')
),
already_sent AS (
    -- Contatos que já receberam esta mensagem
    SELECT DISTINCT contact_id
    FROM tbl_message_logs
    WHERE message_id = $2 
        AND event_type = 'sent'
),
test_contacts AS (
    -- Contatos marcados como teste
    SELECT DISTINCT tc.id
    FROM tbl_contacts tc
    INNER JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
    INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
    WHERE LOWER(tg.tag_name) = 'test'
),
message_active AS (
    -- Verificar se a mensagem está ativa
    SELECT id FROM tbl_messages 
    WHERE id = $2 AND processed = FALSE
)
SELECT DISTINCT
    tc.id,
    tc.email
FROM tbl_contacts tc
WHERE
    -- Validações básicas
    tc.email IS NOT NULL 
    AND tc.email <> ''
    AND tc.is_buyer = FALSE
    AND tc.unsubscribed = FALSE
    
    -- Excluir contatos com tags inválidas
    AND tc.id NOT IN (SELECT id FROM excluded_contacts)
    
    -- Excluir contatos que já receberam
    AND tc.id NOT IN (SELECT contact_id FROM already_sent)
    
    -- Filtro de modo teste vs produção
    AND (
        ($1 = TRUE AND tc.id IN (SELECT id FROM test_contacts))
        OR
        ($1 = FALSE AND tc.id NOT IN (SELECT id FROM test_contacts))
    )
    
    -- Verificar que mensagem está ativa
    AND EXISTS (SELECT 1 FROM message_active)
    
ORDER BY tc.id ASC;
