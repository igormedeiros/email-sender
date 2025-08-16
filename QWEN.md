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
  - Setup avançado de envio de emails com IA
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
   - Usuário aprova uma variação ou solicita novas opções
   - Títulos aprovados são armazenados para uso em envios
4. Para otimização de conteúdo:
   - Sistema analisa template HTML e sugere melhorias
   - Usuário revisa e aprova alterações propostas
   - Conteúdo otimizado é salvo para uso em envios
5. Para testes A/B:
   - Sistema configura distribuição de variações de títulos
   - Usuário define percentual de distribuição para cada variação
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

Tags especiais utilizadas pelo sistema:
- `unsubscribed`: Contatos que se descadastraram
- `bounce`: Contatos com emails que retornaram como não entregues
- `test`: Contatos utilizados para testes
- `problem`: Contatos com problemas persistentes de envio
- `invalid`: Contatos com emails inválidos ou que não puderam ser enviados

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
- [ ] Contatos com tags inválidas são ignorados automaticamente
- [ ] Marcação automática de emails inválidos com tag 'invalid'

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
- [ ] Interface do terminal baseada em Charm CLI (CRUSH AI style)
- [ ] Resumo de envio otimizado com formato de tabela
- [ ] Tempo de execução exibido em horas quando maior que 1 hora
- [ ] Listagem de emails enviados com sucesso ocultada por padrão
- [ ] Contatos com tags inválidas são ignorados automaticamente
- [ ] Marcação automática de emails inválidos com tag 'invalid'

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

### 8.9 Setup de Envio de Emails
- [ ] Menu interativo inclui opção "Setup do envio de e-mails"
- [ ] Geração automática de variações de títulos com GenAI
- [ ] Processo de aprovação interativa do usuário para títulos
- [ ] Otimização do corpo do email com GenAI e aprovação do usuário
- [ ] Configuração automática de testes A/B de assuntos
- [ ] Separação completa entre setup de conteúdo e processo de envio
- [ ] Envio de emails utiliza conteúdo previamente aprovado e configurado
- [ ] Análise de resultados de testes A/B para otimização contínua
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

### 8.8 Inteligência de Seleção de Contatos e Otimização de Conteúdo (Backlog)
- [ ] Implementar agentes de IA para análise de perfis de contatos
- [ ] Desenvolver algoritmos para identificação de contatos com maior potencial de conversão
- [ ] Criar mecanismos de personalização de conteúdo baseado em perfil
- [ ] Medir e otimizar taxa de conversão após implementação
- [ ] Implementar agentes de IA com LangGraph para análise de relatórios de envio
- [ ] Utilizar IA para análise de aberturas e cliques em links dos emails
- [ ] Criar otimizações para maior assertividade em vendas através de IA
- [ ] Implementar geração de variações de títulos com aprovação do usuário
- [ ] Otimizar corpo do email do template com GenAI e aprovação do usuário
- [ ] Configurar testes A/B de assuntos no envio de emails

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

### 9.3 Análise Avançada com Agentes de IA
O sistema deve implementar agentes de IA desenvolvidos com LangGraph para análise avançada dos relatórios de envio:
- Análise de padrões de abertura de emails
- Análise de cliques em links dos emails
- Identificação de perfis de contatos com maior taxa de conversão
- Geração de insights para otimização de conteúdo e timing de envio

### 9.4 Otimização de Conteúdo com GenAI
Com base na análise dos dados, o sistema deve:
- Gerar variações de títulos otimizados para maior taxa de abertura
- Sugerir melhorias no corpo do email para aumentar engajamento
- Implementar testes A/B de assuntos automaticamente
- Criar personalizações de conteúdo baseadas no perfil do contato

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
   - Módulos de IA e agentes inteligentes devem estar em `src/email_sender/ai/`

2. **Estrutura de Pacotes**:
   - O código deve ser organizado em pacotes lógicos dentro de `src/`
   - Cada pacote deve conter um arquivo `__init__.py` para definição de exports
   - Módulos relacionados devem ser agrupados em pacotes com nomes significativos
   - Agentes de IA com LangGraph devem ser implementados em pacotes separados para facilitar manutenção

