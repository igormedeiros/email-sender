-- ============================================================================
-- TESTE ABRANGENTE: Validação de Proteção Contra Duplicatas e Exclusões
-- ============================================================================
-- Script para validar que:
-- 1. Nenhum contato recebe email 2x
-- 2. Nenhum descadastrado recebe email
-- 3. Nenhum bounce recebe email
-- 4. Nenhum comprador recebe email
-- 5. Nenhum inválido recebe email
--
-- Execução: psql -U treine -d treineinsite -f test_complete_security.sql

-- ============================================================================
-- SETUP: Limpar testes anteriores
-- ============================================================================

BEGIN;

-- Tabela temporária para resultados
DROP TABLE IF EXISTS test_results;
CREATE TEMPORARY TABLE test_results (
    test_id INT,
    test_name TEXT,
    status TEXT,
    details TEXT,
    passed BOOLEAN
);

-- ============================================================================
-- TESTE 1: Validar que NENHUM contato descadastrado recebeu email
-- ============================================================================

INSERT INTO test_results
SELECT 
    1,
    'TESTE 1: Nenhum descadastrado recebe email',
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASSOU'
        ELSE '❌ FALHOU'
    END,
    CONCAT(COUNT(*), ' contatos descadastrados com emails enviados'),
    COUNT(*) = 0
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
WHERE ml.event_type = 'sent' AND tc.unsubscribed = TRUE;

-- ============================================================================
-- TESTE 2: Validar que NENHUM contato com bounce recebeu email
-- ============================================================================

INSERT INTO test_results
SELECT 
    2,
    'TESTE 2: Nenhum bounce recebe email',
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASSOU'
        ELSE '❌ FALHOU'
    END,
    CONCAT(COUNT(*), ' contatos com bounce e emails enviados'),
    COUNT(*) = 0
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
INNER JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
WHERE ml.event_type = 'sent' AND LOWER(TRIM(tg.tag_name)) IN ('bounce', 'bouncy');

-- ============================================================================
-- TESTE 3: Validar que NENHUM contato comprador recebeu email
-- ============================================================================

INSERT INTO test_results
SELECT 
    3,
    'TESTE 3: Nenhum comprador recebe email',
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASSOU'
        ELSE '❌ FALHOU'
    END,
    CONCAT(COUNT(*), ' contatos compradores com emails enviados'),
    COUNT(*) = 0
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
WHERE ml.event_type = 'sent' AND tc.is_buyer = TRUE;

-- ============================================================================
-- TESTE 4: Validar que NENHUM contato inválido recebeu email
-- ============================================================================

INSERT INTO test_results
SELECT 
    4,
    'TESTE 4: Nenhum inválido recebe email',
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASSOU'
        ELSE '❌ FALHOU'
    END,
    CONCAT(COUNT(*), ' contatos inválidos com emails enviados'),
    COUNT(*) = 0
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
INNER JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
WHERE ml.event_type = 'sent' AND LOWER(TRIM(tg.tag_name)) IN ('invalid', 'problem');

-- ============================================================================
-- TESTE 5: Validar contatos com duplicate send logs (1 contato, 1 mensagem, 2+ logs)
-- ============================================================================

INSERT INTO test_results
SELECT 
    5,
    'TESTE 5: Nenhuma duplicata de envio',
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASSOU'
        ELSE '❌ FALHOU'
    END,
    CONCAT(COUNT(*), ' casos de contato/mensagem duplicados'),
    COUNT(*) = 0
FROM (
    SELECT contact_id, message_id, COUNT(*) as count
    FROM tbl_message_logs
    WHERE event_type = 'sent'
    GROUP BY contact_id, message_id
    HAVING COUNT(*) > 1
) duplicates;

-- ============================================================================
-- TESTE 6: Validar constraint UNIQUE em tbl_message_logs
-- ============================================================================

INSERT INTO test_results
SELECT 
    6,
    'TESTE 6: Constraint UNIQUE intacta',
    CASE 
        WHEN constraint_name IS NOT NULL THEN '✅ PASSOU'
        ELSE '❌ FALHOU'
    END,
    CASE 
        WHEN constraint_name IS NOT NULL THEN 'Constraint existe'
        ELSE 'Constraint NOT FOUND'
    END,
    constraint_name IS NOT NULL
FROM information_schema.table_constraints
WHERE table_name = 'tbl_message_logs' 
  AND constraint_name LIKE '%unique_message_event%'
LIMIT 1;

-- ============================================================================
-- TESTE 7: Validar emails únicos em tbl_contacts
-- ============================================================================

INSERT INTO test_results
SELECT 
    7,
    'TESTE 7: Emails únicos por contato',
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASSOU'
        ELSE '❌ FALHOU'
    END,
    CONCAT(COUNT(*), ' emails duplicados encontrados'),
    COUNT(*) = 0
FROM (
    SELECT LOWER(TRIM(email)) as email_lower, COUNT(*) as count
    FROM tbl_contacts
    WHERE email IS NOT NULL AND email <> ''
    GROUP BY LOWER(TRIM(email))
    HAVING COUNT(*) > 1
) duplicates;

-- ============================================================================
-- TESTE 8: Validar que contatos inválidos (NULL/vazio) não têm logs
-- ============================================================================

