# Email Sender

Sistema robusto para envio de emails em lote com suporte a planilhas Excel, backup automático e relatórios detalhados.

## 📋 Índice
- [Recursos](#recursos)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Estrutura da Planilha](#estrutura-da-planilha)
- [Relatórios](#relatórios)
- [Desenvolvimento](#desenvolvimento)

## 🚀 Recursos

- ✉️ Envio de emails em lote a partir de planilhas Excel
- 🔄 Backup automático e restauração em caso de falhas
- 📊 Relatórios detalhados de envio
- ⏱️ Controle de taxa de envio e intervalos entre lotes
- 🔁 Sistema de retentativas automáticas
- 💾 Salvamento periódico do progresso
- 🛡️ Tratamento seguro de interrupções
- 📝 Suporte a templates de email personalizáveis

## 🛠️ Requisitos

- Python 3.12+
- pip (gerenciador de pacotes Python)
- Acesso a um servidor SMTP

## ⚙️ Instalação

1. Clone o repositório:
\`\`\`bash
git clone <repository-url>
cd email-sender
\`\`\`

2. Crie e ative um ambiente virtual:
\`\`\`bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\\Scripts\\activate   # Windows
\`\`\`

3. Instale as dependências:
\`\`\`bash
pip install -e .
\`\`\`

## 📝 Configuração

1. Copie o arquivo de exemplo de configuração:
\`\`\`bash
cp example.properties dev.properties
\`\`\`

2. Configure as credenciais SMTP e outras opções em \`dev.properties\`:

| Seção | Chave | Descrição | Exemplo |
|-------|-------|-----------|---------|
| smtp | host | Servidor SMTP | smtp.gmail.com |
| smtp | port | Porta SMTP | 587 |
| smtp | username | Usuário SMTP | seu@email.com |
| smtp | password | Senha SMTP | sua_senha |
| smtp | use_tls | Usar TLS | true |
| email | sender | Nome e email do remetente | Seu Nome \<seu@email.com\> |
| email | batch_size | Tamanho do lote | 100 |
| email | xlsx_file | Arquivo de emails | emails.xlsx |
| email | test_recipient | Email para teste | test@example.com |
| email | default_subject | Assunto padrão | Seu assunto padrão |
| email | batch_delay | Delay entre lotes (segundos) | 60 |

## 🎯 Uso

### Testar Configuração SMTP

Verifica se as configurações SMTP estão corretas enviando um email de teste:

\`\`\`bash
python -m email_sender test-smtp
\`\`\`

### Enviar Emails

Envie emails usando um template e planilha:

\`\`\`bash
python -m email_sender send-emails templates/email.txt --subject "Seu Assunto"
\`\`\`

Opções disponíveis:

| Opção | Descrição |
|-------|-----------|
| --xlsx-file | Caminho da planilha (opcional, usa configuração se omitido) |
| --subject, -s | Assunto do email (opcional, usa padrão se omitido) |
| --config, -c | Arquivo de configuração (padrão: dev.properties) |

### Limpar Flags de Envio

Reseta o status de todos os emails na planilha:

\`\`\`bash
python -m email_sender clear-sent-flags
\`\`\`

## 📊 Estrutura da Planilha

A planilha Excel (.xlsx) deve conter as seguintes colunas:

| Coluna | Descrição | Valores |
|--------|-----------|---------|
| email | Endereço de email (obrigatório) | email@domain.com |
| enviado | Status de envio | "" (não enviado), "ok" (enviado) |
| falhou | Status de falha | "" (sem falha), "ok" (falhou) |
| [outros] | Campos adicionais para template | Qualquer valor |

## 📈 Relatórios

Os relatórios são gerados automaticamente na pasta \`reports/\` após cada execução, contendo:

- Total de emails tentados
- Quantidade de envios bem-sucedidos
- Quantidade de falhas
- Tempo total de execução
- Tempo médio por email

Exemplo de nome do arquivo: \`email_report_20250212_172008.txt\`

## 🔧 Desenvolvimento

### Estrutura do Projeto

\`\`\`
email-sender/
├── src/
│   └── email_sender/
│       ├── utils/
│       │   ├── xlsx_reader.py    # Leitor de planilhas
│       │   └── csv_reader.py     # Leitor de CSV (alternativo)
│       ├── templates/
│       │   └── email.txt         # Template padrão
│       ├── cli.py               # Interface de linha de comando
│       ├── config.py            # Gerenciamento de configuração
│       ├── email_service.py     # Serviço de envio de emails
│       └── fast_cli.py         # CLI otimizada
├── tests/                      # Testes automatizados
├── reports/                    # Relatórios gerados
├── example.properties         # Exemplo de configuração
└── setup.py                  # Configuração do pacote
\`\`\`

### Executando Testes

Execute todos os testes:
\`\`\`bash
pytest
\`\`\`

Execute testes com cobertura:
\`\`\`bash
pytest --cov=src/email_sender
\`\`\`

### Características de Segurança

- ✅ Backup automático antes de modificar a planilha
- ✅ Restauração automática em caso de falhas
- ✅ Salvamento atômico usando arquivos temporários
- ✅ Tratamento de sinais (SIGINT) para interrupção segura
- ✅ Limpeza automática de arquivos temporários
- ✅ Retentativas configuráveis para falhas de SMTP