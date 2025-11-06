-- ==============================================================================
-- ÍNDICES PARA PERFORMANCE - Email Sender Database
-- ==============================================================================
-- Estes índices melhoram significativamente a performance das queries mais comuns
-- Created: 2025-11-05

-- ==============================================================================
-- 1. ÍNDICES PARA TABELA tbl_contacts
-- ==============================================================================

-- Índice para buscar contatos por email (usado em descadastro e consultas)
CREATE INDEX IF NOT EXISTS idx_tbl_contacts_email 
    ON tbl_contacts(email) 
    WHERE email IS NOT NULL;

-- Índice para filtrar contatos descadastrados
CREATE INDEX IF NOT EXISTS idx_tbl_contacts_unsubscribed 
    ON tbl_contacts(unsubscribed) 
    WHERE unsubscribed = FALSE;

-- Índice composto para buscar contatos elegíveis
CREATE INDEX IF NOT EXISTS idx_tbl_contacts_buyer_unsubscribed 
    ON tbl_contacts(is_buyer, unsubscribed) 
    WHERE is_buyer = FALSE AND unsubscribed = FALSE;

-- ==============================================================================
-- 2. ÍNDICES PARA TABELA tbl_contact_tags (CRÍTICO)
-- ==============================================================================

-- Índice para buscar tags de um contato (a causa do problema de duplicatas)
CREATE INDEX IF NOT EXISTS idx_tbl_contact_tags_contact_id 
    ON tbl_contact_tags(contact_id);

-- Índice reverso para buscar contatos de uma tag
CREATE INDEX IF NOT EXISTS idx_tbl_contact_tags_tag_id 
    ON tbl_contact_tags(tag_id);

-- Índice composto para o padrão de join mais comum
CREATE INDEX IF NOT EXISTS idx_tbl_contact_tags_contact_tag 
    ON tbl_contact_tags(contact_id, tag_id);

-- ==============================================================================
-- 3. ÍNDICES PARA TABELA tbl_tags
-- ==============================================================================

-- Índice para buscar tags por nome (usado em filtros)
CREATE INDEX IF NOT EXISTS idx_tbl_tags_name 
    ON tbl_tags(tag_name) 
    WHERE tag_name IS NOT NULL;

-- Índice case-insensitive para nome de tags
CREATE INDEX IF NOT EXISTS idx_tbl_tags_name_lower 
    ON tbl_tags(LOWER(tag_name));

-- ==============================================================================
-- 4. ÍNDICES PARA TABELA tbl_messages
-- ==============================================================================

-- Índice para buscar mensagens processadas
CREATE INDEX IF NOT EXISTS idx_tbl_messages_processed 
    ON tbl_messages(processed) 
    WHERE processed = FALSE;

-- Índice para buscar mensagens por evento
CREATE INDEX IF NOT EXISTS idx_tbl_messages_event_id 
    ON tbl_messages(event_id);

-- ==============================================================================
-- 5. ÍNDICES PARA TABELA tbl_message_logs
-- ==============================================================================

-- Índice composto crítico para validar se email já foi enviado
CREATE INDEX IF NOT EXISTS idx_tbl_message_logs_contact_message_event 
    ON tbl_message_logs(contact_id, message_id, event_type) 
    WHERE event_type = 'sent';

-- Índice para buscar logs de envio
CREATE INDEX IF NOT EXISTS idx_tbl_message_logs_message_id 
    ON tbl_message_logs(message_id);

-- Índice para buscar logs por contato
CREATE INDEX IF NOT EXISTS idx_tbl_message_logs_contact_id 
    ON tbl_message_logs(contact_id);

-- ==============================================================================
-- 6. ÍNDICES PARA TABELA tbl_send_state
-- ==============================================================================

-- Índice para estado de envio (rastreamento de último contato processado)
CREATE INDEX IF NOT EXISTS idx_tbl_send_state_key 
    ON tbl_send_state(key);

-- ==============================================================================
-- 7. VERIFICAR E ANALISAR ÍNDICES CRIADOS
-- ==============================================================================

-- Lista todos os índices criados
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
    AND tablename IN ('tbl_contacts', 'tbl_contact_tags', 'tbl_tags', 'tbl_messages', 'tbl_message_logs', 'tbl_send_state')
ORDER BY tablename, indexname;

-- ==============================================================================
-- 8. ANALISAR BANCO APÓS CRIAR ÍNDICES (opcional, para otimização)
-- ==============================================================================

-- Execute para atualizar estatísticas do query planner (melhora performance)
-- ANALYZE;
