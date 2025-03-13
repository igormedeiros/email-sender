import pytest
import os
import pandas as pd
import shutil
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import datetime
from src.config import Config
from src.email_service import EmailService

# Importa a função para teste
from unsubscribe_app import add_to_unsubscribe_list, remove_from_unsubscribe_list, get_unsubscribe_file

# Mock para get_unsubscribe_file
@pytest.fixture
def mock_get_unsubscribe_file():
    """Mock para a função get_unsubscribe_file"""
    with patch('unsubscribe_app.get_unsubscribe_file') as mock:
        mock.return_value = "tests/data/descadastros.csv"
        yield mock

# Fixture para configurar ambiente de teste
@pytest.fixture
def setup_test_env():
    """Configura o ambiente de teste e limpa ao final"""
    # Criar diretório de teste
    os.makedirs("tests/data", exist_ok=True)
    
    yield
    
    # Limpar após os testes
    if os.path.exists("tests/data"):
        shutil.rmtree("tests/data")

# Fixture para EmailService
@pytest.fixture
def email_service(setup_test_env):
    """Fixture para criar uma instância do EmailService para testes"""
    # Configuração mock para testes
    config_mock = MagicMock(spec=Config)
    config_mock.email_config = {
        "unsubscribe_file": "tests/data/unsubscribe.csv",
        "csv_file": "tests/data/test_emails.csv",
        "failed_folder": "tests/data/failed",
        "failed_file": "tests/data/failed_emails.csv"
    }
    return EmailService(config_mock)

# Testes para add_to_unsubscribe_list

def test_add_to_unsubscribe_list_returns_false_when_email_is_empty(mock_get_unsubscribe_file):
    """Testa se a função retorna False quando o email é vazio"""
    # Executar função com email vazio
    result = add_to_unsubscribe_list("")
    
    # Verificar resultado
    assert result is False

def test_add_to_unsubscribe_list_converts_email_to_lowercase(mock_get_unsubscribe_file, setup_test_env):
    """Testa se a função converte o email para lowercase"""
    # Criar uma função mock que captura o email
    email_captured = None
    
    # Mock do open para capturar o email
    with patch('builtins.open', mock_open()) as mock_file:
        with patch('csv.writer') as mock_writer:
            instance = mock_writer.return_value
            
            # Mock para capturar o email
            def side_effect(*args, **kwargs):
                nonlocal email_captured
                if len(args) > 0 and isinstance(args[0], list) and len(args[0]) > 0:
                    email_captured = args[0][0]
            
            instance.writerow.side_effect = side_effect
            
            # Patch do os.path.exists e getsize para simular arquivo inexistente
            with patch('os.path.exists', return_value=False):
                # Executar função com email em maiúsculas
                add_to_unsubscribe_list("TEST@EXAMPLE.COM")
    
    # Verificar se o email foi convertido para lowercase
    assert email_captured == "test@example.com"

def test_add_to_unsubscribe_list_creates_file_when_not_exists(mock_get_unsubscribe_file, setup_test_env):
    """Testa se a função cria o arquivo quando ele não existe"""
    # Definir caminho para o arquivo
    file_path = "tests/data/descadastros.csv"
    mock_get_unsubscribe_file.return_value = file_path
    
    # Certificar-se de que o arquivo não existe
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Executar função
    add_to_unsubscribe_list("test@example.com")
    
    # Verificar se o arquivo foi criado
    assert os.path.exists(file_path)

def test_add_to_unsubscribe_list_writes_header_and_email(mock_get_unsubscribe_file, setup_test_env):
    """Testa se a função escreve o cabeçalho e o email quando cria o arquivo"""
    # Definir caminho para o arquivo
    file_path = "tests/data/descadastros.csv"
    mock_get_unsubscribe_file.return_value = file_path
    
    # Certificar-se de que o arquivo não existe
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Executar função
    add_to_unsubscribe_list("test@example.com")
    
    # Verificar conteúdo do arquivo
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        # Verificar se tem pelo menos 2 linhas (cabeçalho + email)
        assert len(lines) >= 2
        # Verificar cabeçalho
        assert "email,data_descadastro" in lines[0]
        # Verificar email
        assert "test@example.com" in lines[1]

