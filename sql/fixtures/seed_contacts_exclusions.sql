-- Seed de contatos para cenário de envio:
-- 1 válido (deve ser enviado) e 2 que NÃO devem ser enviados (descadastro e bounce)

BEGIN;

-- Limpa entradas anteriores deste cenário (idempotente)
DELETE FROM tbl_contact_tags WHERE contact_id IN (
  SELECT id FROM tbl_contacts WHERE email IN ('valid@test.com', 'unsub@test.com', 'bounce@test.com')
);
DELETE FROM tbl_contacts
WHERE email IN ('valid@test.com', 'unsub@test.com', 'bounce@test.com');

-- Garante as tags necessárias (sem depender de unique constraints)
INSERT INTO tbl_tags (tag_name)
SELECT v FROM (VALUES ('test'), ('bounce'), ('unsubscribed')) AS t(v)
WHERE NOT EXISTS (
  SELECT 1 FROM tbl_tags x WHERE LOWER(TRIM(x.tag_name)) = LOWER(TRIM(t.v))
);

-- Insere contatos com flags usadas pelas queries de seleção
INSERT INTO tbl_contacts (email, unsubscribed, is_bounce, is_buyer)
VALUES
    ('valid@test.com',  FALSE, FALSE, FALSE),  -- elegível (terá tag 'test')
    ('unsub@test.com',  TRUE,  FALSE, FALSE),  -- descadastrado: será ignorado
    ('bounce@test.com', FALSE, TRUE,  FALSE);  -- bounce: será ignorado

-- Vincula tags aos contatos
WITH c AS (
  SELECT id, email FROM tbl_contacts WHERE email IN ('valid@test.com', 'unsub@test.com', 'bounce@test.com')
),
tags AS (
  SELECT id, LOWER(TRIM(tag_name)) AS name FROM tbl_tags WHERE LOWER(TRIM(tag_name)) IN ('test','bounce','unsubscribed')
)
-- valid@test.com -> tag 'test'
INSERT INTO tbl_contact_tags (contact_id, tag_id)
SELECT c_valid.id, t_test.id
FROM c c_valid, tags t_test
WHERE c_valid.email = 'valid@test.com' AND t_test.name = 'test'
  AND NOT EXISTS (
    SELECT 1 FROM tbl_contact_tags ct WHERE ct.contact_id = c_valid.id AND ct.tag_id = t_test.id
  );

-- unsub@test.com -> tags 'test' e 'unsubscribed'
INSERT INTO tbl_contact_tags (contact_id, tag_id)
SELECT c_unsub.id, t_tag.id
FROM c c_unsub, tags t_tag
WHERE c_unsub.email = 'unsub@test.com' AND t_tag.name IN ('test','unsubscribed')
  AND NOT EXISTS (
    SELECT 1 FROM tbl_contact_tags ct WHERE ct.contact_id = c_unsub.id AND ct.tag_id = t_tag.id
  );

-- bounce@test.com -> tags 'test' e 'bounce'
INSERT INTO tbl_contact_tags (contact_id, tag_id)
SELECT c_b.id, t_tag.id
FROM c c_b, tags t_tag
WHERE c_b.email = 'bounce@test.com' AND t_tag.name IN ('test','bounce')
  AND NOT EXISTS (
    SELECT 1 FROM tbl_contact_tags ct WHERE ct.contact_id = c_b.id AND ct.tag_id = t_tag.id
  );

COMMIT;
