"""Interfaces para reportagem de resultados de envio."""
from abc import ABC, abstractmethod
from typing import Dict, Any

class ReportingInterface(ABC):
    """Interface base para geradores de relatórios."""

    @abstractmethod
    def generate_report(
        self,
        start_time: float,
        end_time: float,
        total_sent: int,
        successful: int,
        failed: int,
        *,
        ignored_unsubscribed: int | None = None,
        ignored_bounces: int | None = None,
    ) -> Dict[str, Any]:
        """Gera um relatório do processo de envio de emails.
        
        Args:
            start_time: Timestamp de início
            end_time: Timestamp de fim 
            total_sent: Total de emails tentados
            successful: Total enviado com sucesso
            failed: Total de falhas
            ignored_unsubscribed: (Opcional) Total de descadastrados ignorados
            ignored_bounces: (Opcional) Total de bounces ignorados
            
        Returns:
            Dict com dados do relatório, incluindo:
            - report: Conteúdo do relatório
            - report_file: Caminho do arquivo gerado
            - duration: Duração total em segundos
            - avg_time: Tempo médio por email
            - total_sent: Total de tentativas
            - successful: Total de sucesso
            - failed: Total de falhas
            - duracao_formatada: Duração formatada
            - ignored_unsubscribed: Total de descadastrados (se fornecido)
            - ignored_bounces: Total de bounces (se fornecido)
        """
        pass

    @abstractmethod
    def generate_error_report(self, error_message: str) -> Dict[str, Any]:
        """Gera um relatório simplificado quando ocorre uma falha grave.
        
        Args:
            error_message: Mensagem de erro a ser registrada
            
        Returns:
            Dict com dados do relatório de erro:
            - status: "error"
            - error: Mensagem original
            - report_file: Caminho do arquivo
            - report: Conteúdo formatado
        """
        pass
