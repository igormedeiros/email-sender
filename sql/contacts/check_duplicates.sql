-- Verifica emails duplicados
SELECT email, COUNT(*) as count, MIN(id) as first_id, array_agg(id) as all_ids
FROM tbl_contacts 
WHERE email IS NOT NULL 
GROUP BY email 
HAVING COUNT(*) > 1 
ORDER BY count DESC;

-- Remove duplicatas mantendo apenas o registro mais antigo
DELETE FROM tbl_contacts 
WHERE id IN (
    SELECT id 
    FROM (
        SELECT id, 
               ROW_NUMBER() OVER (PARTITION BY email ORDER BY id) as rnum
        FROM tbl_contacts
        WHERE email IS NOT NULL
    ) t 
    WHERE t.rnum > 1
);