#!/bin/bash

set -e
set -u
set -o pipefail

# --- Variáveis de Configuração ---
PYTHON_EXECUTABLE="uv run python"
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CLI_MODULE="email_sender.cli" # Adjusted for src layout
CONFIG_DIR="${SCRIPT_DIR}/config"

# Verifica se o arquivo de configuração existe
if [ ! -f "${CONFIG_DIR}/config.yaml" ]; then
    echo "❌ Error: Arquivo de configuração não encontrado em ${CONFIG_DIR}/config.yaml"
    exit 1
fi

echo "=== INICIANDO WORKFLOW DE ENVIO DE E-MAILS DE TESTE ==="
echo ""

# Passo 1: Limpar flags de 'enviado' e 'falhou'
echo "[PASSO 1/4] Limpando flags de status dos e-mails em ${SCRIPT_DIR}/data/test_emails.csv..."
env PYTHONPATH="${SCRIPT_DIR}/src" $PYTHON_EXECUTABLE -m $CLI_MODULE clear-sent-flags \
    --csv-file "${SCRIPT_DIR}/data/test_emails.csv" \
    --config "${SCRIPT_DIR}/config/config.yaml"
echo "Flags de status limpas com sucesso."
echo "----------------------------------------"
echo ""

# Passo 2: Sincronizar emails descadastrados
echo "[PASSO 2/4] Sincronizando e-mails descadastrados de ${SCRIPT_DIR}/data/descadastros.csv com ${SCRIPT_DIR}/data/test_emails.csv..."
env PYTHONPATH="${SCRIPT_DIR}/src" $PYTHON_EXECUTABLE -m $CLI_MODULE sync-unsubscribed-command \
    --csv-file "${SCRIPT_DIR}/data/test_emails.csv" \
    --unsubscribe-file "${SCRIPT_DIR}/data/descadastros.csv" \
    --config "${SCRIPT_DIR}/config/config.yaml"
echo "Sincronização de descadastrados concluída."
echo "----------------------------------------"
echo ""

# Passo 3: Sincronizar emails de bounce
echo "[PASSO 3/4] Sincronizando e-mails de bounce de ${SCRIPT_DIR}/data/bounces.csv com ${SCRIPT_DIR}/data/test_emails.csv..."
env PYTHONPATH="${SCRIPT_DIR}/src" $PYTHON_EXECUTABLE -m $CLI_MODULE sync-bounces-command \
    --csv-file "${SCRIPT_DIR}/data/test_emails.csv" \
    --bounces-file "${SCRIPT_DIR}/data/bounces.csv" \
    --config "${SCRIPT_DIR}/config/config.yaml"
echo "Sincronização de bounces concluída."
echo "----------------------------------------"
echo ""

# Passo 4: Enviar emails de teste
echo "[PASSO 4/4] Enviando e-mails de teste..." # Removida menção ao template específico
env PYTHONPATH="${SCRIPT_DIR}/src" $PYTHON_EXECUTABLE -m $CLI_MODULE send-emails \
    --mode test \
    --config "${SCRIPT_DIR}/config/config.yaml"
echo "Envio de e-mails de teste concluído."
echo "----------------------------------------"
echo ""

echo "✅ Workflow de envio de teste finalizado com sucesso!"