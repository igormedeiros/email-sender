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

---

# Especificação do Produto (QWEN.md)

## 1. Visão Geral do Produto

### 1.1 Nome do Produto
Treineinsite Email Sender

### 1.2 Descrição do Produto
O Treineinsite Email Sender é uma aplicação robusta em Python para envio de emails em lote, com foco em integração com banco de dados PostgreSQL. Ele substitui o workflow anterior no n8n, centralizando o gerenciamento de contatos e oferecendo funcionalidades avançadas de envio, personalização de conteúdo e relatórios detalhados. A ferramenta será hospedada em uma VPS operando 24/7, permitindo envios agendados e envios sob demanda de leads identificados como mais quentes por agentes analistas. O sistema também inclui mecanismos de retomada de processos interrompidos através da tabela `tbl_send_state`.

### 1.3 Objetivos do Produto
- Remover a dependência de arquivos CSV para gerenciamento de contatos
- Centralizar o gerenciamento de contatos no banco de dados PostgreSQL
- Implementar um sistema robusto de envio de emails em lote com controle de taxa
- Oferecer uma API REST para integração com outros sistemas
- Fornecer uma interface CLI (Command Line Interface) para operações manuais
- Gerenciar automaticamente descadastros e bounces
- Gerar relatórios detalhados de envio
- Futuro: Implementar inteligência para análise de contatos e personalização de conteúdo (Backlog)

## 2. Requisitos Funcionais

### 2.1 Gerenciamento de Contatos
- Carregar contatos elegíveis para envio diretamente do PostgreSQL
- Excluir contatos com tags de exclusão (Unsubscribed, Bounce, buyer_s2c5f20)
- Diferenciar contatos de teste (tag 'Test') para envios em modo de teste
- Evitar reenvio de emails para contatos que já receberam a mensagem
- Implementar processo de limpeza de base via integração com API SMTP (Locaweb) para identificar e marcar contatos com bounce

### 2.2 Envio de Emails
- Enviar emails em lote com controle de taxa (configurável por `batch_size` e `batch_delay`)
- Suportar envio em modo de teste (para contatos com tag 'Test') e produção
- Processar templates HTML com placeholders personalizáveis
- Substituir placeholders no template com dados do contato e informações do evento
- Adicionar links de descadastro dinâmicos no rodapé dos emails
- Implementar mecanismo de retentativas para falhas de envio
- Aplicar timeout configurável para tentativas de envio
- Agendar envio de emails para horários específicos
- Retomar processos de envio interrompidos através da tabela `tbl_send_state`
- Tratar adequadamente transações abortadas no banco de dados
- Limitar número de retentativas a 2 tentativas máximas para falhas de conexão
- Marcar contatos com problemas de envio com tag 'problem' para evitar reenvios
- Reduzir tempo de espera entre retentativas para otimizar tempo total de envio

### 2.3 Gerenciamento de Eventos
- Integrar com a API do Sympla para obter informações de eventos
- Permitir seleção de eventos através de interface interativa
- Armazenar informações do evento ativo no PostgreSQL
- Atualizar automaticamente link do evento com parâmetro de cupom

### 2.4 Personalização de Conteúdo
- Utilizar GenAI (Google Gemini) para geração automática de assuntos de email
- Permitir fallback para composição de assunto baseado em dados do evento
- Suportar variáveis personalizadas no conteúdo de email via `config/email.yaml`

### 2.5 Relatórios e Monitoramento
- Registrar status de envio de cada email em log no PostgreSQL
- Gerar relatórios detalhados após cada envio (sucessos, falhas, tempo de execução)
- Enviar notificações via Telegram para início e conclusão de envios
- Implementar tracking de abertura de emails via pixel transparente
- Registrar cliques em links dos emails
- Analisar relatórios de envio para identificar emails com problemas persistentes
- Gerar listas de emails que devem ser marcados para não serem mais enviados devido a timeouts repetidos
- Marcar automaticamente contatos com problemas persistentes de envio com tag 'problem'

