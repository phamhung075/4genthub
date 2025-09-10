#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///

import json
import os
import sys
from pathlib import Path

# Import the AI_DATA path loader
sys.path.insert(0, str(Path(__file__).parent))
from utils.env_loader import get_ai_data_path

def main():
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)
        
        # Get AI_DATA path from environment
        log_dir = get_ai_data_path()
        log_path = log_dir / 'post_tool_use.json'
        
        # Read existing log data or initialize empty list
        if log_path.exists():
            with open(log_path, 'r') as f:
                try:
                    log_data = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    log_data = []
        else:
            log_data = []
        
        # Append new data
        log_data.append(input_data)
        
        # Write back to file with formatting
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        sys.exit(0)
        
    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Exit cleanly on any other error
        sys.exit(0)

if __name__ == '__main__':
    main()