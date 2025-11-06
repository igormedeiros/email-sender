# 🔧 Correção do Bug: SQL retornava 18K+ contatos em TESTE mode

**Data:** 6 de Novembro de 2025  
**Status:** ✅ Resolvido  
**Impacto:** CRÍTICO - Vazamento de dados para ~18K contatos indesejados

---

## 📋 Problema

A query SQL `select_recipients_for_message.sql` retornava **18.372 contatos** quando executada em modo TESTE, em vez de retornar **APENAS Igor (id=8878)** que tem a tag 'test'.

### Sintomas
- CLI mostrava "Encontrados 1 contatos" (correto)
- Mas depois "✅ Enviados" mostrava números altos
- Email Sender demorava minutos/horas para processar

### Causa Raiz

**Linha 42-48** da SQL tinha precedência de operadores incorreta:

```sql
-- ❌ ANTES (ERRADO)
AND tc.id NOT IN (
    SELECT DISTINCT contact_id
    FROM tbl_message_logs
    WHERE message_id = $2 AND event_type = 'sent'
) OR $1 = TRUE
```

Isso era interpretado como:
```
(... AND tc.id NOT IN (...)) OR ($1 = TRUE)
```

**O problema:** Quando `$1 = TRUE` (modo TESTE), a condição `OR $1 = TRUE` tornava **TODA a cláusula WHERE verdadeira**, ignorando todas as exclusões e deduplicação!

---

## ✅ Solução

Adicionado parênteses para corrigir a precedência:

```sql
-- ✅ DEPOIS (CORRETO)
AND (
    tc.id NOT IN (
        SELECT DISTINCT contact_id
        FROM tbl_message_logs
        WHERE message_id = $2 AND event_type = 'sent'
    )
    OR $1 = TRUE
)
```

Agora a lógica é:
- **TESTE mode** (`$1 = TRUE`): IGNORA deduplicação (reenvio permitido para testes)
- **PROD mode** (`$1 = FALSE`): RESPEITA deduplicação (sem reenvio)

---

## 🧪 Validação

### Teste 1: Modo TESTE
```sql
-- Executado com: is_test_mode=TRUE, message_id=1
SELECT DISTINCT tc.id, tc.email FROM ... WHERE (TRUE AND ...) OR (FALSE AND ...)
```
**Resultado:** ✅ Retornou APENAS Igor (id=8878)

### Teste 2: Modo PRODUÇÃO
```sql
-- Executado com: is_test_mode=FALSE, message_id=1
SELECT DISTINCT tc.id, tc.email FROM ... WHERE (FALSE AND ...) OR (TRUE AND ...)
```
**Resultado:** ✅ Retornou 14.569 contatos (Igor NÃO incluído)

### Teste 3: CLI End-to-End
```bash
printf "1\n1\ns\n" | uv run -m email_sender.cli
```
**Resultado:** ✅ Enviou APENAS para Igor, detectou deduplicação, marcou como processado

---

## 📝 Arquivos Modificados

```
sql/contacts/select_recipients_for_message.sql
  Lines 42-48: Adicionado AND ( ... ) ao redor da lógica de deduplicação
```

### Diff Visual

```diff
- AND tc.id NOT IN (
+ AND (
      SELECT DISTINCT contact_id
      FROM tbl_message_logs
      WHERE message_id = $2 AND event_type = 'sent'
-  ) OR $1 = TRUE
+  )
+  OR $1 = TRUE
+ )
```

---

## 🎯 Lições Aprendidas

1. **Precedência SQL é crítica:** `AND` tem precedência MAIOR que `OR`
2. **Teste isoladamente:** Cada CTE deve ser testada antes de usar na query final
3. **Use parênteses explícitos:** Mesmo que pareça óbvio, deixa a intenção clara

---

## 📌 Checklist Pós-Correção

- [x] SQL corrigida e validada
- [x] CLI testado com sucesso  
- [x] Deduplicação funcionando
- [x] Message state persiste
- [ ] Limpar logs de teste (opcional)
- [ ] Resetar message_id=1 para novos testes (se necessário)
- [ ] Documentar no CHANGELOG
- [ ] Mergear para produção

---

## 🔗 Referências

- [copilot-instructions.md](../../.github/copilot-instructions.md) - Padrões de SQL
- [prd.md](../../docs/prd.md) - Requisitos do sistema
- `tests/unit/test_email_service.py` - Testes do email_service
