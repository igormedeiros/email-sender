from email_sender.controller_cli import app


def test_controller_cli_app_exists():
    assert app is not None
