#!/bin/bash

# Script para executar testes com ambiente configurado
# Autor: Igor Medeiros

# Definir variáveis de ambiente
export PYTHONPATH=.:src

# Cores para saída
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir mensagens coloridas
print_colored() {
    echo -e "${2}${1}${NC}"
}

# Header
print_colored "===== EXECUTANDO TESTES DO EMAIL-SENDER =====" "${BLUE}"
print_colored "Ambiente de execução:" "${BLUE}"
print_colored "  PYTHONPATH=$PYTHONPATH" "${YELLOW}"

# Verificar se pytest está instalado
if ! command -v pytest &> /dev/null; then
    print_colored "❌ Pytest não está instalado. Instale-o com:" "${RED}"
    print_colored "   pip install -r requirements.txt" "${YELLOW}"
    exit 1
fi

# Executar testes com cobertura
print_colored "\n📊 Executando testes com cobertura..." "${BLUE}"

if [[ "$1" == "-m" && "$2" == "backup" ]]; then
    # Executar apenas testes de backup
    print_colored "Executando apenas testes de backup..." "${YELLOW}"
    python3 -m pytest -m backup -v --cov=. --cov-report=term --cov-report=html:reports/coverage_html
elif [[ -n "$1" ]]; then
    # Executar teste específico
    print_colored "Executando teste específico: $1" "${YELLOW}"
    python3 -m pytest "$1" -v --cov=. --cov-report=term --cov-report=html:reports/coverage_html
else
    # Executar todos os testes
    python3 -m pytest -v --cov=. --cov-report=term --cov-report=html:reports/coverage_html
fi

# Verificar resultado
if [ $? -eq 0 ]; then
    print_colored "\n✅ Testes concluídos com sucesso!" "${GREEN}"
    print_colored "📊 Relatório de cobertura HTML disponível em: reports/coverage_html/index.html" "${GREEN}"
    exit 0
else
    print_colored "\n❌ Testes falharam!" "${RED}"
    exit 1
fi 