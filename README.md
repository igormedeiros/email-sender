# Email Sender - Sistema Minimalista de Envio de Emails em Lote

Sistema robusto e production-ready para envio de emails em lote a partir de um banco de dados PostgreSQL. Projetado com princípios **KISS (Keep It Simple, Stupid)** para máxima clareza e manutenibilidade.

**Status:** ✅ Production Ready | **Version:** 2.0 | **Last Updated:** November 7, 2025

---

## 📋 Índice

1. [Quick Start](#-quick-start)
2. [Funcionalidades](#-funcionalidades)
3. [Instalação Detalhada](#-instalação-detalhada)
4. [Uso e Comandos](#-uso-e-comandos)
5. [Menu de Produção (Clear Flags)](#-menu-de-produção-clear-flags)
6. [Configuração](#-configuração)
7. [Arquitetura](#-arquitetura)
8. [Proteção Contra Duplicatas](#-proteção-contra-duplicatas-4-níveis)
9. [Relatórios](#-relatórios)
10. [Performance](#-performance)
11. [Segurança](#-segurança)
12. [Banco de Dados](#-banco-de-dados)
13. [Testes](#-testes)
14. [Deployment](#-deployment)
15. [Desenvolvimento](#-desenvolvimento)
16. [Changelog](#-changelog)

---

## 🚀 Quick Start

### Instalação Rápida

```bash
# 1. Clone e configure
git clone <repo>
cd treineinsite
uv sync

# 2. Configure credenciais
cp .env.example .env
nano .env  # edite com suas credenciais

# 3. Configure aplicação
cp config/config.yaml.example config/config.yaml
cp config/email.yaml.example config/email.yaml

# 4. Teste e execute
python -m email_sender.cli test-smtp
uv run -m email_sender.cli
```

---

## 📋 Funcionalidades

- ✉️ **Envio em Lote:** Processa até 200 emails por lote (configurável)
- 🔄 **Retry Automático:** 2 tentativas com backoff exponencial
- 🛡️ **Anti-Duplicata:** 4 níveis de proteção (memória, dict, BD, tags)
- 📊 **Relatórios:** Saída em tempo real + arquivo de log
- 🎯 **Filtragem:** Automática de descadastrados, bounces, inválidos
- 🤖 **GenAI:** Geração automática de assuntos (Google Gemini)
- 🔧 **Configuração Externa:** 100% YAML + .env (sem hardcoding)
- ⚡ **Performance:** 1.000 emails em ~2 minutos
- 🔄 **Menu de Produção:** Opção de limpar flags antes de reenviar
- 📈 **Progress Tracking:** Percentual e ETA durante envio
- 📁 **Relatórios em Arquivo:** Txt com lista de enviados/falhados

---

## 🔧 Instalação Detalhada

### Pré-requisitos

- Python 3.12+
- PostgreSQL 12+
- uv (gerenciador de dependências): https://docs.astral.sh/uv/

### Passo 1: Clonar e Configurar Ambiente

```bash
git clone <repository-url>
cd treineinsite
uv sync
```

### Passo 2: Copiar Arquivos de Exemplo

```bash
cp .env.example .env
cp config/config.yaml.example config/config.yaml
cp config/email.yaml.example config/email.yaml
cp config/templates/email.html.example config/templates/email.html
```

### Passo 3: Configurar Credenciais (.env)

```bash
nano .env
```

Exemplo:
```bash
# Banco de Dados
DB_HOST=easypanel.treineinsite.com.br
DB_PORT=5432
DB_USER=seu_usuario
DB_PASSWORD=sua_senha_postgres
DB_NAME=treineinsite

# SMTP
SMTP_USERNAME=seu_usuario_smtp
SMTP_PASSWORD=sua_senha_smtp

# GenAI (opcional)
GENAI_API_KEY=sua_chave_google_gemini
```

### Passo 4: Configurar Aplicação (config.yaml)

```yaml
database:
  host: easypanel.treineinsite.com.br
  port: 5432
  user: seu_usuario
  password: ${DB_PASSWORD}
  database: treineinsite

smtp:
  host: smtplw.com.br
  port: 587
  user: ${SMTP_USERNAME}
  password: ${SMTP_PASSWORD}
  use_tls: true
  retry_attempts: 2
  retry_delay: 5
  send_timeout: 10

email:
  sender: "Treineinsite <contato@treineinsite.com>"
  batch_size: 200
  batch_delay: 5
```

### Passo 5: Configurar Conteúdo de Email (email.yaml)

```yaml
evento:
  nome: "POWER TREINE (SP) - Proteção e Seletividade"
  link: "https://www.sympla.com.br/evento/..."
  data: "8 e 9 de novembro"
  cidade: "São Paulo"
  local: "Wyndham São Paulo Ibirapuera"
  cupom: "BlackFriday"

email:
  subject: "🔥 BLACK FRIDAY: 50% OFF no Curso de Proteção..."
  template_path: "config/templates/email.html"
```

### Passo 6: Testar Conexão

```bash
python -m email_sender.cli test-smtp
```

---

## 💻 Uso e Comandos

### Menu Interativo (Recomendado)

```bash
uv run -m email_sender.cli
```

**Opções:**
```
Treineinsite • Email Sender CLI

1 - Enviar emails
2 - Testar SMTP
3 - Ver contatos
4 - Importar contatos (CSV)
5 - Sair
```

### Opção 1: Enviar Emails

```
Escolha: 1

Modo de envio:
1 - Teste (contatos com tag 'Test') [padrão]
2 - ⚠️  Produção (TODOS os contatos)

Escolha [1-2]: 1

✓ Modo TESTE - contatos com tag 'Test'

═══════════════════════════════════════════════
📋 Dados do Email a Enviar
═══════════════════════════════════════════════
Assunto: 🔥 BLACK FRIDAY: 50% OFF...
Evento: POWER TREINE (SP)
Data: 8 e 9 de novembro
Local: Wyndham São Paulo Ibirapuera
Cupom: BlackFriday
Modo: TESTE (tag 'Test')
═══════════════════════════════════════════════

Continuar com o envio? (s/n): s

Iniciando envio de emails...
📧 igor.medeiros@gmail.com
✅ Email enviado para igor.medeiros@gmail.com

Relatório salvo em: reports/email_report_20251107_094047.txt

Resumo do Envio:
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Métrica          ┃ Valor ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total processado │ 1     │
│ Enviados         │ 1     │
│ Falhas           │ 0     │
└──────────────────┴───────┘
```

### Opção 2: Testar SMTP

```
Escolha: 2

Testando conexão SMTP...
✅ Conexão SMTP estabelecida com sucesso
```

### Opção 3: Ver Contatos

```
Escolha: 3

Encontrados 14569 contatos elegíveis

│ ID   │ Email                │
├──────┼──────────────────────┤
│ 123  │ usuario1@example.com │
│ 124  │ usuario2@example.com │
│ ... + 14569 mais
```

### Opção 4: Importar Contatos

1. Crie arquivo `contacts.csv`:
```csv
email
fulano@example.com
beltrano@example.com
```

2. Escolha opção 4 no menu

---

## 🚀 Menu de Produção (Clear Flags)

### O Problema

Quando você quer **reenviar uma mesma mensagem** para a **mesma base de contatos**, o sistema tem proteção contra duplicatas. Portanto, precisa limpar os históricos antigos.

### Como Funciona

Ao escolher **Modo de Produção (opção 2)**, você vê um menu com 3 opções:

```
⚠️  MODO PRODUÇÃO - CUIDADO!

Opções:
1 - Enviar normalmente (sem limpar flags)
2 - Limpar flags antes de enviar (reenviar para todos)
3 - Cancelar

Escolha [1-3]: 
```

### Opções Disponíveis

| # | Opção | O que faz | Quando usar |
|---|-------|----------|------------|
| **1** | Enviar normalmente | Envia apenas para quem **NÃO recebeu** | ✅ Primeira vez |
| **2** | Limpar flags | **DELETE** logs antigos + reenviar para **TODOS** | 🔄 Reenvio em massa |
| **3** | Cancelar | Cancela sem fazer nada | ❌ Cancelar |

### O que "Limpar Flags" faz

```sql
-- Deleta registros de envio anterior
DELETE FROM tbl_message_logs 
WHERE message_id = 1 AND event_type = 'sent';

-- Marca mensagem como não processada (permite reenvio)
UPDATE tbl_messages 
SET processed = FALSE 
WHERE id = 1;
```

### Exemplos de Uso

#### ✅ Exemplo 1: Primeira vez enviando para produção
```
Escolha [1-3]: 1  # Enviar normalmente
Tem certeza? Digite 'SIM' para confirmar: SIM
```
✅ Envia para quem ainda não recebeu

#### 🔄 Exemplo 2: Reenviar para TODOS os contatos
```
Escolha [1-3]: 2  # Limpar flags
Limpando flags de envio anteriores...
✅ Flags limpos com sucesso!

Tem certeza? Digite 'SIM' para confirmar: SIM
```
✅ Limpa histórico + envia para todos

#### ❌ Exemplo 3: Cancelar operação
```
Escolha [1-3]: 3  # Cancelar
Operação cancelada.
```
✅ Retorna ao menu

### Importante

- **Modo TESTE**: Permite reenvio **automaticamente** (sem menu de flags)
- **Modo PRODUÇÃO**: Oferece escolha entre enviar normalmente, limpar flags, ou cancelar
- **Confirmação obrigatória**: Requer digitar "SIM" para confirmar qualquer operação

---

## 🔧 Configuração

### config.yaml (Operacional)

```yaml
database:
  host: localhost
  port: 5432
  user: postgres
  password: ${DB_PASSWORD}
  database: treineinsite

smtp:
  host: smtplw.com.br
  port: 587
  user: ${SMTP_USERNAME}
  password: ${SMTP_PASSWORD}
  use_tls: true
  retry_attempts: 2
  retry_delay: 5
  send_timeout: 10

email:
  sender: "Treineinsite <contato@treineinsite.com>"
  batch_size: 200
  batch_delay: 5
  test_recipient: "test@example.com"
```

### .env (Credenciais - NÃO versionado)

```bash
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=sua_senha_postgres
DB_NAME=treineinsite

SMTP_USERNAME=seu_usuario_smtp
SMTP_PASSWORD=sua_senha_smtp

GENAI_API_KEY=sua_chave_google_gemini
```

### email.yaml (Conteúdo Dinâmico - NÃO versionado)

```yaml
evento:
  nome: "Curso de Proteção"
  link: "https://exemplo.com/evento"
  data: "15 e 16 de março"
  cidade: "São Paulo"
  local: "Local do Evento"
  cupom: "PROMO30"

email:
  subject: "🔥 30% OFF - Curso de Proteção em São Paulo"
  template_path: "config/templates/email.html"

promocao:
  desconto: "30%"
```

---

## 🏗️ Arquitetura

### Stack Tecnológico

| Componente | Tecnologia | Propósito |
|-----------|-----------|----------|
| Linguagem | Python 3.12+ | Core do sistema |
| CLI | Typer + Rich | Interface de linha de comando |
| Banco | PostgreSQL + psycopg | Persistência e lógica |
| SMTP | smtplib (stdlib) | Envio de emails |
| IA | Google Gemini | Geração de assuntos |
| Config | YAML + .env | Configuração externa |
| Build | uv | Gerenciador de dependências |

### Componentes Principais

- **cli.py** - Interface CLI com menu interativo
- **email_service.py** - Lógica central de envio + deduplicação (4 níveis)
- **smtp_manager.py** - Gerenciador de conexões SMTP com retry
- **db.py** - Camada de acesso a PostgreSQL
- **config.py** - Gerenciador de configurações YAML + .env
- **utils/ui.py** - Componentes de UI com Rich

### Estrutura de Arquivos

```
src/email_sender/       # Core
├── cli.py
├── email_service.py
├── smtp_manager.py
├── db.py
├── config.py
└── utils/
    └── ui.py

config/                 # Configuração
├── config.yaml
├── email.yaml
└── templates/
    └── email.html

sql/                    # Queries
├── contacts/
│   ├── select_recipients_for_message.sql
│   └── check_contact_exclusions.sql
├── messages/
│   ├── check_message_sent.sql
│   ├── insert_message_sent_log.sql
│   └── create_message.sql

tests/                  # Testes
├── conftest.py
└── unit/
    ├── test_email_service.py
    ├── test_smtp_manager.py
    ├── test_db.py
    └── test_config.py

reports/                # Relatórios gerados
```

---

## 🛡️ Proteção Contra Duplicatas (4 Níveis)

O sistema implementa 4 camadas de proteção para evitar envio duplicado:

### 1️⃣ Nível 1: Memória (Sessão Atual)

```python
self._sent_contacts = set()

if contact_id in self._sent_contacts:
    continue  # Já enviado nesta sessão
```

**Quando:** Durante o envio
**Cobertura:** Toda a sessão do programa

### 2️⃣ Nível 2: Dict (Contagem por Mensagem)

```python
if contact_id in sent_dict:
    sent_dict[contact_id] += 1
    if sent_dict[contact_id] > 1:
        continue  # Duplicado detectado
```

**Quando:** Durante iteração
**Cobertura:** Por mensagem

### 3️⃣ Nível 3: Banco de Dados

```sql
SELECT id FROM tbl_message_logs
WHERE contact_id = 8878 
  AND message_id = 1 
  AND event_type = 'sent'
```

**Quando:** Antes de enviar (APENAS PRODUÇÃO)
**Cobertura:** Histórico completo

### 4️⃣ Nível 4: Tags de Exclusão

```sql
SELECT contact_id FROM tbl_contact_tags ctg
INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
WHERE LOWER(tg.tag_name) IN (
  'unsubscribed', 'bounce', 'invalid', 'problem'
)
```

**Quando:** Ao carregar contatos
**Cobertura:** Todas as execuções

### 📊 Resumo

| Nível | Tipo | Modo Prod | Modo Teste |
|-------|------|----------|-----------|
| 1 | Memória | ✅ Ativo | ✅ Ativo |
| 2 | Dict | ✅ Ativo | ✅ Ativo |
| 3 | BD | ✅ Ativo | ❌ Bypass |
| 4 | Tags | ✅ Ativo | ✅ Ativo |

---

## 📊 Relatórios

### Formato do Arquivo

Gerados automaticamente em `reports/email_report_YYYYMMDD_HHMMSS.txt`

**Exemplo:**
```
================================================================================
RELATÓRIO DE ENVIO DE EMAILS
================================================================================

Data/Hora: 07/11/2025 09:40:47
Tempo total: 0.2s

Resumo:
  Total processado: 1
  Enviados com sucesso: 1
  Falhas: 0
  Taxa de sucesso: 100.0%

================================================================================
EMAILS ENVIADOS COM SUCESSO
================================================================================
  ✓ igor.medeiros@gmail.com

================================================================================
EMAILS COM FALHA
================================================================================
  Nenhuma falha.

================================================================================
```

### Conteúdo

- Data e hora do envio
- Tempo total de execução
- Total de contatos processados
- Enviados com sucesso
- Falhas registradas
- Taxa de sucesso percentual
- Lista completa de emails enviados
- Lista completa de emails com falha

---

## 📈 Performance

| Métrica | Valor |
|---------|-------|
| Emails/minuto | ~500 |
| 1.000 emails | ~2 minutos |
| 10.000 emails | ~20 minutos |
| Memória (1000 emails) | ~50MB |
| Startup time | <1s |
| Conexão SMTP | Reutilizada |

### Otimizações

- ✅ Reuso de conexão SMTP
- ✅ Batch processing (200 emails/lote)
- ✅ Índices no PostgreSQL
- ✅ Queries otimizadas
- ✅ Logging minimalista (INFO)
- ✅ Progress tracking com ETA

---

## 🔒 Segurança

### Dados Sensíveis

- ✅ Credenciais em `.env` (não versionado)
- ✅ Configurações em `config/` (não versionado)
- ✅ Templates em `templates/` (não versionado)
- ✅ Sem hardcoding no código

### Integridade

- ✅ 4 níveis de proteção contra duplicatas
- ✅ Autocommit no PostgreSQL
- ✅ Tratamento de exceções
- ✅ Logs detalhados
- ✅ Rastreamento de estado

### .gitignore

```
.env
config/config.yaml
config/email.yaml
config/templates/email.html
reports/
*.log
__pycache__/
.pytest_cache/
```

---

## 🗄️ Banco de Dados

### Tabelas Principais

- **tbl_contacts** - Contatos (id, email, unsubscribed, is_buyer)
- **tbl_contact_tags** - Tags por contato (N:N)
- **tbl_messages** - Mensagens (subject, html_body, processed)
- **tbl_message_logs** - Logs de envio (contact_id, message_id, event_type)
- **tbl_tags** - Tags disponíveis

### Tags de Exclusão

- `unsubscribed` - Descadastrados
- `bounce` - Emails que retornaram
- `invalid` - Emails inválidos
- `problem` - Contatos com problemas de envio
- `Test` - Contatos de teste (só aparecem em modo teste)

### Filtros Automáticos

- ✅ Tag `unsubscribed` = ignorado
- ✅ Tag `bounce` = ignorado
- ✅ Tag `invalid` = ignorado
- ✅ Tag `problem` = ignorado
- ✅ Modo `test` = apenas tag `Test`
- ✅ Modo `production` = todos elegíveis

---

## 🧪 Testes

### Executar

```bash
# Todos os testes
uv run pytest

# Com cobertura
uv run pytest --cov=src/email_sender --cov-report=html

# Testes específicos
uv run pytest tests/unit/test_email_service.py -v
uv run pytest tests/unit/test_smtp_manager.py -v
```

### Requisitos

- Mínimo 85% cobertura
- Sem acesso à rede (mocks)
- Fixtures em `conftest.py`
- Testes isolados

---

## 🚀 Deployment

### Em VPS 24/7

Crie arquivo: `/etc/systemd/system/email-sender.service`

```ini
[Unit]
Description=Treineinsite Email Sender
After=network.target

[Service]
Type=simple
User=emailsender
WorkingDirectory=/home/emailsender/treineinsite
ExecStart=/home/emailsender/.local/bin/uv run -m email_sender.cli
Restart=on-failure
RestartSec=60

[Install]
WantedBy=multi-user.target
```

Ativar:
```bash
sudo systemctl enable email-sender
sudo systemctl start email-sender
sudo systemctl status email-sender
```

---

## 🔧 Desenvolvimento

### Princípios KISS

- ✅ Código simples e direto
- ✅ Poucas dependências
- ✅ Sem abstrações desnecessárias
- ✅ SQL em arquivos (não inline)
- ✅ Configuração externa

### Estrutura de Código

```python
# ✅ Correto
from email_sender.config import Config
from email_sender.email_service import EmailService

class EmailService:
    def __init__(self, config: Config, db: Database, smtp: SmtpManager):
        self.config = config
        self.db = db
        self.smtp = smtp
    
    def send_batch(self, message_id: int) -> dict:
        """Enviar emails com 4 níveis de deduplicação."""
        # Implementação limpa
```

### SQL em Arquivos

```python
# ✅ Correto
recipients = db.fetch_all("sql/contacts/select_recipients_for_message.sql", params)

# ❌ Errado (evitar)
recipients = db.fetch_all("""SELECT ... FROM tbl_contacts WHERE ...""", params)
```

---

## 📝 Changelog

### v2.0.2 - November 7, 2025

**🎯 Features Implementadas:**
- ✅ Menu de produção com opções de clear-flags
- ✅ Progress tracking com ETA
- ✅ Relatórios em arquivo (txt)
- ✅ Logging minimalista
- ✅ Consolidação de documentação no README

**🐛 Bugs Corrigidos:**
- ✅ Inverted deduplication logic (test mode)
- ✅ db.disconnect() → db.close()
- ✅ SQL recipients query (AND/OR precedence)

**🚀 Performance:**
- ✅ SMTP connection reuse (3-6x faster)
- ✅ Placeholder substitution
- ✅ Optimized batch processing

---

## 📞 Suporte

Para dúvidas ou problemas:

1. Consulte a documentação acima
2. Revise `src/email_sender/` para entender o código
3. Execute testes: `uv run pytest -v`
4. Verifique logs: `tail -f reports/email_report_*.txt`

---

**Version:** 2.0 | **Status:** Production Ready ✅ | **Last Updated:** November 7, 2025
