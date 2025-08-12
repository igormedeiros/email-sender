# Padrões de Projeto, Diretrizes e Instruções para Copilot/IA

Este documento consolida as diretrizes de engenharia e instruções de uso de IA no projeto.

## Stack, arquitetura e princípios
- Linguagem: Python 3.12+
- Tipo de app: CLI com Typer + Rich
- Princípios: KISS, Clean Code, Clean Architecture
- Paradigma: OO simples (preferir composição)
- GenAI: isolado e desacoplado do domínio

## Estrutura de pastas
```
.
├── src/
│   └── email_sender/
│       ├── cli.py
│       ├── application/
│       ├── domain/
│       ├── infrastructure/
│       └── interfaces/
├── tests/
│   ├── conftest.py
│   └── unit/
├── sql/
│   ├── contacts/
│   ├── messages/
│   ├── leads/
│   ├── tags/
│   └── events/
└── .github/
    └── copilot-instructions.md
```
- Apenas `src/` e `tests/` na raiz além de pastas utilitárias como `sql/`.

## Imports
- Nunca `import src.*`. Usar `from email_sender...`.

## CLI
- Comandos curtos e claros
- `--help` completo, Rich para UX
- Códigos de saída padronizados

## Organização do CLI
- `email_sender/cli.py` registra comandos e delega para casos de uso

## Clean Architecture
- Domain, Application, Interfaces (ports), Infrastructure (adapters)
- Dependências apontam para dentro

## Nova arquitetura (esqueleto recomendado)
```
src/email_sender/
  domain/
  interfaces/
  application/
  infrastructure/
  cli.py
```

## Eventos e notificações (Telegram)
- Notificar início/fim e resumos; ler credenciais do `.env`.

## .env (obrigatório)
- `ENVIRONMENT`, variáveis de Postgres e Telegram

## Regras de execução por ambiente
- `test`: não enviar para base real; apenas testes
- `prod`: filtros completos, retries e throttle

## LangChain e GenAI
- Componentes de IA em `infrastructure/genai/` e portas em `interfaces/`
- Prompts fora do código (ver seção SQL/Prompts)

## Erros, logs e observabilidade
- Exceções específicas; logs claros

## Testes
- `pytest`, sem acesso à rede; dublês nas interfaces

## Qualidade e estilo
- Black + isort (+ mypy quando fizer sentido)
- Nomes descritivos, funções curtas, poucos níveis de aninhamento

## Idioma e nomenclatura
- Identificadores em inglês; comentários/docstrings em PT‑BR

## Empacotamento e execução (uv)
- Usar `uv` para sync/add/remove/lock e executar `pytest`/CLI

## Convenções adicionais
- Funções puras no domínio, dependências injetadas

## Organização de SQL e Prompts (Regra)
- Não misturar consultas SQL ou prompts de IA dentro do código Python.
- Centralizar SQL em `sql/` com subpastas temáticas (`contacts/`, `messages/`, `events/`, `leads/`, `tags/`).
  - Cada `.sql` começa com cabeçalho de origem (workflow/nó) e variáveis usadas.
- Prompts de IA devem ser versionados fora do código Python, preferencialmente em:
  - `.github/business_rules.prompt.md` (regras de negócio)
  - `.github/copilot-instructions.md` (este documento)
  - `prompts/` (se necessário) para prompts operacionais
- O código deve referenciar arquivos externos (SQL/Prompts) por caminho via configuração; nunca inline.
