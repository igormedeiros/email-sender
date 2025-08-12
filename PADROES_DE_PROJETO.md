# Padrões de Projeto e Diretrizes de Engenharia

Este documento define como vamos construir e evoluir o projeto.

## Stack, arquitetura e princípios
- **Linguagem**: Python 3.12+
- **Tipo de app**: CLI com UX semelhante ao Cursor CLI (comandos expressivos, flags claras, ajuda rica, saída colorida)
- **Framework de CLI**: Typer + Rich
- **Princípios**: KISS, Clean Code, Clean Architecture
- **Paradigma**: orientação a objetos com simplicidade (modelos de domínio enxutos; classes coesas; evitar herança desnecessária; preferir composição)
- **GenAI**: usar LangChain apenas quando necessário para recursos de IA generativa; componentes de IA devem estar isolados e desacoplados do núcleo de domínio

## Estrutura de pastas
```
.
├── src/
│   └── email_sender/
│       ├── cli.py            # ponto de entrada do CLI
│       ├── __init__.py
│       ├── application/      # casos de uso (orquestram o domínio)
│       ├── domain/           # entidades e regras de negócio puras
│       ├── infrastructure/   # gateways, adapters (SMTP, arquivos, etc.)
│       └── interfaces/       # portas (protocolos/abstrações) para dependências externas
├── tests/
│   ├── conftest.py           # bloqueio de rede global e fixtures comuns
│   └── unit/                 # testes unitários por módulo
└── PADROES_DE_PROJETO.md
├── sql/                     # consultas SQL organizadas (extraídas de automações/workflows)
│   ├── contacts/
│   ├── messages/
│   ├── leads/
│   ├── tags/
│   └── events/
└── .github/
    └── copilot-instructions.md  # instruções ao Copilot/IA
```

- Apenas `src/` e `tests/` na raiz. Evitar diretórios paralelos desnecessários.
- O pacote do projeto vive em `src/email_sender`.

## Imports (nunca usar prefixo src)
- Nunca escrever imports do tipo `import src.alguma_coisa`.
- Os imports devem partir do pacote: `from email_sender.application.use_cases import ...`.
- A configuração do caminho já garante que `src/` esteja no `sys.path` (ver `conftest.py` na raiz e `pytest.ini`).

## CLI (semelhante ao Cursor CLI)
- Comandos top-level curtos e claros, por exemplo:
  - `email-sender send --to file.csv --template template.html`
  - `email-sender schedule --at "2025-08-11 09:00" --config config.yaml`
  - `email-sender validate --config config.yaml`
- Requisitos:
  - `--help` completo com exemplos
  - Saída colorida e barras de progresso (Rich)
  - Códigos de saída padronizados (0 sucesso; 1 erro de uso; 2 erro operacional)
  - Logs legíveis no terminal (nível INFO por padrão, DEBUG via `--verbose`)

### Interface de terminal (banner azul)
Banner sugerido com visual moderno em tons de azul claro (ANSI truecolor). Pode ser impresso no início do CLI:

```ansi
\x1b[38;2;102;178;255m _______ _____  ______  ___ ___ _   _ _______ _____ _   _  _____ _______\x1b[0m
\x1b[38;2;77;166;255m|__   __|_   _||  ____||_ _/ _ \\ | | |__   __|_   _| \\ | |/ ____|__   __|\x1b[0m
\x1b[38;2;51;153;255m   | |    | |  | |__    | | | | \\| |    | |    | | |  \\| | (___    | |   \x1b[0m
\x1b[38;2;26;140;255m   | |    | |  |  __|   | | | | . ` |    | |    | | | . ` |\\___ \\   | |   \x1b[0m
\x1b[38;2;0;128;255m   | |   _| |_ | |____ _| | |_| |\\  |    | |   _| |_| |\\  |____) |  | |   \x1b[0m
\x1b[38;2;0;102;204m   |_|  |_____||______|___|\\___/ |_|    |_|  |_____|_| \\_|_____/   |_|   \x1b[0m
```

### Organização do CLI
- `email_sender/cli.py`: define a aplicação Typer e registra comandos
- Cada comando mapeia para um caso de uso em `application/`
- Adapters (SMTP, leitura de CSV/YAML, etc.) ficam em `infrastructure/`
- O domínio (endereços, template, mensagem) está em `domain/` sem dependências externas

## Clean Architecture (camadas)
- **Domain**: entidades e regras puras; sem dependências com frameworks, IO ou rede
- **Application**: casos de uso orquestram entidades e portas; dependem do domínio e de interfaces
- **Interfaces (ports)**: Protocolos/ABCs descrevendo contratos de infraestrutura
- **Infrastructure (adapters)**: implementações concretas (SMTP, arquivo, memória, Postgres, Telegram). Ficam atrás das portas
- Dependências só apontam para dentro (nunca do domínio para fora)

### Nova arquitetura (a partir do zero)
```
src/email_sender/
  domain/
    entities/
      contact.py          # id, email, tags, flags (unsubscribed/bounced)
      message.py          # id, subject, internal_name, event_id, processed
      event.py            # dados do evento ativo (sympla_id, nome, datas, link)
      log.py              # message log: sent/opened/clicked
    value_objects/
      email_address.py    # validação forte de e-mail
    services/
      subject_generator.py # interface para geração de assuntos (opcional LangChain)
  interfaces/
    repositories/
      contacts_repo.py
      messages_repo.py
      events_repo.py
      logs_repo.py
      lead_score_repo.py
      tags_repo.py
    gateways/
      mail_sender.py      # porta para envio SMTP
      template_renderer.py
      telegram_notifier.py
      http_tracking.py    # porta para webhooks/pixel se mantivermos
  application/
    use_cases/
      send_campaign.py        # orquestra envio (seleção, render, envio, log, mark processed)
      track_open.py           # registra abertura
      track_click.py          # registra clique
      unsubscribe.py          # processa descadastro
      sync_bounces.py         # coleta bounces e aplica limpeza
      sync_unsubscribed.py    # aplica descadastros na base
    dto/
      send_campaign_dto.py
  infrastructure/
    repositories/
      postgres/...
      csv/...
    gateways/
      smtp_smtplib.py
      telegram_bot.py
      jinja_renderer.py
      http_flask.py (opcional)
  cli.py
```

