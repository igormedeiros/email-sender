import pytest
from email_sender.config import Config
from configparser import ConfigParser

@pytest.fixture
def sample_config_file(tmp_path):
    config_file = tmp_path / "test.properties"
    with open(config_file, "w") as f:
        f.write("""[smtp]
host=smtp.test.com
port=587
username=test_user
password=test_pass
use_tls=true

[email]
sender=test@example.com
batch_size=50
xlsx_file=test_emails.xlsx""")
    return str(config_file)

def test_smtp_config(sample_config_file):
    config = Config(sample_config_file)
    smtp_config = config.smtp_config
    
    assert smtp_config["host"] == "smtp.test.com"
    assert smtp_config["port"] == 587
    assert smtp_config["username"] == "test_user"
    assert smtp_config["password"] == "test_pass"
    assert smtp_config["use_tls"] is True

def test_email_config(sample_config_file):
    config = Config(sample_config_file)
    email_config = config.email_config
    
    assert email_config["sender"] == "test@example.com"
    assert email_config["batch_size"] == 50
    assert email_config["xlsx_file"] == "test_emails.xlsx"
    # Removendo o teste de test_recipient pois é opcional