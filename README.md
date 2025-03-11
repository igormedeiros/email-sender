# Email Sender

Sistema robusto para envio de emails em lote com suporte a planilhas CSV, backup automático e relatórios detalhados. Todas as configurações são mantidas em arquivos YAML externos, sem valores hardcoded no código.

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

- ✉️ Envio de emails em lote a partir de planilhas CSV
- 🔄 Backup automático e restauração em caso de falhas
- 📊 Relatórios detalhados de envio
- ⏱️ Controle de taxa de envio e intervalos entre lotes
- 🔁 Sistema de retentativas automáticas
- 💾 Salvamento periódico do progresso
- 🛡️ Tratamento seguro de interrupções
- 📝 Suporte a templates de email personalizáveis
- 🚫 Gerenciamento automático de descadastros (unsubscribe)
- 🔧 Configuração 100% externa via arquivos YAML (sem valores hardcoded)
- 🌐 API REST para todas as funcionalidades
- 🔌 Arquitetura desacoplada com controllers e service

## 🛠️ Requisitos

- Python 3.12+
- pip (gerenciador de pacotes Python)
- Acesso a um servidor SMTP

## ⚙️ Instalação

1. Clone o repositório:
```bash
git clone <repository-url>
cd email-sender
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate   # Windows
```

3. Instale as dependências:
```bash
pip install -e .
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

| Seção | Chave | Descrição | Exemplo |
|-------|-------|-----------|---------|
| smtp | host | Servidor SMTP | smtp.gmail.com |
| smtp | port | Porta SMTP | 587 |
| smtp | use_tls | Usar TLS | true |
| smtp | retry_attempts | Número de tentativas | 3 |
| smtp | retry_delay | Delay entre tentativas (segundos) | 5 |
| smtp | send_timeout | Timeout de envio (segundos) | 10 |

3. Configure as credenciais SMTP no arquivo `.env`:

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| SMTP_USERNAME | Usuário SMTP | seu@email.com |
| SMTP_PASSWORD | Senha SMTP | sua_senha |

4. Outras configurações disponíveis no arquivo `config/config.yaml`:

| Seção | Chave | Descrição | Exemplo |
|-------|-------|-----------|---------|
| email | sender | Nome e email do remetente | Seu Nome \<seu@email.com\> |
| email | batch_size | Tamanho do lote | 100 |
| email | csv_file | Arquivo de emails | data/emails_geral.csv |
| email | test_recipient | Email para teste | test@example.com |
| email | batch_delay | Delay entre lotes (segundos) | 60 |
| email | unsubscribe_file | Arquivo de descadastros | data/descadastros.csv |
| email | test_emails_file | Arquivo para testes em lote | data/test_emails.csv |

5. Conteúdo dinâmico para os templates em `config/email.yaml`:

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
  subject: "Aprenda Proteção e Seletividade"  # Assunto padrão para os emails

# URLs de gerenciamento de inscrição
# ---------------------------------
urls:
  unsubscribe: "https://seu-site.com/unsubscribe"  # URL para descadastro
  subscribe: "https://seu-site.com/resubscribe"    # URL para recadastro
```

6. Crie os arquivos CSV necessários na pasta `data/` seguindo as estruturas descritas em `example_emails.csv.md`:

```bash
mkdir -p data
touch data/emails_geral.csv data/test_emails.csv data/descadastros.csv
```

5. Configuração da API REST em `config/rest.yaml`:

| Seção | Chave | Descrição | Padrão |
|-------|-------|-----------|--------|
| server | host | Host para o servidor | 0.0.0.0 |
| server | port | Porta HTTP | 5000 |
| server | debug | Modo debug | true |
| security | enable_cors | Habilitar CORS | true |
| security | allowed_origins | Origens permitidas | * |
| security | rate_limiting.enabled | Habilitar rate limiting | true |
| security | rate_limiting.requests_per_minute | Requisições por minuto | 60 |
| logging | level | Nível de log | INFO |
| logging | file | Arquivo de log | (vazio) |
| timeout | request | Timeout (segundos) | 60 |
| endpoints | [categoria].enabled | Habilitar categoria | true |
| endpoints | [categoria].base_path | Caminho base para categoria | /api/... |
| endpoints | [categoria].operations.[operação].enabled | Habilitar operação | true |
| endpoints | [categoria].operations.[operação].path | Caminho da operação | /... |
| endpoints | [categoria].operations.[operação].methods | Métodos HTTP permitidos | [GET/POST/etc] |
| documentation | enabled | Habilitar documentação | true |
| documentation | path | Caminho da documentação | /api/docs |
| documentation | openapi_file | Arquivo OpenAPI | config/api-docs.yaml |

