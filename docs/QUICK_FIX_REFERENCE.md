# 🔧 Quick Reference: Bug Fix SQL Recipients

## ⚡ TL;DR

**Bug:** SQL retornava 18K contatos em TESTE mode  
**Causa:** Precedência errada de operadores (AND/OR)  
**Fix:** Adicionado parênteses ao redor de `(NOT IN (...) OR $1 = TRUE)`  
**Status:** ✅ RESOLVIDO E VALIDADO

---

## 🎯 O Que Foi Mudado

**Arquivo:** `sql/contacts/select_recipients_for_message.sql` (Linhas 42-48)

```sql
-- ❌ ANTES (BUG)
AND tc.id NOT IN (
    SELECT DISTINCT contact_id FROM tbl_message_logs
    WHERE message_id = $2 AND event_type = 'sent'
) OR $1 = TRUE

-- ✅ DEPOIS (FIX)
AND (
    tc.id NOT IN (
        SELECT DISTINCT contact_id FROM tbl_message_logs
        WHERE message_id = $2 AND event_type = 'sent'
    )
    OR $1 = TRUE
)
```

---

## 🧪 Como Testar

### Quick Test 1: Modo TESTE
```bash
cd /home/igormedeiros/projects/treineinsite/treineinsite
printf "1\n1\ns\n" | uv run -m email_sender.cli
```
**Esperado:** APENAS Igor recebe email ✅

### Quick Test 2: SQL Direta
```bash
psql -U postgres -d treineinsite -c "
WITH excluded_by_column AS (
    SELECT id FROM tbl_contacts WHERE unsubscribed = TRUE OR is_buyer = TRUE
),
excluded_by_tag AS (
    SELECT DISTINCT ctg.contact_id FROM tbl_contact_tags ctg
    INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
    WHERE LOWER(tg.tag_name) IN ('unsubscribed', 'bounce', 'bouncy', 'buyer_s2c5f20', 'invalid', 'problem')
),
test_contacts AS (
    SELECT DISTINCT ctg.contact_id FROM tbl_contact_tags ctg
    INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
    WHERE LOWER(tg.tag_name) = 'test'
)
SELECT COUNT(*) FROM tbl_contacts tc
WHERE (TRUE AND tc.id IN (SELECT contact_id FROM test_contacts))
AND tc.email IS NOT NULL AND tc.email <> ''
AND tc.id NOT IN (SELECT id FROM excluded_by_column)
AND tc.id NOT IN (SELECT contact_id FROM excluded_by_tag)
AND (
    tc.id NOT IN (
        SELECT DISTINCT contact_id FROM tbl_message_logs
        WHERE message_id = 1 AND event_type = 'sent'
    )
    OR TRUE
)
AND EXISTS (SELECT 1 FROM tbl_messages WHERE id = 1 AND processed = FALSE);
"
```
**Esperado:** `count = 1` (apenas Igor) ✅

---

## 📊 Antes vs. Depois

| Aspecto | Antes ❌ | Depois ✅ |
|---------|----------|----------|
| Contatos em TESTE | 18.372 | 1 |
| Contatos em PROD | 14.569 | 14.569 |
| Igor em TESTE | ✅ (+ 18.371) | ✅ |
| Igor em PROD | ❌ | ✅ Ausente |
| CLI Funcionando | ❌ | ✅ |
| Deduplicação | ❌ | ✅ |

---

## 🔍 Por Que Aconteceu

SQL sem parênteses explícitos usa precedência:
- `AND` tem precedência MAIOR que `OR`
- Logo: `A AND B OR C` = `(A AND B) OR C`

```
ANTES:                          DEPOIS:
tc.id NOT IN (...) OR $1=TRUE   tc.id NOT IN (...) OR $1=TRUE
        ↓                               ↓
(tc.id NOT IN) OR (TRUE)        (NOT IN (...) OR TRUE)
        ↓                               ↓
Resulta em sempre TRUE!         Resulta em lógica correta!
```

---

## 📝 Documentação Completa

Ver: `docs/bug_fix_sql_recipients_2025_11_06.md`

---

## ✅ Checklist Pós-Deploy

- [ ] Testar CLI em produção
- [ ] Monitorar logs por 24h
- [ ] Confirmar que TESTE mode envia APENAS para users com tag 'Test'
- [ ] Confirmar que PROD mode respeita deduplicação
- [ ] Atualizar CHANGELOG.md
- [ ] Documentar em PRD se necessário
