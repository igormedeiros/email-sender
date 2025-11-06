-- Encontra contatos duplicados (mesmo email em múltiplos registros)
-- Mostra quantas vezes cada email aparece
SELECT 
    email,
    COUNT(*) as count,
    MIN(id) as first_id,
    MAX(id) as last_id,
    array_agg(id ORDER BY id) as all_ids,
    array_agg(DISTINCT created_at ORDER BY created_at) as created_dates
FROM tbl_contacts 
WHERE email IS NOT NULL AND email <> ''
GROUP BY email 
HAVING COUNT(*) > 1 
ORDER BY count DESC;
