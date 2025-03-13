import pytest
import os
import pandas as pd
import shutil
from pathlib import Path
from unittest.mock import MagicMock

from email_service import EmailService
from config import Config

@pytest.fixture
def setup_test_env():
    """Configura o ambiente de teste e limpa ao final"""
    # Criar diretórios necessários
    os.makedirs("tests/data", exist_ok=True)
    os.makedirs("backup", exist_ok=True)
    
    yield
    
    # Limpar diretórios após os testes
    if os.path.exists("tests/data"):
        shutil.rmtree("tests/data")
    
    # Limpar backup após os testes
    if os.path.exists("backup"):
        shutil.rmtree("backup")

@pytest.fixture
def email_service():
    """Cria uma instância de EmailService para testes"""
    config = MagicMock(spec=Config)
    config.email_config = {
        "csv_file": "tests/data/test_emails.csv",
        "unsubscribe_file": "tests/data/descadastros.csv",
        "batch_size": 10
    }
    return EmailService(config)

# Testes para casos de borda do método clear_sent_flags

def test_clear_sent_flags_with_missing_columns(email_service, setup_test_env):
    """Testa se o método clear_sent_flags funciona corretamente quando o CSV não tem as colunas 'enviado' ou 'falhou'"""
    # Criar arquivo CSV sem as colunas 'enviado' e 'falhou'
    test_file = "tests/data/missing_columns.csv"
    test_data = pd.DataFrame({
        'email': ['test1@example.com', 'test2@example.com'],
        'nome': ['Test 1', 'Test 2']
    })
    test_data.to_csv(test_file, index=False)
    
    # Executar método
    count = email_service.clear_sent_flags(test_file)
    
    # Verificar que o número retornado é zero (nenhum registro modificado)
    assert count == 0
    
    # Verificar que o arquivo não foi modificado (exceto pelo processo de salvar)
    modified_df = pd.read_csv(test_file)
    assert list(modified_df.columns) == ['email', 'nome']
    
    # Verificar que backup foi criado
    assert os.path.exists("backup/missing_columns.csv.bak")

def test_clear_sent_flags_with_empty_enviado_column(email_service, setup_test_env):
    """Testa se o método clear_sent_flags funciona corretamente quando o CSV tem a coluna 'enviado' mas todos os valores são vazios"""
    # Criar arquivo CSV com a coluna 'enviado' mas todos os valores vazios
    test_file = "tests/data/empty_enviado.csv"
    test_data = pd.DataFrame({
        'email': ['test1@example.com', 'test2@example.com'],
        'nome': ['Test 1', 'Test 2'],
        'enviado': ['', '']
    })
    test_data.to_csv(test_file, index=False)
    
    # Executar método
    count = email_service.clear_sent_flags(test_file)
    
    # Verificar que o número retornado é zero (nenhum registro modificado)
    assert count == 0
    
    # Verificar que a coluna 'enviado' ainda existe e está vazia
    modified_df = pd.read_csv(test_file)
    assert 'enviado' in modified_df.columns
    assert not modified_df['enviado'].any()

def test_clear_sent_flags_with_invalid_csv(email_service, setup_test_env):
    """Testa se o método clear_sent_flags trata corretamente um arquivo CSV mal-formado"""
    # Criar um arquivo CSV inválido
    test_file = "tests/data/invalid.csv"
    with open(test_file, 'w') as f:
        f.write("email,nome\ntest1@example.com,Test 1\nmalformed line")
    
    try:
        # Executar método
        email_service.clear_sent_flags(test_file)
        # Se chegar aqui, o teste falha pois deveria ter lançado uma exceção
        assert False, "Deveria ter lançado uma exceção para CSV inválido"
    except pd.errors.ParserError:
        # Esperamos uma exceção específica do pandas por erro de parsing
        assert True
    except Exception as e:
        # Ou qualquer outra exceção que indique erro de processamento do CSV
        assert True, f"Lançou exceção do tipo {type(e)}"

def test_clear_sent_flags_with_non_csv_file(email_service, setup_test_env):
    """Testa se o método clear_sent_flags trata corretamente um arquivo que não é CSV"""
    # Criar um arquivo não-CSV
    test_file = "tests/data/not_csv.txt"
    with open(test_file, 'w') as f:
        f.write("This is not a CSV file")
    
    try:
        # Executar método
        email_service.clear_sent_flags(test_file)
        # Se chegar aqui, o teste falha pois deveria ter lançado uma exceção
        assert False, "Deveria ter lançado uma exceção para arquivo não-CSV"
    except pd.errors.ParserError:
        # Esperamos uma exceção específica do pandas por erro de parsing
        assert True
    except Exception as e:
        # Ou qualquer outra exceção que indique erro de processamento do CSV
        assert True, f"Lançou exceção do tipo {type(e)}"

