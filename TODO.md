# Plano de Implementação do Projeto

## Visão Geral
Este projeto visa migrar o workflow de envio de e-mails atualmente em n8n para uma aplicação Python, utilizando FastAPI para a API e PostgreSQL para o gerenciamento de contatos. O objetivo principal é remover a dependência de arquivos CSV, centralizar o gerenciamento de contatos no banco de dados e implementar endpoints para gerenciar a inscrição/desinscrição de contatos.

## Pré-requisitos
- [ ] Configuração do ambiente Python com `uv` como gerenciador de dependências.
- [ ] Instalação das dependências Python (`FastAPI`, `SQLAlchemy`, `psycopg2-binary`, `PyYAML`, `python-jose[cryptography]`, `uvicorn`, `Jinja2`, `python-telegram-bot`)
- [ ] Acesso e credenciais para o banco de dados PostgreSQL.
- [ ] Credenciais para o serviço de envio de e-mails (SMTP).

## Tarefas de Implementação

### Conjunto 1: Configuração e Modelagem de Dados (Prioridade: Crítica)
- [ ] **Tarefa 1.1**: Estruturar o projeto Python
  - Criar a estrutura de diretórios para a aplicação FastAPI, separando a lógica de API, CLI e serviços.
  - Detalhes técnicos e abordagem: Definir `main.py` (para API), `cli.py` (para CLI), `config/`, `database/`, `models/`, `services/`, `templates/`.
  - Dependências: Nenhuma

- [ ] **Tarefa 1.2**: Gerenciar configurações com `config.yaml` e `email.yaml`
  - Criar `config/config.yaml` para credenciais de banco de dados, SMTP e JWT.
  - Criar `config/email.yaml` para configurações de e-mail (título, caminho do template, etc.).
  - Detalhes técnicos e abordagem: Utilizar `PyYAML` para carregar as configurações. Implementar um módulo `config.py` para abstrair o acesso a essas configurações.
  - Dependências: Nenhuma

- [ ] **Tarefa 1.3**: Estabelecer conexão com PostgreSQL
  - Configurar a conexão com o banco de dados PostgreSQL utilizando SQLAlchemy.
  - Detalhes técnicos e abordagem: Criar um módulo `database/connection.py` para gerenciar a conexão e sessões. As credenciais devem vir do `config.yaml`.
  - Dependências: Tarefa 1.2

- [ ] **Tarefa 1.4**: Definir modelos de dados (SQLAlchemy ORM)
  - Mapear as tabelas `tbl_contacts`, `tbl_contact_tags`, `tbl_tags`, `tbl_messages`, `tbl_message_sent_logs` para modelos SQLAlchemy.
  - Detalhes técnicos e abordagem: Criar `models/` com as classes ORM correspondentes às tabelas existentes no n8n workflow. Garantir que os modelos reflitam as boas práticas para manipulação por LLMs (nomes claros, tipagem explícita).
  - Dependências: Tarefa 1.3

### Conjunto 2: Lógica de Contatos e E-mails (Prioridade: Alta)
- [ ] **Tarefa 2.1**: Replicar a lógica de carregamento de contatos
  - Implementar a query SQL do nó "Load Contacts" do n8n em Python, utilizando os modelos SQLAlchemy.
  - Detalhes técnicos e abordagem: Criar uma função em `services/contact_service.py` para buscar contatos elegíveis para envio, considerando as tags de exclusão (`Unsubscribed`, `Bounce`, `buyer_s2c5f20`) e a tag `Test`.
  - Dependências: Tarefa 1.4

- [ ] **Tarefa 2.2**: Desenvolver o serviço de envio de e-mails
  - Implementar a funcionalidade de envio de e-mails via SMTP.
  - Detalhes técnicos e abordagem: Utilizar a biblioteca `smtplib` do Python. Criar um serviço em `services/email_service.py` que utilize as configurações de SMTP do `config.yaml`.
  - Dependências: Tarexa 1.2

- [ ] **Tarefa 2.3**: Gerar templates de e-mail HTML
  - Adaptar o template HTML do n8n para ser renderizado dinamicamente em Python com Jinja2.
  - Detalhes técnicos e abordagem: Criar um diretório `templates/` e usar Jinja2 para preencher os placeholders. O template HTML deve conter no rodapé um link para descadastro (`/unsubscribe?email={{ contact.email }}`), apontando para o endpoint que trata desse processo com o PostgreSQL.
  - Dependências: Tarefa 1.2

- [ ] **Tarefa 2.4**: Implementar a lógica de log de envio
  - Registrar o status de envio de cada e-mail na tabela `tbl_message_sent_logs`.
  - Detalhes técnicos e abordagem: Integrar a inserção de logs no `email_service.py` após cada tentativa de envio, registrando o `contact_id`, `message_id`, `event_type` ('sent'), `event_timestamp` e `status` (resposta do SMTP).
  - Dependências: Tarefa 1.4, Tarefa 2.2

### Conjunto 3: API FastAPI e Autenticação (Prioridade: Alta)
- [ ] **Tarefa 3.1**: Criar a aplicação FastAPI e autenticação JWT
  - Inicializar a aplicação FastAPI e configurar a autenticação via JWT para endpoints seguros.
  - Detalhes técnicos e abordagem: Utilizar `python-jose` para JWT. Criar um módulo `api/auth.py` para lidar com a autenticação e dependências de segurança. A chave secreta JWT deve vir do `config.yaml`.
  - Dependências: Tarefa 1.2