def test_add_to_unsubscribe_list_adds_timestamp(mock_get_unsubscribe_file, setup_test_env):
    """Testa se o método add_to_unsubscribe_list adiciona um timestamp ao registrar o email"""
    # Definir caminho para o arquivo
    file_path = "tests/data/descadastros.csv"
    mock_get_unsubscribe_file.return_value = file_path
    
    # Certificar-se de que o arquivo não existe
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Definir um timestamp fixo para o teste
    fixed_time = datetime.datetime(2023, 1, 1, 10, 30, 0)
    expected_timestamp = "2023-01-01 10:30:00"
    
    # Usar patch para mockar o datetime.now()
    with patch('datetime.datetime') as mock_datetime:
        # Configurar o mock para retornar o timestamp fixo
        mock_datetime.now.return_value = fixed_time
        # Preservar o strftime real
        mock_datetime.strftime = datetime.datetime.strftime
        
        # Executar a função
        add_to_unsubscribe_list("timestamp_test@example.com")
    
    # Verificar se o email foi adicionado com o timestamp correto
    df = pd.read_csv(file_path)
    
    # Verificar se o email existe no dataframe
    filtered_df = df[df['email'] == "timestamp_test@example.com"]
    assert len(filtered_df) == 1, "O email deveria ter sido adicionado à lista"
    
    # Verificar se a coluna de timestamp existe
    assert 'data_descadastro' in filtered_df.columns, "A coluna data_descadastro deveria existir"
    assert not filtered_df['data_descadastro'].isna().any(), "O timestamp não deveria ser nulo"
    
    # Verificar se o valor do timestamp é o esperado
    timestamp_value = filtered_df['data_descadastro'].values[0]
    assert timestamp_value == expected_timestamp, f"O timestamp deveria ser {expected_timestamp}, mas foi {timestamp_value}"

def test_add_to_unsubscribe_list_skips_duplicated_email(mock_get_unsubscribe_file, setup_test_env):
    """Testa se a função ignora emails duplicados (case insensitive)"""
    # Definir caminho para o arquivo
    file_path = "tests/data/descadastros.csv"
    mock_get_unsubscribe_file.return_value = file_path
    
    # Criar arquivo com um email já registrado
    df = pd.DataFrame({
        'email': ['test@example.com'],
        'data_descadastro': ['2023-01-01 12:00:00']
    })
    df.to_csv(file_path, index=False)
    
    # Verificar o número de linhas antes
    linha_antes = len(pd.read_csv(file_path))
    
    # Executar função com mesmo email em caso diferente
    result = add_to_unsubscribe_list("TEST@example.com")
    
    # Verificar se a função retornou True (email já existe)
    assert result is True
    
    # Verificar se o número de linhas não mudou (não adicionou duplicado)
    linha_depois = len(pd.read_csv(file_path))
    assert linha_antes == linha_depois

def test_add_to_unsubscribe_list_handles_csv_error(mock_get_unsubscribe_file, setup_test_env):
    """Testa se a função lida corretamente com erros ao ler o CSV"""
    # Definir caminho para o arquivo
    file_path = "tests/data/descadastros.csv"
    mock_get_unsubscribe_file.return_value = file_path
    
    # Criar um arquivo CSV malformado
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("email,data_descadastro\n")
        f.write("malformed,line\n")
    
    # Mock do pandas.read_csv para lançar exceção
    with patch('pandas.read_csv') as mock_read_csv:
        mock_read_csv.side_effect = Exception("CSV error")
        
        # Executar função
        result = add_to_unsubscribe_list("new@example.com")
    
    # Verificar se a função lidou com o erro e retornou True
    assert result is True
    
    # Verificar se o arquivo foi recriado com o novo email
    df = pd.read_csv(file_path)
    assert 'new@example.com' in df['email'].values

# Testes para remove_from_unsubscribe_list

