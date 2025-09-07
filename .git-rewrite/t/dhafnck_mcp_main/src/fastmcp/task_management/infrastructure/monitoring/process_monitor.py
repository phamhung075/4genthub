"""Process Monitor

Infrastructure component for monitoring and managing system processes with timeout protection.
"""

import logging
import time
import threading
import subprocess
import signal
import os
import uuid
from typing import Dict, Any, Optional

from ...domain.enums.compliance_enums import ProcessStatus
from ...domain.value_objects.compliance_objects import ProcessInfo

logger = logging.getLogger(__name__)


class ProcessMonitor:
    """Infrastructure service for process monitoring and timeout protection"""
    
    def __init__(self, default_timeout: int = 20):
        self.default_timeout = default_timeout
        self._active_processes: Dict[str, ProcessInfo] = {}
        self._monitoring_thread: Optional[threading.Thread] = None
        self._monitoring_active = False
        self._lock = threading.Lock()
        
    def start_monitoring(self):
        """Start process monitoring thread"""
        with self._lock:
            if not self._monitoring_active:
                self._monitoring_active = True
                self._monitoring_thread = threading.Thread(target=self._monitor_processes, daemon=True)
                self._monitoring_thread.start()
                logger.info("Process monitoring started")
    
    def stop_monitoring(self):
        """Stop process monitoring"""
        with self._lock:
            self._monitoring_active = False
            if self._monitoring_thread:
                self._monitoring_thread.join(timeout=5)
                logger.info("Process monitoring stopped")
    
    def execute_with_timeout(self, command: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute command with timeout protection"""
        timeout = timeout or self.default_timeout
        process_id = str(uuid.uuid4())
        
        # Create process info
        process_info = ProcessInfo(
            process_id=process_id,
            command=command,
            start_time=time.time(),
            timeout_seconds=timeout,
            status=ProcessStatus.RUNNING
        )
        
        # Register process
        with self._lock:
            self._active_processes[process_id] = process_info
        
        try:
            # Execute command with timeout
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Update process status
            completed_process = ProcessInfo(
                process_id=process_id,
                command=command,
                start_time=process_info.start_time,
                timeout_seconds=timeout,
                status=ProcessStatus.COMPLETED,
                pid=result.pid if hasattr(result, 'pid') else None
            )
            
            with self._lock:
                self._active_processes[process_id] = completed_process
            
            execution_time = time.time() - process_info.start_time
            
            return {
                "success": True,
                "process_id": process_id,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "execution_time": execution_time,
                "timeout_enforced": False
            }
            
        except subprocess.TimeoutExpired:
            # Update process status to timeout
            timeout_process = ProcessInfo(
                process_id=process_id,
                command=command,
                start_time=process_info.start_time,
                timeout_seconds=timeout,
                status=ProcessStatus.TIMEOUT
            )
            
            with self._lock:
                self._active_processes[process_id] = timeout_process
            
            # Force cleanup
            self._cleanup_process(process_id)
            
            return {
                "success": False,
                "process_id": process_id,
                "error": "Command timed out",
                "timeout_enforced": True,
                "execution_time": timeout
            }
            
        except Exception as e:
            # Update process status to error
            error_process = ProcessInfo(
                process_id=process_id,
                command=command,
                start_time=process_info.start_time,
                timeout_seconds=timeout,
                status=ProcessStatus.ERROR
            )
            
            with self._lock:
                self._active_processes[process_id] = error_process
            
            return {
                "success": False,
                "process_id": process_id,
                "error": str(e),
                "timeout_enforced": False
            }
            
        finally:
            # Clean up process record after delay
            threading.Timer(60.0, lambda: self._remove_process(process_id)).start()
    
    def get_active_processes(self) -> Dict[str, ProcessInfo]:
        """Get currently active processes"""
        with self._lock:
            return self._active_processes.copy()
    
    def get_process_info(self, process_id: str) -> Optional[ProcessInfo]:
        """Get information about a specific process"""
        with self._lock:
            return self._active_processes.get(process_id)
    
    def _monitor_processes(self):
        """Monitor active processes for timeout"""
        while self._monitoring_active:
            current_time = time.time()
            
            with self._lock:
                processes_to_cleanup = []
                
                for process_id, process_info in self._active_processes.items():
                    if process_info.status != ProcessStatus.RUNNING:
                        continue
                        
                    elapsed = current_time - process_info.start_time
                    
                    # Check for timeout
                    if elapsed >= process_info.timeout_seconds:
                        logger.warning(f"Process {process_id} timed out after {elapsed}s")
                        
                        # Update status to timeout
                        timeout_process = ProcessInfo(
                            process_id=process_info.process_id,
                            command=process_info.command,
                            start_time=process_info.start_time,
                            timeout_seconds=process_info.timeout_seconds,
                            status=ProcessStatus.TIMEOUT,
                            pid=process_info.pid
                        )
                        self._active_processes[process_id] = timeout_process
                        processes_to_cleanup.append(process_id)
            
            # Cleanup processes outside of lock
            for process_id in processes_to_cleanup:
                self._cleanup_process(process_id)
            
            time.sleep(1)  # Check every second
    
    def _cleanup_process(self, process_id: str):
        """Cleanup timed out process"""
        process_info = self.get_process_info(process_id)
        if not process_info or not process_info.pid:
            return
        
        try:
            # Graceful termination
            os.kill(process_info.pid, signal.SIGTERM)
            time.sleep(2)
            
            # Force kill if still running
            try:
                os.kill(process_info.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # Process already terminated
            
            logger.info(f"Process {process_id} cleaned up after timeout")
            
        except Exception as e:
            logger.error(f"Failed to cleanup process {process_id}: {e}")
    
    def _remove_process(self, process_id: str):
        """Remove process from active processes"""
        with self._lock:
            if process_id in self._active_processes:
                del self._active_processes[process_id]