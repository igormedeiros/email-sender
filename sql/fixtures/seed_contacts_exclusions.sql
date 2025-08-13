-- Seed de contatos para cenário de envio (modo teste):
-- 1 válido (deve ser enviado) e 2 que NÃO devem ser enviados (descadastro e bounce)
-- Contato válido: igor.medeiros@gmail.com

BEGIN;

-- Limpa entradas anteriores deste cenário (idempotente)
DELETE FROM tbl_contact_tags WHERE contact_id IN (
  SELECT id FROM tbl_contacts WHERE email IN ('igor.medeiros@gmail.com', 'unsub@test.com', 'bounce@test.com')
);
DELETE FROM tbl_contacts
WHERE email IN ('igor.medeiros@gmail.com', 'unsub@test.com', 'bounce@test.com');

-- Garante as tags necessárias (sem depender de unique constraints)
INSERT INTO tbl_tags (tag_name)
SELECT v FROM (VALUES ('test'), ('bounce'), ('unsubscribed')) AS t(v)
WHERE NOT EXISTS (
  SELECT 1 FROM tbl_tags x WHERE LOWER(TRIM(x.tag_name)) = LOWER(TRIM(t.v))
);

-- Insere contatos com flags usadas pelas queries de seleção
-- Colunas padrão (sem depender de is_bounce). Se existir is_buyer, mantém FALSE.
INSERT INTO tbl_contacts (email, unsubscribed, is_buyer)
VALUES
    ('igor.medeiros@gmail.com',  FALSE, FALSE),  -- elegível (terá tag 'test')
    ('unsub@test.com',  TRUE,  FALSE),  -- descadastrado: será ignorado
    ('bounce@test.com', FALSE, FALSE);  -- bounce: será ignorado (via tag)

-- Vincula tags aos contatos (sem CTE; independente por INSERT)
-- igor.medeiros@gmail.com -> tag 'test'
INSERT INTO tbl_contact_tags (contact_id, tag_id)
SELECT 
  (SELECT id FROM tbl_contacts WHERE email = 'igor.medeiros@gmail.com'),
  (SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'test')
WHERE NOT EXISTS (
  SELECT 1 FROM tbl_contact_tags ct
  WHERE ct.contact_id = (SELECT id FROM tbl_contacts WHERE email = 'igor.medeiros@gmail.com')
    AND ct.tag_id = (SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'test')
);

-- unsub@test.com -> tag 'test'
INSERT INTO tbl_contact_tags (contact_id, tag_id)
SELECT 
  (SELECT id FROM tbl_contacts WHERE email = 'unsub@test.com'),
  (SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'test')
WHERE NOT EXISTS (
  SELECT 1 FROM tbl_contact_tags ct
  WHERE ct.contact_id = (SELECT id FROM tbl_contacts WHERE email = 'unsub@test.com')
    AND ct.tag_id = (SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'test')
);

-- unsub@test.com -> tag 'unsubscribed'
INSERT INTO tbl_contact_tags (contact_id, tag_id)
SELECT 
  (SELECT id FROM tbl_contacts WHERE email = 'unsub@test.com'),
  (SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'unsubscribed')
WHERE NOT EXISTS (
  SELECT 1 FROM tbl_contact_tags ct
  WHERE ct.contact_id = (SELECT id FROM tbl_contacts WHERE email = 'unsub@test.com')
    AND ct.tag_id = (SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'unsubscribed')
);

-- bounce@test.com -> tag 'test'
INSERT INTO tbl_contact_tags (contact_id, tag_id)
SELECT 
  (SELECT id FROM tbl_contacts WHERE email = 'bounce@test.com'),
  (SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'test')
WHERE NOT EXISTS (
  SELECT 1 FROM tbl_contact_tags ct
  WHERE ct.contact_id = (SELECT id FROM tbl_contacts WHERE email = 'bounce@test.com')
    AND ct.tag_id = (SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'test')
);

-- bounce@test.com -> tag 'bounce'
INSERT INTO tbl_contact_tags (contact_id, tag_id)
SELECT 
  (SELECT id FROM tbl_contacts WHERE email = 'bounce@test.com'),
  (SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'bounce')
WHERE NOT EXISTS (
  SELECT 1 FROM tbl_contact_tags ct
  WHERE ct.contact_id = (SELECT id FROM tbl_contacts WHERE email = 'bounce@test.com')
    AND ct.tag_id = (SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'bounce')
);

COMMIT;
