#!/bin/bash

set -e
set -u
set -o pipefail

# --- Variáveis de Configuração ---
PYTHON_EXECUTABLE="uv run python"
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CLI_MODULE="email_sender.cli" # Ajustado para usar o módulo via Python -m

# Verifica se o arquivo de configuração existe
CONFIG_DIR="${SCRIPT_DIR}/config"
if [ ! -f "${CONFIG_DIR}/config.yaml" ]; then
    echo "❌ Error: Arquivo de configuração não encontrado em ${CONFIG_DIR}/config.yaml"
    exit 1
fi

echo "#######################################################################"
echo "### ATENÇÃO: CONTINUANDO WORKFLOW DE ENVIO DE E-MAILS DE PRODUÇÃO ###"
echo "#######################################################################"
echo ""
echo "Este script irá operar nos arquivos de dados de PRODUÇÃO definidos"
echo "na configuração (config/config.yaml e config/email.yaml)."
echo "Ele NÃO LIMPARÁ as flags de 'enviado' ou 'falhou' existentes,"
echo "permitindo continuar um envio interrompido."
echo "As listas de descadastro e bounce SERÃO sincronizadas."
echo ""
read -p "Você tem certeza que deseja continuar este workflow? (s/N): " confirmation
if [[ "$confirmation" != [sS] ]]; then
    echo "Operação cancelada pelo usuário."
    exit 0
fi
echo ""

# Passo 1: Sincronizar emails descadastrados com o CSV de produção
# Assume que os arquivos de descadastro e CSV de produção estão configurados em config.yaml
echo "[PASSO 1/3] Sincronizando e-mails descadastrados com o arquivo CSV de PRODUÇÃO..."
env PYTHONPATH="${SCRIPT_DIR}/src" $PYTHON_EXECUTABLE -m $CLI_MODULE sync-unsubscribed-command --config "${SCRIPT_DIR}/config/config.yaml"
# Se precisar especificar os arquivos explicitamente, descomente e ajuste as linhas abaixo:
# env PYTHONPATH="${SCRIPT_DIR}/src" $PYTHON_EXECUTABLE -m $CLI_MODULE sync-unsubscribed-command \
#    --csv-file "${SCRIPT_DIR}/data/emails_geral.csv" \
#    --unsubscribe-file "${SCRIPT_DIR}/data/descadastros.csv" \
#    --config "${SCRIPT_DIR}/config/config.yaml"
echo "Sincronização de descadastrados concluída."
echo "----------------------------------------"
echo ""

# Passo 2: Sincronizar emails de bounce com o CSV de produção
# Assume que os arquivos de bounces e CSV de produção estão configurados em config.yaml
echo "[PASSO 2/3] Sincronizando e-mails de bounce com o arquivo CSV de PRODUÇÃO..."
env PYTHONPATH="${SCRIPT_DIR}/src" $PYTHON_EXECUTABLE -m $CLI_MODULE sync-bounces-command --config "${SCRIPT_DIR}/config/config.yaml"
# Se precisar especificar os arquivos explicitamente, descomente e ajuste as linhas abaixo:
# env PYTHONPATH="${SCRIPT_DIR}/src" $PYTHON_EXECUTABLE -m $CLI_MODULE sync-bounces-command \
#    --csv-file "${SCRIPT_DIR}/data/emails_geral.csv" \
#    --bounces-file "${SCRIPT_DIR}/data/bounces.csv" \
#    --config "${SCRIPT_DIR}/config/config.yaml"
echo "Sincronização de bounces concluída."
echo "----------------------------------------"
echo ""

# Passo 3: Continuar enviando emails de produção
echo "[PASSO 3/3] Continuando o envio de e-mails de PRODUÇÃO..."
env PYTHONPATH="${SCRIPT_DIR}/src" $PYTHON_EXECUTABLE -m $CLI_MODULE send-emails --mode production --config "${SCRIPT_DIR}/config/config.yaml" --content "${SCRIPT_DIR}/config/email.yaml"
# O comando send-emails em modo production usará os arquivos CSV e bounces
# configurados em config.yaml se não especificados aqui.
# Ele respeitará as flags 'enviado', 'falhou' e 'bounce' existentes.
# Exemplo para especificar explicitamente (se necessário):
# env PYTHONPATH="${SCRIPT_DIR}/src" $PYTHON_EXECUTABLE -m $CLI_MODULE send-emails --mode production \
#    --csv-file "${SCRIPT_DIR}/data/emails_geral.csv" \
#    --bounces-file "${SCRIPT_DIR}/data/bounces.csv" \
#    --config "${SCRIPT_DIR}/config/config.yaml" \
#    --content "${SCRIPT_DIR}/config/email.yaml"
echo "Envio de e-mails de PRODUÇÃO (continuação) concluído."
echo "----------------------------------------"
echo ""

echo "✅ Workflow de continuação de envio de PRODUÇÃO finalizado!"
