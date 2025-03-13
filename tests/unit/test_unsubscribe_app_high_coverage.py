import pytest
import os
import pandas as pd
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import datetime
import tempfile
from flask import url_for

from unsubscribe_app import app, get_unsubscribe_file, add_to_unsubscribe_list, remove_from_unsubscribe_list
from unsubscribe_app import index, unsubscribe, resubscribe

# Fixtures para testes
@pytest.fixture
def setup_test_env():
    """Configura o ambiente de teste e limpa ao final"""
    # Criar diretório de teste
    os.makedirs("tests/data", exist_ok=True)
    
    yield
    
    # Limpar após os testes
    if os.path.exists("tests/data"):
        shutil.rmtree("tests/data")

@pytest.fixture
def client():
    """Cria um cliente Flask para testar as rotas"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# Testes para get_unsubscribe_file
def test_get_unsubscribe_file_returns_correct_path():
    """Testa se o método retorna o caminho correto"""
    with patch('pathlib.Path.parent') as mock_parent:
        # Configurar mock para retornar um path conhecido
        mock_parent.parent = Path("/home/test")
        
        # Executar método
        path = get_unsubscribe_file()
        
        # Verificar que o caminho termina com descadastros.csv
        assert path.endswith("data/descadastros.csv")

# Testes adicionais para add_to_unsubscribe_list
def test_add_to_unsubscribe_list_adds_entry_to_existing_file(setup_test_env):
    """Testa se o método adiciona uma entrada a um arquivo existente"""
    # Criar arquivo de descadastros com um email
    file_path = "tests/data/descadastros.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    df = pd.DataFrame({
        'email': ['existing@example.com'],
        'data_descadastro': ['2023-01-01 12:00:00']
    })
    df.to_csv(file_path, index=False)
    
    # Mockar o método get_unsubscribe_file para retornar o arquivo de teste
    with patch('unsubscribe_app.get_unsubscribe_file', return_value=file_path):
        # Adicionar novo email
        result = add_to_unsubscribe_list("new@example.com")
        
        # Verificar resultado
        assert result is True
        
        # Verificar que o email foi adicionado ao arquivo
        df = pd.read_csv(file_path)
        assert 'new@example.com' in df['email'].values
        assert 'existing@example.com' in df['email'].values

def test_add_to_unsubscribe_list_handles_malformed_file(setup_test_env):
    """Testa se o método lida corretamente com arquivos mal-formados"""
    # Criar um arquivo mal-formado
    file_path = "tests/data/descadastros.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w') as f:
        f.write("malformed content")
    
    # Mockar o método get_unsubscribe_file para retornar o arquivo de teste
    with patch('unsubscribe_app.get_unsubscribe_file', return_value=file_path):
        # Adicionar email
        result = add_to_unsubscribe_list("test@example.com")
        
        # Verificar resultado
        assert result is True
        
        # Verificar que o arquivo foi recriado corretamente
        df = pd.read_csv(file_path)
        assert 'email' in df.columns
        assert 'data_descadastro' in df.columns
        assert 'test@example.com' in df['email'].values

def test_add_to_unsubscribe_list_normalizes_email(setup_test_env):
    """Testa se o método normaliza o email (lowercase e trim)"""
    file_path = "tests/data/descadastros.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Mockar o método get_unsubscribe_file para retornar o arquivo de teste
    with patch('unsubscribe_app.get_unsubscribe_file', return_value=file_path):
        # Adicionar email com espaços e maiúsculas
        result = add_to_unsubscribe_list("  TEST@EXAMPLE.COM  ")
        
        # Verificar resultado
        assert result is True
        
        # Verificar que o email foi normalizado
        df = pd.read_csv(file_path)
        assert 'test@example.com' in df['email'].values

def test_add_to_unsubscribe_list_handles_file_without_header(setup_test_env):
    """Testa se o método lida corretamente com arquivos sem cabeçalho"""
    # Criar arquivo sem cabeçalho
    file_path = "tests/data/descadastros.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w') as f:
        f.write("old1@example.com\nold2@example.com\n")
    
    # Mockar o método get_unsubscribe_file para retornar o arquivo de teste
    with patch('unsubscribe_app.get_unsubscribe_file', return_value=file_path):
        # Configurar mock para simular erro no pandas
        with patch('pandas.read_csv') as mock_read_csv:
            mock_read_csv.side_effect = Exception("CSV without header")
            
            # Adicionar email
            result = add_to_unsubscribe_list("test@example.com")
            
            # Verificar resultado
            assert result is True
            
            # Verificar que o arquivo foi recriado com cabeçalho
            with open(file_path, 'r') as f:
                content = f.read()
                assert "email,data_descadastro" in content
                assert "test@example.com" in content

# Testes adicionais para remove_from_unsubscribe_list
def test_remove_from_unsubscribe_list_normalizes_email(setup_test_env):
    """Testa se o método normaliza o email ao remover (lowercase e trim)"""
    # Criar arquivo de descadastros com um email
    file_path = "tests/data/descadastros.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    df = pd.DataFrame({
        'email': ['test@example.com'],
        'data_descadastro': ['2023-01-01 12:00:00']
    })
    df.to_csv(file_path, index=False)
    
    # Mockar o método get_unsubscribe_file para retornar o arquivo de teste
    with patch('unsubscribe_app.get_unsubscribe_file', return_value=file_path):
        # Remover email com espaços e maiúsculas
        result = remove_from_unsubscribe_list("  TEST@EXAMPLE.COM  ")
        
        # Verificar resultado
        assert result is True
        
        # Verificar que o email foi removido
        df = pd.read_csv(file_path)
        assert len(df) == 0

def test_remove_from_unsubscribe_list_handles_csv_error(setup_test_env):
    """Testa se o método lida corretamente com erros ao ler o CSV"""
    # Criar arquivo de descadastros
    file_path = "tests/data/descadastros.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w') as f:
        f.write("email,data_descadastro\ntest@example.com,2023-01-01 12:00:00\n")
    
    # Mockar o método get_unsubscribe_file para retornar o arquivo de teste
    with patch('unsubscribe_app.get_unsubscribe_file', return_value=file_path):
        # Configurar mock para simular erro no pandas
        with patch('pandas.read_csv') as mock_read_csv:
            mock_read_csv.side_effect = Exception("CSV error")
            
            # Remover email
            result = remove_from_unsubscribe_list("test@example.com")
            
            # Verificar resultado
            assert result is True
            
            # Verificar que o arquivo foi recriado com cabeçalho
            with open(file_path, 'r') as f:
                content = f.read()
                assert "email,data_descadastro" in content
                # O email deve ter sido removido
                assert "test@example.com" not in content

# Testes para as rotas Flask
def test_index_route(client):
    """Testa a rota raiz"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'API de descadastro' in response.data

