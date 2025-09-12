"""
Centralized logging for hook system.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from enum import Enum


class LogLevel(Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Logger:
    """Centralized logger for hook system."""
    
    def __init__(self, name: str, log_dir: Path = None):
        self.name = name
        self.log_dir = log_dir or Path('logs')
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"{name}.log"
        self.json_file = self.log_dir / f"{name}.json"
        self._entries = []
        self._load_existing_entries()
    
    def _load_existing_entries(self):
        """Load existing JSON log entries."""
        if self.json_file.exists():
            try:
                with open(self.json_file, 'r') as f:
                    self._entries = json.load(f)
                    # Keep only last 100 entries
                    if len(self._entries) > 100:
                        self._entries = self._entries[-100:]
            except Exception:
                self._entries = []
    
    def log(self, level: LogLevel, message: str, data: Dict[str, Any] = None):
        """Log a message with optional data."""
        timestamp = datetime.now().isoformat()
        
        # Create log entry
        entry = {
            'timestamp': timestamp,
            'level': level.value,
            'name': self.name,
            'message': message
        }
        
        if data:
            entry['data'] = data
        
        # Add to entries list
        self._entries.append(entry)
        
        # Write to text log
        self._write_text_log(timestamp, level, message)
        
        # Write to JSON log
        self._write_json_log()
        
        # Output to stderr for critical errors
        if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            print(f"[{level.value}] {message}", file=sys.stderr)
    
    def _write_text_log(self, timestamp: str, level: LogLevel, message: str):
        """Write to text log file."""
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"{timestamp} - [{level.value}] - {message}\n")
        except Exception:
            pass
    
    def _write_json_log(self):
        """Write to JSON log file."""
        try:
            # Keep only last 100 entries
            if len(self._entries) > 100:
                self._entries = self._entries[-100:]
            
            with open(self.json_file, 'w') as f:
                json.dump(self._entries, f, indent=2)
        except Exception:
            pass
    
    def debug(self, message: str, data: Dict[str, Any] = None):
        """Log debug message."""
        self.log(LogLevel.DEBUG, message, data)
    
    def info(self, message: str, data: Dict[str, Any] = None):
        """Log info message."""
        self.log(LogLevel.INFO, message, data)
    
    def warning(self, message: str, data: Dict[str, Any] = None):
        """Log warning message."""
        self.log(LogLevel.WARNING, message, data)
    
    def error(self, message: str, data: Dict[str, Any] = None):
        """Log error message."""
        self.log(LogLevel.ERROR, message, data)
    
    def critical(self, message: str, data: Dict[str, Any] = None):
        """Log critical message."""
        self.log(LogLevel.CRITICAL, message, data)