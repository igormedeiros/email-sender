-- Registrar envio de email (apenas 2 parâmetros)
-- $1: contact_id (int)
-- $2: message_id (int)
INSERT INTO tbl_message_logs (contact_id, message_id, event_type, event_timestamp)
VALUES ($1, $2, 'sent', NOW());
