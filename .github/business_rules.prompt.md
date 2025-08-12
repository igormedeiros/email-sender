# Email Sender - Documentação de Regras de Negócio

_Gerado em: 10 de maio de 2025_

Este documento descreve as regras de negócio fundamentais, comportamentos e funcionalidades da aplicação Email Sender. Serve como referência para compreender como o sistema opera e quais regras governam seu comportamento.

## 1. Conceitos Fundamentais

### 1.1 Visão Geral do Sistema

O Email Sender é uma aplicação robusta projetada para processamento de emails em lote com recursos avançados para gerenciamento de listas de emails, acompanhamento de status de entrega e garantia de comunicação confiável. O sistema foi projetado para:

- Enviar emails em lotes a partir de uma base de contatos
- Rastrear o status de entrega de emails
- Gerenciar descadastros e bounces
- Fornecer relatórios detalhados
- Implementar tratamento de erros e recuperação resiliente
- Suportar modos de teste e produção

### 1.2 Componentes Principais

1. **Email Service**: Serviço principal que gerencia o processo de envio de emails
2. (removido) 
3. **Template Processor**: Gerencia a personalização do conteúdo dos emails
4. **SMTP Manager**: Gerencia a comunicação com o servidor de email
5. **Report Generator**: Cria relatórios detalhados das campanhas de email
6. **Configuration Management**: Configuração externa via arquivos YAML

## 2. Regras de Gerenciamento de Dados

### 2.1 Estrutura dos dados de contato

- email: endereço de e-mail válido (obrigatório)
- flags e tags de status (ex.: unsubscribed, bounce)
- atributos de personalização (ex.: nome, empresa, cargo)

#### 2.1.1 (Modo CLI baseado em CSV)
- Colunas esperadas no CSV principal: `email`, `enviado`, `falhou`, `descadastro` (S/""), `bounced` (True/False)
- Normalização automática: emails convertidos para minúsculas quando `enviado` está vazio
- Filtragem implícita no processamento: somente linhas com `enviado==""` e `falhou!="ok"` e `descadastro!="S"`

### 2.2 Armazenamento

- Dois cenários suportados:
  - **Workflow n8n (produção)**: Postgres para `tbl_contacts`, `tbl_tags`/`tbl_contact_tags`, `tbl_messages`, `tbl_message_logs`, `tbl_lead_scores`, `tbl_events`.
  - **CLI Python (CSV)**: arquivos CSV versionados localmente para base de envio; listas de `descadastros.csv` e `bounces.csv` externas.

### 2.3 Regras de Segurança de Dados

1. **Consistência**: operações críticas transacionais
2. **Idempotência**: chaves compostas em logs para evitar duplicatas
3. **Restauração em Caso de Falha**: Se uma operação falhar, o sistema restaura automaticamente os dados do backup
4. **Tratamento de Sinais**: Captura sinais SIGINT e outros sinais de interrupção para salvar dados com segurança

### 2.4 Regras de Processamento de Dados

1. **Processamento em Lotes**: Os emails são processados em tamanhos de lote configuráveis
2. (removido)
3. **Normalização de Email**: Todos os endereços de email são convertidos para minúsculas para consistência
4. **Tratamento de Duplicatas**: O sistema pode identificar e gerenciar endereços de email duplicados

## 3. Regras de Envio de Email

### 3.1 Fluxo de Envio

1. **Inicialização**:

   - Carregar configuração
   - Validar origem de dados
   - Validar existência do template
   - Carregar listas de descadastros e bounces

2. **Filtragem**:

   - Pular contatos já logados como enviados na campanha atual
   - Pular emails descadastrados
   - Pular emails com histórico de bounce
   - Pular endereços de email inválidos

3. **Processamento**:

   - Processar emails em lotes de tamanho configurável
   - Aplicar atrasos configuráveis entre lotes
   - Personalizar conteúdo usando template e dados do destinatário
   - Rastrear tentativas de envio e resultados

4. **Conclusão**:
   - Gerar relatório detalhado
   - Limpar arquivos temporários
   - Fornecer estatísticas sobre taxas de sucesso/falha

### 3.2 Tratamento de Erros e Novas Tentativas

1. **Erros de Conexão**:

   - O sistema detecta erros relacionados à rede/conexão automaticamente
   - Erros de conexão acionam tentativas de reenvio

