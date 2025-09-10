#!/usr/bin/env python3
"""Utility to load environment paths from .env file."""

import os
from pathlib import Path
from dotenv import load_dotenv

def get_ai_data_path():
    """
    Get the AI_DATA path from .env file.
    Falls back to 'logs' if not set.
    """
    # Load .env file
    load_dotenv()
    
    # Get AI_DATA from environment, default to 'logs'
    ai_data_path = os.getenv('AI_DATA', 'logs')
    
    # Convert to Path object and ensure it's absolute
    if not os.path.isabs(ai_data_path):
        ai_data_path = Path.cwd() / ai_data_path
    else:
        ai_data_path = Path(ai_data_path)
    
    # Ensure the directory exists
    ai_data_path.mkdir(parents=True, exist_ok=True)
    
    return ai_data_path

def get_ai_docs_path():
    """
    Get the AI_DOCS path from .env file.
    Falls back to 'ai_docs' if not set.
    """
    # Load .env file
    load_dotenv()
    
    # Get AI_DOCS from environment, default to 'ai_docs'
    ai_docs_path = os.getenv('AI_DOCS', 'ai_docs')
    
    # Convert to Path object and ensure it's absolute
    if not os.path.isabs(ai_docs_path):
        ai_docs_path = Path.cwd() / ai_docs_path
    else:
        ai_docs_path = Path(ai_docs_path)
    
    # Ensure the directory exists
    ai_docs_path.mkdir(parents=True, exist_ok=True)
    
    return ai_docs_path

def get_log_path():
    """
    Get the LOG_PATH from .env file.
    Falls back to 'logs' if not set.
    """
    # Load .env file
    load_dotenv()
    
    # Get LOG_PATH from environment, default to 'logs'
    log_path = os.getenv('LOG_PATH', 'logs')
    
    # Convert to Path object and ensure it's absolute
    if not os.path.isabs(log_path):
        log_path = Path.cwd() / log_path
    else:
        log_path = Path(log_path)
    
    # Ensure the directory exists
    log_path.mkdir(parents=True, exist_ok=True)
    
    return log_path

def get_all_paths():
    """
    Get all configured paths as a dictionary.
    Returns dict with 'ai_data', 'ai_docs', and 'log_path' keys.
    """
    return {
        'ai_data': get_ai_data_path(),
        'ai_docs': get_ai_docs_path(),
        'log_path': get_log_path()
    }