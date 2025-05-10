\
import os
import sys
import time
import signal
import errno
from pathlib import Path

class DaemonError(Exception):
    \"\"\"Custom exception for daemon-related errors.\"\"\"
    pass

class DaemonProcess:
    \"\"\"
    A class to handle daemonization, PID file management, and process status.
    \"\"\"
    def __init__(self, pid_file: Path, process_name: str = "Daemon"):
        \"\"\"
        Initialize the DaemonProcess handler.

        Args:
            pid_file: Path to the PID file.
            process_name: Name of the daemon process (for logging/error messages).
        \"\"\"
        self.pid_file = Path(pid_file)
        self.process_name = process_name

    def _write_pid_file(self):
        \"\"\"Writes the current process ID to the PID file.\"\"\"
        try:
            self.pid_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.pid_file, 'w') as pf:
                pf.write(str(os.getpid()))
        except IOError as e:
            raise DaemonError(f"Unable to write PID file {self.pid_file}: {e}")

    def _remove_pid_file(self):
        \"\"\"Removes the PID file if it exists.\"\"\"
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except OSError as e:
            # This error might be logged by the caller if important
            sys.stderr.write(f"Warning: Could not remove PID file {self.pid_file}: {e}\\n")

    def get_pid(self) -> int | None:
        \"\"\"
        Reads the PID from the PID file.

        Returns:
            The PID as an integer if the file exists and is valid, otherwise None.
        \"\"\"
        if not self.pid_file.exists():
            return None
        try:
            with open(self.pid_file, 'r') as pf:
                pid_str = pf.read().strip()
                if not pid_str:  # Handle empty PID file
                    return None
                pid = int(pid_str)
            return pid
        except (ValueError, FileNotFoundError): # Invalid content or file gone
            return None
        except IOError: # Permission issues, etc.
            return None

    def is_running(self) -> bool:
        \"\"\"
        Checks if the daemon process is currently running.
        A process is considered running if a PID exists in the PID file
        and a process with that PID is active.
        \"\"\"
        pid = self.get_pid()
        if pid is None:
            # If pid_file exists but get_pid() returned None, it implies a corrupt/empty PID file.
            # Such a stale file might be cleaned up by the caller if is_running() is False.
            return False
        try:
            os.kill(pid, 0)  # Send signal 0 to check if process exists
            return True
        except OSError as err:
            if err.errno == errno.ESRCH: # No such process
                return False
            elif err.errno == errno.EPERM: # No permission to signal, but process exists
                return True # Assume it's running if we lack permission but it's there
            raise # Re-raise other OSErrors
        except Exception: # Catch any other unexpected errors during os.kill
            return False


    def start(self, work_dir: Path, stdout_log_path: Path, stderr_log_path: Path):
        \"\"\"
        Daemonizes the current process. This method will exit the original
        parent process and continue execution only in the daemonized child process.
        If this method returns, the current process IS the daemon.

        Args:
            work_dir: The working directory for the daemon.
            stdout_log_path: Path to redirect daemon's stdout.
            stderr_log_path: Path to redirect daemon's stderr.

        Raises:
            DaemonError: If the daemon is already running or daemonization fails.
        \"\"\"
        current_pid = self.get_pid()
        if current_pid is not None and self.is_running():
             raise DaemonError(f"{self.process_name} is already running with PID {current_pid} (PID file: {self.pid_file}).")
        elif self.pid_file.exists() and current_pid is None: # Corrupt/empty PID file
            self._remove_pid_file() # Clean up corrupt PID file before starting

        # First fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # Exit first parent
        except OSError as e:
            raise DaemonError(f"Fork #1 failed for {self.process_name}: {e.errno} ({e.strerror})")

        os.chdir(str(work_dir))
        os.setsid()  # Create a new session
        os.umask(0)  # Grant all permissions for files created by the daemon

        # Second fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # Exit second parent
        except OSError as e:
            raise DaemonError(f"Fork #2 failed for {self.process_name}: {e.errno} ({e.strerror})")

        # Flush standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()

        # Redirect standard file descriptors
        try:
            stdout_log_path.parent.mkdir(parents=True, exist_ok=True)
            stderr_log_path.parent.mkdir(parents=True, exist_ok=True)

            # Open standard streams
            # Use 'a' for append text mode, matching typical log file behavior.
            stdin_fd = open(os.devnull, 'r')
            stdout_fd = open(stdout_log_path, 'a')
            stderr_fd = open(stderr_log_path, 'a')

            os.dup2(stdin_fd.fileno(), sys.stdin.fileno())
            os.dup2(stdout_fd.fileno(), sys.stdout.fileno())
            os.dup2(stderr_fd.fileno(), sys.stderr.fileno())

            # Close original FDs
            stdin_fd.close()
            stdout_fd.close()
            stderr_fd.close()
        except Exception as e:
            # This is hard to report if stderr is already redirected or closed.
            # The error might be silently lost or go to the new stderr_log_path.
            raise DaemonError(f"Failed to redirect stdio for {self.process_name}: {e}")

        # Write PID file from the daemon process
        self._write_pid_file()
        # At this point, the current process is the daemon.
        # The method returns, and the caller (which is now the daemon) continues.

    def stop(self, sig: int = signal.SIGTERM, timeout: int = 5) -> bool:
        \"\"\"
        Stops the daemon process.

        Args:
            sig: The signal to send for termination (default: SIGTERM).
            timeout: Seconds to wait for the process to terminate before trying SIGKILL.

        Returns:
            True if the daemon was stopped successfully or was not running.
            False if errors occurred during stopping.
        \"\"\"
        pid = self.get_pid()

        if pid is None: # No PID file
            if self.pid_file.exists(): # Stale (empty/corrupt) PID file
                self._remove_pid_file()
            return True # Not running

        if not self.is_running(): # Process with PID not found
            self._remove_pid_file() # Clean up stale PID file
            return True

        try:
            os.kill(pid, sig)
        except OSError as err:
            if err.errno == errno.ESRCH:  # No such process
                self._remove_pid_file()
                return True  # Already stopped
            # For EPERM (permission denied), we can't stop it, so return False
            return False # Failed to send signal for other reasons

        # Wait for termination
        for _ in range(timeout):
            time.sleep(1)
            if not self.is_running():
                self._remove_pid_file()
                return True

        # If still running, escalate to SIGKILL
        try:
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.5) # Brief pause for OS to process SIGKILL
            if not self.is_running():
                self._remove_pid_file()
                return True
            else: # Still running after SIGKILL
                return False # Failed to kill
        except OSError as err:
            if err.errno == errno.ESRCH: # No such process (killed between last check and now)
                self._remove_pid_file()
                return True
            return False # Error sending SIGKILL
        except Exception:
            return False # Other unexpected error
