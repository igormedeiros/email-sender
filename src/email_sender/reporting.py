\
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

log = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)

    def generate_report(self, start_time: float, end_time: float, total_sent: int, successful: int, failed: int) -> Dict[str, Any]:
        """
        Generates a report of the email sending process.
        """
        duration = end_time - start_time
        avg_time = duration / total_sent if total_sent > 0 else 0

        # Calculate hours, minutes, and seconds
        horas = int(duration // 3600)
        minutos = int((duration % 3600) // 60)
        segundos = int(duration % 60)

        report_content = f"""Relatório de Envio de Emails
Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
-----------------------------------------
Total de emails tentados: {total_sent}
Enviados com sucesso: {successful}
Falhas: {failed}
Tempo total: {duration:.2f} segundos ({horas}h {minutos}min {segundos}s)
Tempo médio por email: {avg_time:.2f} segundos
"""
        report_file_name = f"email_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path = self.reports_dir / report_file_name

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            log.info(f"Report generated: {report_path}")
        except IOError as e:
            log.error(f"Failed to write report file {report_path}: {e}")
            # Fallback or re-raise, depending on desired error handling
            raise

        return {
            "report": report_content,
            "report_file": str(report_path), # Return full path
            "duration": duration,
            "avg_time": avg_time,
            "total_sent": total_sent,
            "successful": successful,
            "failed": failed,
            "duracao_formatada": f"{horas}h {minutos}min {segundos}s"
        }

    def generate_error_report(self, error_message: str) -> Dict[str, Any]:
        """
        Generates a simplified error report when a major failure occurs.
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
            # Fallback or re-raise
            raise

        return {
            "status": "error",
            "error": error_message,
            "report_file": str(report_path), # Return full path
            "report": f"Erro: {error_message}"
        }
