#!/bin/bash
# Script de deploy remoto com uv + execução de testes

set -e
set -u
set -o pipefail

# --- Configurações ---
VPS_HOST="191.252.205.241"
VPS_USER="root"
APP_NAME="email-sender"
VPS_PROJECT_PATH="/home/$VPS_USER/$APP_NAME"
BACKUP_BASE="/home/$VPS_USER/app/backups"
SSH_KEY="$HOME/.ssh/id_ed25519"
GIT_REPO="git@github.com:igormedeiros/email-sender.git"

# --- Cores ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   Deploy do Email-Sender para VPS   ${NC}"
echo -e "${BLUE}============================================${NC}"

# --- Comando SSH ---
SSH_CMD="ssh"
[[ -n "$SSH_KEY" ]] && SSH_CMD="$SSH_CMD -i $SSH_KEY"
SSH_CMD="$SSH_CMD $VPS_USER@$VPS_HOST"

# --- Execução remota ---
$SSH_CMD "
set -e

echo -e '${BLUE}🔄 Iniciando backup do projeto...${NC}'
mkdir -p $BACKUP_BASE
TIMESTAMP=\$(date +%d-%m-%Y-%H-%M-%S)
BACKUP_DIR=\"$BACKUP_BASE/${APP_NAME}-\$TIMESTAMP\"

# Criar backup dos arquivos importantes antes de atualizar
if [ -d \"$VPS_PROJECT_PATH\" ]; then
    # Criar diretório de backup
    mkdir -p \"\$BACKUP_DIR/config\" \"\$BACKUP_DIR/data\"
    
    # Fazer backup dos arquivos de configuração e dados
    if [ -d \"$VPS_PROJECT_PATH/config\" ]; then
        cp -r \"$VPS_PROJECT_PATH/config\" \"\$BACKUP_DIR/\"
    fi
    
    if [ -d \"$VPS_PROJECT_PATH/data\" ]; then
        cp -r \"$VPS_PROJECT_PATH/data\" \"\$BACKUP_DIR/\"
    fi
    
    echo -e '${GREEN}📁 Backup salvo em: \$BACKUP_DIR${NC}'
else
    echo -e '${YELLOW}⚠️ Diretório do projeto não encontrado. Criando novo...${NC}'
    mkdir -p \"$VPS_PROJECT_PATH\"
    echo -e '${BLUE}📥 Clonando o repositório...${NC}'
    git clone $GIT_REPO \"$VPS_PROJECT_PATH\"
    cd \"$VPS_PROJECT_PATH\"
fi

# Se o diretório do projeto já existe, apenas atualize via git pull
if [ -d \"$VPS_PROJECT_PATH/.git\" ]; then
    echo -e '${BLUE}📥 Atualizando o repositório com git pull...${NC}'
    cd \"$VPS_PROJECT_PATH\"
    git pull origin main
else
    echo -e '${YELLOW}⚠️ Repositório Git não encontrado. Fazendo clone completo...${NC}'
    rm -rf \"$VPS_PROJECT_PATH\"
    mkdir -p \"$VPS_PROJECT_PATH\"
    git clone $GIT_REPO \"$VPS_PROJECT_PATH\"
    cd \"$VPS_PROJECT_PATH\"
fi

cd \"$VPS_PROJECT_PATH\"

echo -e '${BLUE}🔍 Verificando pip/setuptools no Python 3.12...${NC}'
# Verificar se distutils está instalado (para evitar o ModuleNotFoundError: No module named 'distutils')
if ! dpkg -l | grep -q python3.12-distutils; then
    echo -e '${YELLOW}⚠️ python3.12-distutils não encontrado. Instalando...${NC}'
    apt-get update && apt-get install -y python3.12-distutils python3-dev
fi

if ! python3.12 -m pip --version >/dev/null 2>&1; then
    echo -e '${YELLOW}⚠️ pip não encontrado para Python 3.12. Instalando...${NC}'
    curl -sS https://bootstrap.pypa.io/pip/get-pip.py -o get-pip.py
    python3.12 get-pip.py
fi

echo -e '${BLUE}📦 Garantindo setuptools e wheel...${NC}'
python3.12 -m pip install --upgrade setuptools wheel

echo -e '${BLUE}📦 Instalando dependências com uv (pyproject.toml)...${NC}'
/root/.local/bin/uv venv && /root/.local/bin/uv pip install --editable .

echo -e '${BLUE}🚀 Preparando ambiente e configuração...${NC}'
chmod +x ./cmd_test.sh
chmod +x ./cmd_send.sh
chmod +x ./cmd_continue.sh
chmod +x ./cmd_schedule.sh

# Verificar se os diretórios importantes existem
mkdir -p data logs reports backup config/templates

# Verificar se o arquivo de configuração existe ou criar a partir do exemplo
if [ ! -f ./config/config.yaml ]; then
    echo -e '${YELLOW}⚠️ Arquivo config.yaml não encontrado. Copiando exemplo...${NC}'
    cp ./example_config.yaml ./config/config.yaml
fi

# Verificar se o arquivo de conteúdo de email existe ou criar a partir do exemplo
if [ ! -f ./config/email.yaml ]; then
    echo -e '${YELLOW}⚠️ Arquivo email.yaml não encontrado. Copiando exemplo...${NC}'
    cp ./example_email.yaml ./config/email.yaml
fi

# Verificar se o template de email existe ou criar pasta de templates
if [ ! -d ./config/templates ]; then
    echo -e '${YELLOW}⚠️ Diretório de templates não encontrado. Criando...${NC}'
    mkdir -p ./config/templates
fi

# Verificar se o template HTML existe ou criar a partir do exemplo
if [ ! -f ./config/templates/email.html ]; then
    echo -e '${YELLOW}⚠️ Template de email não encontrado. Copiando exemplo...${NC}'
    cp ./example_template.html ./config/templates/email.html
fi

# Verificar se há arquivos .csv em data
if [ ! -f ./data/test_emails.csv ]; then
    echo -e '${YELLOW}⚠️ Criando arquivo test_emails.csv vazio...${NC}'
    echo 'email,name,sent,failed,bounce,unsubscribed' > ./data/test_emails.csv
    echo 'test@example.com,Test User,false,false,false,false' >> ./data/test_emails.csv
fi

if [ ! -f ./data/bounces.csv ]; then
    echo -e '${YELLOW}⚠️ Criando arquivo bounces.csv vazio...${NC}'
    echo 'email,reason,date' > ./data/bounces.csv
fi

if [ ! -f ./data/descadastros.csv ]; then
    echo -e '${YELLOW}⚠️ Criando arquivo descadastros.csv vazio...${NC}'
    echo 'email,date' > ./data/descadastros.csv
fi

if [ ! -f ./data/emails_geral.csv ]; then
    echo -e '${YELLOW}⚠️ Criando arquivo emails_geral.csv vazio...${NC}'
    echo 'email,name,sent,failed,bounce,unsubscribed' > ./data/emails_geral.csv
fi

echo -e '${BLUE}🚀 Executando script de teste (cmd_test.sh)...${NC}'
export PATH=\$PATH:/root/.local/bin && ./cmd_test.sh

echo -e '${GREEN}✅ Deploy e testes finalizados com sucesso.${NC}'
" || {
    echo -e "${RED}❌ ERRO: Falha na execução do comando remoto.${NC}"
    exit 1
}

echo -e "${GREEN}✓ Deploy completo! Tudo certo na VPS.${NC}"