6. Documentação da API em `config/api-docs.yaml`:

Este arquivo contém a especificação OpenAPI/Swagger da API, incluindo:

- Definições de endpoints (paths)
- Parâmetros de entrada
- Esquemas de dados
- Respostas possíveis
- Exemplos

A documentação segue o formato [OpenAPI 3.0](https://swagger.io/specification/) e pode ser visualizada em `/api/docs` quando a API está em execução.

## 🎯 Uso

O sistema pode ser utilizado de duas formas: através da interface de linha de comando (CLI) ou via API REST.

### Interface de Linha de Comando (CLI)

A CLI oferece acesso a todas as funcionalidades principais do sistema através de comandos no terminal.

#### Testar Configuração SMTP

Verifica se as configurações SMTP estão corretas enviando um email de teste:

```bash
python -m src.cli test-smtp [--config config/config.yaml] [--content config/email.yaml]
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

Envie emails usando um template e planilha, especificando obrigatoriamente o modo de envio:

```bash
# Modo de teste (arquivo data/test_emails.csv)
python -m src.cli send-emails templates/email.html --mode=test

# Modo de produção (arquivo data/emails_geral.csv)
python -m src.cli send-emails templates/email.html --mode=production

# Especificando arquivo CSV personalizado
python -m src.cli send-emails templates/email.html --mode=production --csv-file data/minha_lista.csv

# Ignorando sincronização de descadastros
python -m src.cli send-emails templates/email.html --mode=production --skip-sync
```

Este comando sincroniza automaticamente a lista de descadastros antes de iniciar o envio, garantindo que emails descadastrados não recebam mensagens.

> **⚠️ Segurança:** É obrigatório especificar o modo de envio:
> - `--mode=test`: Usa o arquivo `data/test_emails.csv` para testes seguros (definido em config/config.yaml)
> - `--mode=production`: Usa a lista completa `emails_geral.csv` para envios reais (definido em config/config.yaml)
>
> Não é possível executar o comando sem especificar um destes modos, evitando envios acidentais.

Parâmetros:
- `template`: Nome ou caminho do template HTML a ser usado (obrigatório)
- `--csv-file`: Caminho do arquivo CSV (opcional, usa configuração se omitido)
- `--config, -c`: Arquivo de configuração (padrão: config/config.yaml)
- `--content`: Arquivo de conteúdo dinâmico (padrão: config/email.yaml)
- `--skip-sync`: Ignora a sincronização da lista de descadastros antes do envio
- `--mode`: **Obrigatório**: especifique o modo de envio (`test` ou `production`)

Durante a execução, o progresso é exibido em tempo real:
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
python -m src.cli sync-unsubscribed-command [--csv-file data/emails_geral.csv] [--unsubscribe-file data/descadastros.csv]
```

Este comando atualiza a coluna `descadastro` no arquivo principal com base na lista de emails descadastrados. É executado automaticamente antes de cada envio, mas pode ser executado manualmente quando necessário. Ele marcará com "S" os emails que constam na lista de descadastros.

Parâmetros opcionais:
- `--csv-file`: Caminho para o arquivo CSV principal (usa o da configuração se omitido)
- `--unsubscribe-file`: Caminho para o arquivo de descadastros (usa o da configuração se omitido)
- `--config, -c`: Arquivo de configuração (padrão: config/config.yaml)
- `--content`: Arquivo de conteúdo dinâmico (padrão: config/email.yaml)

Além disso, se existirem emails na lista de descadastros que não estão presentes na lista principal de emails, o comando adicionará esses emails à lista principal com a flag `descadastro` já marcada como "S". Isso garante que todos os emails descadastrados estejam sempre registrados na lista principal.

#### Limpar Flags de Envio

Reseta o status de todos os emails na planilha, permitindo o reenvio para todos os contatos:

```bash
python -m src.cli clear-sent-flags [--csv-file data/emails_geral.csv]
```

Parâmetros opcionais:
- `--csv-file`: Caminho para o arquivo CSV (usa o da configuração se omitido)
- `--config, -c`: Arquivo de configuração (padrão: config/config.yaml)
- `--content`: Arquivo de conteúdo dinâmico (padrão: config/email.yaml)

Este comando limpa as colunas `enviado` e `falhou` do arquivo CSV, permitindo que emails já enviados ou que falharam anteriormente sejam processados novamente no próximo envio.

### API REST

O sistema disponibiliza uma API REST para acessar todas as funcionalidades através de requisições HTTP, ideal para integração com outras aplicações.

#### Iniciar a API REST

```bash
python -m src.rest_api
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

#### Endpoints Disponíveis

##### Verificação de Status

```
GET /api/health
```

Verifica se a API está funcionando corretamente.

Exemplo de requisição:
```bash
curl -X GET http://localhost:5000/api/health
```

Exemplo de resposta:
```json
{
  "status": "ok",
  "timestamp": "2023-03-15T14:30:00Z"
}
```

##### Envio de Emails

```
POST /api/emails/send
```

Envia emails em lote baseado nos parâmetros fornecidos.

Exemplo de requisição:
```bash
curl -X POST http://localhost:5000/api/emails/send \
  -H "Content-Type: application/json" \
  -d '{
    "csv_file": "data/emails.csv",
    "template": "templates/email.html",
    "skip_unsubscribed_sync": false,
    "mode": "test"
  }'
