# Product Requirements Document (PRD) - Treineinsite Email Sender

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
- Implementar comandos para:
  - Envio de emails (toda a base)
  - Auto-teste (diagnóstico geral)
  - Geração de massa de teste
  - Atualização de dados do evento Sympla
  - Análise de relatórios de envio e marcação de contatos problemáticos

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

### 2.11 Agendamento de Envio de Emails
- Permitir agendamento de campanhas de envio para datas e horários específicos
- Armazenar informações de agendamento no banco de dados PostgreSQL
- Implementar serviço de agendamento para disparo automático de emails
- Enviar notificações sobre envios agendados
- Permitir envio imediato de emails para leads identificados como quentes por agentes analistas

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

### 5.7 Fluxo de Agendamento de Envio de Emails
1. Usuário define data e hora para envio através da CLI ou API
2. Sistema armazena informações de agendamento no PostgreSQL
3. Scheduling Service monitora agendamentos pendentes
4. No horário agendado, o serviço inicia o processo de envio de emails
5. Notificações são enviadas sobre o início do envio agendado
6. Agente analista pode acionar envio imediato de emails para leads quentes através da CLI ou API

## 6. Configurações Principais

### 6.1 SMTP (`config/config.yaml`)
- `host`: Servidor SMTP
- `port`: Porta SMTP (587 para STARTTLS)
- `username`: Usuário SMTP
- `password`: Senha SMTP (via secrets manager)
- `use_tls`: Usar TLS
- `retry_attempts`: Número de tentativas de envio
- `retry_delay`: Pausa entre tentativas
- `send_timeout`: Timeout por tentativa

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

## 7. Considerações de Implementação

### 7.1 Estrutura de Banco de Dados
O sistema utiliza as seguintes tabelas no PostgreSQL:
- `tbl_contacts`: Armazena informações dos contatos
- `tbl_contact_tags`: Relaciona contatos com tags
- `tbl_tags`: Lista de tags disponíveis
- `tbl_messages`: Registra campanhas de envio
- `tbl_message_logs`: Registra logs de envio
- `tbl_events`: Armazena informações de eventos
- `tbl_send_state`: Armazena o estado de envio para retomada de processos interrompidos

### 7.2 Tratamento de Erros
- Implementar retentativas para erros de conexão e timeout
- Registrar falhas em logs detalhados
- Continuar processamento mesmo após falhas individuais
- Notificar sobre falhas críticas via Telegram
- Tratar adequadamente transações abortadas no banco de dados

### 7.3 Segurança
- Gerenciar segredos através de múltiplas fontes (env, .env, cloud providers)
- Proteger endpoints da API com autenticação (JWT planejado)
- Validar e sanitizar inputs de usuários
- Excluir dados sensíveis do versionamento Git

### 7.4 Inicialização do Banco de Dados
- O sistema requer a criação da tabela `tbl_send_state` para rastrear o estado dos envios
- Scripts de inicialização estão disponíveis para criar as tabelas necessárias
- A tabela `tbl_send_state` permite retomar processos de envio interrompidos
- Configuração adequada de transações com autocommit para evitar bloqueios

## 8. Critérios de Aceitação

### 8.1 Envio de Emails
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

### 8.2 Gerenciamento de Contatos
- [x] Contatos unsubscribed não recebem emails
- [x] Contatos com bounce não recebem emails
- [x] Contatos de teste só recebem emails em modo de teste
- [x] Não há reenvio de emails para contatos que já receberam
- [x] Processo de limpeza identifica e marca contatos com bounce

### 8.3 Integração com Sympla
- [x] Eventos são buscados corretamente na API do Sympla
- [x] Evento selecionado é armazenado no PostgreSQL
- [x] Link do evento inclui parâmetro de cupom

### 8.4 API REST
- [x] Endpoint `/api/health` responde corretamente
- [x] Endpoint `/api/unsubscribe` processa descadastros
- [x] Endpoint `/api/tracking/open` registra aberturas de emails
- [x] Endpoint `/api/tracking/click` registra cliques em links
- [x] Documentação OpenAPI é gerada automaticamente

