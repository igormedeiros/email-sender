# Email Sender

Sistema robusto para envio de emails em lote com suporte a banco de dados PostgreSQL, backup automático e relatórios detalhados. Todas as configurações são mantidas em arquivos YAML externos, sem valores hardcoded no código.

## 📋 Índice

- [Recursos](#recursos)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Estrutura dos Dados](#estrutura-dos-dados)
- [Relatórios](#relatórios)
- [Versionamento](#versionamento)
- [Desenvolvimento](#desenvolvimento)
- [API REST](#api-rest)
- [Autenticação JWT](#autenticação-jwt)

## 🚀 Recursos

- ✉️ Envio de emails em lote a partir do banco de dados PostgreSQL
- 🔄 Backup automático e restauração em caso de falhas
- 📊 Relatórios detalhados de envio
- ⏱️ Controle de taxa de envio e intervalos entre lotes
- 🔁 Sistema de retentativas automáticas
- 💾 Salvamento periódico do progresso
- 🛡️ Tratamento seguro de interrupções
- 📝 Suporte a templates de email personalizáveis
- 🚫 Gerenciamento automático de descadastros (unsubscribe)
- 🚫 Gerenciamento de emails com bounce
- 🔧 Configuração 100% externa via arquivos YAML (sem valores hardcoded)
- 🌐 API REST para todas as funcionalidades
- 🔌 Arquitetura desacoplada com controllers e service
- ⏯️ Retomada automática de processos interrompidos

## 🛠️ Requisitos

- Python 3.12+
- uv (gerenciador de dependências rápido)
  - Instalação: veja as instruções em `https://docs.astral.sh/uv/` (Linux/Mac/Windows)
- Acesso a um servidor SMTP

## 🚀 Como usar (rápido)

- Interativo (recomendado):
  ```bash
  uv run treineinsite-sendemails
  ```
  - Setas para navegar; Enter para selecionar; TAB alterna `ENVIRONMENT` entre `test` e `production`.
  - Se o prompt/lista ficarem "colados" em uma linha, rode sem buffer:
    ```bash
    uv run -u treineinsite-sendemails
    # ou
    PYTHONUNBUFFERED=1 uv run treineinsite-sendemails
    ```

- Enviar emails sem menu (modo avançado):
  ```bash
  uv run python -m email_sender.controller_cli send-emails --mode=test --content config/email.yaml
  uv run python -m email_sender.controller_cli send-emails --mode=production --content config/email.yaml
  ```

- Iniciar API REST:
  ```bash
  uv run python -m email_sender.rest_api
  ```

## ⚙️ Instalação (com uv)

1. Clone o repositório:

   ```bash
   git clone <repository-url>
   cd email-sender
   ```

2. Sincronize dependências com uv (cria o ambiente automaticamente):

   ```bash
   uv sync
   ```

3. Execute a CLI (exemplos):

   ```bash
   # Modo interativo (menu)
   uv run treineinsite-sendemails

   # Modo não interativo (Typer)
   uv run python -m email_sender.controller_cli send-emails --mode=test --content config/email.yaml
   ```

## 📝 Configuração

> ℹ️ **Importante**: O sistema utiliza exclusivamente arquivos YAML para todas as configurações. Nenhuma configuração é hardcoded no código fonte.

1. O sistema utiliza arquivos YAML para configuração e um arquivo .env para credenciais. Os arquivos originais não estão versionados, então você precisará criar cópias dos exemplos:

```bash
# Copie os arquivos de exemplo para os nomes corretos
cp example_config.yaml config/config.yaml
cp example_email.yaml config/email.yaml
cp config/rest.yaml.example config/rest.yaml
cp config/api-docs.yaml.example config/api-docs.yaml
cp templates/email.html.example templates/email.html
cp .env.example .env

# Edite as credenciais
nano .env  # Coloque suas credenciais SMTP
```

2. Configure as opções no arquivo `config/config.yaml`:

| Seção | Chave          | Descrição                         | Exemplo        |
| ----- | -------------- | --------------------------------- | -------------- |
| smtp  | host           | Servidor SMTP                     | smtp.gmail.com |
| smtp  | port           | Porta SMTP                        | 587            |
| smtp  | use_tls        | Usar TLS                          | true           |
| smtp  | retry_attempts | Número de tentativas              | 3              |
| smtp  | retry_delay    | Delay entre tentativas (segundos) | 5              |
| smtp  | send_timeout   | Timeout de envio (segundos)       | 10             |

3. Configure as credenciais SMTP no arquivo `.env`:

| Variável             | Descrição                           | Exemplo       |
| -------------------- | ----------------------------------- | ------------- |
| SMTP_USERNAME        | Usuário SMTP                        | seu@email.com |
| SMTP_PASSWORD        | Senha SMTP                          | sua_senha     |
| SUBJECT_INTERACTIVE  | Ativa aprovação interativa de assunto | 1 (ativado)   |

4. Outras configurações disponíveis no arquivo `config/config.yaml`:

| Seção | Chave            | Descrição                    | Exemplo                    |
| ----- | ---------------- | ---------------------------- | -------------------------- |
| email | sender           | Nome e email do remetente    | Seu Nome \<seu@email.com\> |
| email | batch_size       | Tamanho do lote              | 200                        |
| email | test_recipient   | Email para teste             | test@example.com           |
| email | batch_delay      | Delay entre lotes (segundos) | 5                          |

5. Configurações de SMTP para retentativas

| Seção | Chave            | Descrição                           | Exemplo |
| ----- | ---------------- | ----------------------------------- | ------- |
| smtp  | retry_attempts   | Número máximo de tentativas         | 3       |
| smtp  | retry_delay      | Delay entre tentativas (segundos)   | 5       |
| smtp  | send_timeout     | Timeout de envio (segundos)         | 10      |

**Importante**: O sistema limita o número de retentativas a 2 tentativas máximas para falhas de conexão e marca contatos com problemas de envio com a tag 'problem' para evitar reenvios futuros. O tempo de espera entre retentativas é otimizado para reduzir o tempo total de envio.

6. Aprovação interativa de assunto

Ao enviar emails (toda a base), o sistema gera automaticamente um assunto para os emails. Com a variável `SUBJECT_INTERACTIVE=1` configurada no arquivo `.env`, o sistema solicitará a aprovação do assunto gerado antes de iniciar o envio.

Caso o usuário não aprove o assunto, o sistema irá gerar uma nova variação (até 2 tentativas adicionais) e solicitar novamente a aprovação. Isso permite garantir que o assunto dos emails seja apropriado antes do envio em lote.

7. Conteúdo dinâmico para os templates em `config/email.yaml`:

O arquivo `config/email.yaml` contém variáveis que serão substituídas no template HTML. Exemplo:

```yaml
# Conteúdo dinâmico para os templates de email
# -----------------------------------------------------

# Informações do evento
# ---------------------
evento:
  link: "https://exemplo.com/evento"
  data: "15 e 16 de março"
  cidade: "Sua Cidade"
  local: "Nome do Local, Sua Cidade - UF"
  horario: "9h às 18h (ambos os dias)"

# Promoções e ofertas
# -------------------
promocao:
  desconto: "30%"

# Configurações de email
# ---------------------
email:
  subject: "Aprenda Proteção e Seletividade" # Assunto padrão para os emails

# URLs de gerenciamento de inscrição
# ---------------------------------
urls:
  unsubscribe: "https://seu-site.com/unsubscribe" # URL para descadastro
  subscribe: "https://seu-site.com/resubscribe" # URL para recadastro
```



7. Configuração da API REST em `config/rest.yaml`:

| Seção         | Chave                                     | Descrição                   | Padrão               |
| ------------- | ----------------------------------------- | --------------------------- | -------------------- |
| server        | host                                      | Host para o servidor        | 0.0.0.0              |
| server        | port                                      | Porta HTTP                  | 5000                 |
| server        | debug                                     | Modo debug                  | true                 |
| security      | enable_cors                               | Habilitar CORS              | true                 |
| security      | allowed_origins                           | Origens permitidas          | \*                   |
| security      | rate_limiting.enabled                     | Habilitar rate limiting     | true                 |
| security      | rate_limiting.requests_per_minute         | Requisições por minuto      | 60                   |
| logging       | level                                     | Nível de log                | INFO                 |
| logging       | file                                      | Arquivo de log              | (vazio)              |
| timeout       | request                                   | Timeout (segundos)          | 60                   |
| endpoints     | [categoria].enabled                       | Habilitar categoria         | true                 |
| endpoints     | [categoria].base_path                     | Caminho base para categoria | /api/...             |
| endpoints     | [categoria].operations.[operação].enabled | Habilitar operação          | true                 |
| endpoints     | [categoria].operations.[operação].path    | Caminho da operação         | /...                 |
| endpoints     | [categoria].operations.[operação].methods | Métodos HTTP permitidos     | [GET/POST/etc]       |
| documentation | enabled                                   | Habilitar documentação      | true                 |
| documentation | path                                      | Caminho da documentação     | /api/docs            |
| documentation | openapi_file                              | Arquivo OpenAPI             | config/api-docs.yaml |

8. Documentação da API em `config/api-docs.yaml`:

Este arquivo contém a especificação OpenAPI/Swagger da API, incluindo:

- Definições de endpoints (paths)
- Parâmetros de entrada
- Esquemas de dados
- Respostas possíveis
- Exemplos

A documentação segue o formato [OpenAPI 3.0](https://swagger.io/specification/) e pode ser visualizada em `/api/docs` quando a API está em execução.

9. Inicialização do Banco de Dados:

O sistema requer a criação da tabela `tbl_send_state` para rastrear o estado dos envios e permitir a retomada de processos interrompidos. Para inicializar o banco de dados, execute:

```bash
python3 scripts/init_db.py
```

Este script criará a tabela `tbl_send_state` no banco de dados PostgreSQL configurado nas variáveis de ambiente.

## 🎯 Uso

O sistema pode ser utilizado de duas formas: através da interface de linha de comando (CLI) ou via API REST.

### Interface de Linha de Comando (CLI)

A CLI oferece acesso a todas as funcionalidades principais do sistema através de comandos no terminal.

#### Testar Configuração SMTP

Verifica se as configurações SMTP estão corretas enviando um email de teste:

```bash
email-sender test-smtp [--config config/config.yaml] [--content config/email.yaml]
# Alternativa sem entrypoint
python -m email_sender.controller_cli test-smtp [--config config/config.yaml] [--content config/email.yaml]
```

Parâmetros opcionais:

- `--config, -c`: Caminho para o arquivo de configuração (padrão: config/config.yaml)
- `--content`: Caminho para o arquivo de conteúdo de email (padrão: config/email.yaml)

Resposta esperada:

```
📧 test@example.com
✅ test@example.com
```

#### Enviar Emails

Antes de enviar emails, certifique-se de que o banco de dados foi inicializado corretamente executando o script `scripts/init_db.py`. Isso criará a tabela `tbl_send_state` necessária para rastrear o estado dos envios e permitir a retomada de processos interrompidos.

Envie emails usando um template e planilha, especificando obrigatoriamente o modo de envio:

```bash
# Modo de teste (lê o caminho do template de config/email.yaml -> email.template_path)
email-sender send-emails --mode=test

# Modo de produção
email-sender send-emails --mode=production

# Ignorando sincronização de descadastros e bounces
email-sender send-emails --mode=production --skip-sync

# Alternativa sem entrypoint
python -m email_sender.controller_cli send-emails --mode=test
```

Este comando sincroniza automaticamente a lista de descadastros e bounces (a menos que `--skip-sync` seja usado) antes de iniciar o envio, garantindo que emails descadastrados ou com bounce não recebam mensagens.

> **⚠️ Segurança:** É obrigatório especificar o modo de envio:
>
> - `--mode=test`: Usa a lista de emails de teste do banco de dados para testes seguros
> - `--mode=production`: Usa a lista completa de emails do banco de dados para envios reais
>
> Não é possível executar o comando sem especificar um destes modos, evitando envios acidentais.

#### Análise de Relatórios de Envio

O sistema inclui ferramentas para análise de relatórios de envio e identificação de contatos com problemas persistentes:

```bash
# Analisar emails com falhas repetidas
python scripts/analyze_failed_emails.py

# Verificar contatos marcados como problemáticos
python scripts/check_problematic_contacts.py

# Remover a tag 'problem' de um contato específico
python scripts/remove_problem_tag.py <contact_id>
```

Essas ferramentas ajudam a manter a qualidade da base de contatos identificando e marcando automaticamente emails que apresentam problemas persistentes de envio.

Parâmetros:

- `template`: Nome ou caminho do template HTML a ser usado (obrigatório)

- `--config, -c`: Arquivo de configuração (padrão: config/config.yaml)
- `--content`: Arquivo de conteúdo dinâmico (padrão: config/email.yaml)
- `--skip-sync`: Ignora a sincronização da lista de descadastros e bounces antes do envio
- `--mode`: **Obrigatório**: especifique o modo de envio (`test` ou `production`)


```
📧 usuario1@example.com
✅ usuario1@example.com
📧 usuario2@example.com
✅ usuario2@example.com
...

Progresso: 50/100 emails processados (50.0%)

Resumo do lote atual:
✓ Enviados neste lote: 48
✗ Falhas neste lote: 2
Taxa de sucesso do lote: 96.0%

Resumo geral:
✓ Total enviados: 98
✗ Total falhas: 2
Taxa de sucesso geral: 98.0%
Faltam: 0 emails
```

#### Sincronizar Lista de Descadastros

Sincroniza manualmente a lista de descadastros com o arquivo principal de emails:

```bash
email-sender sync-unsubscribed-command
```

Este comando atualiza a coluna `descadastro` no arquivo principal com base na lista de emails descadastrados. É executado automaticamente antes de cada envio, mas pode ser executado manualmente quando necessário. Ele marcará com "S" os emails que constam na lista de descadastros.

Parâmetros opcionais:

- `--unsubscribe-file`: Caminho para o arquivo de descadastros (usa o da configuração se omitido)
- `--config, -c`: Arquivo de configuração (padrão: config/config.yaml)
- `--content`: Arquivo de conteúdo dinâmico (padrão: config/email.yaml)

Além disso, se existirem emails na lista de descadastros que não estão presentes na lista principal de emails, o comando adicionará esses emails à lista principal com a flag `descadastro` já marcada como "S". Isso garante que todos os emails descadastrados estejam sempre registrados na lista principal.

#### Sincronizar Lista de Bounces

Sincroniza manualmente a lista de emails de bounce com o arquivo principal de emails:

```bash
email-sender sync-bounces-command
```

Este comando atualiza a coluna `bounce` no arquivo principal com base na lista de emails de bounce. Ele marcará com "S" os emails que constam na lista de bounces. É executado automaticamente antes de cada envio de produção (a menos que `--skip-sync` seja usado), mas pode ser executado manualmente.

Parâmetros opcionais:

- `--config, -c`: Arquivo de configuração (padrão: config/config.yaml)
- `--content`: Arquivo de conteúdo dinâmico (padrão: config/email.yaml)

#### Limpar Flags de Envio

Reseta o status de todos os emails na planilha, permitindo o reenvio para todos os contatos:

```bash
email-sender clear-sent-flags
```

Parâmetros opcionais:

- `--config, -c`: Arquivo de configuração (padrão: config/config.yaml)
- `--content`: Arquivo de conteúdo dinâmico (padrão: config/email.yaml)

Este comando limpa as colunas `enviado` e `falhou` do banco de dados, permitindo que emails já enviados ou que falharam anteriormente sejam processados novamente no próximo envio.

#### Importar Contatos de CSV

Para importar uma lista de contatos em massa, siga os passos:

1.  Crie um arquivo chamado `contacts.csv` na raiz do projeto.
2.  O arquivo deve conter uma única coluna com o cabeçalho `email`.

**Exemplo de `contacts.csv`:**

```csv
email
fulano@example.com
beltrano@example.com
ciclano@example.com
```

3.  Execute a aplicação no modo interativo e selecione a opção **"Importar contatos (contacts.csv)"** no menu.

O sistema irá ler o arquivo, ignorar duplicatas e inserir os novos contatos no banco de dados, deixando-os prontos para receber campanhas.

#### Remover Duplicados

Remove linhas duplicadas da base de dados PostgreSQL baseado em uma coluna específica (por padrão, a coluna 'email'):

```bash
# Remoção básica (usa coluna 'email' e mantém a primeira ocorrência)
email-sender remove-duplicates

# Especificando a coluna para verificar duplicados
email-sender remove-duplicates --column nome

# Escolhendo qual ocorrência manter (primeira ou última)
email-sender remove-duplicates --keep last

# Salvando em um novo arquivo em vez de substituir o original
```

Este comando analisa a base de dados, identifica duplicatas com base na coluna especificada, e mantém apenas uma ocorrência de cada valor único.

Parâmetros:

- `--column, -c`: Coluna a ser usada para identificar duplicados (padrão: "email")
- `--keep, -k`: Qual ocorrência manter ("first" ou "last", padrão: "first")
- `--output, -o`: Arquivo de saída (se não especificado, substitui o original)
- `--config`: Caminho para o arquivo de configuração (padrão: config/config.yaml)

### API REST

O sistema disponibiliza uma API REST para acessar todas as funcionalidades através de requisições HTTP, ideal para integração com outras aplicações.

#### Iniciar a API REST

```bash
python -m email_sender.rest_api
```

A API será iniciada conforme as configurações definidas em `config/rest.yaml`. Por padrão, estará disponível em `http://localhost:5000`.

Saída esperada:

```
⚡ Iniciando API REST em http://0.0.0.0:5000
📝 Documentação disponível em http://0.0.0.0:5000/api/docs
```

#### Configuração da API

A API REST pode ser configurada através do arquivo `config/rest.yaml`, permitindo personalizar:

- Host e porta do servidor
- Modo de depuração
- Configurações de CORS (Cross-Origin Resource Sharing)
- Nível e destino dos logs
- Timeout para requisições
- Habilitação/desabilitação de endpoints específicos
- Configurações de segurança e rate limiting
- Documentação da API

Veja a [seção de configuração](#configuração) para detalhes sobre as opções disponíveis.

#### Estrutura da API baseada em YAML

A API é completamente configurável através de definições em arquivos YAML:

1. **Configuração de Servidor e Segurança**: `config/rest.yaml`

   - Configurações técnicas: host, porta, timeouts, CORS, rate limiting
   - Habilitação/desabilitação de endpoints
   - Definição de caminhos (paths) para os endpoints

2. **Documentação e Schemas da API**: `config/api-docs.yaml`
   - Definição de endpoints no formato OpenAPI/Swagger
   - Schemas de validação para entrada/saída
   - Documentação de respostas e códigos de erro

Esta estrutura permite:

- Modificar endpoints sem alterar código
- Habilitar/desabilitar recursos específicos
- Ajustar parâmetros de segurança
- Gerar documentação automática

#### Documentação Interativa da API

A documentação interativa da API pode ser acessada em `/api/docs` quando a API está em execução:

```
http://localhost:5000/api/docs
```

Esta interface permite explorar todos os endpoints disponíveis, seus parâmetros e até mesmo testar as chamadas diretamente do navegador.

#### Principais Endpoints

| Endpoint                        | Método | Descrição                            |
| ------------------------------- | ------ | ------------------------------------ |
| `/api/health`                   | GET    | Verificar status do serviço          |
| `/api/emails/send`              | POST   | Enviar emails em lote                |
| `/api/emails/test-smtp`         | POST   | Testar conexão SMTP                  |
| `/api/emails/clear-flags`       | POST   | Limpar flags de envio                |
| `/api/emails/sync-unsubscribed` | POST   | Sincronizar lista de descadastros    |
| `/api/emails/sync-bounces`      | POST   | Sincronizar lista de bounces         |
| `/api/config`                   | GET    | Obter configurações atuais           |
| `/api/config`                   | PUT    | Atualizar configurações              |
| `/api/config/partial`           | PATCH  | Atualizar configurações parcialmente |

Consulte a documentação OpenAPI completa em `/api/docs` para detalhes sobre parâmetros, respostas e exemplos de cada endpoint.

## 📊 Estrutura dos Dados



## 📈 Relatórios

Os relatórios são gerados automaticamente na pasta `reports/` após cada execução, contendo:

- Total de emails tentados
- Quantidade de envios bem-sucedidos
- Quantidade de falhas
- Tempo total de execução
- Tempo médio por email

Exemplo de nome do arquivo: `email_report_20250212_172008.txt`

## 🔒 Versionamento

### ⚠️ Arquivos Excluídos do Versionamento

Para garantir a segurança das informações, os seguintes tipos de arquivos são excluídos do versionamento Git:

- **Credenciais**: arquivos `.env`, senhas e credenciais
- **Configurações**: arquivos YAML na pasta `config/`
- **Templates de Email**: arquivos HTML na pasta `templates/`
- **Logs e Relatórios**: arquivos na pasta `reports/`

### 📊 Análise de Relatórios de Envio

O sistema inclui ferramentas para análise de relatórios de envio e identificação de contatos com problemas persistentes:

1. **scripts/analyze_failed_emails.py**: Analisa relatórios de envio e gera listas de emails com falhas repetidas
2. **scripts/check_problematic_contacts.py**: Verifica contatos marcados como problemáticos
3. **scripts/remove_problem_tag.py**: Remove a tag 'problem' de um contato específico

Essas ferramentas ajudam a manter a qualidade da base de contatos identificando e marcando automaticamente emails que apresentam problemas persistentes de envio.

### 📝 Arquivos de Exemplo

Para facilitar a configuração, o projeto inclui os seguintes arquivos de exemplo que são versionados:

| Arquivo Original       | Arquivo de Exemplo             | Descrição                    |
| ---------------------- | ------------------------------ | ---------------------------- |
| `config/config.yaml`   | `example_config.yaml`          | Configurações do sistema     |
| `config/email.yaml`    | `example_email.yaml`           | Conteúdo dinâmico de emails  |
| `templates/email.html` | `templates/email.html.example` | Template de email            |
| `.env`                 | `.env.example`                 | Credenciais SMTP             |

## 🔧 Desenvolvimento

### Princípios de Desenvolvimento

1. **Configuração Externa**: Todas as configurações, URLs, credenciais e parâmetros operacionais devem ser definidos em arquivos YAML externos. Nunca hardcode valores no código.

2. **Separação de Responsabilidades**:

   - `config/config.yaml`: Configurações técnicas e operacionais
   - `config/email.yaml`: Conteúdo dinâmico e texto para templates
   - `.env`: Apenas credenciais sensíveis

3. **Extensibilidade**: Novos parâmetros devem ser adicionados aos arquivos de configuração, não ao código.

### Estrutura do Projeto

```
email-sender/
├── config/              # Arquivos de configuração
│   ├── config.yaml      # Configuração operacional
│   ├── email.yaml       # Conteúdo dinâmico para templates
│   ├── rest.yaml        # Configuração da API REST
│   └── api-docs.yaml    # Documentação OpenAPI
├── data/                # Arquivos de dados (não versionados)
├── templates/           # Templates de email
│   └── email.html       # Template padrão de email HTML
├── logs/                # Logs da aplicação (não versionados)
├── src/                 # Código fonte
│   ├── api/                     # Nova estrutura de API REST
│   │   ├── routes/              # Rotas organizadas por domínio
│   │   │   ├── email_routes.py  # Endpoints para operações de email
│   │   │   ├── config_routes.py # Endpoints para configurações
│   │   │   └── docs_routes.py   # Endpoints para documentação
│   │   ├── schemas/             # Validação e serialização
│   │   │   └── models.py        # Modelos de dados para API
│   │   ├── app.py               # Aplicação Flask principal
│   │   └── utils.py             # Utilitários da API
│   ├── utils/
│   ├── cli.py                   # Ponto de entrada da CLI
│   ├── controller_cli.py        # Controller para interface CLI
│   ├── controller_rest.py       # Controller para compatibilidade
│   ├── rest_api.py              # Ponto de entrada da API REST
│   ├── config.py                # Gerenciamento de configuração
│   ├── email_service.py         # Serviço de envio de emails
│   └── unsubscribe_app.py       # App de descadastro/unsubscribe
├── tests/               # Testes automatizados
├── reports/             # Relatórios gerados (não versionados)
├── example_config.yaml          # Exemplo de configuração
├── example_email.yaml           # Exemplo de conteúdo de email
├── config/rest.yaml.example     # Exemplo de configuração REST
├── config/api-docs.yaml.example # Exemplo de documentação OpenAPI
├── templates/email.html.example # Exemplo de template
├── .env.example                 # Exemplo de credenciais
└── setup.py             # Configuração do pacote
```

### Executando Testes

Execute todos os testes:

```bash
pytest
```

Execute testes com cobertura:

```bash
pytest --cov=src
```

### Características de Segurança

- ✅ Backup automático antes de modificar a planilha
- ✅ Restauração automática em caso de falhas
- ✅ Salvamento atômico usando arquivos temporários
- ✅ Tratamento de sinais (SIGINT) para interrupção segura
- ✅ Limpeza automática de arquivos temporários
- ✅ Retentativas configuráveis para falhas de SMTP
- ✅ Exclusão de dados sensíveis do versionamento
- ✅ Configuração 100% externa (sem valores hardcoded)

## Autenticação JWT

O sistema implementa autenticação JWT (JSON Web Token) para proteger endpoints da API REST. A seguir, estão as informações sobre como usar a autenticação:

### Configuração do JWT

No arquivo `config/rest.yaml`:

```yaml
security:
  jwt:
    enabled: true
    secret_key: "${JWT_SECRET_KEY}" # Use variável de ambiente para o segredo
    token_expiry_hours: 24
    refresh_token_expiry_hours: 168 # 7 dias
```

Certifique-se de definir a variável de ambiente JWT_SECRET_KEY com um valor forte e seguro:

```bash
# No Linux/Mac:
export JWT_SECRET_KEY="seu_segredo_muito_seguro_e_longo"

# No Windows:
set JWT_SECRET_KEY=seu_segredo_muito_seguro_e_longo

# Ou adicione no arquivo .env:
JWT_SECRET_KEY=seu_segredo_muito_seguro_e_longo
```

> ⚠️ **IMPORTANTE**: Utilize um segredo forte e único para o JWT. O segredo deve ter pelo menos 32 caracteres e conter letras, números e símbolos para garantir segurança adequada.

## Padrões de Projeto e Práticas de Desenvolvimento

### Princípios de Desenvolvimento

O sistema segue os seguintes princípios de desenvolvimento:

1. **Clean Code**: Código claro, legível e autoexplicativo
2. **KISS (Keep It Simple, Stupid)**: Manter o código minimalista, evitando complexidade desnecessária
3. **DRY (Don't Repeat Yourself)**: Evitar duplicação de código através de reutilização
4. **Separação de Responsabilidades**: Cada módulo tem uma única responsabilidade bem definida
5. **Orientação a Objeto Moderada**: Aplicada de forma equilibrada sem aumentar complexidade

### Estrutura do Projeto

- Todos os arquivos de código Python (.py) estão dentro dos diretórios `src/` ou `tests/`
- Nenhum código .py está fora desses diretórios principais
- Arquivos de configuração no diretório `config/`
- Templates de email no diretório `templates/`
- Relatórios e logs no diretório `reports/`

### Testes e Qualidade

- Testes automatizados com pytest
- Cobertura de código acima de 85%
- Relatórios de cobertura em XML (coverage.xml) e HTML
- Linting com flake8 e formatação com black
- Integração contínua com verificação automática de qualidade

### Reutilização e Manutenção

- Componentização de funcionalidades comuns
- Configuração externa em arquivos YAML e .env
- Versionamento semântico e CHANGELOG.md atualizado
- Exclusão de arquivos sensíveis do versionamento Git

### Setup Avançado de Envio de Emails

O sistema inclui funcionalidades avançadas de setup de envio de emails:

1. **Otimização de Conteúdo com GenAI**:
   - Geração automática de variações de títulos
   - Otimização do corpo do email com sugestões de IA
   - Processo de aprovação interativa do usuário

2. **Testes A/B de Assuntos**:
   - Configuração automática de testes A/B
   - Distribuição controlada de variações de títulos
   - Análise de resultados para identificar a melhor opção

3. **Separação de Responsabilidades**:
   - Setup de conteúdo separado do processo de envio
   - Envio de emails utiliza conteúdo previamente aprovado
   - Menu dedicado para configuração avançada

### Interface do Terminal Moderna

O sistema utiliza uma interface de terminal moderna baseada em Charm CLI, inspirada no CRUSH AI:

1. **Experiência Visual Aprimorada**:
   - Interface interativa com menus estilizados
   - Resumos de envio em formato de tabela otimizado
   - Tempo de execução exibido em horas quando maior que 1 hora
   - Ocultação de listagens de sucesso para foco em problemas

2. **Tratamento Inteligente de Contatos**:
   - Marcação automática de emails inválidos com tag 'invalid'
   - Ignorar contatos com tags inválidas durante o envio
   - Resumo detalhado de métricas de envio

3. **Configuração Personalizável**:
   - Temas visuais configuráveis
   - Formatos de exibição personalizáveis
   - Opções de filtragem de informações exibidas

Para acessar o setup avançado de envio de emails, use o menu interativo da CLI e selecione a opção "Setup do envio de e-mails".

### Proteção de Endpoints

O sistema utiliza diferentes tipos de proteção para os endpoints:

1. **@token_required**: Requer apenas um token JWT válido
2. **@role_required('admin')**: Requer um token JWT válido e a role específica ('admin')

Os seguintes endpoints estão protegidos:

| Endpoint                        | Método | Proteção               | Função                               |
| ------------------------------- | ------ | ---------------------- | ------------------------------------ |
| `/api/health`                   | GET    | token_required         | Verificação de status                |
| `/api/emails/send`              | POST   | token_required         | Envio de emails                      |
| `/api/emails/test-smtp`         | POST   | token_required         | Teste SMTP                           |
| `/api/emails/clear-flags`       | POST   | role_required('admin') | Limpar flags                         |
| `/api/emails/sync-unsubscribed` | POST   | role_required('admin') | Sincronizar descadastros             |
| `/api/emails/sync-bounces`      | POST   | role_required('admin') | Sincronizar bounces                  |
| `/api/config`                   | GET    | role_required('admin') | Obter configurações                  |
| `/api/config`                   | PUT    | role_required('admin') | Atualizar configurações              |
| `/api/config/partial`           | PATCH  | role_required('admin') | Atualizar configurações parcialmente |

## Histórico de Atualizações

### Setembro 2025
- Correção do teste falhando em CLI helpers relacionado à variável de ambiente EMAIL_SENDER
- Adição de novos testes para melhorar a cobertura de código
- Simplificação da estrutura do projeto mantendo a funcionalidade principal
- Atualização da documentação para refletir as mudanças atuais