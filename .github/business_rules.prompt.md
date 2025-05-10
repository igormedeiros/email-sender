# Email Sender - Documentação de Regras de Negócio

_Gerado em: 10 de maio de 2025_

Este documento descreve as regras de negócio fundamentais, comportamentos e funcionalidades da aplicação Email Sender. Serve como referência para compreender como o sistema opera e quais regras governam seu comportamento.

## 1. Conceitos Fundamentais

### 1.1 Visão Geral do Sistema

O Email Sender é uma aplicação robusta projetada para processamento de emails em lote com recursos avançados para gerenciamento de listas de emails, acompanhamento de status de entrega e garantia de comunicação confiável. O sistema foi projetado para:

- Enviar emails em lotes a partir de fontes de dados CSV
- Rastrear o status de entrega de emails
- Gerenciar descadastros e bounces
- Fornecer relatórios detalhados
- Implementar tratamento de erros e recuperação resiliente
- Suportar modos de teste e produção

### 1.2 Componentes Principais

1. **Email Service**: Serviço principal que gerencia o processo de envio de emails
2. **CSV Reader**: Manipula entrada/saída de dados com recursos de segurança
3. **Template Processor**: Gerencia a personalização do conteúdo dos emails
4. **SMTP Manager**: Gerencia a comunicação com o servidor de email
5. **Report Generator**: Cria relatórios detalhados das campanhas de email
6. **Configuration Management**: Configuração externa via arquivos YAML

## 2. Regras de Gerenciamento de Dados

### 2.1 Estrutura de Arquivos CSV

O sistema processa arquivos CSV com a seguinte estrutura:

#### 2.1.1 Colunas Obrigatórias

| Coluna      | Descrição                       | Valores                                      |
| ----------- | ------------------------------- | -------------------------------------------- |
| email       | Endereço de email (obrigatório) | Endereço de email válido                     |
| enviado     | Status de envio                 | "" (não enviado), "ok" (enviado com sucesso) |
| falhou      | Status de falha                 | "" (sem falha), "ok" (falha no envio)        |
| descadastro | Flag de descadastramento        | "" (enviar), "S" (não enviar)                |

#### 2.1.2 Colunas Opcionais

Colunas adicionais podem ser incluídas para personalização:

- nome: Nome do destinatário
- empresa: Nome da empresa
- cargo: Cargo/função
- Quaisquer outras colunas necessárias para personalização do template

### 2.2 Arquivos de Dados

O sistema utiliza os seguintes arquivos de dados:

1. **emails_geral.csv**: Lista principal de emails para produção
2. **test_emails.csv**: Lista de emails de teste para validação
3. **descadastros.csv**: Lista de emails descadastrados
4. **bounces.csv**: Lista de emails com problemas de entrega

### 2.3 Regras de Segurança de Dados

1. **Backups Automáticos**: O sistema cria cópias de backup dos arquivos CSV antes de fazer modificações
2. **Salvamentos Atômicos**: Os arquivos são salvos usando operações atômicas para prevenir corrupção de dados
3. **Restauração em Caso de Falha**: Se uma operação falhar, o sistema restaura automaticamente os dados do backup
4. **Tratamento de Sinais**: Captura sinais SIGINT e outros sinais de interrupção para salvar dados com segurança

### 2.4 Regras de Processamento de Dados

1. **Processamento em Lotes**: Os emails são processados em tamanhos de lote configuráveis
2. **Detecção de CSV**: O sistema detecta automaticamente separadores CSV (vírgula ou ponto e vírgula)
3. **Normalização de Email**: Todos os endereços de email são convertidos para minúsculas para consistência
4. **Tratamento de Duplicatas**: O sistema pode identificar e gerenciar endereços de email duplicados

## 3. Regras de Envio de Email

### 3.1 Fluxo de Envio

1. **Inicialização**:

   - Carregar configuração
   - Criar backup do arquivo CSV
   - Validar existência do template
   - Carregar listas de descadastros e bounces

2. **Filtragem**:

   - Pular emails já marcados como enviados
   - Pular emails marcados como falha
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
   - Emails que falham após todas as tentativas são marcados como falha no CSV
   - O sistema preserva a mensagem de erro específica para solução de problemas

### 3.3 Modo de Teste

1. O sistema suporta modos de teste e produção
2. O modo de teste usa um arquivo CSV separado (test_emails.csv) para evitar comunicação com clientes reais durante testes
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
   - {nome}, {empresa}, {cargo}: Substituídos pelos dados do destinatário do CSV
   - Qualquer coluna no CSV pode ser usada como placeholder com a sintaxe {nome_da_coluna}

3. **Placeholders Especiais**:

   - {desconto_paragrafo}: Conteúdo condicional que aparece apenas se o desconto estiver configurado
   - {link_evento}, {data_evento}, {cidade}, {local}: Informações específicas do evento

4. **Processamento CSS**:
   - Se a biblioteca premailer estiver disponível, o CSS externo é automaticamente incorporado
   - O caminho do arquivo CSS pode ser especificado na configuração

## 5. Gerenciamento de Descadastros e Bounces

### 5.1 Tratamento de Descadastros

1. Antes do envio, o sistema carrega emails descadastrados do arquivo descadastros.csv
2. Emails marcados com "S" na coluna descadastro nunca são enviados
3. Emails descadastrados são pulados e reportados nas estatísticas

### 5.2 Tratamento de Bounces

1. Emails com bounce são rastreados no arquivo bounces.csv
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
- Gerenciar dados CSV
- Verificar status
- Gerar relatórios

### 9.2 API REST

Uma API REST expõe a funcionalidade do sistema para integração com outras aplicações.

## 10. Implantação e Gerenciamento

### 10.1 Processo de Implantação

1. Configuration files are separate from code
2. Deployment script (deploy.sh) automates the deployment process
3. Configuration is preserved during deployments

### 10.2 Security Considerations

1. Password and sensitive data are stored in configuration files excluded from version control
2. TLS support for secure SMTP communication
3. No hardcoded credentials in code
