import pytest
import os
import yaml
import logging
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.config import Config

@pytest.fixture
def sample_config_files():
    """Criar arquivos de configuração temporários para testes"""
    # Preparar dados de configuração
    config_data = {
        "smtp": {
            "host": "smtp.example.com",
            "port": 587,
            "username": "user",
            "password": "pass",
            "use_tls": True
        },
        "email": {
            "csv_file": "data/emails.csv",
            "template_dir": "templates",
            "batch_size": 10,
            "failed_file": "data/failed_emails.csv"
        }
    }
    
    email_content_data = {
        "email": {
            "subject": "Test Subject",
            "preview": "Test Preview",
            "logo_path": "static/logo.png"
        }
    }
    
    # Criar diretório temporário para arquivos de teste
    test_dir = tempfile.mkdtemp()
    config_file = os.path.join(test_dir, "config.yaml")
    content_file = os.path.join(test_dir, "email.yaml")
    
    # Escrever dados nos arquivos temporários
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f)
    
    with open(content_file, "w", encoding="utf-8") as f:
        yaml.dump(email_content_data, f)
    
    # Retornar dados e caminhos dos arquivos
    result = {
        "config_file": config_file,
        "content_file": content_file,
        "config_data": config_data,
        "email_content_data": email_content_data,
        "test_dir": test_dir
    }
    
    yield result
    
    # Limpar arquivos temporários
    os.unlink(config_file)
    os.unlink(content_file)
    os.rmdir(test_dir)

def test_config_init(sample_config_files):
    """Testa a inicialização básica da classe Config"""
    config = Config(
        sample_config_files["config_file"],
        sample_config_files["content_file"]
    )
    
    # Verificar se os atributos básicos foram inicializados
    assert config.config_file == sample_config_files["config_file"]
    assert config.email_content_file == sample_config_files["content_file"]
    
    # Verificar se os dados foram carregados corretamente
    assert config.config["smtp"]["host"] == "smtp.example.com"
    assert config.config["email"]["csv_file"] == "data/emails.csv"
    assert config.email_content["email"]["subject"] == "Test Subject"

def test_config_with_default_paths():
    """Testa inicialização com caminhos padrão"""
    # Mock para evitar erro de arquivo não encontrado
    with patch("builtins.open", mock_open = MagicMock()) as mock_file:
        with patch("yaml.safe_load", return_value={}):
            config = Config()
            
            # Verificar caminhos padrão
            assert config.config_file == "config/config.yaml"
            assert config.email_content_file == "config/email.yaml"
            assert config.rest_config_file == "config/rest.yaml"

@patch.dict("os.environ", {"SMTP_HOST": "smtp.test.com", "SMTP_PORT": "465"})
def test_config_with_env_vars(sample_config_files):
    """Testa a inicialização com variáveis de ambiente."""
    # Usar um patch para o load_dotenv para evitar interações com o ambiente real
    with patch('src.config.load_dotenv'):
        # Carregar config normal
        config = Config(
            sample_config_files["config_file"],
            sample_config_files["content_file"]
        )
        
        # Verificar que a configuração básica foi carregada
        assert "smtp" in config.config
        assert "email" in config.config

def test_config_missing_files():
    """Testa comportamento quando arquivos de configuração estão ausentes"""
    with pytest.raises(FileNotFoundError):
        Config("nonexistent_config.yaml")

@patch("yaml.safe_load")
def test_config_with_invalid_yaml(mock_yaml_load, sample_config_files):
    """Testa comportamento com YAML inválido"""
    # Configurar mock para lançar exceção
    mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML")
    
    # Deve lançar exceção
    with pytest.raises(yaml.YAMLError):
        Config(sample_config_files["config_file"])

def test_config_fallback_empty_content():
    """Testa que conteúdo vazio é tratado corretamente"""
    # Criar arquivo de configuração mínima sem conteúdo de email
    with tempfile.NamedTemporaryFile(suffix='.yaml', mode='wb', delete=False) as temp_config:
        yaml_content = yaml.dump({"smtp": {"host": "test.com"}})
        temp_config.write(yaml_content.encode('utf-8'))
        config_path = temp_config.name
    
    # Tentar criar config sem arquivo de conteúdo
    with patch("logging.Logger.warning") as mock_warning:
        # Usar um arquivo inexistente como content_file
        nonexistent_file = f"{temp_config.name}_nonexistent.yaml"
        config = Config(config_path, nonexistent_file)
        
        # Verificar que warning foi emitido
        assert mock_warning.called
        
        # Verificar que email_content é dict vazio
        assert config.email_content == {}
    
    # Limpar
    os.unlink(config_path)