### 2.6 API REST
- Implementar endpoint para verificação de saúde do serviço (`/api/health`)
- Implementar endpoint para descadastro de contatos (`/api/unsubscribe`)
- Implementar endpoint para tracking de abertura de emails via pixel (`/api/tracking/open`)
- Implementar endpoint para tracking de cliques em links (`/api/tracking/click`)
- Configurar autenticação e autorização para endpoints protegidos (JWT - não implementado ainda)
- Gerar documentação OpenAPI/Swagger automaticamente

### 2.7 Interface CLI
- Oferecer menu interativo para seleção de operações
- Permitir alternância entre ambientes de teste e produção
- Implementar comandos principais conforme especificado
- Interface do terminal baseada em Charm CLI (CRUSH AI style) para melhor experiência do usuário
- Resumo de envio otimizado com formato de tabela e exibição de tempo em horas quando necessário
- Marcação automática de contatos inválidos com tag 'invalid'

### 2.8 Segurança e Configuração
- Gerenciar segredos (credenciais SMTP, API keys) através de múltiplas fontes (env, .env, AWS, Azure)
- Armazenar todas as configurações em arquivos YAML externos
- Proteger dados sensíveis excluindo-os do versionamento Git

### 2.9 Integração com API SMTP (Locaweb)
- Integrar com a API de relatórios da Locaweb para obter dados de bounce
- Processar relatórios de envio para identificar emails com problemas
- Marcar automaticamente contatos com bounce no banco de dados PostgreSQL
- Evitar futuros envios para contatos marcados como bounce
- Agendar execução periódica do processo de limpeza

### 2.10 Inteligência de Seleção de Contatos e Conteúdo (Backlog)
- Implementar agentes de IA (LangGraph) para análise de contatos e definição de conteúdo personalizado
- Otimizar seleção de contatos com maior probabilidade de conversão
- Personalizar conteúdo de emails com base no perfil do contato
- Aumentar assertividade nos envios para maximizar vendas
- Otimizar custo-benefício dos envios considerando o custo por email

## 3. Requisitos Não-Funcionais

### 3.1 Desempenho
- Processar lotes de emails com tamanho configurável
- Implementar pausas entre lotes para evitar sobrecarga de recursos
- Suportar timeouts configuráveis para operações de envio

### 3.2 Confiabilidade
- Implementar mecanismo de retentativas para falhas de conexão
- Tratar interrupções de forma segura e permitir retomada do processo
- Registrar logs detalhados de todas as operações

### 3.3 Segurança
- Utilizar TLS para conexões SMTP
- Proteger credenciais sensíveis
- Implementar autenticação JWT para API (planejado)

### 3.4 Manutenibilidade
- Código modular e bem estruturado
- Configurações externalizadas
- Documentação clara e abrangente

## 4. Arquitetura do Sistema

### 4.1 Componentes Principais
1. **CLI (Command Line Interface)**: Interface interativa para operações manuais
2. **API REST**: Interface para integração com outros sistemas
3. **Email Service**: Lógica central de envio de emails
4. **Database Layer**: Camada de acesso ao PostgreSQL
5. **Template Processor**: Processamento de templates HTML
6. **SMTP Manager**: Gerenciamento de conexões SMTP
7. **Config Manager**: Gerenciamento de configurações
8. **Report Generator**: Geração de relatórios de envio
9. **Tracking Service**: Serviço para tracking de abertura e cliques
10. **Contact Intelligence Service** (Futuro): Serviço para análise inteligente de contatos e personalização de conteúdo (Backlog)
11. **Scheduling Service**: Serviço para agendamento de envio de emails
12. **UI Manager**: Gerenciamento de interface do terminal baseada em Charm CLI (CRUSH AI style)

