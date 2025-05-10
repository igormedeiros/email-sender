import datetime
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

# Configuration
# Assumes this file is in ROOT/email_sender/src/
try:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
except NameError: 
    PROJECT_ROOT = Path(os.getcwd()).resolve() # Fallback for environments where __file__ is not defined

DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
SCHEDULER_JOBS_FILE = DATA_DIR / "scheduler_jobs.json"
SCHEDULED_JOBS_LOG_DIR = LOGS_DIR / "scheduler_jobs"

# This was defined in scheduler_service.py, ensure it's consistent or passed if needed
# For now, assuming cmd_send.sh is at the project root.
CMD_SEND_SCRIPT_NAME = "cmd_send.sh" 


class JobManager:
    def __init__(self, project_root_path=None):
        if project_root_path:
            self.project_root = Path(project_root_path)
        else:
            self.project_root = PROJECT_ROOT

        self.data_dir = self.project_root / "data"
        self.logs_dir = self.project_root / "logs"
        self.jobs_file = self.data_dir / "scheduler_jobs.json"
        self.scheduled_jobs_log_dir = self.logs_dir / "scheduler_jobs"
        
        # CMD_SEND_SCRIPT_PATH should be relative to project_root
        self.cmd_send_script_path = Path(CMD_SEND_SCRIPT_NAME) # Relative path

        # Ensure necessary directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.scheduled_jobs_log_dir.mkdir(exist_ok=True)

    def _log_message(self, message, level="INFO", job_id=None):
        """Internal helper for logging messages. Output goes to stdout."""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = f"[{now}] [{level}]"
        if job_id:
            prefix += f" [Job {job_id}]"
        log_entry = f"{prefix} {message}"
        # This print will be captured by the daemon's redirected stdout/stderr
        # or shown directly on the console if run via CLI for non-daemon actions.
        print(log_entry, flush=True)

    def _load_jobs(self):
        if not self.jobs_file.exists():
            return []
        try:
            with open(self.jobs_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            self._log_message(f"Error: Could not decode JSON from {self.jobs_file}. Returning empty list.", level="ERROR")
            return []
        except Exception as e:
            self._log_message(f"Error loading jobs from {self.jobs_file}: {e}", level="ERROR")
            return []

    def _save_jobs(self, jobs):
        try:
            with open(self.jobs_file, 'w', encoding='utf-8') as f:
                json.dump(jobs, f, indent=4)
        except Exception as e:
            self._log_message(f"Error saving jobs to {self.jobs_file}: {e}", level="ERROR")

    def add_job(self, datetime_str, command_script_relative_path_str=None):
        try:
            run_at_dt = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            print(f"Error: Invalid date/time format '{datetime_str}'. Please use 'YYYY-MM-DD HH:MM'.", file=sys.stderr)
            return None

        # Use provided command script or default
        script_to_schedule = Path(command_script_relative_path_str) if command_script_relative_path_str else self.cmd_send_script_path
        
        # Ensure the script path is relative to project_root for storage
        if script_to_schedule.is_absolute():
            try:
                script_to_schedule_relative = script_to_schedule.relative_to(self.project_root)
            except ValueError:
                print(f"Error: Command script {script_to_schedule} is not within the project root {self.project_root}.", file=sys.stderr)
                return None
        else:
            script_to_schedule_relative = script_to_schedule

        absolute_script_path = self.project_root / script_to_schedule_relative

        if not absolute_script_path.is_file():
            print(f"Error: Command script {absolute_script_path} is not found.", file=sys.stderr)
            return None
        if not os.access(absolute_script_path, os.X_OK):
            print(f"Error: Command script {absolute_script_path} is not executable.", file=sys.stderr)
            print(f"Please ensure it exists and run 'chmod +x {absolute_script_path}'.", file=sys.stderr)
            return None

        jobs = self._load_jobs()
        job_id = str(uuid.uuid4())
        
        new_job = {
            "id": job_id,
            "run_at": run_at_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "command_script": str(script_to_schedule_relative), # Store relative path
            "status": "pending",
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "logfile": None, # Will be relative to project_root
            "last_run_attempt": None,
            "run_output_excerpt": None
        }
        jobs.append(new_job)
        self._save_jobs(jobs)
        print(f"Successfully scheduled job with ID: {job_id} to run at {run_at_dt.strftime('%Y-%m-%d %H:%M')}")
        print(f"Command: {new_job['command_script']}")
        return job_id

    def list_jobs(self):
        jobs = self._load_jobs()
        if not jobs:
            print("No jobs scheduled.")
            return

        print("Scheduled jobs:")
        for job in jobs:
            print(f"  ID: {job['id']}")
            print(f"    Run At: {job['run_at']}")
            print(f"    Status: {job['status']}")
            print(f"    Command: {job.get('command_script', 'N/A')}")
            print(f"    Created At: {job.get('created_at', 'N/A')}")
            if job.get('logfile'): # Logfile is stored relative to project root
                print(f"    Logfile: {job['logfile']}")
            if job.get('last_run_attempt'):
                print(f"    Last Attempt: {job['last_run_attempt']}")
            if job.get('run_output_excerpt'):
                print(f"    Output Excerpt: {job['run_output_excerpt']}")
            print("---")

    def remove_job(self, job_id):
        jobs = self._load_jobs()
        initial_len = len(jobs)
        jobs = [job for job in jobs if job['id'] != job_id]

        if len(jobs) == initial_len:
            print(f"Error: Job with ID '{job_id}' not found.", file=sys.stderr)
            return False
        else:
            self._save_jobs(jobs)
            print(f"Successfully removed job with ID: {job_id}")
            return True

    def remove_all_jobs(self):
        self._save_jobs([])
        print("All scheduled jobs have been removed.")

    def run_pending_jobs(self):
        self._log_message("Checking for pending jobs...")
        jobs = self._load_jobs()
        now = datetime.datetime.now()
        jobs_modified_in_run = False

        for job_index, job_data in enumerate(jobs): # Use a copy for modification safety if needed, but direct modification is fine with save
            current_job = job_data # Keep a reference for clarity
            if current_job['status'] == 'pending':
                try:
                    run_at_dt = datetime.datetime.strptime(current_job['run_at'], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    self._log_message(f"Job {current_job['id']} has invalid run_at format: {current_job['run_at']}. Skipping.", level="ERROR", job_id=current_job['id'])
                    current_job['status'] = 'error_invalid_date'
                    jobs_modified_in_run = True
                    continue # to next job in the list

                if now >= run_at_dt:
                    self._log_message(f"Job {current_job['id']} is due. Attempting to run {current_job['command_script']}...", job_id=current_job['id'])
                    current_job['status'] = 'running'
                    current_job['last_run_attempt'] = now.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Log file path construction (relative to project root for storage)
                    log_filename = f"job_{current_job['id']}_{now.strftime('%Y%m%d%H%M%S')}.log"
                    # scheduled_jobs_log_dir is absolute, make logfile_path_for_storage relative
                    relative_log_dir = self.scheduled_jobs_log_dir.relative_to(self.project_root)
                    logfile_path_for_storage = relative_log_dir / log_filename
                    current_job['logfile'] = str(logfile_path_for_storage)
                    
                    jobs_modified_in_run = True 
                    self._save_jobs(jobs) # Save 'running' status and logfile path before execution

                    # Absolute path for execution
                    absolute_script_to_run = self.project_root / current_job['command_script']
                    absolute_job_logfile_path = self.project_root / current_job['logfile']

                    try:
                        if not absolute_script_to_run.is_file():
                            error_msg = f"Error: Script {absolute_script_to_run} not found at execution time."
                            self._log_message(error_msg, level="ERROR", job_id=current_job['id'])
                            current_job['status'] = 'failed_script_not_found'
                            current_job['run_output_excerpt'] = error_msg
                            self._save_jobs(jobs) 
                            continue
                        if not os.access(absolute_script_to_run, os.X_OK):
                            error_msg = f"Error: Script {absolute_script_to_run} is not executable at execution time."
                            self._log_message(error_msg, level="ERROR", job_id=current_job['id'])
                            current_job['status'] = 'failed_script_not_executable'
                            current_job['run_output_excerpt'] = error_msg
                            self._save_jobs(jobs)
                            continue

                        # Ensure the directory for the job log file exists
                        absolute_job_logfile_path.parent.mkdir(parents=True, exist_ok=True)

                        process = subprocess.Popen(
                            ["/bin/bash", str(absolute_script_to_run)],
                            cwd=self.project_root, 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            encoding='utf-8'
                        )
                        stdout, stderr = process.communicate(timeout=3600) # 1 hour timeout

                        with open(absolute_job_logfile_path, 'w', encoding='utf-8') as lf:
                            lf.write(f"Job ID: {current_job['id']}\n")
                            lf.write(f"Executed Command: /bin/bash {current_job['command_script']}\n")
                            lf.write(f"Timestamp: {current_job['last_run_attempt']}\n")
                            lf.write(f"Return Code: {process.returncode}\n")
                            lf.write("--- STDOUT ---\n")
                            lf.write(stdout)
                            lf.write("\n--- STDERR ---\n")
                            lf.write(stderr)
                        
                        if process.returncode == 0:
                            current_job['status'] = 'completed'
                            self._log_message(f"Completed successfully. Log: {current_job['logfile']}", job_id=current_job['id'])
                        else:
                            current_job['status'] = 'failed'
                            self._log_message(f"Failed with return code {process.returncode}. Log: {current_job['logfile']}", level="ERROR", job_id=current_job['id'])
                        
                        output_summary = (stdout + stderr).strip().replace('\n', ' ')
                        current_job['run_output_excerpt'] = (output_summary[:195] + '...') if len(output_summary) > 200 else output_summary

                    except subprocess.TimeoutExpired:
                        current_job['status'] = 'failed_timeout'
                        current_job['run_output_excerpt'] = "Job timed out after 1 hour."
                        self._log_message(f"Timed out. Log: {current_job['logfile']}", level="ERROR", job_id=current_job['id'])
                        with open(absolute_job_logfile_path, 'a', encoding='utf-8') as lf:
                            lf.write("\n--- SCHEDULER: JOB TIMED OUT (1 hour) ---")
                    except Exception as e:
                        current_job['status'] = 'failed_exception'
                        error_str = str(e).replace('\n', ' ')
                        current_job['run_output_excerpt'] = f"Exception during job execution: {error_str[:150]}"
                        self._log_message(f"Exception while running: {e}", level="CRITICAL", job_id=current_job['id'])
                        with open(absolute_job_logfile_path, 'a', encoding='utf-8') as lf:
                            lf.write(f"\n--- SCHEDULER: EXCEPTION DURING EXECUTION ---\n{str(e)}")
                    finally:
                        jobs[job_index] = current_job # Update the job in the main list
                        jobs_modified_in_run = True 
                        self._save_jobs(jobs) # Save final status of this job
            # End of job processing loop

        if not jobs_modified_in_run:
            self._log_message("No jobs were due or their status changed in this check.")
        else:
            # This final save is a bit redundant if every modification inside the loop saves,
            # but it's a safeguard. Consider if _save_jobs is too frequent.
            # self._save_jobs(jobs) 
            self._log_message("Finished checking and processing jobs.")