2. **Configuração de Novas Tentativas**:

   - Janela de novas tentativas padrão: 5 minutos máximo para falhas de conexão
   - Número configurável de tentativas de reenvio (padrão: 3)
   - Atraso configurável entre tentativas (padrão: 60 segundos)
   - Timeout configurável por tentativa (padrão: 10 segundos)

3. **Marcação de Falhas**:
   - Emails que falham após todas as tentativas são marcados com falha na base
   - O sistema preserva a mensagem de erro específica para solução de problemas

### 3.4 Validação de Emails (modo CLI)
- Ignorar registros com email ausente, `NaN` ou sem `@` (contabilizados como inválidos)
- Emails na lista de descadastros ou bounces são pulados e contabilizados como "pulados"
- Tamanho de lote e pausa entre lotes configuráveis

### 3.3 Modo de Teste

1. O sistema suporta modos de teste e produção
2. O modo de teste usa lista/segmento de contatos de teste para evitar comunicação com clientes reais
3. Todas as outras funcionalidades permanecem as mesmas entre os modos de teste e produção

## 4. Regras de Conteúdo de Email

### 4.1 Processamento de Templates

1. **Templates HTML**:

   - Sistema usa templates HTML com marcadores de placeholder
   - Templates são carregados do caminho especificado ou do diretório templates/

2. **Substituição de Placeholders**:

   - {email}: Substituído pelo email do destinatário
   - {unsubscribe_url}: Substituído pela URL de descadastro da configuração
   - {subscribe_url}: Substituído pela URL de cadastro da configuração
   - {nome}, {empresa}, {cargo}: Substituídos pelos dados do destinatário
   - Qualquer atributo pode ser usado como placeholder com a sintaxe {nome_do_atributo}

3. **Placeholders Especiais**:

   - {desconto_paragrafo}: Conteúdo condicional que aparece apenas se o desconto estiver configurado
   - {link_evento}, {data_evento}, {cidade}, {local}: Informações específicas do evento

4. **Processamento CSS**:
   - Se a biblioteca premailer estiver disponível, o CSS externo é automaticamente incorporado
   - O caminho do arquivo CSS pode ser especificado na configuração

## 5. Gerenciamento de Descadastros e Bounces

### 5.1 Tratamento de Descadastros

1. Antes do envio, o sistema consulta contatos com unsubscribed=true
2. Emails marcados com "S" na coluna descadastro nunca são enviados
3. Emails descadastrados são pulados e reportados nas estatísticas

### 5.2 Tratamento de Bounces

1. Emails com bounce são rastreados via tags/flags na base
2. Emails na lista de bounces são pulados durante o processo de envio
3. Os bounces pulados são reportados nas estatísticas

## 6. Relatórios e Monitoramento

### 6.1 Geração de Relatórios

Para cada processo de envio, o sistema gera relatórios com:

1. Total de emails com tentativa de envio
2. Contagem de emails enviados com sucesso
3. Contagem de emails com falha
4. Carimbos de data/hora detalhados e duração
5. Tempo médio por email
6. Emails pulados (descadastrados, bounces, inválidos)
7. Estatísticas de erros de conexão

### 6.2 Saída do Console

O sistema fornece uma saída de console rica durante a operação:

1. Mensagens de status com código de cores
2. Barras de progresso com estimativas de tempo
3. Informações de processamento em lote
4. Mensagens de erro detalhadas para resolução de problemas
5. Tabelas de resumo com resultados de envio

### 6.3 Logs

1. O sistema mantém logs detalhados de todas as operações
2. Formatação rica para logs do console
3. Logs baseados em arquivos para arquivamento e solução de problemas

## 7. Regras de Configuração

### 7.1 Estrutura de Configuração

O sistema usa arquivos YAML para configuração com estas seções principais:

1. **Configuração SMTP**:

   - host: Nome do servidor SMTP
   - port: Porta do servidor SMTP
   - use_tls: Booleano para uso de TLS
   - retry_attempts: Número de tentativas de reenvio
   - retry_delay: Atraso entre tentativas em segundos
   - send_timeout: Timeout por tentativa de envio

2. **Configuração de Email**:

   - sender: Endereço de email e nome de exibição do remetente
   - batch_size: Número de emails por lote
   - batch_delay: Atraso entre lotes em segundos
   - csv_file: Caminho do arquivo CSV principal
   - unsubscribe_file: Caminho da lista de descadastros
   - test_recipient: Email para testes individuais
   - test_emails_file: Caminho do arquivo CSV de teste