### 4.2 Tecnologias Utilizadas
- **Linguagem**: Python 3.12+
- **Gerenciador de Dependências**: uv
- **Frameworks**: FastAPI (API), Typer (CLI)
- **Banco de Dados**: PostgreSQL
- **ORM**: psycopg (driver Postgres)
- **Templates**: Processamento manual de placeholders
- **Autenticação**: JWT (planejado)
- **Notificações**: Telegram Bot API
- **Inteligência Artificial**: Google Gemini, LangGraph (futuro)
- **Agendamento**: APScheduler (ou similar)
- **Interface do Terminal**: Charm CLI (inspirado no CRUSH AI)

## 5. Fluxos de Trabalho Principais

### 5.1 Fluxo de Envio de Emails
1. Iniciar processo via CLI ou API
2. Carregar configurações de `config.yaml` e `email.yaml`
3. Conectar ao PostgreSQL
4. Selecionar contatos elegíveis (excluindo unsubscribed, bounces, etc.)
5. Para cada lote de contatos:
   - Processar template HTML com dados do contato
   - Gerar assunto via GenAI ou fallback
   - Enviar email via SMTP
   - Registrar resultado no log
   - Pausar entre lotes
6. Marcar mensagem como processada
7. Gerar relatório de envio
8. Enviar notificação de conclusão via Telegram

### 5.2 Fluxo de Atualização de Evento via Sympla
1. Obter token da API do Sympla (do ambiente ou solicitar ao usuário)
2. Buscar últimos 3 eventos na API
3. Permitir seleção interativa de evento
4. Atualizar `config/email.yaml` com informações do evento
5. Desativar eventos antigos no PostgreSQL
6. Inserir ou atualizar evento selecionado no PostgreSQL

### 5.3 Fluxo de Descadastro
1. Usuário clica no link de descadastro no email
2. Requisição chega ao endpoint `/api/unsubscribe` via GET ou POST
3. Email é normalizado (trim e lowercase)
4. Registro do contato é atualizado no PostgreSQL (`unsubscribed = TRUE`)
5. Resposta de sucesso é retornada

### 5.4 Fluxo de Tracking de Abertura
1. Template de email inclui um pixel transparente em sua estrutura HTML
2. Pixel faz requisição para endpoint `/api/tracking/open` com parâmetros de identificação
3. API registra evento de abertura no log do contato e mensagem
4. Resposta retorna um pixel transparente 1x1

### 5.5 Fluxo de Tracking de Cliques
1. Links no email são reescritos para passar pelo endpoint de tracking
2. Usuário clica no link
3. Requisição chega ao endpoint `/api/tracking/click` com parâmetros de identificação
4. API registra evento de clique no log do contato e mensagem
5. Usuário é redirecionado para o destino original do link

### 5.6 Fluxo de Limpeza de Base via API SMTP
1. Processo automatizado acessa a API de relatórios da Locaweb
2. Obtém relatórios de envio com status de bounce
3. Processa relatórios para identificar emails com problemas
4. Atualiza registros de contatos no PostgreSQL, adicionando tag 'Bounce'
5. Agenda próxima execução do processo de limpeza

### 5.8 Fluxo de Setup de Envio de Emails
1. Usuário seleciona "Setup do envio de e-mails" no menu interativo da CLI
2. Sistema apresenta opções de configuração avançada:
   - Geração de títulos otimizados com GenAI
   - Otimização do corpo do email com GenAI
   - Configuração de testes A/B de assuntos
3. Para geração de títulos:
   - Sistema gera 3-5 variações de títulos com GenAI
   - Usuário aprova/reprova cada variação
   - Títulos aprovados são armazenados para uso em envios
4. Para otimização de conteúdo:
   - Sistema analisa template HTML e sugere melhorias
   - Usuário aprova/reprova sugestões
   - Conteúdo otimizado é salvo para uso em envios
5. Para testes A/B:
   - Sistema configura distribuição de variações de títulos
   - Define critérios de sucesso e análise
   - Sistema agenda análise automática de resultados
6. Envio de emails utiliza conteúdo previamente configurado e aprovado

## 6. Configurações Principais

