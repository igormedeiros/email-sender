import argparse
import datetime
import os
import sys
import time
from pathlib import Path

from .daemon_utils import DaemonProcess, DaemonError
from .scheduler_job_manager import JobManager

# --- Configuration ---
# Determine project root assuming this script is in ROOT/email_sender/src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
SCHEDULER_PID_FILE = DATA_DIR / "scheduler_daemon.pid"
SCHEDULER_DAEMON_LOG_FILE = LOGS_DIR / "scheduler_daemon.log"

# Ensure necessary directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# --- Daemon Instance ---
DAEMON_STDOUT_LOG = LOGS_DIR / "scheduler_daemon_stdout.log"
DAEMON_STDERR_LOG = LOGS_DIR / "scheduler_daemon_stderr.log"
daemon_process = DaemonProcess(
    pid_file=SCHEDULER_PID_FILE,
    process_name="SchedulerDaemon"
)

# --- JobManager Instance ---
job_manager = JobManager(project_root_path=PROJECT_ROOT)

# --- Helper Functions (Daemon Specific) ---

def _log_daemon_message(message, level="INFO"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{now}] [{level}] {message}\n"
    print(log_entry, end='', flush=True)
    try:
        with open(SCHEDULER_DAEMON_LOG_FILE, 'a') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write to SCHEDULER_DAEMON_LOG_FILE: {e}\n", file=sys.stderr, flush=True)

# --- Job Management Functions (delegated to JobManager) ---

def add_job_cli(datetime_str):
    job_manager.add_job(datetime_str)

def list_jobs_cli():
    job_manager.list_jobs()

def remove_job_cli(job_id):
    job_manager.remove_job(job_id)

def remove_all_jobs_cli():
    if sys.stdin.isatty():
        confirm = input("Are you sure you want to remove ALL scheduled jobs? (yes/No): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled.")
            return
    job_manager.remove_all_jobs()

# --- Daemon and Job Execution Logic ---

def start_daemon():
    _log_daemon_message("Attempting to start scheduler daemon...")
    try:
        daemon_process.start(
            work_dir=PROJECT_ROOT,
            stdout_log_path=DAEMON_STDOUT_LOG,
            stderr_log_path=DAEMON_STDERR_LOG
        )
        _log_daemon_message(f"Scheduler daemon process started successfully with PID {os.getpid()}. Monitoring jobs.")
    except DaemonError as e:
        error_msg = f"Failed to start daemon: {e}"
        _log_daemon_message(error_msg, level="ERROR")
        print(error_msg, file=sys.stderr, flush=True)
        sys.exit(1)
    except Exception as e:
        error_msg = f"An unexpected error occurred while trying to start the daemon: {e}"
        _log_daemon_message(error_msg, level="CRITICAL")
        print(error_msg, file=sys.stderr, flush=True)
        sys.exit(1)

    try:
        while True:
            job_manager.run_pending_jobs()
            time.sleep(60)
    except KeyboardInterrupt:
        _log_daemon_message("Daemon received KeyboardInterrupt. Shutting down.")
    except Exception as e:
        _log_daemon_message(f"Unhandled exception in daemon loop: {e}", level="CRITICAL")
    finally:
        _log_daemon_message("Scheduler daemon stopping.")
        if daemon_process.is_running() and daemon_process.get_pid() == os.getpid():
            daemon_process._remove_pid_file()

def stop_daemon():
    _log_daemon_message("Attempting to stop scheduler daemon...")
    try:
        pid = daemon_process.get_pid()
        if pid is None:
            print("Scheduler daemon PID file not found or invalid. Is it running?")
            _log_daemon_message("Stop command: PID file not found or invalid.", level="WARNING")
            if daemon_process.pid_file.exists():
                daemon_process._remove_pid_file()
            return

        if not daemon_process.is_running():
            print(f"Scheduler daemon (PID {pid} from file) is not actually running. Cleaning up PID file.")
            _log_daemon_message(f"Stop command: Process with PID {pid} not running. Stale PID file removed.", level="WARNING")
            daemon_process._remove_pid_file()
            return

        print(f"Sending stop signal to scheduler daemon (PID {pid})...")
        if daemon_process.stop():
            print(f"Scheduler daemon (PID {pid}) stopped successfully.")
            _log_daemon_message(f"Daemon (PID {pid}) stopped successfully.")
        else:
            print(f"Failed to stop scheduler daemon (PID {pid}). It might still be running. Check logs and system processes.")
            _log_daemon_message(f"Failed to stop daemon (PID {pid}). Manual intervention may be required.", level="ERROR")

    except DaemonError as e:
        print(f"DaemonError while stopping: {e}", file=sys.stderr, flush=True)
        _log_daemon_message(f"DaemonError during stop: {e}", level="ERROR")
    except Exception as e:
        print(f"An unexpected error occurred while trying to stop the daemon: {e}", file=sys.stderr, flush=True)
        _log_daemon_message(f"Unexpected error stopping daemon: {e}", level="ERROR")