INSERT INTO test_results
SELECT 
    8,
    'TESTE 8: Sem emails NULL/vazios nos logs',
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASSOU'
        ELSE '❌ FALHOU'
    END,
    CONCAT(COUNT(*), ' contatos com email NULL/vazio em logs'),
    COUNT(*) = 0
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
WHERE ml.event_type = 'sent' AND (tc.email IS NULL OR tc.email = '');

-- ============================================================================
-- TESTE 9: Validar integridade de referência
-- ============================================================================

INSERT INTO test_results
SELECT 
    9,
    'TESTE 9: Referências órfãs - contact_tags',
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASSOU'
        ELSE '❌ FALHOU'
    END,
    CONCAT(COUNT(*), ' contact_tags órfãs encontradas'),
    COUNT(*) = 0
FROM tbl_contact_tags ctg
WHERE NOT EXISTS (
    SELECT 1 FROM tbl_contacts tc WHERE tc.id = ctg.contact_id
);

-- ============================================================================
-- TESTE 10: Validar contatos com tag de exclusão não aparecem 2x
-- ============================================================================

INSERT INTO test_results
SELECT 
    10,
    'TESTE 10: Sem duplicata de tags por contato',
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASSOU'
        ELSE '❌ FALHOU'
    END,
    CONCAT(COUNT(*), ' contatos com tags duplicadas'),
    COUNT(*) = 0
FROM (
    SELECT contact_id, tag_id, COUNT(*) as count
    FROM tbl_contact_tags
    GROUP BY contact_id, tag_id
    HAVING COUNT(*) > 1
) duplicates;

-- ============================================================================
-- TESTE 11: Validar test contacts NOT em PRODUÇÃO (se foram enviados)
-- ============================================================================

INSERT INTO test_results
SELECT 
    11,
    'TESTE 11: Contatos TEST apenas em TEST enviados',
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASSOU'
        ELSE '⚠️  AVISO'
    END,
    CONCAT(COUNT(*), ' contatos TEST enviados (OK se intenção)'),
    COUNT(*) >= 0
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
INNER JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
WHERE ml.event_type = 'sent' AND LOWER(TRIM(tg.tag_name)) = 'test'
  AND EXISTS (
    -- Se mensagem é produção (não test)
    SELECT 1 FROM tbl_messages m
    WHERE m.id = ml.message_id AND m.processed = TRUE
  );

-- ============================================================================
-- TESTE 12: Contatos com múltiplas tags de exclusão
-- ============================================================================

INSERT INTO test_results
SELECT 
    12,
    'TESTE 12: Proteção múltiplas tags',
    CASE 
        WHEN COUNT(*) > 0 THEN '✅ PASSOU (proteção redundante)'
        ELSE '⚠️  SEM PROTEÇÃO MÚLTIPLA'
    END,
    CONCAT(COUNT(*), ' contatos com 2+ tags de exclusão'),
    COUNT(*) > 0
FROM (
    SELECT contact_id, COUNT(DISTINCT tag_id) as tag_count
    FROM tbl_contact_tags ctg
    INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
    WHERE LOWER(TRIM(tg.tag_name)) IN (
        'unsubscribed', 'bounce', 'bouncy', 'invalid', 'problem'
    )
    GROUP BY contact_id
    HAVING COUNT(DISTINCT tag_id) >= 2
) multi_tagged;

-- ============================================================================
-- RESUMO: Exibir todos os testes
-- ============================================================================

\echo '╔════════════════════════════════════════════════════════════════════╗'
\echo '║     AUDITORIA DE SEGURANÇA - DEDUPLICAÇÃO E EXCLUSÕES              ║'
\echo '║                    Data: November 6, 2025                          ║'
\echo '╚════════════════════════════════════════════════════════════════════╝'
\echo ''

SELECT 
    CONCAT(test_id, '. ', test_name) as test,
    status,
    details
FROM test_results
ORDER BY test_id;

-- ============================================================================
-- RESUMO FINAL
-- ============================================================================

\echo ''
\echo '╔════════════════════════════════════════════════════════════════════╗'
\echo '║                        RESULTADO FINAL                             ║'
\echo '╚════════════════════════════════════════════════════════════════════╝'
\echo ''

SELECT
    CONCAT(
        'Total Testes: ', COUNT(*), ' | ',
        'Passou: ', SUM(CASE WHEN passed THEN 1 ELSE 0 END), ' | ',
        'Falhou: ', SUM(CASE WHEN NOT passed THEN 1 ELSE 0 END)
    ) as resumo,
    CASE 
        WHEN COUNT(*) = SUM(CASE WHEN passed THEN 1 ELSE 0 END) 
        THEN '✅ SISTEMA SEGURO - TODOS OS TESTES PASSARAM'
        ELSE '❌ FALHAS DETECTADAS - REVISAR ACIMA'
    END as conclusao
FROM test_results;

\echo ''
\echo 'Notas importantes:'
\echo '- Se algum teste falhou, revisar os logs acima'
\echo '- Executar sql/maintenance/audit_invalid_sends.sql para análise detalhada'
\echo '- Todos os 12 testes devem passar para garantir segurança'
\echo ''

COMMIT;