def test_unsubscribe_route_without_email(client):
    """Testa a rota de descadastro sem email"""
    response = client.get('/unsubscribe')
    assert response.status_code == 200
    assert b'Ocorreu um erro' in response.data
    assert b'Email n' in response.data  # "Email não fornecido"

def test_unsubscribe_route_with_email(client, setup_test_env):
    """Testa a rota de descadastro com email"""
    # Mockar a função add_to_unsubscribe_list para evitar efeitos colaterais
    with patch('unsubscribe_app.add_to_unsubscribe_list', return_value=True):
        # Mockar url_for para evitar erro de contexto de aplicativo
        with patch('flask.url_for') as mock_url_for:
            mock_url_for.return_value = "/resubscribe"
            
            response = client.get('/unsubscribe?email=test@example.com')
            
            assert response.status_code == 200
            assert b'Descadastro Confirmado' in response.data
            assert b'test@example.com' in response.data

def test_unsubscribe_route_with_error(client):
    """Testa a rota de descadastro com erro"""
    # Mockar a função add_to_unsubscribe_list para simular erro
    with patch('unsubscribe_app.add_to_unsubscribe_list', return_value=False):
        response = client.get('/unsubscribe?email=test@example.com')
        
        assert response.status_code == 200
        assert b'Ocorreu um erro' in response.data
        assert b'processsar seu descadastro' in response.data or b'processar seu descadastro' in response.data

def test_resubscribe_route(client):
    """Testa a rota de recadastro (desativada)"""
    response = client.get('/resubscribe')
    
    assert response.status_code == 200
    assert b'Funcionalidade indispon' in response.data  # "Funcionalidade indisponível" 