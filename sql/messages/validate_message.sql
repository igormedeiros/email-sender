-- Validar que a mensagem existe e está pronta para envio
-- $1: message_id
SELECT id FROM tbl_messages WHERE id = $1 AND processed = FALSE LIMIT 1;
