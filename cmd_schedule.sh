#!/bin/bash

# Front-end script to manage the Python-based email scheduling service.

set -e
set -u
set -o pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# Path to the scheduler service Python script
PYTHON_SCHEDULER_SCRIPT_REL_PATH="email_sender/src/scheduler_service.py"
PYTHON_SCHEDULER_SCRIPT=$(realpath "$SCRIPT_DIR/$PYTHON_SCHEDULER_SCRIPT_REL_PATH")

# Attempt to find a suitable Python interpreter
if command -v python3 &>/dev/null; then
    PYTHON_INTERPRETER="python3"
elif command -v python &>/dev/null; then
    PYTHON_INTERPRETER="python"
else
    echo "Error: Neither 'python3' nor 'python' command found. Please install Python or ensure it's in your PATH."
    exit 1
fi

# Ensure the scheduler script exists
if [ ! -f "$PYTHON_SCHEDULER_SCRIPT" ]; then
    echo "Error: Scheduler service Python script not found at $PYTHON_SCHEDULER_SCRIPT"
    echo "Expected relative path from project root: $PYTHON_SCHEDULER_SCRIPT_REL_PATH"
    exit 1
fi

usage() {
    echo "Usage: $0 <action> [arguments]"
    echo ""
    echo "This script is a command-line interface for the Python-based email scheduling service."
    echo "It passes commands and arguments to: $PYTHON_SCHEDULER_SCRIPT_REL_PATH"
    echo ""
    echo "Service Management Actions:"
    echo "  start                      - Start the scheduler daemon."
    echo "  stop                       - Stop the scheduler daemon."
    echo "  status                     - Check the status of the scheduler daemon."
    echo ""
    echo "Job Management Actions:"
    echo "  add <YYYY-MM-DD HH:MM>     - Schedule a new email sending job to run cmd_send.sh."
    echo "                             Example: $0 add "2025-12-31 23:59""
    echo "  list                       - List all scheduled jobs."
    echo "  remove <JOB_ID>            - Remove a scheduled job by its JOB_ID."
    echo "                             (Use 'list' to find the JOB_ID)"
    echo "  remove_all                 - Remove all scheduled jobs."
    echo "  run_once <YYYY-MM-DD HH:MM> - Schedule cmd_send.sh to run once at the specified time."
    echo "                                This job will be automatically removed after execution."
    echo "                             Example: $0 run_once "2025-12-31 23:59""
    # echo "  logs [JOB_ID]              - View logs (daemon log if no JOB_ID, or specific job log)." # Uncomment if scheduler_service.py supports this
    echo ""
    echo "The Python script ($PYTHON_SCHEDULER_SCRIPT_REL_PATH) handles all scheduling logic,"
    echo "job persistence (data/scheduler_jobs.json), PID management (data/scheduler_daemon.pid),"
    echo "and logging (logs/scheduler_daemon.log, logs/scheduler_jobs/)."
    exit 1
}

if [ $# -eq 0 ]; then
    usage
fi

ACTION="$1"
# Safely shift arguments. If no arguments after ACTION, $@ will be empty.
# This prevents "unbound variable" error if set -u is active and no args follow ACTION.
if [ $# -gt 0 ]; then
    shift
fi

# Execute the Python scheduler service script with the given action and arguments
# The Python script (scheduler_service.py) is responsible for parsing these arguments
# and performing the requested operations.
"$PYTHON_INTERPRETER" "$PYTHON_SCHEDULER_SCRIPT" "$ACTION" "$@"

exit 0
