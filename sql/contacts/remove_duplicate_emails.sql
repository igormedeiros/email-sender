-- Remove contatos duplicados mantendo apenas o primeiro (ID menor) de cada email
-- Este script identifica duplicatas e remove os registros posteriores

-- STEP 1: Visualizar duplicatas antes de remover (opcional, para auditoria)
-- Descomente a linha abaixo para ver as duplicatas que serão removidas:
-- SELECT * FROM tbl_contacts WHERE id IN (
--     SELECT id FROM (
--         SELECT id, ROW_NUMBER() OVER (PARTITION BY email ORDER BY id) as rnum
--         FROM tbl_contacts 
--         WHERE email IS NOT NULL AND email <> ''
--     ) t 
--     WHERE t.rnum > 1
-- );

-- STEP 2: Remover os registros duplicados
-- Mantém apenas o primeiro registro (ID menor) de cada email
DELETE FROM tbl_contacts 
WHERE id IN (
    SELECT id FROM (
        SELECT 
            id,
            email, 
            ROW_NUMBER() OVER (PARTITION BY email ORDER BY id) as rnum
        FROM tbl_contacts 
        WHERE email IS NOT NULL AND email <> ''
    ) t 
    WHERE t.rnum > 1
);

-- STEP 3: Verificar resultado
-- Contar quantas duplicatas restam (deve ser 0)
SELECT 
    COUNT(DISTINCT email) as unique_emails,
    COUNT(*) as total_records,
    COUNT(*) - COUNT(DISTINCT email) as duplicates_remaining
FROM tbl_contacts 
WHERE email IS NOT NULL AND email <> '';

-- STEP 4: Adicionar constraint UNIQUE para prevenir futuras duplicatas (opcional)
-- Descomente abaixo se quiser adicionar segurança:
-- ALTER TABLE tbl_contacts 
-- ADD CONSTRAINT unique_email_constraint UNIQUE(email);
