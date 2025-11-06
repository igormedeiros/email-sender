-- ==============================================================================
-- AUDITORIA: Verificar emails enviados para contatos descadastrados/bounce
-- ==============================================================================

-- Contar emails enviados para contatos descadastrados
SELECT 
    '❌ ENVIADOS PARA DESCADASTRADOS' as issue,
    COUNT(DISTINCT ml.contact_id) as contact_count,
    COUNT(DISTINCT ml.message_id) as message_count
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
WHERE ml.event_type = 'sent' AND tc.unsubscribed = TRUE;

-- Contar emails enviados para contatos com bounce
SELECT 
    '❌ ENVIADOS PARA BOUNCE' as issue,
    COUNT(DISTINCT ml.contact_id) as contact_count,
    COUNT(DISTINCT ml.message_id) as message_count
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
INNER JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
WHERE ml.event_type = 'sent' AND LOWER(tg.tag_name) IN ('bounce', 'bouncy');

-- Contar emails enviados para buyers
SELECT 
    '❌ ENVIADOS PARA BUYERS' as issue,
    COUNT(DISTINCT ml.contact_id) as contact_count,
    COUNT(DISTINCT ml.message_id) as message_count
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
WHERE ml.event_type = 'sent' AND tc.is_buyer = TRUE;

-- Contar emails enviados para contatos com tag 'invalid' ou 'problem'
SELECT 
    '❌ ENVIADOS PARA INVÁLIDOS/PROBLEMA' as issue,
    COUNT(DISTINCT ml.contact_id) as contact_count,
    COUNT(DISTINCT ml.message_id) as message_count
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
INNER JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
WHERE ml.event_type = 'sent' AND LOWER(tg.tag_name) IN ('invalid', 'problem');

-- ==============================================================================
-- LISTAGEM: IDs dos contatos que NÃO DEVIAM RECEBER
-- ==============================================================================

-- Lista de emails enviados para descadastrados (para marcar para remoção)
SELECT 
    ml.contact_id,
    tc.email,
    'unsubscribed' as reason,
    COUNT(DISTINCT ml.message_id) as message_count
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
WHERE ml.event_type = 'sent' AND tc.unsubscribed = TRUE
GROUP BY ml.contact_id, tc.email
ORDER BY message_count DESC;

-- Lista de emails enviados para bounce
SELECT 
    ml.contact_id,
    tc.email,
    'bounce' as reason,
    COUNT(DISTINCT ml.message_id) as message_count
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
INNER JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
WHERE ml.event_type = 'sent' AND LOWER(tg.tag_name) IN ('bounce', 'bouncy')
GROUP BY ml.contact_id, tc.email
ORDER BY message_count DESC;
