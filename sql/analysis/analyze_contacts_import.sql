-- SQL: Análise de contatos antes/depois da importação
-- Use este script para verificar o estado do banco antes e depois

-- ============================================================================
-- ANTES DA IMPORTAÇÃO
-- ============================================================================

-- 1. Total de contatos no banco
SELECT COUNT(*) as total_contatos FROM tbl_contacts;

-- 2. Contatos elegíveis (válidos para envio)
SELECT COUNT(*) as elegveis
FROM tbl_contacts tc
WHERE tc.unsubscribed = FALSE
  AND tc.is_buyer = FALSE
  AND NOT EXISTS (
    SELECT 1 FROM tbl_contact_tags ctg
    JOIN tbl_tags tg ON ctg.tag_id = tg.id
    WHERE ctg.contact_id = tc.id 
      AND LOWER(tg.tag_name) IN ('bounce', 'unsubscribed', 'invalid', 'problem')
  );

-- 3. Contatos por status
SELECT 
    'Total' as categoria, COUNT(*) as quantidade FROM tbl_contacts
UNION ALL
SELECT 'Elegíveis', COUNT(*) FROM tbl_contacts WHERE unsubscribed = FALSE AND is_buyer = FALSE
UNION ALL
SELECT 'Descadastrados', COUNT(*) FROM tbl_contacts WHERE unsubscribed = TRUE
UNION ALL
SELECT 'Compradores', COUNT(*) FROM tbl_contacts WHERE is_buyer = TRUE
UNION ALL
SELECT 'Com tag teste', COUNT(DISTINCT tc.id) 
  FROM tbl_contacts tc
  JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
  JOIN tbl_tags tg ON ctg.tag_id = tg.id
  WHERE LOWER(tg.tag_name) = 'test'
ORDER BY quantidade DESC;

-- ============================================================================
-- VERIFICAR CONTATOS ESPECÍFICOS
-- ============================================================================

-- Buscar contato pelo email
SELECT 
    tc.id,
    tc.email,
    tc.unsubscribed,
    tc.is_buyer,
    tc.created_at,
    array_agg(DISTINCT LOWER(tg.tag_name)) as tags
FROM tbl_contacts tc
LEFT JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
LEFT JOIN tbl_tags tg ON ctg.tag_id = tg.id
WHERE tc.email = 'seu_email@example.com'
GROUP BY tc.id, tc.email, tc.unsubscribed, tc.is_buyer, tc.created_at;

-- ============================================================================
-- VALIDAR ELEGIBILIDADE (4 critérios)
-- ============================================================================

-- Validação completa de um contato
WITH contact_check AS (
    SELECT 
        tc.id,
        tc.email,
        CASE WHEN tc.unsubscribed = TRUE THEN '❌ Descadastrado' ELSE '✅ OK' END as unsubscribed_check,
        CASE WHEN tc.is_buyer = TRUE THEN '❌ Comprador' ELSE '✅ OK' END as buyer_check,
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM tbl_contact_tags ctg
                JOIN tbl_tags tg ON ctg.tag_id = tg.id
                WHERE ctg.contact_id = tc.id AND LOWER(tg.tag_name) = 'bounce'
            ) THEN '❌ Bounce'
            ELSE '✅ OK'
        END as bounce_check,
        CASE
            WHEN EXISTS (
                SELECT 1 FROM tbl_contact_tags ctg
                JOIN tbl_tags tg ON ctg.tag_id = tg.id
                WHERE ctg.contact_id = tc.id AND LOWER(tg.tag_name) = 'invalid'
            ) THEN '❌ Inválido'
            ELSE '✅ OK'
        END as invalid_check
    FROM tbl_contacts tc
    WHERE tc.email = 'seu_email@example.com'
)
SELECT 
    id,
    email,
    unsubscribed_check,
    buyer_check,
    bounce_check,
    invalid_check,
    CASE 
        WHEN unsubscribed_check = '✅ OK' 
         AND buyer_check = '✅ OK'
         AND bounce_check = '✅ OK'
         AND invalid_check = '✅ OK'
        THEN '✅ ELEGÍVEL'
        ELSE '❌ INELEGÍVEL'
    END as status_final
FROM contact_check;

-- ============================================================================
-- ANÁLISE DE DISTRIBUIÇÃO DE TAGS
-- ============================================================================

SELECT 
    tg.tag_name,
    COUNT(DISTINCT ctg.contact_id) as quantidade
FROM tbl_tags tg
LEFT JOIN tbl_contact_tags ctg ON tg.id = ctg.tag_id
GROUP BY tg.id, tg.tag_name
ORDER BY quantidade DESC;

-- ============================================================================
-- PARA DEPOIS DA IMPORTAÇÃO: Verificar novos contatos
-- ============================================================================

-- Listar últimos 10 contatos inseridos
SELECT 
    id,
    email,
    unsubscribed,
    is_buyer,
    created_at
FROM tbl_contacts
ORDER BY created_at DESC
LIMIT 10;

-- Verificar se novos contatos estão elegíveis
SELECT 
    COUNT(DISTINCT tc.id) as novos_elegveis
FROM tbl_contacts tc
WHERE tc.created_at >= NOW() - INTERVAL '1 day'
  AND tc.unsubscribed = FALSE
  AND tc.is_buyer = FALSE
  AND NOT EXISTS (
    SELECT 1 FROM tbl_contact_tags ctg
    JOIN tbl_tags tg ON ctg.tag_id = tg.id
    WHERE ctg.contact_id = tc.id 
      AND LOWER(tg.tag_name) IN ('bounce', 'unsubscribed', 'invalid', 'problem')
  );
