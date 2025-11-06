-- ==============================================================================
-- CONSTRAINTS DE INTEGRIDADE - Email Sender Database
-- ==============================================================================
-- Previne dados inválidos e duplicatas futuras
-- Created: 2025-11-05

-- ==============================================================================
-- 1. ADICIONAR CONSTRAINT UNIQUE EM tbl_contacts (EMAIL)
-- ==============================================================================

-- Constraint de email único (evita duplicatas de contato)
-- NOTA: Se já houver duplicatas, execute remove_duplicate_emails.sql primeiro
ALTER TABLE tbl_contacts
ADD CONSTRAINT unique_email_per_contact 
UNIQUE(email) 
WHERE email IS NOT NULL;

-- ==============================================================================
-- 2. ADICIONAR CONSTRAINT UNIQUE EM tbl_tags (TAG_NAME)
-- ==============================================================================

-- Tag names devem ser únicos (evita duplicatas de tags)
ALTER TABLE tbl_tags
ADD CONSTRAINT unique_tag_name 
UNIQUE(tag_name);

-- ==============================================================================
-- 3. ADICIONAR CONSTRAINT UNIQUE EM tbl_contact_tags
-- ==============================================================================

-- Evita que um contato receba a mesma tag múltiplas vezes
ALTER TABLE tbl_contact_tags
ADD CONSTRAINT unique_contact_tag 
UNIQUE(contact_id, tag_id);

-- ==============================================================================
-- 4. ADICIONAR CONSTRAINT UNIQUE EM tbl_message_logs
-- ==============================================================================

-- Evita que o mesmo evento seja registrado múltiplas vezes para um contato e mensagem
ALTER TABLE tbl_message_logs
ADD CONSTRAINT unique_message_event_per_contact 
UNIQUE(contact_id, message_id, event_type);

-- ==============================================================================
-- 5. ADICIONAR CONSTRAINT DE CHAVE ESTRANGEIRA COM VALIDAÇÕES
-- ==============================================================================

-- Validar que contact_id em tbl_contact_tags existe em tbl_contacts
ALTER TABLE tbl_contact_tags
ADD CONSTRAINT fk_contact_tags_contact_id
FOREIGN KEY(contact_id) 
REFERENCES tbl_contacts(id) 
ON DELETE CASCADE;

-- Validar que tag_id em tbl_contact_tags existe em tbl_tags
ALTER TABLE tbl_contact_tags
ADD CONSTRAINT fk_contact_tags_tag_id
FOREIGN KEY(tag_id) 
REFERENCES tbl_tags(id) 
ON DELETE CASCADE;

-- ==============================================================================
-- 6. ADICIONAR NOT NULL CONSTRAINTS
-- ==============================================================================

-- Email não pode ser vazio em tbl_contacts
ALTER TABLE tbl_contacts
ALTER COLUMN email SET NOT NULL;

-- Tag name não pode ser vazia em tbl_tags
ALTER TABLE tbl_tags
ALTER COLUMN tag_name SET NOT NULL;

-- ==============================================================================
-- 7. ADICIONAR CONSTRAINT DE CHECK (VALIDAÇÃO)
-- ==============================================================================

-- is_buyer deve ser booleano válido
ALTER TABLE tbl_contacts
ADD CONSTRAINT check_is_buyer_boolean 
CHECK (is_buyer IN (TRUE, FALSE));

-- unsubscribed deve ser booleano válido
ALTER TABLE tbl_contacts
ADD CONSTRAINT check_unsubscribed_boolean 
CHECK (unsubscribed IN (TRUE, FALSE));

-- ==============================================================================
-- 8. LISTAR TODAS AS CONSTRAINTS CRIADAS
-- ==============================================================================

SELECT 
    constraint_name,
    table_name,
    constraint_type
FROM information_schema.table_constraints
WHERE table_schema = 'public'
    AND table_name IN ('tbl_contacts', 'tbl_contact_tags', 'tbl_tags', 'tbl_message_logs')
ORDER BY table_name, constraint_name;