### 6.1 SMTP (`config/config.yaml`)
- `host`: Servidor SMTP
- `port`: Porta SMTP (587 para STARTTLS)
- `username`: Usuário SMTP
- `password`: Senha SMTP (via secrets manager)
- `use_tls`: Usar TLS
- `retry_attempts`: Número de tentativas de envio
- `retry_delay`: Pausa entre tentativas

### 6.2 Email (`config/config.yaml`)
- `sender`: Remetente dos emails
- `batch_size`: Número de emails por lote (padrão: 200)
- `batch_delay`: Pausa entre lotes (segundos) (padrão: 5s)
- `test_recipient`: Email para testes
- `public_domain`: Domínio para links de descadastro

### 6.3 Evento (`config/email.yaml`)
- `sympla_id`: ID do evento no Sympla
- `nome`: Nome do evento
- `link`: Link do evento (com cupom)
- `data`: Data do evento (formato amigável)
- `cidade`: Cidade do evento
- `uf`: Estado do evento
- `local`: Local específico do evento
- `cupom`: Código de cupom promocional

### 6.4 IA e Otimização (`config/ai.yaml`)
- `genai_provider`: Provedor de GenAI (google, openai, etc.)
- `genai_model`: Modelo de linguagem a ser utilizado
- `approval_required`: Requerir aprovação do usuário para conteúdo gerado
- `ab_test_enabled`: Habilitar testes A/B automaticamente
- `ab_test_distribution`: Distribuição percentual para testes A/B

### 6.5 Interface do Terminal (`config/ui.yaml`)
- `theme`: Tema visual para interface do terminal (baseado em Charm CLI)
- `summary_format`: Formato do resumo de envio (tabela, compacto, etc.)
- `display_success_list`: Exibir listagem de emails enviados com sucesso (true/false)
- `time_format`: Formato de exibição do tempo (minutos, horas, automático)
- `ignored_tags`: Lista de tags que devem ser ignoradas no envio

## 7. Critérios de Aceitação

### 7.1 Envio de Emails
- [x] Emails são enviados corretamente para contatos elegíveis
- [x] Templates HTML são processados com placeholders substituídos
- [x] Links de descadastro são gerados corretamente
- [x] Assuntos são gerados automaticamente via GenAI ou fallback
- [x] Controles de taxa são respeitados (batch_size, batch_delay)
- [x] Retentativas são feitas para falhas de envio
- [x] Estado de envio é persistido na tabela tbl_send_state para retomada de processos
- [x] Tratamento adequado de transações abortadas no banco de dados
- [x] Limitação de retentativas a 2 tentativas máximas para falhas de conexão
- [x] Marcação de contatos com problemas de envio com tag 'problem' para evitar reenvios
- [x] Otimização do tempo de espera entre retentativas para reduzir tempo total de envio

### 7.2 Gerenciamento de Contatos
- [x] Contatos unsubscribed não recebem emails
- [x] Contatos com bounce não recebem emails
- [x] Contatos de teste só recebem emails em modo de teste
- [x] Não há reenvio de emails para contatos que já receberam
- [x] Processo de limpeza identifica e marca contatos com bounce
- [ ] Contatos com tags inválidas são ignorados automaticamente
- [ ] Marcação automática de emails inválidos com tag 'invalid'

### 7.3 Integração com Sympla
- [x] Eventos são buscados corretamente na API do Sympla
- [x] Evento selecionado é armazenado no PostgreSQL
- [x] Link do evento inclui parâmetro de cupom

### 7.4 API REST
- [x] Endpoint `/api/health` responde corretamente
- [x] Endpoint `/api/unsubscribe` processa descadastros
- [x] Endpoint `/api/tracking/open` registra aberturas de emails
- [x] Endpoint `/api/tracking/click` registra cliques em links
- [x] Documentação OpenAPI é gerada automaticamente

