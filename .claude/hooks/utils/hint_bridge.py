#!/usr/bin/env python3
"""
Hint Bridge - Stores hints from post_tool_use to display in next pre_tool_use.

Since post_tool_use output might not be visible, this bridge allows
hints to be stored and displayed on the next tool invocation.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

class HintBridge:
    """Bridge to pass hints between post and pre tool hooks."""
    
    def __init__(self):
        self.hint_file = Path.cwd() / '.claude' / 'hooks' / 'data' / 'pending_hints.json'
        self.hint_file.parent.mkdir(parents=True, exist_ok=True)
    
    def store_hint(self, hint_message: str, tool_name: str, action: str = None):
        """Store a hint to be displayed on next tool use."""
        hint_data = {
            'message': hint_message,
            'from_tool': tool_name,
            'from_action': action,
            'created_at': datetime.now().isoformat(),
            'displayed': False
        }
        
        # Load existing hints
        hints = self._load_hints()
        
        # Add new hint
        hints.append(hint_data)
        
        # Keep only recent hints (last 10)
        hints = hints[-10:]
        
        # Save hints
        with open(self.hint_file, 'w') as f:
            json.dump(hints, f, indent=2)
    
    def get_pending_hints(self) -> Optional[str]:
        """Get all pending hints and mark them as displayed."""
        hints = self._load_hints()
        
        # Filter undisplayed hints from last 5 minutes
        pending = []
        cutoff_time = datetime.now() - timedelta(minutes=5)
        
        for hint in hints:
            created_at = datetime.fromisoformat(hint['created_at'])
            if not hint['displayed'] and created_at > cutoff_time:
                pending.append(hint)
                hint['displayed'] = True
        
        if not pending:
            return None
        
        # Save updated hints (marked as displayed)
        with open(self.hint_file, 'w') as f:
            json.dump(hints, f, indent=2)
        
        # Format pending hints for display
        if len(pending) == 1:
            return pending[0]['message']
        else:
            # Combine multiple hints
            combined = "<system-reminder>\n📌 PENDING REMINDERS FROM PREVIOUS ACTIONS:\n"
            for hint in pending:
                # Extract just the content without the wrapper
                msg = hint['message']
                if '<system-reminder>' in msg:
                    msg = msg.replace('<system-reminder>', '').replace('</system-reminder>', '').strip()
                combined += f"\n{msg}\n"
            combined += "</system-reminder>"
            return combined
    
    def _load_hints(self) -> list:
        """Load hints from file."""
        if not self.hint_file.exists():
            return []
        
        try:
            with open(self.hint_file, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def clear_old_hints(self):
        """Clear hints older than 10 minutes."""
        hints = self._load_hints()
        cutoff_time = datetime.now() - timedelta(minutes=10)
        
        # Keep only recent hints
        recent_hints = []
        for hint in hints:
            created_at = datetime.fromisoformat(hint['created_at'])
            if created_at > cutoff_time:
                recent_hints.append(hint)
        
        # Save filtered hints
        with open(self.hint_file, 'w') as f:
            json.dump(recent_hints, f, indent=2)


# Singleton instance
_bridge = HintBridge()

def store_hint(hint_message: str, tool_name: str, action: str = None):
    """Store a hint for next tool use."""
    _bridge.store_hint(hint_message, tool_name, action)

def get_pending_hints() -> Optional[str]:
    """Get pending hints to display."""
    return _bridge.get_pending_hints()

def clear_old_hints():
    """Clear old hints."""
    _bridge.clear_old_hints()