-- ============================================================================
-- SCRIPT DE CORREÇÃO: Limpar dados duplicados e criar constraint
-- ============================================================================
-- Este script:
-- 1. Remove logs duplicados (mantendo apenas o primeiro)
-- 2. Marca contatos afetados com tag 'alert_duplicate_send'
-- 3. Cria constraint UNIQUE para prevenir futuras duplicatas
--
-- Execução: psql -U treine -d treineinsite -f fix_duplicates_and_constraint.sql

BEGIN;

\echo '╔════════════════════════════════════════════════════════════════════╗'
\echo '║              CORREÇÃO: Remover Duplicatas e Constraints           ║'
\echo '╚════════════════════════════════════════════════════════════════════╝'
\echo ''

-- ============================================================================
-- PASSO 1: Contar duplicatas antes
-- ============================================================================

\echo '📊 PASSO 1: Contagem de duplicatas ANTES'

SELECT 
    CONCAT('  Duplicatas encontradas: ', COUNT(*)) as diagnostico
FROM (
    SELECT contact_id, message_id, COUNT(*) as count
    FROM tbl_message_logs
    WHERE event_type = 'sent'
    GROUP BY contact_id, message_id
    HAVING COUNT(*) > 1
) dup;

-- ============================================================================
-- PASSO 2: Criar tag de alerta (se não existir)
-- ============================================================================

\echo ''
\echo '🏷️  PASSO 2: Criar tag de alerta para contatos afetados'

INSERT INTO tbl_tags (tag_name)
VALUES ('alert_duplicate_send')
ON CONFLICT (tag_name) DO NOTHING;

SELECT '  Tag criada/verificada: alert_duplicate_send' as status;

-- ============================================================================
-- PASSO 3: Marcar contatos com duplicatas
-- ============================================================================

\echo ''
\echo '🔖 PASSO 3: Marcar contatos com envio duplicado'

WITH duplicated_contacts AS (
    SELECT DISTINCT contact_id
    FROM tbl_message_logs
    WHERE event_type = 'sent'
    GROUP BY contact_id, message_id
    HAVING COUNT(*) > 1
)
INSERT INTO tbl_contact_tags (contact_id, tag_id)
SELECT 
    dc.contact_id,
    (SELECT id FROM tbl_tags WHERE tag_name = 'alert_duplicate_send')
FROM duplicated_contacts dc
WHERE NOT EXISTS (
    SELECT 1 FROM tbl_contact_tags ct
    WHERE ct.contact_id = dc.contact_id
    AND ct.tag_id = (SELECT id FROM tbl_tags WHERE tag_name = 'alert_duplicate_send')
);

SELECT 
    CONCAT('  Contatos marcados: ', COUNT(*)) as status
FROM tbl_contact_tags
WHERE tag_id = (SELECT id FROM tbl_tags WHERE tag_name = 'alert_duplicate_send');

-- ============================================================================
-- PASSO 4: Remover logs duplicados (manter primeiro)
-- ============================================================================

\echo ''
\echo '🗑️  PASSO 4: Remover logs duplicados (manter primeira ocorrência)'

DELETE FROM tbl_message_logs a
USING tbl_message_logs b
WHERE a.contact_id = b.contact_id
  AND a.message_id = b.message_id
  AND a.event_type = 'sent'
  AND a.id > b.id;

SELECT '  ✅ Logs duplicados removidos' as status;

-- ============================================================================
-- PASSO 5: Criar constraint UNIQUE
-- ============================================================================

\echo ''
\echo '🔐 PASSO 5: Criar constraint UNIQUE'

ALTER TABLE tbl_message_logs
ADD CONSTRAINT unique_message_event_per_contact 
UNIQUE(contact_id, message_id, event_type);

SELECT '  ✅ Constraint criada com sucesso' as status;

-- ============================================================================
-- PASSO 6: Verificação final
-- ============================================================================

\echo ''
\echo '✓ VERIFICAÇÃO FINAL'

SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '  ✅ Nenhuma duplicata restante'
        ELSE CONCAT('  ❌ Ainda existem ', COUNT(*), ' duplicatas')
    END as resultado
FROM (
    SELECT contact_id, message_id, COUNT(*) as count
    FROM tbl_message_logs
    WHERE event_type = 'sent'
    GROUP BY contact_id, message_id
    HAVING COUNT(*) > 1
) remaining_dups;

-- ============================================================================
-- PASSO 7: Listagem de contatos afetados
-- ============================================================================

\echo ''
\echo '📋 Contatos afetados marcados com tag "alert_duplicate_send":'

SELECT 
    tc.id,
    tc.email,
    COUNT(DISTINCT ml.message_id) as message_count
FROM tbl_contact_tags ctg
INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
INNER JOIN tbl_contacts tc ON ctg.contact_id = tc.id
LEFT JOIN tbl_message_logs ml ON tc.id = ml.contact_id AND ml.event_type = 'sent'
WHERE tg.tag_name = 'alert_duplicate_send'
GROUP BY tc.id, tc.email
ORDER BY message_count DESC
LIMIT 20;

\echo ''
\echo '╔════════════════════════════════════════════════════════════════════╗'
\echo '║                    CORREÇÃO CONCLUÍDA COM SUCESSO                 ║'
\echo '╚════════════════════════════════════════════════════════════════════╝'
\echo ''
\echo '✅ Sistema agora está TOTALMENTE PROTEGIDO:'
\echo '   • Constraint UNIQUE criada em tbl_message_logs'
\echo '   • Duplicatas removidas'
\echo '   • Contatos afetados marcados para análise'
\echo ''

COMMIT;