- [ ] **Tarefa 3.2**: Implementar endpoint para remoção de contatos (unsubscribe)
  - Criar um endpoint GET/POST (`/unsubscribe`) para que os usuários possam se descadastrar da lista de e-mails.
  - Detalhes técnicos e abordagem: O endpoint deve receber o e-mail do contato (via query param ou corpo da requisição) e atualizar o status `unsubscribed` na tabela `tbl_contacts` para `TRUE` e/ou adicionar a tag 'Unsubscribed' em `tbl_contact_tags`. Este endpoint não precisa de autenticação.
  - Dependências: Tarefa 1.4

- [ ] **Tarefa 3.3**: Implementar endpoint para reativação de contatos (resubscribe)
  - Criar um endpoint GET/POST (`/resubscribe`) para que os usuários possam se recadastrar na lista de e-mails.
  - Detalhes técnicos e abordagem: O endpoint deve receber o e-mail do contato e reverter o status `unsubscribed` para `FALSE` e/ou remover a tag 'Unsubscribed'. Este endpoint não precisa de autenticação.
  - Dependências: Tarefa 1.4

- [ ] **Tarefa 3.4**: Implementar endpoint para iniciar o envio de e-mails (trigger)
  - Criar um endpoint POST (`/send-emails`) protegido por JWT para disparar o processo de envio de e-mails.
  - Detalhes técnicos e abordagem: Este endpoint deve chamar as funções de carregamento de contatos (Tarefa 2.1) e o serviço de envio de e-mails (Tarefa 2.2). Deve ser assíncrono para não bloquear a API.
  - Dependências: Tarefa 2.1, Tarefa 2.2, Tarefa 3.1

- [ ] **Tarefa 3.5**: Implementar endpoint para agendar mensagens
  - Criar um endpoint POST (`/schedule-message`) protegido por JWT para agendar o envio de e-mails.
  - Detalhes técnicos e abordagem: Este endpoint deve receber os parâmetros da mensagem (ID da mensagem, evento, etc.) e agendar uma tarefa em background (e.g., com `APScheduler` ou similar) para disparar o processo de envio em um horário futuro. As informações do evento devem ser gravadas e atualizadas em um `event.yaml`.
  - Dependências: Tarefa 1.2, Tarefa 3.1

### Conjunto 4: Interface de Linha de Comando (CLI) e Notificações (Prioridade: Média)
- [ ] **Tarefa 4.1**: Desenvolver interface CLI para envio de e-mails
  - Criar um comando CLI para disparar o processo de envio de e-mails manualmente.
  - Detalhes técnicos e abordagem: Utilizar `argparse` ou `Click` para criar o comando `python cli.py send-emails`. Este comando deve reutilizar a lógica de carregamento e envio de e-mails (Tarefa 2.1, Tarefa 2.2).
  - Dependências: Tarefa 2.1, Tarefa 2.2

- [ ] **Tarefa 4.2**: Integrar notificações do Telegram
  - Adaptar a lógica de notificação de início e fim do processo de envio para o Telegram.
  - Detalhes técnicos e abordagem: Utilizar a biblioteca `python-telegram-bot`. As credenciais do Telegram devem vir do `config.yaml`. As notificações devem ser disparadas tanto pela API quanto pela CLI.
  - Dependências: Tarefa 1.2

- [ ] **Tarefa 4.3**: Adicionar tratamento de erros e logging
  - Implementar um sistema robusto de tratamento de erros e logging para a aplicação (API e CLI).
  - Detalhes técnicos e abordagem: Utilizar o módulo `logging` do Python para registrar eventos e erros, configurando diferentes níveis de log (INFO, WARNING, ERROR).
  - Dependências: Nenhuma

## Estratégia de Testes
- [ ] Testes unitários para cada função de serviço (`contact_service.py`, `email_service.py`, `config.py`, `database/connection.py`)
- [ ] Testes de integração para os endpoints da FastAPI (`/unsubscribe`, `/resubscribe`, `/send-emails`, `/schedule-message`)
- [ ] Testes de integração para os comandos CLI.
- [ ] Testes de banco de dados para garantir a correta manipulação dos dados de contato e logs.

## Considerações de Deploy
- [ ] Processo de build: Dockerfile para empacotar a aplicação FastAPI e CLI.
- [ ] Configuração do ambiente: Gerenciamento de variáveis de ambiente para produção (e.g., via Docker secrets ou Kubernetes secrets).
- [ ] Configuração de monitoramento e logs: Integração com ferramentas de monitoramento (e.g., Prometheus, Grafana) e centralização de logs (e.g., ELK Stack).

## Pós-Implementação
- [ ] Atualizações de documentação: Documentar a API FastAPI (com Swagger/OpenAPI gerado automaticamente) e a interface CLI.
- [ ] Otimização de performance: Otimizar queries SQL e o processo de envio de e-mails para grandes volumes, considerando o uso de filas de mensagens (e.g., RabbitMQ, Kafka) para envios assíncronos.
- [ ] Considerações de manutenção: Definir rotinas de manutenção do banco de dados e monitoramento contínuo. Implementar alertas para falhas no envio de e-mails ou na API.