### 8.5 Interface CLI
- [x] Menu interativo funciona corretamente
- [x] Alternância entre ambientes test/prod funciona
- [x] Comandos principais estão disponíveis e funcionais

### 8.6 Relatórios e Monitoramento
- [x] Logs são registrados corretamente no PostgreSQL
- [x] Relatórios são gerados após envios
- [x] Notificações via Telegram são enviadas
- [x] Tracking de abertura de emails funciona corretamente
- [x] Tracking de cliques em links funciona corretamente
- [x] Análise de relatórios de envio identifica emails com problemas persistentes
- [x] Geração de listas de emails que devem ser marcados para não serem mais enviados devido a timeouts repetidos
- [x] Marcação automática de contatos com problemas persistentes de envio com tag 'problem'

### 8.7 Agendamento de Envio de Emails
- [x] É possível agendar envio de emails para data/hora específica
- [x] Sistema armazena corretamente informações de agendamento
- [x] Emails são enviados automaticamente no horário agendado
- [x] Notificações são enviadas sobre envios agendados
- [x] É possível acionar envio imediato de emails para leads quentes

### 8.8 Inteligência de Seleção de Contatos (Backlog)
- [ ] Implementar agentes de IA para análise de perfis de contatos
- [ ] Desenvolver algoritmos para identificação de contatos com maior potencial de conversão
- [ ] Criar mecanismos de personalização de conteúdo baseado em perfil
- [ ] Medir e otimizar taxa de conversão após implementação
- [ ] Alternância entre ambientes test/prod funciona
- [ ] Comandos principais estão disponíveis e funcionais

### 8.6 Relatórios e Monitoramento
- [ ] Logs são registrados corretamente no PostgreSQL
- [ ] Relatórios são gerados após envios
- [ ] Notificações via Telegram são enviadas
- [ ] Tracking de abertura de emails funciona corretamente
- [ ] Tracking de cliques em links funciona corretamente

### 8.7 Agendamento de Envio de Emails
- [ ] É possível agendar envio de emails para data/hora específica
- [ ] Sistema armazena corretamente informações de agendamento
- [ ] Emails são enviados automaticamente no horário agendado
- [ ] Notificações são enviadas sobre envios agendados
- [ ] É possível acionar envio imediato de emails para leads quentes

### 8.8 Inteligência de Seleção de Contatos (Backlog)
- [ ] Implementar agentes de IA para análise de perfis de contatos
- [ ] Desenvolver algoritmos para identificação de contatos com maior potencial de conversão
- [ ] Criar mecanismos de personalização de conteúdo baseado em perfil
- [ ] Medir e otimizar taxa de conversão após implementação### 8.8 Inteligência de Seleção de Contatos (Backlog)
- [ ] Implementar agentes de IA para análise de perfis de contatos
- [ ] Desenvolver algoritmos para identificação de contatos com maior potencial de conversão
- [ ] Criar mecanismos de personalização de conteúdo baseado em perfil
- [ ] Medir e otimizar taxa de conversão após implementação

## 9. Análise de Relatórios de Envio

### 9.1 Identificação de Problemas Persistentes
O sistema deve analisar os relatórios de envio para identificar emails que apresentam problemas persistentes, especialmente:
- Timeouts repetidos
- Erros de conexão
- Falhas de entrega

### 9.2 Geração de Listas de Contatos Problemáticos
Com base na análise dos relatórios, o sistema deve gerar listas de contatos que:
- Tiveram 2 ou mais falhas consecutivas de envio
- Apresentaram timeouts em múltiplas tentativas
- Devem ser marcados com a tag 'problem' para evitar reenvios futuros

### 9.3 Marcação Automática de Contatos
O sistema deve marcar automaticamente contatos com problemas persistentes:
- Adicionando a tag 'problem' aos contatos identificados
- Registrando a data e motivo da marcação
- Impedindo envios futuros para esses contatos

### 9.4 Relatórios de Qualidade da Base
O sistema deve gerar relatórios sobre a qualidade da base de contatos:
- Percentual de contatos com problemas persistentes
- Tendências de falhas por domínio de email
- Impacto na taxa de entrega geral## 9. Padrões de Projeto e Práticas de Desenvolvimento

