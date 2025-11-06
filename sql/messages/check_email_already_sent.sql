-- Verificar se email já foi enviado para esta mensagem
-- $1: contact_id
-- $2: message_id
-- Retorna: id se já foi enviado, NULL caso contrário

SELECT id 
FROM tbl_message_logs 
WHERE contact_id = $1 AND message_id = $2 AND event_type = 'sent' 
LIMIT 1;
