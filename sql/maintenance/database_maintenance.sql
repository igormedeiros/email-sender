-- ==============================================================================
-- MANUTENÇÃO DO BANCO DE DADOS - Email Sender
-- ==============================================================================
-- Script para executar limpeza e otimização regular
-- Deve ser executado periodicamente (ex: uma vez por semana)
-- Created: 2025-11-05

-- ==============================================================================
-- 1. VERIFICAR INTEGRIDADE DOS DADOS
-- ==============================================================================

-- Contar estatísticas gerais
SELECT 
    (SELECT COUNT(*) FROM tbl_contacts) as total_contacts,
    (SELECT COUNT(DISTINCT email) FROM tbl_contacts WHERE email IS NOT NULL) as unique_emails,
    (SELECT COUNT(*) FROM tbl_contact_tags) as total_tags_assigned,
    (SELECT COUNT(*) FROM tbl_messages WHERE processed = FALSE) as pending_messages,
    (SELECT COUNT(*) FROM tbl_message_logs) as total_sent_logs;

-- ==============================================================================
-- 2. LIMPAR REGISTROS ÓRFÃOS
-- ==============================================================================

-- Deletar contact_tags de contatos que não existem mais
DELETE FROM tbl_contact_tags
WHERE contact_id NOT IN (SELECT id FROM tbl_contacts);

-- Deletar contact_tags de tags que não existem mais
DELETE FROM tbl_contact_tags
WHERE tag_id NOT IN (SELECT id FROM tbl_tags);

-- Deletar message_logs de contatos que não existem mais
DELETE FROM tbl_message_logs
WHERE contact_id NOT IN (SELECT id FROM tbl_contacts);

-- Deletar message_logs de mensagens que não existem mais
DELETE FROM tbl_message_logs
WHERE message_id NOT IN (SELECT id FROM tbl_messages);

-- ==============================================================================
-- 3. REMOVER DUPLICATAS DE EMAIL (se houver)
-- ==============================================================================

-- Deletar contatos duplicados mantendo apenas o primeiro
DELETE FROM tbl_contacts 
WHERE id IN (
    SELECT id FROM (
        SELECT 
            id,
            ROW_NUMBER() OVER (PARTITION BY email ORDER BY id) as rnum
        FROM tbl_contacts 
        WHERE email IS NOT NULL AND email <> ''
    ) t 
    WHERE t.rnum > 1
);

-- ==============================================================================
-- 4. NORMALIZAR DADOS DE EMAIL
-- ==============================================================================

-- Remover espaços em branco de emails
UPDATE tbl_contacts
SET email = TRIM(LOWER(email))
WHERE email IS NOT NULL;

-- Remover emails duplicados (caso insensitive)
DELETE FROM tbl_contacts c1
USING tbl_contacts c2
WHERE c1.id > c2.id
  AND LOWER(c1.email) = LOWER(c2.email);

-- ==============================================================================
-- 5. LIMPAR TAG NAMES
-- ==============================================================================

-- Remover espaços em branco e normalizar case
UPDATE tbl_tags
SET tag_name = TRIM(LOWER(tag_name))
WHERE tag_name IS NOT NULL;

-- Remover tags duplicadas (case insensitive)
DELETE FROM tbl_tags t1
USING tbl_tags t2
WHERE t1.id > t2.id
  AND LOWER(t1.tag_name) = LOWER(t2.tag_name);

-- ==============================================================================
-- 6. ATUALIZAR ESTATÍSTICAS PARA QUERY PLANNER
-- ==============================================================================

-- Isso melhora significativamente a performance das queries
ANALYZE tbl_contacts;
ANALYZE tbl_contact_tags;
ANALYZE tbl_tags;
ANALYZE tbl_messages;
ANALYZE tbl_message_logs;
ANALYZE tbl_send_state;

-- ==============================================================================
-- 7. VACUUM PARA RECUPERAR ESPAÇO EM DISCO
-- ==============================================================================

-- Remove dados deletados e marca espaço como disponível
-- Nota: Isso pode travar a tabela por um tempo
VACUUM ANALYZE tbl_contacts;
VACUUM ANALYZE tbl_contact_tags;
VACUUM ANALYZE tbl_tags;
VACUUM ANALYZE tbl_messages;
VACUUM ANALYZE tbl_message_logs;

-- ==============================================================================
-- 8. VERIFICAR ÍNDICES PARA FRAGMENTAÇÃO
-- ==============================================================================

-- Listar índices com tamanho
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_indexes
NATURAL JOIN pg_class
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;

-- ==============================================================================
-- 9. RECRIAR ÍNDICES FRAGMENTADOS (opcional)
-- ==============================================================================

-- REINDEX INDEX idx_tbl_contacts_email;
-- REINDEX INDEX idx_tbl_contact_tags_contact_id;
-- REINDEX INDEX idx_tbl_message_logs_contact_message_event;

-- ==============================================================================
-- 10. RELATÓRIO FINAL DE SAÚDE
-- ==============================================================================

SELECT 
    '[✅ MANUTENÇÃO CONCLUÍDA]' as status,
    NOW() as timestamp,
    (SELECT COUNT(*) FROM tbl_contacts) as total_contacts,
    (SELECT COUNT(*) FROM tbl_contact_tags) as total_associations,
    (SELECT COUNT(*) FROM tbl_messages) as total_messages,
    (SELECT COUNT(*) FROM tbl_message_logs) as total_logs;
