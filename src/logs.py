import logging
import os
import re
from logging import Logger, Formatter
from logging.handlers import RotatingFileHandler
from typing import List, Optional, Union

def setup_logging(
    name: str,
    log_level: Optional[int] = None,
    log_file: Optional[str] = None,
    sensitive_fields: Optional[List[str]] = None
) -> Logger:
    """
    Configura e retorna um logger configurado.
    
    Args:
        name: Nome do logger
        log_level: Nível de log (opcional)
        log_file: Caminho para o arquivo de log (opcional)
        sensitive_fields: Lista de campos sensíveis para redação (opcional)
        
    Returns:
        Logger configurado
    """
    # Obter logger
    logger = logging.getLogger(name)
    
    # Definir nível de log
    if log_level is None:
        log_level = logging.INFO
    logger.setLevel(log_level)
    
    # Adicionar handler de console se não houver
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(console_handler)
    
    # Adicionar handler de arquivo se especificado
    if log_file:
        file_handler = configure_file_handler(log_file)
        logger.addHandler(file_handler)
    
    # Adicionar filtro para campos sensíveis
    if sensitive_fields:
        log_filter = LogFilter(sensitive_fields)
        logger.addFilter(log_filter)
    
    return logger

def get_logger(
    name: str,
    log_level: Optional[int] = None,
    log_file: Optional[str] = None
) -> Logger:
    """
    Obtém um logger configurado.
    
    Args:
        name: Nome do logger
        log_level: Nível de log (opcional)
        log_file: Caminho para o arquivo de log (opcional)
        
    Returns:
        Logger configurado
    """
    return setup_logging(name, log_level=log_level, log_file=log_file)

def configure_file_handler(log_file: str) -> RotatingFileHandler:
    """
    Configura um handler de arquivo rotativo.
    
    Args:
        log_file: Caminho para o arquivo de log
        
    Returns:
        Handler de arquivo configurado
    """
    # Criar diretório do arquivo de log se não existir
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configurar handler
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    
    # Adicionar formatter
    handler.setFormatter(Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    return handler

def log_exception(logger: Logger, message: str, exception: Exception) -> None:
    """
    Loga uma exceção com detalhes.
    
    Args:
        logger: Logger a ser usado
        message: Mensagem de contexto
        exception: Exceção a ser logada
    """
    logger.error(
        f"{message}: {type(exception).__name__}: {str(exception)}"
    )

class LogFilter(logging.Filter):
    """
    Filtro para redação de informações sensíveis em logs.
    """
    
    def __init__(self, sensitive_fields: List[str], placeholder: str = "[REDACTED]"):
        """
        Inicializa o filtro.
        
        Args:
            sensitive_fields: Lista de campos sensíveis para redação
            placeholder: Texto de substituição
        """
        super().__init__()
        self.sensitive_fields = [field.lower() for field in sensitive_fields]
        self.placeholder = placeholder
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filtra o registro de log, substituindo valores sensíveis.
        
        Args:
            record: Registro de log
            
        Returns:
            True (sempre permite o registro, apenas modifica)
        """
        message = record.getMessage()
        
        # Substituir valores sensíveis mantendo o caso original
        for field in self.sensitive_fields:
            # Padrão para capturar várias formas do campo
            # Ex: "password: 123", "password=123", "password='123'"
            pattern = rf'({field})(\s*[:=]\s*|=|\s+)([\'"]?[^\s,\'"]+[\'"]?)'
            message = re.sub(pattern, rf'\1\2{self.placeholder}', message, flags=re.IGNORECASE)
        
        # Atualizar mensagem
        record.msg = message
        
        return True 