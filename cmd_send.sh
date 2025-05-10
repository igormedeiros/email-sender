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

echo "####################################################################"
echo "### ATENÇÃO: INICIANDO WORKFLOW DE ENVIO DE E-MAILS DE PRODUÇÃO ###"
echo "####################################################################"
echo ""
echo "Este script irá operar nos arquivos de dados de PRODUÇÃO definidos"
echo "na configuração (config/config.yaml e config/email.yaml)."
echo "Verifique se as configurações estão corretas ANTES de prosseguir."
echo ""
read -p "Você tem certeza que deseja continuar? (s/N): " confirmation
if [[ "$confirmation" != [sS] ]]; then
    echo "Operação cancelada pelo usuário."
    exit 0
fi
echo ""

# Passo 1: Limpar flags de 'enviado' e 'falhou' do CSV de produção
# Assume que o CSV de produção está configurado em config.yaml
echo "[PASSO 1/4] Limpando flags de status dos e-mails no arquivo CSV de PRODUÇÃO..."
env PYTHONPATH="${SCRIPT_DIR}/src" $PYTHON_EXECUTABLE -m $CLI_MODULE clear-sent-flags --config "${SCRIPT_DIR}/config/config.yaml" --csv-file "${SCRIPT_DIR}/data/emails_geral.csv"
echo "Flags de status limpas com sucesso (se o arquivo CSV de produção foi encontrado e processado)."
echo "----------------------------------------"
echo ""

# Passo 2: Sincronizar emails descadastrados com o CSV de produção
# Assume que os arquivos de descadastro e CSV de produção estão configurados em config.yaml
echo "[PASSO 2/4] Sincronizando e-mails descadastrados com o arquivo CSV de PRODUÇÃO..."
env PYTHONPATH="${SCRIPT_DIR}/src" $PYTHON_EXECUTABLE -m $CLI_MODULE sync-unsubscribed-command --config "${SCRIPT_DIR}/config/config.yaml" \
   --csv-file "${SCRIPT_DIR}/data/emails_geral.csv" \
   --unsubscribe-file "${SCRIPT_DIR}/data/descadastros.csv"
echo "Sincronização de descadastrados concluída."
echo "----------------------------------------"
echo ""

# Passo 3: Sincronizar emails de bounce com o CSV de produção
# Assume que os arquivos de bounces e CSV de produção estão configurados em config.yaml
echo "[PASSO 3/4] Sincronizando e-mails de bounce com o arquivo CSV de PRODUÇÃO..."
env PYTHONPATH="${SCRIPT_DIR}/src" $PYTHON_EXECUTABLE -m $CLI_MODULE sync-bounces-command --config "${SCRIPT_DIR}/config/config.yaml" \
   --csv-file "${SCRIPT_DIR}/data/emails_geral.csv" \
   --bounces-file "${SCRIPT_DIR}/data/bounces.csv"
echo "Sincronização de bounces concluída."
echo "----------------------------------------"
echo ""

# Passo 4: Enviar emails de produção
echo "[PASSO 4/4] Enviando e-mails de PRODUÇÃO..."
env PYTHONPATH="${SCRIPT_DIR}/src" $PYTHON_EXECUTABLE -m $CLI_MODULE send-emails --mode production --config "${SCRIPT_DIR}/config/config.yaml" --content "${SCRIPT_DIR}/config/email.yaml"

echo "Envio de e-mails de PRODUÇÃO concluído."
echo "----------------------------------------"
echo ""

echo "✅ Workflow de envio de PRODUÇÃO finalizado com sucesso!"