```

Parâmetros:
- `template` (obrigatório): Nome ou caminho do template HTML
- `mode` (obrigatório): Modo de envio ("test" ou "production")
- `csv_file` (opcional): Caminho para o arquivo CSV
- `skip_unsubscribed_sync` (opcional): Se deve ignorar a sincronização de descadastros

Exemplo de resposta:
```json
{
  "status": "success",
  "message": "Emails enviados com sucesso",
  "report": {
    "report_file": "email_report_20230315_143000.txt",
    "total_sent": 100,
    "successful": 95,
    "failed": 5,
    "duration": 120.5,
    "avg_time": 1.2
  }
}
```

##### Teste de Conexão SMTP

```
POST /api/emails/test-smtp
```

Testa a conexão SMTP enviando um email de teste.

Exemplo de requisição:
```bash
curl -X POST http://localhost:5000/api/emails/test-smtp \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": "test@example.com"
  }'
```

Parâmetros:
- `recipient` (opcional): Email do destinatário para teste (usa o configurado em config.yaml se omitido)

Exemplo de resposta:
```json
{
  "status": "success",
  "message": "Email de teste enviado para test@example.com"
}
```

##### Limpar Flags de Envio

```
POST /api/emails/clear-flags
```

Limpa as flags de envio em um arquivo CSV.

Exemplo de requisição:
```bash
curl -X POST http://localhost:5000/api/emails/clear-flags \
  -H "Content-Type: application/json" \
  -d '{
    "csv_file": "data/emails.csv"
  }'
```

Parâmetros:
- `csv_file` (opcional): Caminho para o arquivo CSV (usa o configurado em config.yaml se omitido)

Exemplo de resposta:
```json
{
  "status": "success",
  "message": "150 flags limpas com sucesso"
}
```

##### Sincronizar Emails Descadastrados

```
POST /api/emails/sync-unsubscribed
```

Sincroniza a lista de emails descadastrados com o arquivo principal.

Exemplo de requisição:
```bash
curl -X POST http://localhost:5000/api/emails/sync-unsubscribed \
  -H "Content-Type: application/json" \
  -d '{
    "csv_file": "data/emails.csv",
    "unsubscribe_file": "data/descadastros.csv"
  }'
```

Parâmetros:
- `csv_file` (opcional): Caminho para o arquivo CSV principal
- `unsubscribe_file` (opcional): Caminho para o arquivo de descadastros

Exemplo de resposta:
```json
{
  "status": "success",
  "message": "50 emails sincronizados",
  "csv_file": "data/emails.csv",
  "unsubscribe_file": "data/descadastros.csv"
}
```

##### Obter Configurações

```
GET /api/config
```

Retorna as configurações atuais do arquivo email.yaml.

Exemplo de requisição:
```bash
curl -X GET http://localhost:5000/api/config
```

Exemplo de resposta:
```json
{
  "evento": {
    "link": "https://exemplo.com/evento",
    "data": "15 e 16 de março",
    "cidade": "Sua Cidade",
    "local": "Nome do Local, Sua Cidade - UF"
  },
  "promocao": {
    "desconto": "30%"
  },
  "email": {
    "subject": "Aprenda Proteção e Seletividade"
  },
  "urls": {
    "unsubscribe": "https://seu-site.com/unsubscribe",
    "subscribe": "https://seu-site.com/resubscribe"
  }
}
```

##### Atualizar Configurações

```
PUT /api/config
```

Substitui completamente o arquivo email.yaml com as novas configurações.

Exemplo de requisição:
```bash
curl -X PUT http://localhost:5000/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "evento": {
      "link": "https://novo-site.com/evento",
      "data": "20 e 21 de abril",
      "cidade": "Nova Cidade",
      "local": "Novo Local, Nova Cidade - UF"
    },
    "promocao": {
      "desconto": "40%"
    },
    "email": {
      "subject": "Novo Curso Disponível"
    },
    "urls": {
      "unsubscribe": "https://novo-site.com/unsubscribe",
      "subscribe": "https://novo-site.com/resubscribe"
    }
  }'
