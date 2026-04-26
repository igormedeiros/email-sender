# PRD - Treineinsite Email Sender

**Status:** Production Ready ✅ | **Version:** 3.1 | **Last Updated:** April 2026

---

## Resumo

**Treineinsite Email Sender** é um sistema para envio de emails em lote a partir de um banco PostgreSQL. Interface CLI interativa, proteção contra duplicatas em 4 níveis, e otimizações de performance (v3.0: ~39% mais rápido).

### Números-Chave

| Métrica | Valor |
|---------|-------|
| Arquivos Python (core) | 6 (cli, email_service, smtp_manager, db, config, hardbounce_manager*) |
| Tabelas PostgreSQL | 10+ |
| 1.000 emails | ~1,1 min |
| 10.000 emails | ~11 min |
| Taxa de sucesso | 99.5% (com retry) |

_* hardbounce_manager.py referenciado no CLI mas ainda não implementado_

---

## Objetivo

Substituir o workflow n8n anterior, centralizando contatos em PostgreSQL com:

- Envio em lote com controle de taxa
- Interface CLI interativa (8 opções)
- Templates HTML com placeholders
- Gerenciamento de descadastros, bounces e hardbounces
- Relatórios detalhados de envio
- Retentativas com backoff exponencial
- Proteção contra duplicatas em 4 níveis
- Configuração 100% externa (YAML + .env)

---

## Arquitetura

### Stack

| Componente | Tecnologia | Propósito |
|-----------|-----------|----------|
| Linguagem | Python 3.12+ | Core |
| CLI | Typer + Rich | Interface de linha de comando |
| Banco | PostgreSQL + psycopg3 | Persistência |
| SMTP | smtplib (stdlib) | Envio de emails |
| Config | YAML + .env | Configuração externa |
| Build | uv | Gerenciador de dependências |

### Estrutura de Arquivos

```
src/email_sender/
├── __init__.py
├── cli.py                    # CLI principal (8 opções de menu)
├── email_service.py          # Lógica central (4-level dedup)
├── smtp_manager.py           # SMTP + retry backoff exponencial
├── db.py                     # Acesso a BD (queries por arquivo SQL)
├── config.py                 # Gerenciador de configurações
└── hardbounce_manager.py     # [TODO] Gestão de hardbounces (Locaweb SMTP)

config/
├── config.yaml               # Configurações operacionais
├── email.yaml                # Conteúdo dinâmico de emails
└── templates/
    └── email.html            # Template HTML

sql/
├── contacts/
│   ├── select_recipients_for_message.sql
│   ├── select_recipients_for_message_test_mode.sql
│   ├── select_contact_by_email.sql
│   └── check_contact_exclusions.sql
├── messages/
│   ├── check_message_exists.sql
│   ├── check_message_valid.sql
│   ├── check_all_emails_already_sent.sql
│   ├── insert_message_sent_log.sql
│   ├── mark_message_processed.sql
│   ├── mark_message_unprocessed.sql
│   └── clear_sent_flags.sql
├── events/
├── tags/
├── leads/
├── maintenance/
├── migrations/
└── analysis/

specs/
└── PRD.md                    # Este documento
```

### Fluxo de Envio

```
CLI (typer) → opção 1: Enviar
    ↓
email_service.send_batch()
    ├─ Conecta ao BD
    ├─ Valida mensagem
    ├─ Carrega contatos elegíveis (DB)
    ├─ Pré-carrega IDs já enviados em memória (produção)
    ├─ Desconecta BD (libera recursos durante SMTP)
    ├─ Conecta SMTP
    ├─ Para cada contato:
    │   ├─ Deduplica (proteção 1: memória da sessão)
    │   ├─ Deduplica (proteção 2: IDs pré-carregados, apenas produção)
    │   ├─ Envia via SMTP (smtp_manager com retry)
    │   └─ Marca em memória
    ├─ Desconecta SMTP
    ├─ Reconecta BD
    ├─ Persiste logs em batch (apenas produção)
    ├─ Marca mensagem como processada (apenas produção)
    └─ Gera relatório (reports/email_report_YYYYMMDD_HHMMSS.txt)
```

---

## Funcionalidades

### CLI — 8 opções de menu

```
1 - Enviar emails (modo teste ou produção)
2 - Testar SMTP
3 - Listar contatos elegíveis
4 - Importar contatos (CSV)
5 - Editar evento (in-CLI, persiste em email.yaml)
6 - Manutenção do banco
7 - Gerenciar hardbounces [TODO: hardbounce_manager.py]
8 - Sair
```

**Subcomandos CLI diretos:**
```bash
uv run treineinsite-sendemails send         # modo teste
uv run treineinsite-sendemails send --prod  # produção
uv run treineinsite-sendemails test-smtp
uv run treineinsite-sendemails contacts
uv run treineinsite-sendemails import-csv <arquivo>
uv run treineinsite-sendemails edit-event
uv run treineinsite-sendemails clean-db
uv run treineinsite-sendemails bounces
```

### Envio de Emails

