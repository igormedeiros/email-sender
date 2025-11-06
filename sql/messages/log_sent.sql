-- Registrar envio de email
-- $1: contact_id
-- $2: message_id
INSERT INTO tbl_message_logs (contact_id, message_id, event_type, created_at) 
VALUES ($1, $2, 'sent', NOW());