def test_remove_from_unsubscribe_list_returns_false_when_email_is_empty(mock_get_unsubscribe_file):
    """Testa se a função retorna False quando o email é vazio"""
    # Executar função com email vazio
    result = remove_from_unsubscribe_list("")
    
    # Verificar resultado
    assert result is False

def test_remove_from_unsubscribe_list_returns_true_when_file_not_exists(mock_get_unsubscribe_file, setup_test_env):
    """Testa se a função retorna True quando o arquivo não existe"""
    # Definir caminho para um arquivo inexistente
    file_path = "tests/data/nonexistent.csv"
    mock_get_unsubscribe_file.return_value = file_path
    
    # Certificar-se de que o arquivo não existe
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Executar função
    result = remove_from_unsubscribe_list("test@example.com")
    
    # Verificar resultado
    assert result is True

def test_remove_from_unsubscribe_list_removes_email(mock_get_unsubscribe_file, setup_test_env):
    """Testa se a função remove o email corretamente"""
    # Definir caminho para o arquivo
    file_path = "tests/data/descadastros.csv"
    mock_get_unsubscribe_file.return_value = file_path
    
    # Criar arquivo com emails
    df = pd.DataFrame({
        'email': ['test1@example.com', 'test2@example.com', 'test3@example.com'],
        'data_descadastro': ['2023-01-01', '2023-01-02', '2023-01-03']
    })
    df.to_csv(file_path, index=False)
    
    # Executar função
    result = remove_from_unsubscribe_list("test2@example.com")
    
    # Verificar resultado
    assert result is True
    
    # Verificar se o email foi removido
    df_updated = pd.read_csv(file_path)
    assert 'test1@example.com' in df_updated['email'].values
    assert 'test3@example.com' in df_updated['email'].values
    assert 'test2@example.com' not in df_updated['email'].values

def test_remove_from_unsubscribe_list_handles_case_insensitive(mock_get_unsubscribe_file, setup_test_env):
    """Testa se a função remove_from_unsubscribe_list trata diferenças de maiúsculas/minúsculas corretamente"""
    # Definir caminho para o arquivo
    file_path = "tests/data/descadastros.csv"
    mock_get_unsubscribe_file.return_value = file_path
    
    # Preparar arquivo de cancelamento com um e-mail
    df = pd.DataFrame({"email": ["test@example.com"], "data_descadastro": ["2023-01-01 12:00:00"]})
    df.to_csv(file_path, index=False)
    
    # Remover o email com uma capitalização diferente
    result = remove_from_unsubscribe_list("TEST@example.com")
    
    # Verificar se o email foi removido
    df = pd.read_csv(file_path)
    assert len(df) == 0, "O email deveria ter sido removido mesmo com capitalização diferente"
    assert result == True, "A função deveria retornar True ao remover um email existente"

def test_remove_from_unsubscribe_list_handles_csv_without_header(mock_get_unsubscribe_file, setup_test_env):
    """Testa se a função lida corretamente com CSV sem cabeçalho 'email'"""
    # Definir caminho para o arquivo
    file_path = "tests/data/descadastros.csv"
    mock_get_unsubscribe_file.return_value = file_path
    
    # Criar arquivo CSV sem cabeçalho 'email'
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("col1,col2\n")
        f.write("test1@example.com,data1\n")
        f.write("test2@example.com,data2\n")
    
    # Executar função
    result = remove_from_unsubscribe_list("test2@example.com")
    
    # Verificar resultado
    assert result is True
    
    # Verificar se o email foi removido
    df_updated = pd.read_csv(file_path)
    assert 'test2@example.com' not in df_updated.iloc[:, 0].values

# Teste para a função get_unsubscribe_file
def test_get_unsubscribe_file_returns_correct_path():
    """Testa se a função retorna o caminho correto"""
    # Configurar um caminho de arquivo
    with patch('os.path.join', return_value="data/descadastros.csv"):
        # Executar função
        path = get_unsubscribe_file()
        
        # Verificar se o caminho termina com "data/descadastros.csv"
        assert path.endswith("data/descadastros.csv") 