### 7.5 Interface CLI
- [x] Menu interativo funciona corretamente
- [x] Alternância entre ambientes test/prod funciona
- [x] Comandos principais estão disponíveis e funcionais
- [ ] Interface do terminal baseada em Charm CLI (CRUSH AI style)
- [ ] Resumo de envio otimizado com formato de tabela
- [ ] Tempo de execução exibido em horas quando maior que 1 hora
- [ ] Listagem de emails enviados com sucesso ocultada por padrão

### 7.6 Setup de Envio de Emails
- [ ] Menu interativo inclui opção "Setup do envio de e-mails"
- [ ] Geração automática de variações de títulos com GenAI
- [ ] Processo de aprovação interativa do usuário para títulos
- [ ] Otimização do corpo do email com GenAI e aprovação do usuário
- [ ] Configuração automática de testes A/B de assuntos
- [ ] Separação completa entre setup de conteúdo e processo de envio
- [ ] Envio de emails utiliza conteúdo previamente aprovado e configurado
- [ ] Análise de resultados de testes A/B para otimização contínua

## 8. Instruções para Correção de Problemas

### 8.1 Problema: Emails sendo enviados sem corpo HTML

#### 8.1.1 Diagnóstico
Quando executamos o comando `uv run -m email_sender.cli` e escolhemos a opção de enviar emails em massa, os emails estavam sendo enviados sem corpo (corpo vazio). Isso indicava um problema no processamento do template HTML.

#### 8.1.2 Causa Identificada
O problema estava na função `_replace_placeholders` do arquivo `src/email_sender/email_templating.py`. Havia um conflito de nomes com a variável `re` que estava sendo usada tanto como módulo importado quanto como variável local, causando um erro `UnboundLocalError`.

#### 8.1.3 Solução Aplicada
1. **Correção do conflito de nomes**: Substituímos a importação e uso da variável `re` por `regex_module` para evitar o conflito:
   ```python
   # Antes (causando erro):
   remaining_placeholders = re.findall(r'\{([^}]+)\}', html_content)
   
   # Depois (corrigido):
   import re as regex_module
   remaining_placeholders = regex_module.findall(r'\{([^}]+)\}', html_content)
   ```

2. **Adição de logs detalhados**: Para facilitar a depuração futura, adicionamos logs detalhados em várias partes do código:
   - Na função `process_email_template` do `email_service.py`
   - Na função `process` do `email_templating.py`
   - Na função `_replace_placeholders` do `email_templating.py`
   - No `SmtpManager` para verificar o conteúdo sendo enviado

3. **Configuração de logging**: Criamos um arquivo de configuração de logging (`src/email_sender/logging_config.py`) e o integramos aos principais módulos da aplicação (`cli.py` e `controller_cli.py`).

#### 8.1.4 Verificação
Após a correção, executamos novamente o envio de emails e verificamos:
- O template HTML está sendo carregado corretamente (tamanho: 3527)
- O conteúdo HTML processado tem um tamanho adequado (3942 e 3924 caracteres)
- Os placeholders estão sendo substituídos corretamente
- O email está sendo enviado com conteúdo HTML
- O relatório gerado confirma que os emails foram enviados com sucesso (2 enviados, 0 falhas)

#### 8.1.5 Arquivos Modificados
- `src/email_sender/email_templating.py` - Correção do conflito de nomes
- `src/email_sender/email_service.py` - Adição de logs
- `src/email_sender/smtp_manager.py` - Adição de logs
- `src/email_sender/logging_config.py` - Novo arquivo de configuração de logging
- `src/email_sender/cli.py` - Integração da configuração de logging
- `src/email_sender/controller_cli.py` - Integração da configuração de logging

## 9. Histórico de Atualizações

### 9.1 Setembro 2025
- Correção do teste falhando em CLI helpers relacionado à variável de ambiente EMAIL_SENDER
- Adição de novos testes para melhorar a cobertura de código
- Simplificação da estrutura do projeto mantendo a funcionalidade principal
- Atualização da documentação para refletir as mudanças atuais