-- Seed de contatos para cenário de envio (modo teste):
-- 1 válido (deve ser enviado) e 2 que NÃO devem ser enviados (descadastro e bounce)
-- Contato válido: igor.medeiros@gmail.com

BEGIN;

-- Limpa entradas anteriores deste cenário (idempotente)
-- Apenas remove tags específicas para não violar FKs em logs
DELETE FROM tbl_contact_tags 
WHERE contact_id IN (
  SELECT id FROM tbl_contacts WHERE email IN ('igor.medeiros@gmail.com', 'unsub@test.com', 'bounce@test.com')
)
AND tag_id IN (
  SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) IN ('test','unsubscribed','bounce')
);

-- Garante as tags necessárias (sem depender de unique constraints)
INSERT INTO tbl_tags (tag_name)
SELECT v FROM (VALUES ('test'), ('bounce'), ('unsubscribed')) AS t(v)
WHERE NOT EXISTS (
  SELECT 1 FROM tbl_tags x WHERE LOWER(TRIM(x.tag_name)) = LOWER(TRIM(t.v))
);

-- Garante a existência dos contatos (insere se não existir)
INSERT INTO tbl_contacts (email, unsubscribed, is_buyer)
SELECT 'igor.medeiros@gmail.com', FALSE, FALSE
WHERE NOT EXISTS (SELECT 1 FROM tbl_contacts WHERE email = 'igor.medeiros@gmail.com');
INSERT INTO tbl_contacts (email, unsubscribed, is_buyer)
SELECT 'unsub@test.com', TRUE, FALSE
WHERE NOT EXISTS (SELECT 1 FROM tbl_contacts WHERE email = 'unsub@test.com');
INSERT INTO tbl_contacts (email, unsubscribed, is_buyer)
SELECT 'bounce@test.com', FALSE, FALSE
WHERE NOT EXISTS (SELECT 1 FROM tbl_contacts WHERE email = 'bounce@test.com');

-- Ajusta flags independentemente de já existirem
UPDATE tbl_contacts SET unsubscribed = FALSE, is_buyer = FALSE WHERE email = 'igor.medeiros@gmail.com';
UPDATE tbl_contacts SET unsubscribed = TRUE,  is_buyer = FALSE WHERE email = 'unsub@test.com';
UPDATE tbl_contacts SET unsubscribed = FALSE, is_buyer = FALSE WHERE email = 'bounce@test.com';

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
