-- check_all_emails_already_sent.sql
-- Propósito: Pré-carregar TODOS os contatos que já receberam uma mensagem específica
-- OTIMIZAÇÃO FASE 1: Evita 1 query por email (usado em pré-carregamento)
-- Variáveis: $1 = message_id
-- Uso: Executado UMA VEZ antes do loop de envio
-- Performance: 1 query para 10K emails (vs 10K queries antigo)

SELECT DISTINCT contact_id
FROM tbl_message_logs
WHERE message_id = $1
  AND event_type = 'sent'
ORDER BY contact_id;