### 9.1 Princípios de Desenvolvimento
O sistema deve seguir os seguintes princípios de desenvolvimento para garantir código limpo, legível e de fácil manutenção:

1. **Clean Code**: O código deve ser claro, legível e autoexplicativo, seguindo as melhores práticas de programação Python
2. **Princípio KISS (Keep It Simple, Stupid)**: Manter o código minimalista, evitando complexidade desnecessária
3. **Princípio DRY (Don't Repeat Yourself)**: Evitar duplicação de código através de reutilização e abstração adequada
4. **Separação de Responsabilidades**: Cada módulo e classe deve ter uma única responsabilidade bem definida
5. **Orientação a Objeto Moderada**: Aplicar orientação a objeto de forma equilibrada, sem aumentar a complexidade e legibilidade do código

### 9.2 Estrutura do Projeto
O projeto deve seguir a seguinte estrutura organizacional:

1. **Organização de Diretórios**:
   - Todos os arquivos de código Python (.py) devem estar dentro dos diretórios `src/` ou `tests/`
   - Nenhum código .py deve estar fora desses diretórios principais
   - Arquivos de configuração devem estar no diretório `config/`
   - Templates de email devem estar no diretório `templates/`
   - Relatórios e logs devem ser gerados no diretório `reports/`

2. **Estrutura de Pacotes**:
   - O código deve ser organizado em pacotes lógicos dentro de `src/`
   - Cada pacote deve conter um arquivo `__init__.py` para definição de exports
   - Módulos relacionados devem ser agrupados em pacotes com nomes significativos

### 9.3 Padrões de Codificação
O código deve seguir os seguintes padrões de codificação:

1. **Imports**:
   - Nunca colocar `src` nos imports; usar imports relativos ou absolutos corretos
   - Organizar imports em ordem: bibliotecas padrão, bibliotecas de terceiros, imports locais
   - Evitar imports circulares através de uma boa arquitetura

2. **Nomenclatura**:
   - Seguir convenções PEP 8 para nomes de variáveis, funções e classes
   - Usar nomes descritivos e significativos
   - Manter consistência na nomenclatura de variáveis e funções

3. **Documentação**:
   - Documentar funções, classes e módulos com docstrings em formato Google Python Style Guide
   - Comentar código complexo quando necessário, mas priorizar código autoexplicativo
   - Manter README.md e documentação atualizados

### 9.4 Testes e Qualidade
O sistema deve seguir práticas rigorosas de teste e garantia de qualidade:

1. **Testes Automatizados**:
   - Todos os recursos principais devem ter testes automatizados
   - Usar pytest como framework de testes principal
   - Configurar pytest.ini para gerar sempre relatórios de cobertura em coverage.xml
   - Manter cobertura de testes acima de 80% para código de produção

2. **Relatórios de Cobertura**:
   - Gerar relatórios de cobertura de código em formato XML (coverage.xml)
   - Gerar relatórios HTML para visualização detalhada
   - Integrar cobertura de testes no processo de CI/CD

3. **Linting e Formatação**:
   - Usar linters como flake8 ou pylint para verificar qualidade de código
   - Aplicar formatação automática com black para consistência
   - Configurar pre-commit hooks para verificar qualidade antes de commits

### 9.5 Reutilização e Manutenção
O sistema deve ser projetado para facilitar reutilização e manutenção:

1. **Componentização**:
   - Criar componentes reutilizáveis para funcionalidades comuns
   - Separar lógica de negócio de lógica de apresentação
   - Usar injeção de dependência quando apropriado

2. **Configuração Externa**:
   - Manter todas as configurações em arquivos externos (YAML, .env)
   - Nunca hardcode valores no código fonte
   - Usar variáveis de ambiente para credenciais sensíveis

3. **Versionamento**:
   - Seguir versionamento semântico (SemVer)
   - Manter CHANGELOG.md atualizado com mudanças em cada versão
   - Excluir arquivos sensíveis e temporários do versionamento Git