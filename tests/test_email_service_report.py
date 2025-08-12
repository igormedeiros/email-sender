import time
from pathlib import Path
from email_sender.reporting import ReportGenerator


def test_report_generator_outputs_file(tmp_path):
    rg = ReportGenerator(reports_dir=str(tmp_path))
    start = time.time()
    end = start + 3.5
    report = rg.generate_report(start, end, total_sent=2, successful=1, failed=1)
    assert Path(report['report_file']).exists()
    assert 'Relatório de Envio de Emails' in report['report']
    assert report['total_sent'] == 2
