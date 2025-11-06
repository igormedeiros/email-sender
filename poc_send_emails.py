import os
from pathlib import Path
from email_sender.controller_cli import send_emails

print("--- Isolated POC for send_emails ---")

# Define file paths
cwd = Path.cwd()
config_file = cwd / "config" / "config.yaml"
content_file = cwd / "config" / "email.yaml"

# Set environment
os.environ["ENVIRONMENT"] = "test"

print(f"Config file: {config_file}")
print(f"Content file: {content_file}")
print(f"Environment: {os.environ.get('ENVIRONMENT')}")

try:
    send_emails(
        subject=None,
        titulo=None,
        config_file=str(config_file),
        content_file=str(content_file),
        skip_unsubscribed_sync=False,
        mode="test",
    )
    print("--- POC finished successfully ---")
except Exception as e:
    print(f"--- 🚨 An error occurred: ---")
    print(e)
    import traceback
    traceback.print_exc()