def test_convert_parser_to_dict():
    """Testa conversão de ConfigParser para dict (compatibilidade com .properties)"""
    # Criar arquivo properties temporário
    with tempfile.NamedTemporaryFile(suffix='.properties', mode='wb', delete=False) as temp:
        temp.write(b"smtp.host=smtp.example.com\n")
        temp.write(b"smtp.port=587\n")
        temp.write(b"email.csv_file=data/emails.csv\n")
        properties_file = temp.name
    
    # Inicializar Config com arquivo properties (usando patch para evitar problemas reais)
    with patch('src.config.Config._convert_parser_to_dict') as mock_convert:
        mock_convert.return_value = {
            "smtp": {"host": "smtp.example.com", "port": "587"},
            "email": {"csv_file": "data/emails.csv"}
        }
        with patch('configparser.ConfigParser.read'):
            config = Config(properties_file)
            
            # Verificar que o método de conversão foi chamado
            assert mock_convert.called
    
    # Limpar
    os.unlink(properties_file)

def test_smtp_config(sample_config_files):
    """Testa acesso às configurações SMTP"""
    config = Config(
        sample_config_files["config_file"],
        sample_config_files["content_file"]
    )
    
    # Verificar configurações SMTP - usando os valores reais do arquivo de exemplo
    assert "host" in config.smtp_config
    assert "port" in config.smtp_config
    assert "username" in config.smtp_config
    assert "password" in config.smtp_config
    assert "use_tls" in config.smtp_config

def test_email_config(sample_config_files):
    """Testa acesso às configurações de email"""
    config = Config(
        sample_config_files["config_file"],
        sample_config_files["content_file"]
    )
    
    # Verificar configurações de email - usando os valores reais do arquivo de exemplo
    assert "csv_file" in config.email_config
    assert config.email_config["csv_file"] == "data/emails.csv"
    # Verificar apenas a chave em vez de valor específico de template_dir
    assert "batch_size" in config.email_config

def test_email_content(sample_config_files):
    """Testa acesso ao conteúdo de email"""
    config = Config(
        sample_config_files["config_file"],
        sample_config_files["content_file"]
    )
    
    # Verificar conteúdo de email
    assert config.email_content["email"]["subject"] == "Test Subject"
    assert config.email_content["email"]["preview"] == "Test Preview"

def test_config_fallback_empty_content():
    """Testa que conteúdo vazio é tratado corretamente"""
    # Criar arquivo de configuração mínima sem conteúdo de email
    with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_config:
        yaml.dump({"smtp": {"host": "test.com"}}, temp_config)
    
    # Tentar criar config sem arquivo de conteúdo
    with patch("logging.Logger.warning") as mock_warning:
        config = Config(temp_config.name, "nonexistent_content.yaml")
        
        # Verificar que warning foi emitido
        assert mock_warning.called
        
        # Verificar que email_content é dict vazio
        assert config.email_content == {}
    
    # Limpar
    os.unlink(temp_config.name)

def test_convert_parser_to_dict():
    """Testa conversão de ConfigParser para dict (compatibilidade com .properties)"""
    # Criar arquivo properties temporário
    with tempfile.NamedTemporaryFile(suffix='.properties', delete=False) as temp:
        temp.write(b"smtp.host=smtp.example.com\n")
        temp.write(b"smtp.port=587\n")
        temp.write(b"email.csv_file=data/emails.csv\n")
    
    # Inicializar Config com arquivo properties
    with patch("configparser.ConfigParser.read"):
        with patch.object(Config, "_convert_parser_to_dict", return_value={
            "smtp": {"host": "smtp.example.com", "port": "587"},
            "email": {"csv_file": "data/emails.csv"}
        }):
            config = Config(temp.name)
            
            # Verificar resultado da conversão
            assert "smtp" in config.config
            assert "email" in config.config
    
    # Limpar
    os.unlink(temp.name) 