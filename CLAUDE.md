# Projeto: treineinsite — Email Sender

## Specs

As especificações completas do projeto estão em `specs/PRD.md`.

## Visão Geral

Sistema de envio de e-mails para **treineinsite.com.br**.

- Dispara e-mails para contatos armazenados no PostgreSQL
- Configurável via YAML (`config/email.yaml`) e variáveis de ambiente (`.env`)
- CLI em Python (`src/email_sender/cli.py`)

## Infraestrutura

**Este projeto deve rodar na VPS.** O ambiente local é apenas para desenvolvimento/teste.

As credenciais de acesso à VPS devem estar no arquivo `.env`:

```env
VPS_HOST=<ip ou hostname da VPS>
VPS_USER=<usuário SSH>
VPS_PORT=22
VPS_SSH_KEY=<caminho para a chave privada, ex: ~/.ssh/id_rsa>
```

## Stack

- Python 3.x
- PostgreSQL (banco de contatos)
- SMTP via `smtplw.com.br`
- `uv` para gestão de dependências

## Variáveis de Ambiente (`.env`)

| Variável | Descrição |
|:---------|:----------|
| `ENVIRONMENT` | `test` ou `production` |
| `PGHOST` | Host do PostgreSQL |
| `PGPORT` | Porta do PostgreSQL |
| `PGUSER` | Usuário do PostgreSQL |
| `PGPASSWORD` | Senha do PostgreSQL |
| `PGDATABASE` | Nome do banco |
| `PGSSLMODE` | SSL mode do PostgreSQL |
| `SMTP_HOST_OVERRIDE` | Host SMTP |
| `SMTP_PORT` | Porta SMTP |
| `SMTP_USERNAME` | Usuário SMTP |
| `SMTP_PASSWORD` | Senha SMTP |
| `SMTP_USE_TLS` | Usar TLS (`true`/`false`) |
| `VPS_HOST` | IP/hostname da VPS |
| `VPS_USER` | Usuário SSH da VPS |
| `VPS_PORT` | Porta SSH (padrão: 22) |
| `VPS_SSH_KEY` | Caminho da chave SSH privada |
