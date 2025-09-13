"""Implementa o relatório de envios em modo texto puro."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from ..interfaces.reporting import ReportingInterface

log = logging.getLogger(__name__)

class TextReportGenerator(ReportingInterface):
    """Gerador de relatórios em formato texto."""

    def __init__(self, reports_dir: str = "reports"):
        """Inicializa o gerador definindo diretório de saída.
        
        Args:
            reports_dir: Caminho do diretório onde salvar relatórios
        """
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)

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
        """Gera um relatório do processo de envio em texto plano.
        
        Args:
            start_time: Timestamp de início
            end_time: Timestamp de fim 
            total_sent: Total de emails tentados
            successful: Total enviado com sucesso
            failed: Total de falhas
            ignored_unsubscribed: (Opcional) Total de descadastrados ignorados
            ignored_bounces: (Opcional) Total de bounces ignorados
            
        Returns:
            Dict com os dados do relatório e métricas
        """
        duration = end_time - start_time
        avg_time = duration / total_sent if total_sent > 0 else 0

        # Calcula horas, minutos e segundos
        horas = int(duration // 3600)
        minutos = int((duration % 3600) // 60)
        segundos = int(duration % 60)

        extra_lines = []
        if ignored_unsubscribed is not None:
            extra_lines.append(f"Descadastrados ignorados: {int(ignored_unsubscribed)}")
        if ignored_bounces is not None:
            extra_lines.append(f"Bounces ignorados: {int(ignored_bounces)}")
        extras_block = ("\n" + "\n".join(extra_lines)) if extra_lines else ""

        report_content = f"""Relatório de Envio de Emails
Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
-----------------------------------------
Total de emails tentados: {total_sent}
Enviados com sucesso: {successful}
Falhas: {failed}
Tempo total: {duration:.2f} segundos ({horas}h {minutos}min {segundos}s)
Tempo médio por email: {avg_time:.2f} segundos
{extras_block}
"""
        report_file_name = f"email_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path = self.reports_dir / report_file_name

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            log.info(f"Report generated: {report_path}")
        except IOError as e:
            log.error(f"Failed to write report file {report_path}: {e}")
            # Falha controlada - propaga erro
            raise

        return {
            "report": report_content,
            "report_file": str(report_path),  # Retorna caminho completo
            "duration": duration,
            "avg_time": avg_time,
            "total_sent": total_sent,
            "successful": successful,
            "failed": failed,
            "duracao_formatada": f"{horas}h {minutos}min {segundos}s",
            "ignored_unsubscribed": ignored_unsubscribed,
            "ignored_bounces": ignored_bounces,
        }

    def generate_error_report(self, error_message: str) -> Dict[str, Any]:
        """Gera um relatório simplificado quando ocorre uma falha grave.
        
        Args:
            error_message: Mensagem de erro a ser registrada
            
        Returns:
            Dict com dados do relatório de erro
        """
        report_file_name = f"email_report_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path = self.reports_dir / report_file_name
        
        error_report_content = f"""Relatório de Erro
Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
-----------------------------------------
Erro: {error_message}
"""
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(error_report_content)
            log.info(f"Error report generated: {report_path}")
        except IOError as e:
            log.error(f"Failed to write error report file {report_path}: {e}")
            # Falha controlada - propaga erro
            raise

        return {
            "status": "error",
            "error": error_message,
            "report_file": str(report_path),  # Retorna caminho completo
            "report": f"Erro: {error_message}"
        }
