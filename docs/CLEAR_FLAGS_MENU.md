# 🚀 Novo Menu de Produção - Clear Flags

## Fluxo Completo:

```
Treineinsite • Email Sender CLI

1 - Enviar emails
2 - Testar SMTP
3 - Ver contatos
4 - Importar contatos (CSV)
5 - Sair

Escolha uma opção: 1

═══════════════════════════════════════════════
Modo de envio:
1 - Teste (contatos com tag 'Test') [padrão]
2 - ⚠️  Produção (TODOS os contatos)

Escolha [1-2] (padrão=1): 2

⚠️  MODO PRODUÇÃO - CUIDADO!

Opções:
1 - Enviar normalmente (sem limpar flags)
2 - Limpar flags antes de enviar (reenviar para todos)
3 - Cancelar

Escolha [1-3]: 2

Limpando flags de envio anteriores...
✅ Flags limpos com sucesso!

Tem certeza? Digite 'SIM' para confirmar: SIM

═══════════════════════════════════════════════
📋 Dados do Email a Enviar
═══════════════════════════════════════════════
[Email preview com assunto, evento, data, local, etc]
═══════════════════════════════════════════════

Continuar com o envio? (s/n): s
```

---

## 📋 Opções Disponíveis em Produção:

| Opção | Comportamento | Quando Usar |
|-------|---------------|------------|
| **1** - Enviar normalmente | Envia apenas para contatos que **NÃO** receberam | ✅ Primeira vez |
| **2** - Limpar flags | **DELETE** logs antigos + **reenviar para TODOS** | 🔄 Reenvio em massa |
| **3** - Cancelar | Cancela a operação sem fazer nada | ❌ Cancelar |

---

## 🔧 O que o "Limpar Flags" faz:

```sql
-- Deleta todos os registros de envio anterior para message_id=1
DELETE FROM tbl_message_logs 
WHERE message_id = 1 AND event_type = 'sent';

-- Marca a mensagem como não processada (permite reenvio)
UPDATE tbl_messages 
SET processed = FALSE 
WHERE id = 1;
```

---

## ⚠️ Importante:

- **Modo TESTE**: Permite reenvio **automaticamente** (sem menu de flags)
- **Modo PRODUÇÃO**: Oferece escolha entre:
  - ✅ Enviar normalmente (lista única)
  - 🔄 Limpar e reenviar para todos
  - ❌ Cancelar

---

## 🚀 Exemplos de Uso:

### Exemplo 1: Primeira vez enviando para produção
```
Escolha [1-3]: 1  # Enviar normalmente
Tem certeza? Digite 'SIM' para confirmar: SIM
```
✅ Envia para quem ainda não recebeu

### Exemplo 2: Reenviar para TODOS os contatos
```
Escolha [1-3]: 2  # Limpar flags
# [Processo de limpeza...]
Tem certeza? Digite 'SIM' para confirmar: SIM
```
✅ Limpa histórico + envia para todos

### Exemplo 3: Cancelar operação
```
Escolha [1-3]: 3  # Cancelar
# Operação cancelada.
```
✅ Retorna ao menu principal

---

## 📊 Estados Possíveis:

| Estado | tbl_message_logs | tbl_messages.processed | Próximo Envio |
|--------|------------------|----------------------|---------------|
| **Nunca enviado** | (vazio) | FALSE | Todos |
| **Enviado uma vez** | 1 registro | FALSE | Ninguém (novo) |
| **Depois de Limpar** | (vazio) | FALSE | Todos novamente |

---

**Status:** ✅ Implementado e testado
**Data:** 2025-11-07
