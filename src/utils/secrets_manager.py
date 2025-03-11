"""
Gerenciador de segredos para credenciais sensíveis.
Suporta vários métodos de armazenamento:
- Variáveis de ambiente
- Arquivos .env (desenvolvimento)
- Secret managers (AWS, Azure, etc.)
"""
import os
import logging
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path
from functools import lru_cache

# Tentar importar bibliotecas opcionais
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

try:
    import boto3
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

try:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

logger = logging.getLogger(__name__)

class SecretSource(Enum):
    """Enum para os tipos de fontes de segredos suportados"""
    ENV = "env"
    DOTENV = "dotenv"
    AWS_SECRETS = "aws"
    AZURE_KEYVAULT = "azure"
    VAULT = "vault"

class SecretsManager:
    """Gerenciador de segredos para credenciais sensíveis"""

    def __init__(self, 
                 source: SecretSource = SecretSource.ENV, 
                 dotenv_path: str = ".env",
                 aws_region: str = "us-east-1",
                 azure_vault_url: str = None,
                 vault_url: str = None,
                 config_defaults: Dict[str, Any] = None):
        """
        Inicializa o gerenciador de segredos.

        Args:
            source: Fonte de segredos a ser usada
            dotenv_path: Caminho para o arquivo .env (se usando DOTENV)
            aws_region: Região AWS (se usando AWS_SECRETS)
            azure_vault_url: URL do Azure Key Vault (se usando AZURE_KEYVAULT)
            vault_url: URL do HashiCorp Vault (se usando VAULT)
            config_defaults: Valores padrão para fallback
        """
        self.source = source
        self.dotenv_path = dotenv_path
        self.aws_region = aws_region
        self.azure_vault_url = azure_vault_url
        self.vault_url = vault_url
        self.config_defaults = config_defaults or {}
        
        # Inicializar a fonte de segredos selecionada
        self._init_source()
        
    def _init_source(self):
        """Inicializa a fonte de segredos selecionada"""
        if self.source == SecretSource.DOTENV:
            if not DOTENV_AVAILABLE:
                logger.warning("Biblioteca python-dotenv não está instalada. Usando variáveis de ambiente do sistema.")
                self.source = SecretSource.ENV
            else:
                if os.path.exists(self.dotenv_path):
                    load_dotenv(self.dotenv_path)
                else:
                    logger.warning(f"Arquivo .env não encontrado em {self.dotenv_path}. Usando variáveis de ambiente do sistema.")
                    self.source = SecretSource.ENV
        
        elif self.source == SecretSource.AWS_SECRETS:
            if not AWS_AVAILABLE:
                logger.warning("Biblioteca boto3 não está instalada. Usando variáveis de ambiente do sistema.")
                self.source = SecretSource.ENV
            else:
                self.aws_client = boto3.client('secretsmanager', region_name=self.aws_region)
        
        elif self.source == SecretSource.AZURE_KEYVAULT:
            if not AZURE_AVAILABLE:
                logger.warning("Biblioteca azure-keyvault-secrets não está instalada. Usando variáveis de ambiente do sistema.")
                self.source = SecretSource.ENV
            elif not self.azure_vault_url:
                logger.warning("URL do Azure Key Vault não configurada. Usando variáveis de ambiente do sistema.")
                self.source = SecretSource.ENV
            else:
                self.azure_credential = DefaultAzureCredential()
                self.azure_client = SecretClient(vault_url=self.azure_vault_url, credential=self.azure_credential)
        
        elif self.source == SecretSource.VAULT:
            logger.warning("HashiCorp Vault ainda não suportado. Usando variáveis de ambiente do sistema.")
            self.source = SecretSource.ENV

    @lru_cache(maxsize=128)
    def get_secret(self, key: str, default: str = None) -> Optional[str]:
        """
        Obtém um segredo da fonte configurada.
        
        Args:
            key: Nome da chave do segredo
            default: Valor padrão se o segredo não for encontrado
            
        Returns:
            Valor do segredo ou o valor padrão se não encontrado
        """
        # Primeiro verifica variáveis de ambiente críticas (substituem qualquer outra fonte)
        # Isso é para permitir sempre sobrescrever via variáveis de ambiente em produção
        env_value = os.environ.get(key)
        if env_value is not None:
            return env_value
            
        # Em seguida, verificar a fonte configurada
        if self.source == SecretSource.ENV or self.source == SecretSource.DOTENV:
            # Já verificamos as variáveis de ambiente acima
            pass
        
        elif self.source == SecretSource.AWS_SECRETS:
            try:
                response = self.aws_client.get_secret_value(SecretId=key)
                if 'SecretString' in response:
                    return response['SecretString']
            except Exception as e:
                logger.error(f"Erro ao obter segredo da AWS: {str(e)}")
        
        elif self.source == SecretSource.AZURE_KEYVAULT:
            try:
                secret = self.azure_client.get_secret(key)
                return secret.value
            except Exception as e:
                logger.error(f"Erro ao obter segredo do Azure Key Vault: {str(e)}")
        
        # Verificar se há um valor padrão nas configurações
        if key in self.config_defaults:
            return self.config_defaults.get(key)
        
        # Por fim, retornar o valor padrão fornecido
        return default

    def get_smtp_credentials(self) -> Dict[str, str]:
        """
        Retorna as credenciais SMTP.
        
        Returns:
            Dicionário com username e password para SMTP
        """
        return {
            "username": self.get_secret("SMTP_USERNAME", ""),
            "password": self.get_secret("SMTP_PASSWORD", "")
        } 