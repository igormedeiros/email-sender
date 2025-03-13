#!/usr/bin/env python3
"""
Script para configurar o ambiente de desenvolvimento.

Este script:
1. Instala todas as dependências do requirements.txt
2. Instala o pacote em modo de desenvolvimento
3. Configura as ferramentas de desenvolvimento
4. Cria as pastas necessárias para o projeto
"""
import os
import subprocess
import sys
from pathlib import Path

def print_colored(message, color="green"):
    """Imprime mensagem colorida no terminal."""
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "blue": "\033[94m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, colors['reset'])}{message}{colors['reset']}")

def run_command(command, description=None, exit_on_error=True):
    """Executa um comando no shell e exibe a saída."""
    if description:
        print_colored(f"➡️ {description}...", "blue")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        if result.stdout:
            print(result.stdout)
        print_colored(f"✅ Comando executado com sucesso: {command}", "green")
        return True
    else:
        print_colored(f"❌ Erro ao executar comando: {command}", "red")
        print_colored(f"Saída de erro:", "red")
        print(result.stderr)
        
        if exit_on_error:
            sys.exit(1)
        return False

def create_directories():
    """Cria os diretórios necessários para o projeto."""
    directories = [
        "data",
        "backup",
        "logs",
        "reports",
        "tests/data",
        "tests/backup"
    ]
    
    print_colored("Criando diretórios do projeto...", "blue")
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print_colored(f"✅ Diretório criado: {directory}", "green")

def setup_dev_environment():
    """Configura o ambiente de desenvolvimento completo."""
    print_colored("🚀 Iniciando configuração do ambiente de desenvolvimento", "blue")
    
    # Instalar dependências
    run_command("pip3 install -r requirements.txt", "Instalando dependências")
    
    # Instalar pacote em modo de desenvolvimento
    run_command("pip3 install -e .", "Instalando pacote em modo de desenvolvimento")
    
    # Criar diretórios
    create_directories()
    
    # Verificar instalação do pytest
    run_command("python3 -m pytest --version", "Verificando instalação do pytest", exit_on_error=False)
    
    print_colored("\n✨ Ambiente de desenvolvimento configurado com sucesso! ✨", "green")
    print_colored("\nVocê pode executar os testes com os seguintes comandos:", "yellow")
    print_colored("  - python3 -m pytest              # Para executar todos os testes", "yellow")
    print_colored("  - python3 -m pytest -m backup    # Para executar apenas os testes de backup", "yellow")
    print_colored("  - python3 -m pytest tests/unit/test_controller_cli_backup.py  # Para testes específicos", "yellow")
    print_colored("  - python3 run_tests.py           # Para executar testes com relatório de cobertura", "yellow")

if __name__ == "__main__":
    setup_dev_environment() 