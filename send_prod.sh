#!/bin/bash

# load environment variables
source .env

# activate virtual environment
source venv/bin/activate

# send emails in production mode
python3 -m src.cli send-emails templates/email.html --mode=production
