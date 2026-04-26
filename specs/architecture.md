# Architecture — Treineinsite Email Sender

**Version:** 3.1 | **Updated:** April 2026

---

## Stack

| Camada | Tecnologia | Papel |
|--------|-----------|-------|
| CLI | Typer + Rich | Interface interativa e subcomandos |
| Serviço | Python 3.12+ | Lógica de negócio e orquestração |
| SMTP | smtplib (stdlib) | Entrega de emails |
| Banco | PostgreSQL + psycopg3 | Persistência de contatos e logs |
| Config | YAML + .env | Configuração externa (sem hard-code) |
| Build | uv | Gestão de dependências |

---

## Módulos

```
src/email_sender/
├── cli.py                 # Ponto de entrada — menu e subcomandos
├── email_service.py       # Orquestrador do envio em lote
├── smtp_manager.py        # Conexão SMTP + retry backoff exponencial
├── db.py                  # Acesso ao BD (queries carregadas de .sql)
├── config.py              # Carrega config.yaml, email.yaml e .env
└── hardbounce_manager.py  # [TODO] Fetch e tag de hardbounces (Locaweb)
```

### Responsabilidades

| Módulo | Responsabilidade |
|--------|----------------|
| `cli.py` | Parse de argumentos, menu interativo, confirmações, disparo dos serviços |
| `email_service.py` | Fluxo completo de envio: busca contatos, dedup, SMTP, logs em batch |
| `smtp_manager.py` | Conexão, envio com retry, timeout, backoff exponencial |
| `db.py` | Conexão PostgreSQL, execução de queries SQL externas |
| `config.py` | Leitura de YAML + .env, placeholders do template, save de email.yaml |
| `hardbounce_manager.py` | [TODO] Fetch hardbounces da API Locaweb, tag `bounce` nos contatos |

---

## Configuração

Dois arquivos YAML + variáveis de ambiente:

| Arquivo | Conteúdo |
|---------|---------|
| `config/config.yaml` | SMTP host/port/timeout/retry, batch_size, batch_delay, template_path |
| `config/email.yaml` | Dados dinâmicos: assunto, evento (nome, data, local, link, cupom), promoção |
| `.env` | Credenciais: PostgreSQL (PG*), SMTP (SMTP_*), ENVIRONMENT |

`config.py` aplica precedência: `.env` sobrescreve `config.yaml` para SMTP host/credenciais.

---

## Fluxo de Envio

```
CLI.send()
  │
  ├─ [1] DB.connect()
  ├─ [2] Valida mensagem (check_message_exists / check_message_valid)
  │       └─ Carrega subject e template HTML de email.yaml + email.html
  │           └─ Substitui placeholders ({cidade}, {data_evento}, etc.)
  ├─ [3] DB.fetch_all(select_recipients)
  │       └─ Modo teste  → select_recipients_for_message_test_mode.sql (tag 'Test')
  │       └─ Produção    → select_recipients_for_message.sql (todos elegíveis)
  │       └─ Target mode → select_contact_by_email.sql
  ├─ [3.5] Pré-carrega IDs já enviados em memória (só produção)
  │         └─ check_all_emails_already_sent.sql → Set[contact_id]
  ├─ [3.6] DB.close()  ← libera conexão antes do gargalo SMTP
  │
  ├─ [4] SMTP.connect()
  ├─ [5] Loop sobre contatos
  │       ├─ Proteção 1: contact_id in _sent_contacts (memória da sessão)
  │       ├─ Proteção 2: contact_id in already_sent_ids (pré-carregado, O(1))
  │       ├─ smtp_manager.send_email(to, subject, html)
  │       │   └─ Retry: 2s → 4s → 8s (backoff exponencial, max 3 tentativas)
  │       └─ Marca contact_id em _sent_contacts
  ├─ [6] SMTP.disconnect()
  │
  ├─ [7] DB.connect()  ← reconecta só ao final
  ├─ [7.1] Batch insert em tbl_message_logs (só produção)
  ├─ [7.2] mark_message_processed (só produção)
  ├─ [7.3] DB.close()
  └─ [8] Gera relatório reports/email_report_YYYYMMDD_HHMMSS.txt
```

---

## Proteção Contra Duplicatas (4 Níveis)

| Nível | Mecanismo | Onde |
|-------|----------|------|
| 1 | `Set _sent_contacts` em memória | Sessão atual |
| 2 | Set pré-carregado do BD (O(1) lookup) | Produção — antes do loop |
| 3 | `tbl_message_logs` — constraint UNIQUE | BD — impede insert duplicado |
| 4 | Exclusão por tags (`bounce`, `invalid`, `unsubscribed`) | SQL de seleção |

---

## Queries SQL

Todas as queries ficam em arquivos `.sql` sob `sql/`. O `db.py` as carrega por caminho.

| Diretório | Propósito |
|-----------|----------|
| `sql/contacts/` | Seleção de destinatários elegíveis, busca por email, inserção |
| `sql/messages/` | Validação, logs de envio, flags de processamento |
| `sql/events/` | CRUD de eventos |
| `sql/tags/` | Atribuição de tags (bounce, click, open) |
| `sql/leads/` | Score de leads |
| `sql/maintenance/` | Índices, dedup, manutenção geral |
| `sql/migrations/` | Alterações de schema |
| `sql/analysis/` | Queries de análise ad-hoc |

---

## Modo Teste vs Produção

| Comportamento | Teste | Produção |
|--------------|-------|---------|
| Contatos selecionados | Tag `Test` | Todos elegíveis |
| Proteção 2 (pré-carregamento) | Desativada | Ativada |
| Grava `tbl_message_logs` | Não | Sim |
| Marca mensagem como processada | Não | Sim |
| Confirmação interativa | Não | Sim ("SIM") |
| Flags limpas após envio | Sim (auto) | Só com `--clear-flags` |

---

## Decisões de Design

**BD desconectado durante envio SMTP**
O gargalo é o SMTP. A conexão de BD é liberada antes do loop e reconectada só ao final para batch insert. Evita timeout de conexão idle e reduz contenção.

**Queries em arquivos `.sql` externos**
Facilita auditoria, versionamento e trocas sem alterar Python. `db.py` carrega o arquivo pelo caminho.

**Sem ORM**
psycopg3 direto. O schema é estável e as queries são simples — ORM seria overhead sem ganho.

**Configuração 100% externa**
Nenhuma credencial ou dado de campanha no código. `config.yaml` para operacional, `email.yaml` para conteúdo de campanha, `.env` para segredos.

**Sem GenAI no envio**
O assunto vem de `email.yaml` (editado via `edit-event`). Geração automática com Gemini foi planejada mas não implementada — fora do escopo atual.

---

## Pendências

| Item | Impacto |
|------|---------|
| `hardbounce_manager.py` não implementado | Comando `bounces` falha em runtime |
| `hardbounce_manager.py` não implementado | Hardbounces da Locaweb não são processados automaticamente |