- Batch configurável (`batch_size`, `batch_delay` no config.yaml)
- Modo TESTE (contatos com tag 'Test') e Produção (todos)
- Target mode: `--target email@exemplo.com` para enviar a um único endereço
- Dry-run: `--dry-run` simula sem enviar
- Clear flags: `--clear-flags` reprocessa contatos já enviados

**Proteção Contra Duplicatas (4 Níveis):**
1. **Memória (sessão):** Set `_sent_contacts` em memória
2. **Pré-carregamento BD:** IDs já enviados carregados antes do loop (O(1) lookup)
3. **BD:** `tbl_message_logs` — verificado antes do envio
4. **Tags:** Exclusão automática de bounce/unsubscribed/invalid via SQL

### Modo Teste vs Produção

| Comportamento | Teste | Produção |
|--------------|-------|---------|
| Contatos | Tag 'Test' apenas | Todos elegíveis |
| Verifica enviados | Não (permite reenvio) | Sim |
| Grava logs no BD | Não | Sim |
| Marca msg processada | Não | Sim |
| Confirmação interativa | Não | Sim ("SIM") |

### Edição de Evento (opção 5)

Edita interativamente em `config/email.yaml`:
- Nome, data, local, link, cupom do evento
- Subject do email

### Placeholders no Template HTML

| Placeholder | Fonte |
|------------|-------|
| `{data_evento}` | `evento.data` |
| `{cidade}` | `evento.cidade` |
| `{link_evento}` | `evento.link` (+ cupom como query param `?d=CUPOM`) |
| `{uf}` | `evento.uf` |
| `{local}` | `evento.local` |
| `{horario}` | `evento.horario` |
| `{desconto_paragrafo}` | `promocao.desconto` |

### Relatórios

- Arquivo em `reports/email_report_YYYYMMDD_HHMMSS.txt`
- Métricas: total processado, enviados, falhas, taxa de sucesso, tempo total
- Lista completa de emails enviados e emails com falha

### Otimizações v3.0

| Mudança | Antes | Depois |
|---------|-------|--------|
| Retry strategy | Linear 5s | Exponencial 2s→4s→8s |
| Timeout SMTP | 10s | 3s |
| Batch delay | 5s/lote | 0s/lote |
| Lookup duplicatas | N queries SQL | Pré-carregamento em memória (O(1)) |
| BD durante envio | Conectado | Desconectado (reconecta no final) |

---

## Schema de Banco de Dados

### Tabelas Principais

- **tbl_contacts:** id, email, unsubscribed, created_at
- **tbl_contact_tags:** contact_id, tag_id (N:N)
- **tbl_tags:** id, tag_name
- **tbl_messages:** id, subject, html_body, created_at
- **tbl_message_logs:** id, contact_id, message_id, event_type, created_at
- **tbl_events:** id, sympla_id, nome, link, cupom
- **tbl_leads:** id, contact_id, score
- tbl_unsubscribes, tbl_bounces (+ outros)

---

## Segurança

- Credenciais apenas em `.env` (não versionado)
- 4 níveis de proteção contra duplicatas
- Confirmação explícita ("SIM") antes de envio em produção
- Retry com backoff exponencial no SMTP

---

## Performance

| Volume | Antes v3.0 | Depois v3.0 |
|--------|-----------|------------|
| 100 emails | ~11s | ~7s (-39%) |
| 1.000 emails | ~1,8 min | ~1,1 min (-39%) |
| 10.000 emails | ~18 min | ~11 min (-39%) |

---

## Deployment (VPS)

```bash
git clone <repo>
cd treineinsite
uv sync
cp .env.example .env && nano .env   # configurar credenciais
# Executar
uv run treineinsite-sendemails
```

Variáveis obrigatórias no `.env`: `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `SMTP_HOST_OVERRIDE`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`

---

## Roadmap

| Item | Status |
|------|--------|
| `hardbounce_manager.py` — buscar hardbounces da Locaweb e taggear contatos | TODO |
| API REST (`/api/send`, `/api/status`) | FastAPI no stack, não exposta |
| Scheduling | Não iniciado |

### Fora do Escopo
- Tracking de opens/clicks
- Lead scoring automático
- Testes A/B
- Integração Sympla direta

---

## Histórico de Versões

### v3.1 — Abril 2026
- Adicionado comando `bounces` (hardbounce management via Locaweb SMTP)
- Removidas variantes `email_service_minimal.py` e `email_service_simple.py`
- Menu CLI expandido de 7 para 8 opções
- `hardbounce_manager.py` pendente de implementação

### v3.0 — Novembro 2025
- SMTP timeout 10s → 3s
- Retry linear → backoff exponencial
- Batch delay 5s → 0s
- Pré-carregamento de duplicatas em memória
- Ganho geral: +39% de performance

### v2.0.1 — 6 Novembro 2025
- **Bug crítico:** `select_recipients_for_message.sql` retornava 18.372 no modo TESTE
- **Causa:** Precedência de operadores SQL sem parênteses
- **Fix:** Parênteses explícitos em `AND (... OR $1 = TRUE)`

### v2.0 — 6 Novembro 2025
- Refatoração completa (KISS)
- CLI interativa com Typer + Rich
- Configuração 100% externa

---

**Documento atualizado:** Abril 2026 | **Versão:** 3.1
