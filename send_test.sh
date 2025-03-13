#!/bin/bash

test_file="test_emails.csv"
descadastros_file="descadastros.csv"
# load environment variables
if [ -f .env ]; then
    source .env
fi

# activate virtual environment
if [ -d venv ]; then
    source venv/bin/activate
fi

# clear flags
python3 -m src.cli clear-sent-flags --csv-file data/$test_file

# Sync unsubscribed
python3 -m src.cli sync-unsubscribed-command --csv-file data/$test_file --unsubscribe-file data/$descadastros_file


# send emails in production mode
python3 -m src.cli send-emails templates/email.html --mode=test
