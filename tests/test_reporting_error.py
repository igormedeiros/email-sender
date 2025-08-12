from pathlib import Path
from email_sender.reporting import ReportGenerator

def test_generate_error_report(tmp_path: Path):
    rg = ReportGenerator(reports_dir=str(tmp_path))
    rep = rg.generate_error_report("boom")
    assert Path(rep["report_file"]).exists()
    assert rep["status"] == "error"