### 9.3 Padrões de Codificação
O código deve seguir os seguintes padrões de codificação:

1. **Imports**:
   - Nunca colocar `src` nos imports; usar imports relativos ou absolutos corretos
   - Organizar imports em ordem: bibliotecas padrão, bibliotecas de terceiros, imports locais
   - Evitar imports circulares através de uma boa arquitetura
   - Imports de módulos de IA devem ser feitos de forma lazy para evitar dependências pesadas

2. **Nomenclatura**:
   - Seguir convenções PEP 8 para nomes de variáveis, funções e classes
   - Usar nomes descritivos e significativos
   - Manter consistência na nomenclatura de variáveis e funções
   - Classes de agentes de IA devem seguir o padrão `NomeAgente` (ex: `OtimizadorConteudoAgente`)

3. **Documentação**:
   - Documentar funções, classes e módulos com docstrings em formato Google Python Style Guide
   - Comentar código complexo quando necessário, mas priorizar código autoexplicativo
   - Manter README.md e documentação atualizados
   - Documentar modelos e prompts de IA utilizados nos agentes

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

### 9.6 Reutilização e Manutenção
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

4. **Interface do Terminal**:
   - Utilizar bibliotecas Charm CLI para interface moderna e interativa
   - Seguir padrões de design inspirados no CRUSH AI
   - Manter consistência visual em todos os componentes da interface
   - Facilitar a leitura e interpretação dos relatórios de envio## 10. Setup de Envio de Emails

### 10.1 Configuração Avançada de Conteúdo
O sistema deve fornecer um menu dedicado para setup avançado de envio de emails:

1. **Criação de Títulos Otimizados**:
   - Geração automática de variações de títulos com GenAI
   - Apresentação de múltiplas opções para aprovação do usuário
   - Armazenamento de títulos aprovados para uso em envios

2. **Otimização de Corpo do Email**:
   - Análise do template HTML com GenAI para sugestões de melhorias
   - Personalização de conteúdo baseada em perfis de contatos
   - Aprovação do usuário antes de aplicar mudanças

3. **Testes A/B de Assuntos**:
   - Configuração automática de testes A/B para diferentes variações de títulos
   - Distribuição controlada de emails com diferentes assuntos
   - Análise de resultados para identificar a variação mais eficaz

### 10.2 Processo de Aprovação
O sistema deve implementar um processo rigoroso de aprovação:

1. **Aprovação de Títulos**:
   - Geração de 3-5 variações de títulos por GenAI
   - Interface interativa para seleção e aprovação do usuário
   - Opção de solicitar novas variações caso nenhuma seja aprovada

2. **Aprovação de Conteúdo**:
   - Visualização prévia do email otimizado
   - Feedback do usuário sobre mudanças propostas
   - Confirmação final antes de salvar alterações

3. **Configuração de Testes A/B**:
   - Definição de percentual de distribuição para cada variação
   - Configuração de métricas de sucesso
   - Agendamento de análise automática de resultados

### 10.3 Integração com Agentes de IA
O setup de envio deve integrar-se com agentes de IA:

1. **Agentes de Análise**:
   - Análise de dados históricos de envio para sugestões de otimização
   - Identificação de padrões de sucesso em títulos e conteúdo
   - Recomendações baseadas em perfis de contatos

2. **Agentes de Otimização**:
   - Geração de conteúdo personalizado para diferentes segmentos
   - Otimização de timing de envio baseada em comportamento dos contatos
   - Sugestões de melhorias contínuas baseadas em resultados

### 10.4 Separação de Responsabilidades
O processo de envio deve ser separado do processo de setup:

1. **Envio de Emails**:
   - Não deve solicitar geração de assunto antes de enviar
   - Deve utilizar títulos previamente aprovados e configurados
   - Foco em performance e confiabilidade do envio

2. **Setup de Envio**:
   - Menu dedicado exclusivamente para configuração avançada
   - Geração e aprovação de conteúdo com GenAI
   - Configuração de testes A/B e otimizações