def status_daemon():
    pid = daemon_process.get_pid()
    if pid is None:
        if daemon_process.pid_file.exists():
            print(f"Scheduler daemon status UNKNOWN (PID file {SCHEDULER_PID_FILE} is present but invalid/empty).")
            print(f"Consider removing it if the daemon is confirmed not to be running: rm {SCHEDULER_PID_FILE}")
        else:
            print("Scheduler daemon is NOT running (PID file not found).")
        return

    if daemon_process.is_running():
        print(f"Scheduler daemon is RUNNING with PID {pid}.")
        print(f"Daemon PID file: {SCHEDULER_PID_FILE}")
        print(f"Daemon stdout log: {DAEMON_STDOUT_LOG.relative_to(PROJECT_ROOT)}")
        print(f"Daemon stderr log: {DAEMON_STDERR_LOG.relative_to(PROJECT_ROOT)}")
        print(f"Daemon internal log: {SCHEDULER_DAEMON_LOG_FILE.relative_to(PROJECT_ROOT)}")
        print(f"Jobs definition file: {job_manager.jobs_file.relative_to(PROJECT_ROOT)}")
        print(f"Scheduled jobs log directory: {job_manager.scheduled_jobs_log_dir.relative_to(PROJECT_ROOT)}")
    else:
        print(f"Scheduler daemon is NOT running (Process with PID {pid} not found, but PID file exists).")
        print(f"This may indicate a stale PID file. Consider removing it: rm {SCHEDULER_PID_FILE}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scheduler Service for command-line scripts")
    subparsers = parser.add_subparsers(dest="action", help="Action to perform", required=True)

    add_parser = subparsers.add_parser("add", help="Schedule a new job. Args: \"YYYY-MM-DD HH:MM\" [script_path]")
    add_parser.add_argument("datetime", type=str, help="Date and time for the job in 'YYYY-MM-DD HH:MM' format.")
    add_parser.add_argument("script_path", type=str, nargs='?', default=None,
                            help="Optional: Path to the script to schedule (relative to project root). Defaults to JobManager's default script.")

    list_parser = subparsers.add_parser("list", help="List all scheduled jobs.")
    
    remove_parser = subparsers.add_parser("remove", help="Remove a job by ID.")
    remove_parser.add_argument("job_id", type=str, help="ID of the job to remove.")

    remove_all_parser = subparsers.add_parser("remove_all", help="Remove all scheduled jobs.")
    
    start_parser = subparsers.add_parser("start", help="Start the scheduler daemon.")
    stop_parser = subparsers.add_parser("stop", help="Stop the scheduler daemon.")
    status_parser = subparsers.add_parser("status", help="Check the status of the scheduler daemon.")
    
    run_once_parser = subparsers.add_parser("run_once", help="Check schedule and run due jobs once, then exit (does not daemonize).")

    args = parser.parse_args()

    if args.action == "add":
        job_manager.add_job(args.datetime, command_script_relative_path_str=args.script_path)
    elif args.action == "list":
        list_jobs_cli()
    elif args.action == "remove":
        remove_job_cli(args.job_id)
    elif args.action == "remove_all":
        remove_all_jobs_cli()
    elif args.action == "start":
        start_daemon()
    elif args.action == "stop":
        stop_daemon()
    elif args.action == "status":
        status_daemon()
    elif args.action == "run_once":
        _log_daemon_message("Running pending jobs once (run_once mode)...")
        job_manager.run_pending_jobs()
        _log_daemon_message("Finished run_once mode.")
    else:
        parser.print_help()

