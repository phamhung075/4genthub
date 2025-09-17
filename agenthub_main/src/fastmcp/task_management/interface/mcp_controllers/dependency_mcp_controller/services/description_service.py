"""Description Service for Dependency Controller"""

from typing import Dict, Any
from ....utils import description_loader


class DescriptionService:
    """Service for managing dependency descriptions"""
    
    def get_dependency_management_descriptions(self) -> Dict[str, Any]:
        """
        Flatten dependency descriptions for robust access.
        
        Returns:
            Dictionary containing dependency management descriptions
        """
        all_desc = description_loader.get_all_descriptions()
        flat = {}
        # Look for 'manage_dependency' in any subdict (e.g., all_desc['task']['manage_dependency'])
        for sub in all_desc.values():
            if isinstance(sub, dict) and "manage_dependency" in sub:
                flat["manage_dependency"] = sub["manage_dependency"]
        return flat