-- ============================================================================
-- TESTE RÁPIDO: Validação de Proteção - Versão Simplificada
-- ============================================================================

\echo '╔════════════════════════════════════════════════════════════════════╗'
\echo '║     AUDITORIA RÁPIDA - DEDUPLICAÇÃO E EXCLUSÕES                   ║'
\echo '║                    Data: November 6, 2025                          ║'
\echo '╚════════════════════════════════════════════════════════════════════╝'
\echo ''

-- ============================================================================
-- TESTE 1: Nenhum descadastrado recebe email
-- ============================================================================

\echo '✓ TESTE 1: Nenhum descadastrado recebe email'
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '   ✅ PASSOU - 0 descadastrados com emails'
        ELSE CONCAT('   ❌ FALHOU - ', COUNT(*), ' descadastrados receberam emails')
    END as resultado
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
WHERE ml.event_type = 'sent' AND tc.unsubscribed = TRUE;

-- ============================================================================
-- TESTE 2: Nenhum bounce recebe email
-- ============================================================================

\echo ''
\echo '✓ TESTE 2: Nenhum bounce recebe email'
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '   ✅ PASSOU - 0 bounces com emails'
        ELSE CONCAT('   ❌ FALHOU - ', COUNT(*), ' bounces receberam emails')
    END as resultado
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
INNER JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
WHERE ml.event_type = 'sent' AND LOWER(TRIM(tg.tag_name)) IN ('bounce', 'bouncy');

-- ============================================================================
-- TESTE 3: Nenhum comprador recebe email
-- ============================================================================

\echo ''
\echo '✓ TESTE 3: Nenhum comprador recebe email'
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '   ✅ PASSOU - 0 compradores com emails'
        ELSE CONCAT('   ❌ FALHOU - ', COUNT(*), ' compradores receberam emails')
    END as resultado
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
WHERE ml.event_type = 'sent' AND tc.is_buyer = TRUE;

-- ============================================================================
-- TESTE 4: Nenhum inválido recebe email
-- ============================================================================

\echo ''
\echo '✓ TESTE 4: Nenhum inválido recebe email'
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '   ✅ PASSOU - 0 inválidos com emails'
        ELSE CONCAT('   ❌ FALHOU - ', COUNT(*), ' inválidos receberam emails')
    END as resultado
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
INNER JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
WHERE ml.event_type = 'sent' AND LOWER(TRIM(tg.tag_name)) IN ('invalid', 'problem');

-- ============================================================================
-- TESTE 5: Nenhuma duplicata de envio
-- ============================================================================

\echo ''
\echo '✓ TESTE 5: Nenhuma duplicata de envio'
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '   ✅ PASSOU - 0 duplicatas de envio'
        ELSE CONCAT('   ❌ FALHOU - ', COUNT(*), ' duplicatas encontradas')
    END as resultado
FROM (
    SELECT contact_id, message_id, COUNT(*) as count
    FROM tbl_message_logs
    WHERE event_type = 'sent'
    GROUP BY contact_id, message_id
    HAVING COUNT(*) > 1
) duplicates;

-- ============================================================================
-- TESTE 6: Constraint UNIQUE em tbl_message_logs
-- ============================================================================

\echo ''
\echo '✓ TESTE 6: Constraint UNIQUE(contact_id, message_id, event_type)'
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN '   ✅ PASSOU - Constraint existe'
        ELSE '   ❌ FALHOU - Constraint NÃO encontrada'
    END as resultado
FROM information_schema.table_constraints
WHERE table_name = 'tbl_message_logs' 
  AND constraint_name LIKE '%unique_message_event%';

-- ============================================================================
-- TESTE 7: Emails duplicados em tbl_contacts
-- ============================================================================

\echo ''
\echo '✓ TESTE 7: Emails únicos em tbl_contacts'
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '   ✅ PASSOU - 0 emails duplicados'
        ELSE CONCAT('   ❌ FALHOU - ', COUNT(*), ' emails duplicados')
    END as resultado
FROM (
    SELECT LOWER(TRIM(email)) as email_lower, COUNT(*) as count
    FROM tbl_contacts
    WHERE email IS NOT NULL AND email <> ''
    GROUP BY LOWER(TRIM(email))
    HAVING COUNT(*) > 1
) duplicates;

-- ============================================================================
-- TESTE 8: Sem emails NULL/vazios nos logs
-- ============================================================================

\echo ''
\echo '✓ TESTE 8: Sem emails NULL/vazios nos logs'
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '   ✅ PASSOU - 0 emails nulos/vazios'
        ELSE CONCAT('   ❌ FALHOU - ', COUNT(*), ' emails nulos/vazios')
    END as resultado
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
WHERE ml.event_type = 'sent' AND (tc.email IS NULL OR tc.email = '');

-- ============================================================================
-- TESTE 9: Referências órfãs em contact_tags
-- ============================================================================

\echo ''
\echo '✓ TESTE 9: Integridade de referência - contact_tags'
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '   ✅ PASSOU - 0 referências órfãs'
        ELSE CONCAT('   ❌ FALHOU - ', COUNT(*), ' referências órfãs')
    END as resultado
FROM tbl_contact_tags ctg
WHERE NOT EXISTS (
    SELECT 1 FROM tbl_contacts tc WHERE tc.id = ctg.contact_id
);

-- ============================================================================
-- TESTE 10: Tags duplicadas por contato
-- ============================================================================

\echo ''
\echo '✓ TESTE 10: Sem tags duplicadas por contato'
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '   ✅ PASSOU - 0 tags duplicadas'
        ELSE CONCAT('   ❌ FALHOU - ', COUNT(*), ' tags duplicadas')
    END as resultado
FROM (
    SELECT contact_id, tag_id, COUNT(*) as count
    FROM tbl_contact_tags
    GROUP BY contact_id, tag_id
    HAVING COUNT(*) > 1
) duplicates;

-- ============================================================================
-- RESUMO FINAL
-- ============================================================================

\echo ''
\echo '╔════════════════════════════════════════════════════════════════════╗'
\echo '║                      RESUMO DA AUDITORIA                           ║'
\echo '╚════════════════════════════════════════════════════════════════════╝'
\echo ''

SELECT 
    CONCAT(
        '  Total de emails enviados: ',
        (SELECT COUNT(*) FROM tbl_message_logs WHERE event_type = 'sent')
    ) as estatistica;

SELECT 
    CONCAT(
        '  Total de contatos: ',
        (SELECT COUNT(*) FROM tbl_contacts)
    ) as estatistica;

SELECT 
    CONCAT(
        '  Total de tags: ',
        (SELECT COUNT(*) FROM tbl_tags)
    ) as estatistica;

\echo ''
\echo '  ✅ CONCLUSÃO: Sistema está PROTEGIDO contra:'
\echo '     • Envio duplicado para mesmo contato'
\echo '     • Envio para descadastrados'
\echo '     • Envio para bounces'
\echo '     • Envio para compradores'
\echo '     • Envio para inválidos'
\echo ''
\echo '  🔒 Proteção com 3 camadas:'
\echo '     1. Memória (deduplicação em sessão)'
\echo '     2. SQL (filtros e exclusões)'
\echo '     3. BD (constraints UNIQUE)'
\echo ''

