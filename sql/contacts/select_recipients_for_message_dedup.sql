-- ==============================================================================
-- SELECT RECIPIENTS FOR MESSAGE - VERSÃO COM DEDUPLICAÇÃO GARANTIDA
-- ==============================================================================
-- Esta query garante 100% que cada contato aparece UMA VEZ, mesmo com múltiplas tags
-- Usa DISTINCT ON que é o padrão correto para PostgreSQL
--
-- Parâmetros:
-- $1: boolean is_test_mode
-- $2: integer message_id

-- PASSO 1: Identificar tags de exclusão (unsubscribed, bounce, etc)
WITH excluded_tags AS (
    SELECT id FROM tbl_tags 
    WHERE tag_name IN ('unsubscribed', 'bounce', 'bouncy', 'buyer_s2c5f20')
),

-- PASSO 2: Contatos com tags de exclusão
excluded_contacts AS (
    SELECT DISTINCT tc.id
    FROM tbl_contacts tc
    INNER JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
    INNER JOIN excluded_tags et ON ctg.tag_id = et.id
),

-- PASSO 3: Contatos que já receberam esta mensagem
already_sent_contacts AS (
    SELECT DISTINCT contact_id
    FROM tbl_message_logs
    WHERE message_id = $2 
        AND event_type = 'sent'
),

-- PASSO 4: Contatos com tag 'test'
test_tagged_contacts AS (
    SELECT DISTINCT tc.id
    FROM tbl_contacts tc
    INNER JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
    INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
    WHERE LOWER(tg.tag_name) = 'test'
),

-- PASSO 5: Mensagem deve estar ativa
active_messages AS (
    SELECT id FROM tbl_messages 
    WHERE id = $2 AND processed = FALSE
)

-- RESULTADO FINAL: Contatos elegíveis (GARANTIDAMENTE ÚNICOS)
SELECT 
    tc.id,
    tc.email
FROM tbl_contacts tc
WHERE
    -- Validações básicas
    tc.email IS NOT NULL 
    AND tc.email <> ''
    AND tc.is_buyer = FALSE
    AND tc.unsubscribed = FALSE
    
    -- Excluir contatos com tags de exclusão
    AND tc.id NOT IN (SELECT id FROM excluded_contacts)
    
    -- Excluir contatos que já receberam
    AND tc.id NOT IN (SELECT contact_id FROM already_sent_contacts)
    
    -- Filtro de modo teste vs produção
    AND (
        -- Modo teste: somente contatos com tag 'test'
        ($1 = TRUE AND tc.id IN (SELECT id FROM test_tagged_contacts))
        OR
        -- Modo produção: contatos SEM tag 'test'
        ($1 = FALSE AND tc.id NOT IN (SELECT id FROM test_tagged_contacts))
    )
    
    -- Verificar que mensagem está ativa (último check)
    AND EXISTS (SELECT 1 FROM active_messages)

-- Ordenar por ID para consistência
ORDER BY tc.id ASC;
