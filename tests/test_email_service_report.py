import time
from pathlib import Path
from email_sender.infrastructure.reporting import TextReportGenerator as ReportGenerator


def test_report_generator_outputs_file(tmp_path):
    rg = ReportGenerator(reports_dir=str(tmp_path))
    start = time.time()
    end = start + 3.5
    report = rg.generate_report(start, end, total_sent=2, successful=1, failed=1)
    assert Path(report['report_file']).exists()
    assert 'Relatório de Envio de Emails' in report['report']
    assert report['total_sent'] == 2


def test_report_generator_with_ignored_counts(tmp_path):
    """Test report generation with ignored unsubscribed and bounce counts."""
    rg = ReportGenerator(reports_dir=str(tmp_path))
    start = time.time()
    end = start + 5.0
    report = rg.generate_report(
        start, 
        end, 
        total_sent=10, 
        successful=8, 
        failed=2,
        ignored_unsubscribed=3,
        ignored_bounces=1
    )
    assert Path(report['report_file']).exists()
    assert 'Relatório de Envio de Emails' in report['report']
    assert report['total_sent'] == 10
    assert report['successful'] == 8
    assert report['failed'] == 2
    assert report['ignored_unsubscribed'] == 3
    assert report['ignored_bounces'] == 1
    # Check that ignored counts appear in the report content
    assert 'Descadastrados ignorados: 3' in report['report']
    assert 'Bounces ignorados: 1' in report['report']


def test_report_generator_error_report(tmp_path):
    """Test error report generation."""
    rg = ReportGenerator(reports_dir=str(tmp_path))
    error_message = "Test error message"
    report = rg.generate_error_report(error_message)
    assert Path(report['report_file']).exists()
    # Check that the error message is in the report content
    assert error_message in report['report']
    assert report['status'] == 'error'
