"""
Hint storage processor - Single Responsibility: Store and retrieve hints.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..core.base import Processor
from ..core.config import get_config


class HintStorageProcessor(Processor):
    """Handles hint storage and retrieval between hook executions."""
    
    def __init__(self):
        self.config = get_config()
        self.storage_file = self.config.data_dir / 'pending_hints.json'
        self.relevance_minutes = self.config.mcp_hint_relevance_minutes
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data - store or retrieve hints as needed."""
        # This processor is called differently for pre and post hooks
        if 'store_hint' in data:
            self.store_hint(
                data['store_hint']['message'],
                data['store_hint']['tool_name'],
                data['store_hint'].get('action')
            )
        
        if 'retrieve_hints' in data:
            data['pending_hints'] = self.get_pending_hints()
        
        return data
    
    def store_hint(self, message: str, tool_name: str, action: str = None):
        """Store a hint for later display."""
        hints = self._load_hints()
        
        # Format message for display
        formatted_message = f"<system-reminder>\n{message}\n</system-reminder>"
        
        hint_data = {
            'message': formatted_message,
            'from_tool': tool_name,
            'from_action': action,
            'created_at': datetime.now().isoformat(),
            'displayed': False
        }
        
        hints.append(hint_data)
        
        # Clean old hints
        hints = self._clean_old_hints(hints)
        
        # Save
        self._save_hints(hints)
    
    def get_pending_hints(self) -> Optional[str]:
        """Get pending hints to display."""
        hints = self._load_hints()
        
        if not hints:
            return None
        
        # Find undisplayed hints
        pending = []
        for hint in hints:
            if not hint.get('displayed', False):
                pending.append(hint['message'])
                hint['displayed'] = True
        
        if not pending:
            return None
        
        # Save updated hints with displayed status
        self._save_hints(hints)
        
        # Return combined messages
        return '\n'.join(pending)
    
    def _load_hints(self) -> List[Dict[str, Any]]:
        """Load hints from storage."""
        if not self.storage_file.exists():
            return []
        
        try:
            with open(self.storage_file, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    
    def _save_hints(self, hints: List[Dict[str, Any]]):
        """Save hints to storage."""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(hints, f, indent=2)
        except Exception:
            pass
    
    def _clean_old_hints(self, hints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove hints older than relevance window."""
        cutoff = datetime.now() - timedelta(minutes=self.relevance_minutes * 2)
        
        cleaned = []
        for hint in hints:
            try:
                created = datetime.fromisoformat(hint['created_at'])
                if created > cutoff:
                    cleaned.append(hint)
            except Exception:
                # Keep hints with invalid timestamps
                cleaned.append(hint)
        
        return cleaned