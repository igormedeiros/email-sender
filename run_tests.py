#!/usr/bin/env python3
"""
Script para executar testes e verificar cobertura de código.
"""
import os
import subprocess
import sys

def run_tests():
    """Executa os testes com pytest e gera relatório de cobertura."""
    # Criar diretório para relatórios se não existir
    if not os.path.exists('reports'):
        os.makedirs('reports')
    
    print("=== Executando testes com cobertura ===")
    
    # Comando para executar pytest com cobertura
    cmd = [
        'python3', '-m', 'pytest', 
        'tests/unit/', 
        '-v',
        '--cov=src',
        '--cov-report=term',
        '--cov-report=html:reports/coverage_html',
        '--cov-report=xml:reports/coverage.xml'
    ]
    
    # Executar comando
    result = subprocess.run(cmd)
    
    # Verificar se os testes passaram
    if result.returncode != 0:
        print("❌ Testes falharam!")
        return False
    
    print("✅ Testes concluídos com sucesso!")
    print(f"📊 Relatório de cobertura HTML disponível em: reports/coverage_html/index.html")
    
    return True

if __name__ == '__main__':
    # Executar testes
    success = run_tests()
    
    # Sair com código de erro apropriado
    sys.exit(0 if success else 1) 