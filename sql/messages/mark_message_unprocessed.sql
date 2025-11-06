-- Marcar mensagem como NÃO processada (para reenvio em modo TESTE)
-- Parâmetro: $1 = message_id
UPDATE tbl_messages 
SET processed = FALSE 
WHERE id = $1;
