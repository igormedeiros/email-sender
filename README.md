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

## 🎯 Uso

### Testar Configuração SMTP

Verifica se as configurações SMTP estão corretas enviando um email de teste:

```bash
python -m src.cli test-smtp
```

### Enviar Emails

Envie emails usando um template e planilha, especificando obrigatoriamente o modo de envio:

```bash
# Modo de teste (arquivo data/test_emails.csv)
python -m src.cli send-emails templates/email.html --mode=test

# Modo de produção (arquivo data/emails_geral.csv)
python -m src.cli send-emails templates/email.html --mode=production
```

Este comando sincroniza automaticamente a lista de descadastros antes de iniciar o envio, garantindo que emails descadastrados não recebam mensagens.

> **⚠️ Segurança:** É obrigatório especificar o modo de envio:
> - `--mode=test`: Usa o arquivo `data/test_emails.csv` para testes seguros (definido em config/config.yaml)
> - `--mode=production`: Usa a lista completa `emails_geral.csv` para envios reais (definido em config/config.yaml)
>
> Não é possível executar o comando sem especificar um destes modos, evitando envios acidentais.

Opções disponíveis:

| Opção | Descrição |
|-------|-----------|
| --csv-file | Caminho do arquivo CSV (opcional, usa configuração se omitido) |
| --config, -c | Arquivo de configuração (padrão: config/config.yaml) |
| --content | Arquivo de conteúdo dinâmico (padrão: config/email.yaml) |
| --skip-sync | Ignora a sincronização da lista de descadastros antes do envio |
| --mode | **Obrigatório**: especifique o modo de envio (`test` ou `production`) |

### Sincronizar Lista de Descadastros

Sincroniza manualmente a lista de descadastros com o arquivo principal de emails:

```bash
python -m src.cli sync-unsubscribed-command
```

Este comando atualiza a coluna `descadastro` no arquivo principal com base na lista de emails descadastrados. É executado automaticamente antes de cada envio, mas pode ser executado manualmente quando necessário. Ele marcará com "S" os emails que constam na lista de descadastros.

Além disso, se existirem emails na lista de descadastros que não estão presentes na lista principal de emails, o comando adicionará esses emails à lista principal com a flag `descadastro` já marcada como "S". Isso garante que todos os emails descadastrados estejam sempre registrados na lista principal.

### Limpar Flags de Envio

Reseta o status de todos os emails na planilha:

```bash
python -m src.cli clear-sent-flags
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
│   └── email.yaml       # Conteúdo dinâmico para templates
├── data/                # Arquivos de dados (não versionados)
│   ├── emails_geral.csv         # Lista principal de emails
│   ├── test_emails.csv          # Emails para teste em lote
│   └── descadastros.csv         # Lista de emails descadastrados
├── templates/           # Templates de email
│   └── email.html       # Template padrão de email HTML
├── src/                 # Código fonte
│   ├── utils/
│   │   └── csv_reader.py    # Leitor de CSV
│   ├── cli.py               # Interface de linha de comando
│   ├── config.py            # Gerenciamento de configuração
│   ├── email_service.py     # Serviço de envio de emails
│   └── unsubscribe_app.py   # App de descadastro/unsubscribe
├── tests/               # Testes automatizados
├── reports/             # Relatórios gerados (não versionados)
├── example_config.yaml          # Exemplo de configuração
├── example_email.yaml           # Exemplo de conteúdo de email
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