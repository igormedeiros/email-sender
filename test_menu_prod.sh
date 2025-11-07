#!/bin/bash

# Script para testar o novo menu de produção
# Simula a seleção: 2 (produção) -> 1 (enviar sem limpar) -> n (cancelar)

echo "=== Teste 1: Modo Produção - Cancelar ==="
printf "2\n1\nn\n" | timeout 15 uv run -m email_sender.cli 1

echo ""
echo "=== Teste 2: Modo Teste ==="
printf "1\nn\n" | timeout 15 uv run -m email_sender.cli 1