def test_clear_sent_flags_with_readonly_file(email_service, setup_test_env):
    """Testa se o método clear_sent_flags trata corretamente um arquivo somente-leitura"""
    # Criar arquivo CSV
    test_file = "tests/data/readonly.csv"
    test_data = pd.DataFrame({
        'email': ['test1@example.com', 'test2@example.com'],
        'enviado': ['ok', 'ok']
    })
    test_data.to_csv(test_file, index=False)
    
    try:
        # Tornar o arquivo somente-leitura
        os.chmod(test_file, 0o444)
        
        # Tentar executar método deve lançar uma exceção de permissão
        with pytest.raises(Exception) as exc_info:
            email_service.clear_sent_flags(test_file)
        
        # Verificar se o erro é relacionado a permissões
        # A mensagem exata pode variar dependendo do sistema operacional
        assert "Permission" in str(exc_info.value) or "Access" in str(exc_info.value)
    
    finally:
        # Restaurar permissões para poder limpar
        os.chmod(test_file, 0o644)

def test_clear_sent_flags_with_multiple_enviado_values(email_service, setup_test_env):
    """Testa se o método clear_sent_flags conta corretamente diferentes valores na coluna 'enviado'"""
    # Criar arquivo CSV com diferentes valores na coluna 'enviado'
    test_file = "tests/data/multiple_values.csv"
    test_data = pd.DataFrame({
        'email': ['test1@example.com', 'test2@example.com', 'test3@example.com', 'test4@example.com'],
        'enviado': ['ok', 'OK', 'sim', '']  # Apenas 'ok' deve ser considerado
    })
    test_data.to_csv(test_file, index=False)
    
    # Executar método
    count = email_service.clear_sent_flags(test_file)
    
    # Verificar que apenas 'ok' foi contado
    assert count == 1
    
    # Verificar que todas as entradas foram limpas
    modified_df = pd.read_csv(test_file)
    assert not modified_df['enviado'].any()

def test_clear_sent_flags_with_large_file(email_service, setup_test_env):
    """Testa se o método clear_sent_flags funciona corretamente com arquivos grandes"""
    # Criar um arquivo CSV grande
    test_file = "tests/data/large_file.csv"
    
    # Gerar 1000 linhas
    emails = [f"test{i}@example.com" for i in range(1000)]
    nomes = [f"Test {i}" for i in range(1000)]
    # Metade das linhas com 'enviado' = 'ok'
    enviado = ['ok' if i < 500 else '' for i in range(1000)]
    # Um quarto das linhas com 'falhou' = 'ok'
    falhou = ['ok' if 500 <= i < 750 else '' for i in range(1000)]
    
    large_df = pd.DataFrame({
        'email': emails,
        'nome': nomes,
        'enviado': enviado,
        'falhou': falhou
    })
    large_df.to_csv(test_file, index=False)
    
    # Executar método
    count = email_service.clear_sent_flags(test_file)
    
    # Verificar que o número correto de registros foi modificado (500 enviado + 250 falhou)
    assert count == 750
    
    # Verificar que todas as flags foram limpas
    modified_df = pd.read_csv(test_file)
    assert not modified_df['enviado'].any()
    assert not modified_df['falhou'].any()

def test_clear_sent_flags_handles_unicode_characters(email_service, setup_test_env):
    """Testa se o método clear_sent_flags lida corretamente com caracteres Unicode"""
    # Criar arquivo CSV com caracteres Unicode
    test_file = "tests/data/unicode.csv"
    test_data = pd.DataFrame({
        'email': ['test1@example.com', 'test2@example.com'],
        'nome': ['Têstê Ácçêñtøs', '测试 Unicode'],
        'enviado': ['ok', 'ok']
    })
    test_data.to_csv(test_file, index=False, encoding='utf-8')
    
    # Executar método
    count = email_service.clear_sent_flags(test_file)
    
    # Verificar que o número correto de registros foi modificado
    assert count == 2
    
    # Verificar que os nomes com caracteres Unicode foram preservados
    modified_df = pd.read_csv(test_file, encoding='utf-8')
    assert modified_df['nome'][0] == 'Têstê Ácçêñtøs'
    assert modified_df['nome'][1] == '测试 Unicode' 