```

Parâmetros:
- Corpo da requisição: Objeto JSON com todas as configurações

Exemplo de resposta:
```json
{
  "status": "success",
  "message": "Configurações atualizadas com sucesso",
  "backup_file": "config/email.backup_20230315_143000.yaml"
}
```

##### Atualizar Configurações Parcialmente

```
PATCH /api/config/partial
```

Atualiza apenas os campos especificados no email.yaml, mantendo os demais inalterados.

Exemplo de requisição:
```bash
curl -X PATCH http://localhost:5000/api/config/partial \
  -H "Content-Type: application/json" \
  -d '{
    "promocao": {
      "desconto": "50%"
    },
    "email": {
      "subject": "Oferta Especial"
    }
  }'
```

Parâmetros:
- Corpo da requisição: Objeto JSON com os campos a serem atualizados

Exemplo de resposta:
```json
{
  "status": "success",
  "message": "Configurações atualizadas parcialmente com sucesso",
  "backup_file": "config/email.backup_20230315_143500.yaml"
}
```

#### Códigos de Erro

A API retorna os seguintes códigos de status HTTP:

- **200 OK**: Requisição processada com sucesso
- **400 Bad Request**: Parâmetros inválidos ou faltando
- **404 Not Found**: Recurso não encontrado
- **422 Unprocessable Entity**: Validação de schema falhou
- **429 Too Many Requests**: Limite de taxa excedido (se rate limiting estiver habilitado)
- **500 Internal Server Error**: Erro interno do servidor

Em caso de erro, a resposta terá o seguinte formato:
```json
{
  "error": "Mensagem detalhada do erro"
}
```

## 📊 Estrutura dos Dados

Os arquivos de dados devem ser criados manualmente na pasta `data/` seguindo as estruturas abaixo:

### Arquivo `emails_geral.csv`

Arquivo principal de emails:

| Coluna | Descrição | Valores |
|--------|-----------|---------|
| email | Endereço de email (obrigatório) | email@domain.com |
| enviado | Status de envio | "" (não enviado), "ok" (enviado) |
| falhou | Status de falha | "" (sem falha), "ok" (falhou) |
| descadastro | Flag de descadastramento | "" (enviar), "S" (não enviar) |
| [outros] | Campos adicionais para template | Qualquer valor |

### Arquivo `test_emails.csv`

Arquivo para testes de envio em lote:

| Coluna | Descrição | Valores |
|--------|-----------|---------|
| email | Endereço de email (obrigatório) | email@domain.com |
| enviado | Status de envio | "" (não enviado), "ok" (enviado) |
| falhou | Status de falha | "" (sem falha), "ok" (falhou) |
| descadastro | Flag de descadastramento | "" (enviar), "S" (não enviar) |
| [outros] | Campos adicionais para template | Qualquer valor |

### Arquivo `descadastros.csv`

Lista de emails descadastrados:

| Coluna | Descrição | Valores |
|--------|-----------|---------|
| email | Endereço de email (obrigatório) | email@domain.com |

> 📝 **Nota:** Para mais detalhes sobre a estrutura dos arquivos CSV, consulte o arquivo `example_emails.csv.md`.

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
- **Dados**: arquivos CSV, Excel e outros dados na pasta `data/` 
- **Configurações**: arquivos YAML na pasta `config/`
- **Templates de Email**: arquivos HTML na pasta `templates/`
- **Logs e Relatórios**: arquivos na pasta `reports/`

> 🚫 **NUNCA VERSIONE ARQUIVOS CSV COM DADOS REAIS!** 
> 
> Todos os arquivos CSV estão configurados no `.gitignore` para serem ignorados pelo Git. Não remova estas exclusões nem tente forçar o versionamento destes arquivos.

### 📝 Arquivos de Exemplo

Para facilitar a configuração, o projeto inclui os seguintes arquivos de exemplo que são versionados:

| Arquivo Original | Arquivo de Exemplo | Descrição |
|------------------|-------------------|-----------|
| `config/config.yaml` | `example_config.yaml` | Configurações do sistema |
| `config/email.yaml` | `example_email.yaml` | Conteúdo dinâmico de emails |
| `templates/email.html` | `templates/email.html.example` | Template de email |
| `.env` | `.env.example` | Credenciais SMTP |
| Arquivos CSV na pasta `data/` | `example_emails.csv.md` | Descrição da estrutura dos arquivos CSV |

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
│   ├── emails_geral.csv         # Lista principal de emails
│   ├── test_emails.csv          # Emails para teste em lote
│   └── descadastros.csv         # Lista de emails descadastrados
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
│   │   └── csv_reader.py        # Leitor de CSV
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
├── example_emails.csv.md        # Documentação da estrutura CSV
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
    secret_key: "${JWT_SECRET_KEY}"  # Use variável de ambiente para o segredo
    token_expiry_hours: 24
    refresh_token_expiry_hours: 168  # 7 dias
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

### Proteção de Endpoints

O sistema utiliza diferentes tipos de proteção para os endpoints:

1. **@token_required**: Requer apenas um token JWT válido
2. **@role_required('admin')**: Requer um token JWT válido e a role específica ('admin')

Os seguintes endpoints estão protegidos:

| Endpoint | Método | Proteção | Função |
|----------|--------|----------|--------|
| `/api/health` | GET | token_required | Verificação de status |
| `/api/emails/send` | POST | token_required | Envio de emails |
| `/api/emails/test-smtp` | POST | token_required | Teste SMTP |
| `/api/emails/clear-flags` | POST | role_required('admin') | Limpar flags |
| `/api/emails/sync-unsubscribed` | POST | role_required('admin') | Sincronizar descadastros |
| `/api/config` | GET | role_required('admin') | Obter configurações |
| `/api/config` | PUT | role_required('admin') | Atualizar configurações |
| `/api/config/partial` | PATCH | role_required('admin') | Atualizar parcialmente |
| `/api/docs` | GET | token_required | Documentação da API |
| `/api/docs/swagger.json` | GET | token_required | Especificação OpenAPI |

### Endpoints de Autenticação

1. **Login** - `/api/auth/login` (POST)
   - Recebe credenciais e retorna token de acesso
   - Payload:
     ```json
     {
       "username": "seu_usuario",
       "password": "sua_senha"
     }
     ```
   - Resposta:
     ```json
     {
       "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
       "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
       "token_type": "bearer"
     }
     ```

2. **Verificar Token** - `/api/auth/verify` (GET)
   - Verifica se o token é válido
   - Header: `Authorization: Bearer seu_token_jwt`
   - Resposta:
     ```json
     {
       "valid": true,
       "user": {
         "id": "1",
         "username": "usuario",
         "roles": ["admin", "user"]
       }
     }
     ```

3. **Renovar Token** - `/api/auth/refresh` (POST)
   - Renova o token de acesso usando um refresh token
   - Payload:
     ```json
     {
       "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
     }
     ```
   - Resposta:
     ```json
     {
       "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
       "token_type": "bearer"
     }
     ```

### Uso em Endpoints Protegidos

Para acessar endpoints protegidos, inclua o token no cabeçalho:

```
Authorization: Bearer seu_token_jwt
```

Exemplo com curl:
```bash
curl -X GET http://localhost:5000/api/health \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

Exemplo com JavaScript:
```javascript
fetch('http://localhost:5000/api/emails/send', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    // payload
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

### Fluxo de Autenticação Recomendado

1. **Obter Token**:
   - Faça login com usuário e senha em `/api/auth/login`
   - Armazene o `access_token` e o `refresh_token` recebidos

2. **Usar o Token**:
   - Inclua o `access_token` no cabeçalho `Authorization: Bearer` em todas as requisições

3. **Lidar com Token Expirado**:
   - Se receber erro 401, use o `refresh_token` para obter um novo `access_token` em `/api/auth/refresh`
   - Se o `refresh_token` também estiver expirado, solicite ao usuário que faça login novamente

4. **Verificar Token (Opcional)**:
   - Para verificar se um token ainda é válido, faça uma requisição para `/api/auth/verify`