3. **Configuração de Conteúdo**:
   - Variáveis de assunto e conteúdo do email
   - Detalhes do evento
   - URLs para links de descadastro/cadastro
   - Detalhes de promoção
   - Referência do arquivo CSS

### 7.2 Ambiente (.env)
- `ENVIRONMENT`: `prod` ou `test` (em `test`, nunca enviar para base real; usar somente CSV/lista de teste)
- Postgres: `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
- Telegram: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Nunca commitar `.env`; versionar `.env.sample` com as chaves acima

### 7.3 Segurança da API
- Endpoints REST requerem token (JWT/API key) quando habilitado nas configurações
- Operações administrativas (ex.: limpar flags, sincronizações) exigem papel `admin`

## 8. Recursos de Resiliência e Segurança

### 8.1 Resiliência de Rede

1. **Detecção de Erros de Conexão**:

   - O sistema detecta e categoriza automaticamente erros de rede/conexão
   - Uma lista abrangente de padrões de erro é mantida para identificar problemas de conexão

2. **Janela de Novas Tentativas Baseada em Tempo**:
   - O sistema implementa uma janela de novas tentativas de 5 minutos para problemas temporários de conexão
   - Emails que não podem ser enviados dentro desta janela são marcados como falha

### 8.2 Segurança do Processo

1. **Tratamento de Sinais**:

   - O sistema captura SIGINT (Ctrl+C) e outros sinais de interrupção
   - Na interrupção, os dados são salvos e os recursos são devidamente fechados

2. **Integridade de Dados**:
   - Backups são criados antes das modificações
   - As mudanças são salvas atomicamente
   - Arquivos temporários são limpos

### 8.3 Recuperação de Erros

1. **Restauração Automática**:

   - O sistema restaura automaticamente a partir do backup em caso de falha
   - Erros críticos são registrados e reportados

2. **Mecanismos de Pausa**:
   - Pausas configuráveis entre lotes para evitar sobrecarga do servidor
   - Atrasos adaptativos entre tentativas

## 9. Capacidades de Integração

### 9.1 Interface de Linha de Comando

O sistema fornece uma interface de linha de comando para:

- Enviar emails
- Executar envios de teste
 
- Verificar status
- Gerar relatórios

### 9.2 API REST (principais endpoints)
- `POST /api/emails/send` (token): dispara envio em lote; aceita `csv_file`, `template`, `skip_unsubscribed_sync`, `mode=test|production`.
- `POST /api/emails/test-smtp` (token): envia email de teste para validar SMTP.
- `POST /api/emails/clear-flags` (admin): limpa flags `enviado`/`falhou` no CSV.
- `POST /api/emails/sync-unsubscribed` (admin): sincroniza `descadastros.csv` com CSV principal.
- `GET /api/config` (admin): obtém `config/email.yaml`.
- `PUT /api/config` (admin): substitui `config/email.yaml` com backup automático.
- `PATCH /api/config/partial` (admin): atualiza parcialmente `config/email.yaml` com merge recursivo.

### 9.3 CLI (comandos Typer)
- `send-emails`:
  - Opções: `--config`, `--content`, `--csv-file`, `--mode=test|production` (padrão vem de `ENVIRONMENT`), `--bounces-file`, `--skip-sync`.
  - Usa `email.yaml` para `template_path` e assunto; aplica retries, timeouts e pausas entre lotes.
- `test-smtp`: envia email de teste para `test_recipient` da configuração.
- `clear-sent-flags`: limpa colunas `enviado`/`falhou` com backup atômico.
- `sync-unsubscribed-command`: reconcilia `descadastros.csv` no CSV principal (marca `descadastro == 'S'`).
- `sync-bounces-command`: marca `bounced == True` no CSV principal com base em lista externa.

## 10. Workflows e passos (base n8n — referência para reimplementar em Python CLI)

Esta seção consolida os fluxos que estavam no `n8n/` e serve como especificação funcional para a nova implementação em Python puro (CLI).

### 10.1 Tabelas/Conceitos usados
- `tbl_contacts`: contatos; campos relevantes: `id`, `email`, `is_buyer`, `unsubscribed`.
- `tbl_tags` e `tbl_contact_tags`: taxonomia e pivot de tags. Tags: `Unsubscribed`, `Bounce` (id 1), `abriu email` (id 6), `Clicked_email` (id 7), `buyer_s2c5f20`, `test`.
- `tbl_messages`: campanhas (`id`, `subject`, `internal_name`, `event_id`, `processed`).
- `tbl_message_logs`: trilhas de eventos (`sent`, `opened`, `clicked`) com `event_timestamp`, `status/details`, `ip_address`, `user_agent`.
- `tbl_lead_scores`: pontuação por contato (opened +1, clicked +3) via upsert.
- `tbl_events`: evento ativo do Sympla (`sympla_id`, `event_name`, datas, `city/state/place_name`, `event_link`, `detail` Markdown, `is_active`).

### 10.2 Configurar/Ativar evento (Sympla)
- Entrada define `eventId` e `cupom`.
- Buscar evento via API Sympla; converter `detail` HTML→Markdown; formatar datas ("01 e 02 de março") e horário ("Xh às Yh"); montar `event_link = url + cupom`.
- Desativar todos (`is_active=false`) e atualizar ou inserir evento com `is_active=true`.
- Notificar via Telegram (cidade, datas, sympla_id).

### 10.3 Obter evento ativo
- `SELECT * FROM tbl_events WHERE is_active = true` e disponibilizar para outros fluxos.

### 10.4 Envio de emails (campanha)
- Início: marcar modo de sessão `test|prod`; obter evento ativo; gerar assunto (IA opcional com memória por `sympla_id`); criar linha em `tbl_messages` (`subject`, `internal_name`) retornando `message_id`.
- Seleção de contatos (Postgres):
  - `email` não vazio; `is_buyer=false`; `unsubscribed=false`.
  - NÃO ter tags: `Unsubscribed`, `Bounce`, `buyer_s2c5f20`.
  - Modo `test=true`: contato deve ter tag `test`. `test=false`: contato não pode ter tag `test`.
  - Não ter log prévio para a `message_id` em `tbl_message_logs`.
  - A `tbl_messages.processed` da mensagem atual deve ser `false`.
- Renderização do HTML: inclui pixel `GET /pixel?contact_id&message_id`, CTA `GET /powertreine?contact_id&message_id` (redireciona para `event_link`), e link de descadastro `GET /unsubscribe?email`.
- Envio SMTP com validação de sucesso (ex.: resposta contém "250 2.0.0 Ok"); throttle ~1.5s; `INSERT` log `sent`.
- Finalização: `UPDATE tbl_messages SET processed=true` e notificação Telegram.
- Observação ambiente: se `ENVIRONMENT=test`, envio limitado a emails de teste; notificações podem ir para chat de testes.

### 10.5 Pixel de abertura
- `GET /pixel?contact_id&message_id` responde com redirect `about:blank`.
- Upsert em `tbl_lead_scores` (+1) e tag "abriu email" (id 6) no contato.
- Log `opened` com IP (e User-Agent se aplicável), evitando duplicatas.

### 10.6 Clique em link
- `GET /powertreine?contact_id&message_id&url=<destino>` redireciona para `event_link` do evento ativo.
- Upsert `tbl_lead_scores` (+3), tag `Clicked_email` (id 7) e log `clicked` (detalhes=URL, IP, User-Agent) sem duplicar.

### 10.7 Descadastro
- `GET /unsubscribe?email=...` marca `unsubscribed=true` no contato e responde com página de confirmação.

### 10.8 Bounces (hard bounces)
- Coletar do provedor via API (status=errors), paginar e filtrar por `bounce_code` (lista de hard bounces). Para cada email: tag `Bounce` (id 1).
- Notificar via Telegram início/fim com totais.
- Observação ambiente: em `test`, limpeza atua somente em base de teste/simulação e notifica no chat de testes.

### 10.9 Regras derivadas
- Idempotência por `message_id/contact_id` usando `tbl_message_logs`.
- Fechamento de campanha por `tbl_messages.processed=true`.
- Segmentação por tags e modo `test`.
- Pontuação de lead por abertura/clique.
- Tracking por pixel e webhooks dedicados.
- Notificações operacionais (Telegram) em marcos do processo.

## 10. Implantação e Gerenciamento

### 10.1 Processo de Implantação

1. Configuration files are separate from code
2. Deployment script (deploy.sh) automates the deployment process
3. Configuration is preserved during deployments

### 10.2 Security Considerations

1. Password and sensitive data are stored in configuration files excluded from version control
2. TLS support for secure SMTP communication
3. No hardcoded credentials in code