- Cada caso de uso em `application/use_cases` dispara eventos de domínio (ex.: CampaignStarted, EmailSent, CampaignCompleted) que são observados por um `telegram_notifier` via porta.
- Em `test` (ENVIRONMENT), o `send_campaign` restringe a seleção a contatos de teste (ou usa repositório dedicado de testes). Em `prod`, aplica filtros completos.

### Eventos e notificações (Telegram)
- Eventos relevantes a notificar:
  - CampaignStarted: início de envio (modo, assunto, totals previstos)
  - EmailSent/Failed/Skipped: contadores agregados (não spam por item)
  - CampaignCompleted: resumo com enviados, falhas, pulados, duração
  - BouncesSyncStarted/Completed: totais de páginas, hard bounces marcados
  - UnsubscribeProcessed: totais marcados/afastados
- Porta `telegram_notifier` recebe mensagens formatadas; adapter lê credenciais do `.env`.

### .env (obrigatório)
- `ENVIRONMENT`: `prod` ou `test` (default: `test`)
- Postgres: `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
- Telegram Bot: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

### Regras de execução por ambiente
- `test`: nunca envia para base real; apenas emails de teste (repositório/segmentação específica); notificações Telegram podem ir para chat de teste
- `prod`: envia para base filtrada; aplica retries/throttle; notifica no chat de produção

## LangChain e GenAI
- Componentes de IA generativa devem ficar em `infrastructure/genai/` e expor portas em `interfaces/`
- Isolar prompts, modelos e providers (OpenAI, etc.) para facilitar troca/mock
- Fornecer fallback deterministicamente testável (ex.: caminhos que não usam rede em testes)
- Não acoplar o domínio à LangChain; apenas a implementações atrás de portas

## Erros, logs e observabilidade
- Usar exceções específicas no domínio (ex.: `InvalidRecipientError`)
- Tratar erros no nível de caso de uso, traduzindo para mensagens claras no CLI
- Logging estruturado (Rich + logging) com níveis adequados

## Testes
- Test runner: `pytest`
- `pytest.ini` aponta para `tests/`
- Nada em testes pode acessar rede. Isso é globalmente bloqueado em `tests/conftest.py`
- Unidades testadas com dublês (mocks/stubs/fakes) das interfaces
- Nomes de testes: `tests/unit/test_<modulo>_<comportamento>.py`
- Cobertura mínima pode ser definida quando estabilizarmos o escopo

## Qualidade e estilo
- Black + isort + mypy (quando fizer sentido nas fronteiras)
- Clean Code: nomes descritivos, funções curtas, poucas responsabilidades por módulo
- Comentários explicam o "porquê" (não o óbvio)
- Preferir composição sobre herança; separar parsing/IO do núcleo do domínio

### Idioma e nomenclatura
- Nomes de variáveis, funções, classes, módulos e pacotes: sempre em inglês (ex.: `emailAddress`, `sendCampaign`, `SmtpManager`).
- Comentários e docstrings: sempre em português (PT‑BR), claros e objetivos.
- Evitar misturar idiomas no mesmo identificador ou comentário.

## Empacotamento e execução
- Pacote `email_sender` em `src/`
- Entry point recomendável (exemplo `pyproject.toml`):

```toml
[project.scripts]
email-sender = "email_sender.cli:app"
```

- O binário `email-sender` invoca a aplicação Typer `app`.

## Gestão de dependências e execução (uv)
- Sempre usar `uv` (PEP 735) para instalar, travar e executar.
- Comandos usuais:
  - Instalar deps (todas as groups): `uv sync --all-groups`
  - Adicionar dependência: `uv add <package>`; em dev: `uv add -G dev <package>`
  - Remover dependência: `uv remove <package>`
  - Atualizar lock: `uv lock --refresh`
  - Rodar testes: `uv run pytest`
  - Rodar CLI sem entrypoint (módulo atual): `uv run python -m email_sender.controller_cli --help`
  - Rodar CLI com entrypoint (quando definido): `uv run email-sender --help`

## Convenções adicionais
- Funções puras no domínio facilitam testes
- Não propagar tipos dinâmicos sem necessidade; anotar assinaturas públicas
- Evitar efeitos colaterais implícitos; explicitar dependências via injeção (ports/adapters)

## Organização de SQL e Prompts (Regra)
- **Não** misturar consultas SQL ou prompts de IA dentro do código Python.
- Centralizar SQL em `sql/` com subpastas temáticas (`contacts/`, `messages/`, `events/`, `leads/`, `tags/`).
  - Cada arquivo `.sql` deve começar com um cabeçalho comentando a origem (ex.: `Source: n8n/<workflow>.json -> <node>`), variáveis de template e propósito.
- Prompts de IA (quando existirem) devem ser versionados fora do código Python, idealmente em:
  - `.github/business_rules.prompt.md` para regras de negócio
  - `.github/copilot-instructions.md` para instruções de desenvolvimento/IA
  - `prompts/` (se necessário) para prompts operacionais, mantendo-os referenciados por caminho.
- O código Python deve carregar SQL/Prompts por caminho (injetado via config) e nunca como string embedada.
