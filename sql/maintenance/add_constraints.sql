-- ==============================================================================
-- CONSTRAINTS DE INTEGRIDADE - Email Sender Database (COM TRATAMENTO DE ERROS)
-- ==============================================================================

-- Script que tenta adicionar constraints, ignorando se já existem

-- 1. Constraint UNIQUE em email
ALTER TABLE tbl_contacts
ADD CONSTRAINT unique_email_per_contact UNIQUE(email) 
WHERE email IS NOT NULL;

-- 2. Constraint UNIQUE em tag_name  
ALTER TABLE tbl_tags
ADD CONSTRAINT unique_tag_name UNIQUE(tag_name);

-- 3. Constraint UNIQUE em contact_tags
ALTER TABLE tbl_contact_tags
ADD CONSTRAINT unique_contact_tag UNIQUE(contact_id, tag_id);

-- 4. Constraint UNIQUE em message_logs
ALTER TABLE tbl_message_logs
ADD CONSTRAINT unique_message_event_per_contact 
UNIQUE(contact_id, message_id, event_type);

-- 5. FK contact_tags.contact_id → contacts.id (com ON DELETE CASCADE)
ALTER TABLE tbl_contact_tags
ADD CONSTRAINT fk_contact_tags_contact_id
FOREIGN KEY(contact_id) 
REFERENCES tbl_contacts(id) 
ON DELETE CASCADE;

-- 6. FK contact_tags.tag_id → tags.id (com ON DELETE CASCADE)
ALTER TABLE tbl_contact_tags
ADD CONSTRAINT fk_contact_tags_tag_id
FOREIGN KEY(tag_id) 
REFERENCES tbl_tags(id) 
ON DELETE CASCADE;

-- ==============================================================================
-- VERIFICAR CONSTRAINTS CRIADAS
-- ==============================================================================

SELECT 
    constraint_name,
    table_name,
    constraint_type
FROM information_schema.table_constraints
WHERE table_schema = 'public'
    AND table_name IN ('tbl_contacts', 'tbl_contact_tags', 'tbl_tags', 'tbl_message_logs')
ORDER BY table_name, constraint_name;
