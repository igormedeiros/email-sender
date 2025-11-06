-- ==============================================================================
-- VALIDAÇÃO DE INTEGRIDADE - Verificar que nenhum contato recebeu duplicatas
-- ==============================================================================
-- Execute esta query periodicamente para auditar o banco de dados

-- 1. Contar quantas vezes cada contato recebeu cada mensagem
SELECT 
    'Contatos com múltiplos envios para mesma mensagem' as issue,
    COUNT(DISTINCT contact_id) as affected_contacts
FROM (
    SELECT 
        contact_id,
        message_id,
        COUNT(*) as send_count
    FROM tbl_message_logs
    WHERE event_type = 'sent'
    GROUP BY contact_id, message_id
    HAVING COUNT(*) > 1
) duplicates;

-- 2. Listar quais contatos receberam duplicatas
WITH duplicate_sends AS (
    SELECT 
        tc.id,
        tc.email,
        tm.id as message_id,
        COUNT(*) as send_count,
        array_agg(DISTINCT tml.id) as log_ids
    FROM tbl_contacts tc
    INNER JOIN tbl_message_logs tml ON tc.id = tml.contact_id
    INNER JOIN tbl_messages tm ON tml.message_id = tm.id
    WHERE tml.event_type = 'sent'
    GROUP BY tc.id, tc.email, tm.id
    HAVING COUNT(*) > 1
)
SELECT * FROM duplicate_sends
ORDER BY email, message_id;

-- 3. Comparar recipients com message_logs (auditoria)
WITH selected_recipients AS (
    SELECT DISTINCT tc.id, tc.email
    FROM tbl_contacts tc
    INNER JOIN tbl_messages tm ON tm.id = 1  -- Usar message_id específica
    INNER JOIN tbl_message_logs tml ON tc.id = tml.contact_id 
        AND tml.message_id = tm.id 
        AND tml.event_type = 'sent'
)
SELECT 
    'Contatos únicos na seleção' as metric,
    COUNT(DISTINCT email) as count
FROM selected_recipients;

-- 4. Verificar que cada message_log é único (constraint)
SELECT 
    'Violações de constraint unique' as check_type,
    COUNT(*) - COUNT(DISTINCT (contact_id, message_id, event_type)) as violations
FROM tbl_message_logs;

-- 5. Relatório de saúde completo
SELECT 
    (SELECT COUNT(*) FROM tbl_contacts) as total_contacts,
    (SELECT COUNT(DISTINCT contact_id) FROM tbl_message_logs WHERE event_type = 'sent') as contacts_ever_sent,
    (SELECT COUNT(DISTINCT message_id) FROM tbl_message_logs WHERE event_type = 'sent') as unique_messages_sent,
    (SELECT COUNT(*) FROM tbl_message_logs WHERE event_type = 'sent') as total_send_logs,
    (SELECT COUNT(DISTINCT (contact_id, message_id)) FROM tbl_message_logs WHERE event_type = 'sent') as unique_contact_message_pairs,
    CASE 
        WHEN (SELECT COUNT(*) FROM tbl_message_logs WHERE event_type = 'sent') = 
             (SELECT COUNT(DISTINCT (contact_id, message_id)) FROM tbl_message_logs WHERE event_type = 'sent')
        THEN '✅ INTEGRIDADE OK - Sem duplicatas'
        ELSE '⚠️ ALERTA - Duplicatas detectadas!'
    END as integrity_status;
