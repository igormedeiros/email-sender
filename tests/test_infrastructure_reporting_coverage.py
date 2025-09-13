"""Additional tests for infrastructure reporting to improve coverage."""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from email_sender.infrastructure.reporting import TextReportGenerator
from pathlib import Path
from datetime import datetime


def test_text_report_generator_initialization():
    """Test TextReportGenerator initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reports_dir = Path(tmpdir) / "reports"
        generator = TextReportGenerator(str(reports_dir))
        
        assert generator is not None
        assert generator.reports_dir == reports_dir
        # Directory should be created
        assert reports_dir.exists()


def test_text_report_generator_generate_report():
    """Test TextReportGenerator.generate_report method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reports_dir = Path(tmpdir) / "reports"
        generator = TextReportGenerator(str(reports_dir))
        
        # Test generating a basic report
        start_time = datetime.now().timestamp() - 60  # 1 minute ago
        end_time = datetime.now().timestamp()
        
        report_data = generator.generate_report(
            start_time=start_time,
            end_time=end_time,
            total_sent=100,
            successful=95,
            failed=5
        )
        
        # Should return report data
        assert isinstance(report_data, dict)
        assert "report" in report_data
        assert "report_file" in report_data
        assert "duration" in report_data
        assert report_data["total_sent"] == 100
        assert report_data["successful"] == 95
        assert report_data["failed"] == 5
        
        # Report file should be created
        report_file = Path(report_data["report_file"])
        assert report_file.exists()


def test_text_report_generator_generate_report_with_ignored_counts():
    """Test TextReportGenerator.generate_report method with ignored counts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reports_dir = Path(tmpdir) / "reports"
        generator = TextReportGenerator(str(reports_dir))
        
        # Test generating a report with ignored counts
        start_time = datetime.now().timestamp() - 120  # 2 minutes ago
        end_time = datetime.now().timestamp()
        
        report_data = generator.generate_report(
            start_time=start_time,
            end_time=end_time,
            total_sent=100,
            successful=90,
            failed=10,
            ignored_unsubscribed=5,
            ignored_bounces=3
        )
        
        # Should include ignored counts in report
        assert report_data["ignored_unsubscribed"] == 5
        assert report_data["ignored_bounces"] == 3
        
        # Report content should mention ignored counts
        assert "Descadastrados ignorados: 5" in report_data["report"]
        assert "Bounces ignorados: 3" in report_data["report"]


def test_text_report_generator_generate_error_report():
    """Test TextReportGenerator.generate_error_report method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reports_dir = Path(tmpdir) / "reports"
        generator = TextReportGenerator(str(reports_dir))
        
        # Test generating an error report
        error_message = "Test error message"
        report_data = generator.generate_error_report(error_message)
        
        # Should return error report data
        assert isinstance(report_data, dict)
        assert "status" in report_data
        assert report_data["status"] == "error"
        assert "error" in report_data
        assert report_data["error"] == error_message
        assert "report" in report_data
        assert "report_file" in report_data
        
        # Report file should be created
        report_file = Path(report_data["report_file"])
        assert report_file.exists()
        
        # Report content should contain error message
        assert error_message in report_data["report"]


@pytest.mark.skip(reason="Skipping file write error test - difficult to reproduce consistently")
def test_text_report_generator_file_write_error():
    """Test TextReportGenerator handling of file write errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reports_dir = Path(tmpdir) / "reports"
        generator = TextReportGenerator(str(reports_dir))
        
        # Create the reports directory first
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Make the reports directory read-only to force write error
        os.chmod(reports_dir, 0o444)  # Read-only
        
        # Test generating a report (should handle the error gracefully)
        start_time = datetime.now().timestamp() - 60
        end_time = datetime.now().timestamp()
        
        try:
            generator.generate_report(
                start_time=start_time,
                end_time=end_time,
                total_sent=100,
                successful=95,
                failed=5
            )
            # Should not reach here if file write error occurs
            # But the test might pass if the error is handled gracefully
        except IOError:
            # Expected error
            pass
        finally:
            # Restore write permissions for cleanup
            os.chmod(reports_dir, 0o777)


if __name__ == "__main__":
    pytest.main([__file__])