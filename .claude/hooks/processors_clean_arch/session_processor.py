"""
Session tracking processor - Single Responsibility: Track work sessions.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Set
from ..core.base import Processor
from ..core.config import get_config


class SessionProcessor(Processor):
    """Tracks work sessions to avoid repeated warnings."""
    
    def __init__(self):
        self.config = get_config()
        self.session_file = self.config.data_dir / 'work_sessions.json'
        self.session_duration = timedelta(hours=self.config.session_duration_hours)
        self.sessions = self._load_sessions()
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process session tracking."""
        tool_name = data.get('tool_name', '')
        tool_input = data.get('tool_input', {})
        
        # Track file modifications
        if tool_name in ['Write', 'Edit', 'MultiEdit']:
            file_path = tool_input.get('file_path', '')
            if file_path:
                self.add_file_to_session(file_path)
                data['in_session'] = self.is_file_in_session(file_path)
        
        # Track directory operations
        elif tool_name == 'Bash':
            command = tool_input.get('command', '')
            if 'mkdir' in command:
                # Extract directory from command
                import re
                match = re.search(r'mkdir\s+(?:-[pm]\s+)?([^\s;|&]+)', command)
                if match:
                    dir_path = match.group(1).strip('"\'')
                    self.add_directory_to_session(dir_path)
                    data['in_session'] = self.is_directory_in_session(dir_path)
        
        return data
    
    def is_file_in_session(self, file_path: str) -> bool:
        """Check if file has been modified in current session."""
        self._clean_old_sessions()
        
        for session_id, session_data in self.sessions.items():
            if self._is_session_valid(session_data):
                if file_path in session_data.get('files', []):
                    return True
        return False
    
    def is_directory_in_session(self, dir_path: str) -> bool:
        """Check if directory has been created in current session."""
        self._clean_old_sessions()
        
        for session_id, session_data in self.sessions.items():
            if self._is_session_valid(session_data):
                if dir_path in session_data.get('directories', []):
                    return True
        return False
    
    def add_file_to_session(self, file_path: str):
        """Add file to current session."""
        session = self._get_or_create_session()
        if 'files' not in session:
            session['files'] = []
        if file_path not in session['files']:
            session['files'].append(file_path)
        self._save_sessions()
    
    def add_directory_to_session(self, dir_path: str):
        """Add directory to current session."""
        session = self._get_or_create_session()
        if 'directories' not in session:
            session['directories'] = []
        if dir_path not in session['directories']:
            session['directories'].append(dir_path)
        self._save_sessions()
    
    def _get_or_create_session(self) -> Dict[str, Any]:
        """Get current session or create new one."""
        # Find valid current session
        for session_id, session_data in self.sessions.items():
            if self._is_session_valid(session_data):
                return session_data
        
        # Create new session
        session_id = datetime.now().isoformat()
        self.sessions[session_id] = {
            'created_at': session_id,
            'files': [],
            'directories': []
        }
        return self.sessions[session_id]
    
    def _is_session_valid(self, session_data: Dict[str, Any]) -> bool:
        """Check if session is still valid."""
        try:
            created_at = datetime.fromisoformat(session_data['created_at'])
            return datetime.now() - created_at < self.session_duration
        except Exception:
            return False
    
    def _clean_old_sessions(self):
        """Remove expired sessions."""
        to_remove = []
        for session_id, session_data in self.sessions.items():
            if not self._is_session_valid(session_data):
                to_remove.append(session_id)
        
        for session_id in to_remove:
            del self.sessions[session_id]
        
        if to_remove:
            self._save_sessions()
    
    def _load_sessions(self) -> Dict[str, Any]:
        """Load sessions from file."""
        if not self.session_file.exists():
            return {}
        
        try:
            with open(self.session_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_sessions(self):
        """Save sessions to file."""
        try:
            with open(self.session_file, 'w') as f:
                json.dump(self.sessions, f, indent=2)
        except Exception:
            pass