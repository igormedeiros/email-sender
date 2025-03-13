import pytest
import os
import logging
import tempfile
import shutil
from unittest.mock import patch, MagicMock, call
from logging.handlers import RotatingFileHandler

from src.logs import (
    setup_logging, 
    get_logger, 
    log_exception, 
    configure_file_handler, 
    LogFilter
)

@pytest.fixture
def temp_log_dir():
    """Fixture que cria um diretório temporário para logs"""
    log_dir = tempfile.mkdtemp()
    yield log_dir
    shutil.rmtree(log_dir)

def test_setup_logging_basic():
    """Testa a configuração básica de logging"""
    # Mock para logging.getLogger
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Chamar setup_logging
        logger = setup_logging('test_module')
        
        # Verificar que o logger foi configurado corretamente
        assert logger == mock_logger
        mock_get_logger.assert_called_once_with('test_module')
        assert mock_logger.setLevel.called

def test_setup_logging_with_log_level():
    """Testa a configuração de logging com nível específico"""
    # Mock para logging.getLogger
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Chamar setup_logging com nível específico
        logger = setup_logging('test_module', log_level=logging.DEBUG)
        
        # Verificar que o logger foi configurado com o nível correto
        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)

def test_setup_logging_with_file_handler(temp_log_dir):
    """Testa a configuração de logging com handler de arquivo"""
    log_file = os.path.join(temp_log_dir, 'test.log')
    
    # Mock para logging.getLogger
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Mock para configure_file_handler
        with patch('src.logs.configure_file_handler') as mock_configure_handler:
            mock_handler = MagicMock()
            mock_configure_handler.return_value = mock_handler
            
            # Chamar setup_logging com arquivo de log
            logger = setup_logging('test_module', log_file=log_file)
            
            # Verificar que o file handler foi configurado e adicionado
            mock_configure_handler.assert_called_once_with(log_file)
            mock_logger.addHandler.assert_called_with(mock_handler)

def test_get_logger():
    """Testa a função get_logger"""
    # Mock para setup_logging
    with patch('src.logs.setup_logging') as mock_setup:
        mock_logger = MagicMock()
        mock_setup.return_value = mock_logger
        
        # Chamar get_logger
        logger = get_logger('test_module')
        
        # Verificar resultado
        assert logger == mock_logger
        mock_setup.assert_called_once_with('test_module', log_level=None, log_file=None)

def test_log_exception():
    """Testa a função log_exception"""
    # Criar logger mock
    mock_logger = MagicMock()
    
    # Criar exceção de teste
    test_exception = ValueError("Test error")
    
    # Chamar log_exception
    log_exception(mock_logger, "Test operation failed", test_exception)
    
    # Verificar que a exceção foi logada corretamente
    mock_logger.error.assert_called()
    error_args = mock_logger.error.call_args[0][0]
    assert "Test operation failed" in error_args
    assert "ValueError" in error_args
    assert "Test error" in error_args

def test_configure_file_handler(temp_log_dir):
    """Testa a configuração do file handler"""
    log_file = os.path.join(temp_log_dir, 'test.log')
    
    # Mock para RotatingFileHandler
    with patch('src.logs.RotatingFileHandler') as mock_handler_class:
        mock_handler = MagicMock()
        mock_handler_class.return_value = mock_handler
        
        # Mock para formatter
        with patch('src.logs.Formatter') as mock_formatter_class:
            mock_formatter = MagicMock()
            mock_formatter_class.return_value = mock_formatter
            
            # Chamar configure_file_handler
            handler = configure_file_handler(log_file)
            
            # Verificar que o handler foi configurado corretamente
            assert handler == mock_handler
            mock_handler_class.assert_called_once_with(
                log_file, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            mock_formatter_class.assert_called_once()
            mock_handler.setFormatter.assert_called_once_with(mock_formatter)

def test_log_filter():
    """Testa a classe LogFilter"""
    # Criar instância do filtro
    filter_instance = LogFilter(['password', 'token', 'secret'])
    
    # Criar record mock com mensagem contendo palavras sensíveis
    mock_record = MagicMock()
    mock_record.getMessage.return_value = "Password: 12345, token=abcde, secret='xyz'"
    
    # Aplicar filtro
    result = filter_instance.filter(mock_record)
    
    # Verificar que o filtro foi aplicado
    assert result is True
    assert mock_record.getMessage.called
    # Verificar que as palavras sensíveis foram redactadas (mantendo a caixa original)
    assert "[REDACTED]" in mock_record.msg
    assert "Password: [REDACTED]" in mock_record.msg.replace("Password", "Password")
    assert "token=[REDACTED]" in mock_record.msg.replace("token", "token")
    assert "secret=[REDACTED]" in mock_record.msg.replace("secret", "secret")

def test_log_filter_case_insensitive():
    """Testa que o filtro de log é case insensitive"""
    # Criar instância do filtro
    filter_instance = LogFilter(['password'])
    
    # Criar record mock com diferentes casos
    mock_record = MagicMock()
    mock_record.getMessage.return_value = "PASSWORD=12345, Password: 67890"
    
    # Aplicar filtro
    result = filter_instance.filter(mock_record)
    
    # Verificar que o filtro foi aplicado a todas as variações
    assert result is True
    assert "PASSWORD=[REDACTED]" in mock_record.msg.replace("PASSWORD", "PASSWORD")
    assert "Password: [REDACTED]" in mock_record.msg.replace("Password", "Password")

def test_log_filter_with_custom_placeholder():
    """Testa o filtro de log com placeholder customizado"""
    # Criar instância do filtro com placeholder customizado
    filter_instance = LogFilter(['password'], placeholder='***HIDDEN***')
    
    # Criar record mock
    mock_record = MagicMock()
    mock_record.getMessage.return_value = "Password: 12345"
    
    # Verificar que o placeholder customizado foi usado
    result = filter_instance.filter(mock_record)
    assert result is True
    assert "***HIDDEN***" in mock_record.msg
    assert "Password: ***HIDDEN***" in mock_record.msg.replace("Password", "Password")

def test_setup_logging_with_filter():
    """Testa a configuração de logging com filtro de dados sensíveis"""
    # Mock para logging.getLogger
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Mock para LogFilter
        with patch('src.logs.LogFilter') as mock_filter_class:
            mock_filter = MagicMock()
            mock_filter_class.return_value = mock_filter
            
            # Chamar setup_logging com sensitive_fields
            logger = setup_logging('test_module', sensitive_fields=['password', 'token'])
            
            # Verificar que o filtro foi criado e adicionado
            mock_filter_class.assert_called_once_with(['password', 'token'])
            mock_logger.addFilter.assert_called_once_with(mock_filter) 