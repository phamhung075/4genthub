"""
Description Loader Utility for Connection Management

This module provides utilities to load connection management tool descriptions from separate files,
enabling clean separation between documentation and controller logic.
Follows the same architecture pattern as task management.
"""

import importlib.util
from typing import Dict, Any, Optional
from pathlib import Path
import fnmatch

class ConnectionDescriptionLoader:
    """
    Utility class for loading connection management tool descriptions from separate files.
    Supports recursive/nested directory traversal for scalable tool documentation loading.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize the connection description loader.
        
        Args:
            base_path: Base path for description files. If None, uses current directory.
        """
        if base_path is None:
            self.base_path = Path(__file__).parent
        else:
            self.base_path = Path(base_path)
    
    def _load_module(self, file_path: Path):
        spec = importlib.util.spec_from_file_location("desc_module", file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module from {file_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _extract_descriptions(self, module) -> Dict[str, Any]:
        result = {}
        for attr in dir(module):
            if attr.endswith("_DESCRIPTION"):
                key = attr.lower().replace("_description", "")
                result.setdefault(key, {})["description"] = getattr(module, attr)
            elif attr.endswith("_PARAMETERS"):
                key = attr.lower().replace("_parameters", "")
                result.setdefault(key, {})["parameters"] = getattr(module, attr)
        return result

    def _recursive_scan(self, directory: Path) -> Dict[str, Any]:
        result = {}
        for entry in directory.iterdir():
            if entry.is_dir():
                nested = self._recursive_scan(entry)
                if nested:
                    result[entry.name] = nested
            elif fnmatch.fnmatch(entry.name, "*_description.py"):
                try:
                    module = self._load_module(entry)
                    descs = self._extract_descriptions(module)
                    for k, v in descs.items():
                        result[k] = v
                except Exception as e:
                    print(f"Warning: Could not load {entry}: {e}")
        return result

    def get_all_descriptions(self) -> Dict[str, Any]:
        """
        Recursively load all tool descriptions and parameters from the base path.
        Returns a nested dictionary reflecting the directory structure.
        """
        return self._recursive_scan(self.base_path)

    def get_connection_management_descriptions(self) -> Dict[str, Any]:
        """Get connection management tool descriptions"""
        all_desc = self.get_all_descriptions()
        # Extract connection management descriptions
        flat = {}
        for key in ("manage_connection",):
            for sub in all_desc.values():
                if isinstance(sub, dict) and key in sub:
                    flat[key] = sub[key]
        return flat

# Global instance for easy access
connection_description_loader = ConnectionDescriptionLoader()