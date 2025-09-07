"""Feature Flag Service for DDD Migration
Provides safe migration capabilities with instant rollback support.
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class FeatureFlag:
    """Represents a feature flag configuration"""
    name: str
    enabled: bool
    description: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class FeatureFlagService:
    """Service for managing feature flags during DDD migration
    
    Provides:
    - Runtime flag modification
    - Environment-based configuration
    - Persistent flag state
    - Rollback capabilities
    - Audit logging
    """
    
    def __init__(self, config_path: Optional[str] = None, user_id: Optional[str] = None):
        """Initialize feature flag service
        
        Args:
            config_path: Path to feature flags configuration file
            user_id: User context for user-scoped feature flags
        """
        self._user_id = user_id  # Store user context
        self._config_path = config_path or self._get_default_config_path()
        self._flags: Dict[str, FeatureFlag] = {}
        self._load_flags()
        
        # Migration-specific flags
        self._initialize_migration_flags()
        
        logger.info(f"FeatureFlagService initialized with {len(self._flags)} flags")

    def _get_user_scoped_repository(self, repository: Any) -> Any:
        """Get a user-scoped version of the repository if it supports user context."""
        if not repository:
            return repository
        if hasattr(repository, 'with_user') and self._user_id:
            return repository.with_user(self._user_id)
        elif hasattr(repository, 'user_id'):
            if self._user_id and repository.user_id != self._user_id:
                repo_class = type(repository)
                if hasattr(repository, 'session'):
                    return repo_class(repository.session, user_id=self._user_id)
        return repository

    def with_user(self, user_id: str) -> 'FeatureFlagService':
        """Create a new service instance scoped to a specific user."""
        return FeatureFlagService(self._config_path, user_id)
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path"""
        return str(Path.cwd() / ".cursor" / "feature_flags.json")
    
    def _load_flags(self) -> None:
        """Load feature flags from configuration file"""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r') as f:
                    data = json.load(f)
                    
                for flag_name, flag_data in data.items():
                    self._flags[flag_name] = FeatureFlag(**flag_data)
                    
                logger.info(f"Loaded {len(self._flags)} feature flags from {self._config_path}")
            else:
                logger.info(f"No existing feature flags file found at {self._config_path}")
                
        except Exception as e:
            logger.error(f"Failed to load feature flags: {e}")
            # Continue with empty flags dict
    
    def _save_flags(self) -> None:
        """Save feature flags to configuration file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            
            # Convert flags to dict format
            data = {name: asdict(flag) for name, flag in self._flags.items()}
            
            with open(self._config_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Saved {len(self._flags)} feature flags to {self._config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save feature flags: {e}")
    
    def _initialize_migration_flags(self) -> None:
        """Initialize migration-specific feature flags"""
        migration_flags = {
            "USE_DDD_COMPLIANT_TOOLS": {
                "enabled": False,
                "description": "Master flag for DDD-compliant architecture migration"
            },
            "USE_NEW_CREATE_TASK": {
                "enabled": False,
                "description": "Use new DDD-compliant create_task implementation"
            },
            "USE_NEW_UPDATE_TASK": {
                "enabled": False,
                "description": "Use new DDD-compliant update_task implementation"
            },
            "USE_NEW_GET_TASK": {
                "enabled": False,
                "description": "Use new DDD-compliant get_task implementation"
            },
            "USE_NEW_LIST_TASKS": {
                "enabled": False,
                "description": "Use new DDD-compliant list_tasks implementation"
            },
            "USE_NEW_DELETE_TASK": {
                "enabled": False,
                "description": "Use new DDD-compliant delete_task implementation"
            },
            "USE_NEW_SEARCH_TASKS": {
                "enabled": False,
                "description": "Use new DDD-compliant search_tasks implementation"
            },
            "USE_NEW_NEXT_TASK": {
                "enabled": False,
                "description": "Use new DDD-compliant next_task implementation"
            },
            "USE_NEW_MANAGE_DEPENDENCIES": {
                "enabled": False,
                "description": "Use new DDD-compliant dependency management"
            },
            "USE_NEW_MANAGE_SUBTASKS": {
                "enabled": False,
                "description": "Use new DDD-compliant subtask management"
            },
            "ENABLE_PARALLEL_TESTING": {
                "enabled": True,
                "description": "Run parallel tests during migration"
            },
            "ENABLE_MIGRATION_LOGGING": {
                "enabled": True,
                "description": "Enhanced logging during migration"
            }
        }
        
        # Create flags that don't exist
        for flag_name, config in migration_flags.items():
            if flag_name not in self._flags:
                now = datetime.now().isoformat()
                self._flags[flag_name] = FeatureFlag(
                    name=flag_name,
                    enabled=config["enabled"],
                    description=config["description"],
                    created_at=now,
                    updated_at=now
                )
        
        # Save any new flags
        self._save_flags()
    
    def is_enabled(self, flag_name: str) -> bool:
        """Check if a feature flag is enabled
        
        Args:
            flag_name: Name of the feature flag
            
        Returns:
            True if flag is enabled, False otherwise
        """
        # Check environment variable override first
        env_var = f"FEATURE_{flag_name.upper()}"
        env_value = os.getenv(env_var)
        if env_value is not None:
            return env_value.lower() in ('true', '1', 'yes', 'on')
        
        # Check stored flag
        flag = self._flags.get(flag_name)
        if flag is None:
            logger.warning(f"Feature flag '{flag_name}' not found, defaulting to False")
            return False
            
        return flag.enabled
    
    def enable_flag(self, flag_name: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Enable a feature flag
        
        Args:
            flag_name: Name of the feature flag
            metadata: Optional metadata to store with the flag
            
        Returns:
            True if successful, False otherwise
        """
        return self._update_flag(flag_name, True, metadata)
    
    def disable_flag(self, flag_name: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Disable a feature flag
        
        Args:
            flag_name: Name of the feature flag
            metadata: Optional metadata to store with the flag
            
        Returns:
            True if successful, False otherwise
        """
        return self._update_flag(flag_name, False, metadata)
    
    def _update_flag(self, flag_name: str, enabled: bool, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update a feature flag
        
        Args:
            flag_name: Name of the feature flag
            enabled: New enabled state
            metadata: Optional metadata to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if flag_name not in self._flags:
                logger.error(f"Feature flag '{flag_name}' not found")
                return False
            
            flag = self._flags[flag_name]
            old_state = flag.enabled
            
            flag.enabled = enabled
            flag.updated_at = datetime.now().isoformat()
            
            if metadata:
                flag.metadata.update(metadata)
            
            self._save_flags()
            
            logger.info(f"Feature flag '{flag_name}' changed from {old_state} to {enabled}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update feature flag '{flag_name}': {e}")
            return False
    
    def get_flag_status(self, flag_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a feature flag
        
        Args:
            flag_name: Name of the feature flag
            
        Returns:
            Flag status dictionary or None if not found
        """
        flag = self._flags.get(flag_name)
        if flag is None:
            return None
            
        return {
            "name": flag.name,
            "enabled": flag.enabled,
            "description": flag.description,
            "created_at": flag.created_at,
            "updated_at": flag.updated_at,
            "metadata": flag.metadata,
            "environment_override": os.getenv(f"FEATURE_{flag_name.upper()}")
        }
    
    def list_flags(self) -> Dict[str, Dict[str, Any]]:
        """List all feature flags with their status
        
        Returns:
            Dictionary of flag names to their status
        """
        return {name: self.get_flag_status(name) for name in self._flags.keys()}
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get overall migration status based on feature flags
        
        Returns:
            Migration status summary
        """
        migration_flags = [
            "USE_DDD_COMPLIANT_TOOLS",
            "USE_NEW_CREATE_TASK",
            "USE_NEW_UPDATE_TASK", 
            "USE_NEW_GET_TASK",
            "USE_NEW_LIST_TASKS",
            "USE_NEW_DELETE_TASK",
            "USE_NEW_SEARCH_TASKS",
            "USE_NEW_NEXT_TASK",
            "USE_NEW_MANAGE_DEPENDENCIES",
            "USE_NEW_MANAGE_SUBTASKS"
        ]
        
        enabled_count = sum(1 for flag in migration_flags if self.is_enabled(flag))
        total_count = len(migration_flags)
        
        return {
            "migration_progress": {
                "enabled_operations": enabled_count,
                "total_operations": total_count,
                "percentage": (enabled_count / total_count) * 100
            },
            "master_flag_enabled": self.is_enabled("USE_DDD_COMPLIANT_TOOLS"),
            "parallel_testing_enabled": self.is_enabled("ENABLE_PARALLEL_TESTING"),
            "migration_logging_enabled": self.is_enabled("ENABLE_MIGRATION_LOGGING"),
            "flags_status": {flag: self.is_enabled(flag) for flag in migration_flags}
        }
    
    def enable_migration_phase(self, phase: str) -> bool:
        """Enable all flags for a specific migration phase
        
        Args:
            phase: Migration phase ('critical', 'remaining', 'all')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if phase == "critical":
                flags = ["USE_NEW_CREATE_TASK", "USE_NEW_UPDATE_TASK", "USE_NEW_GET_TASK"]
            elif phase == "remaining":
                flags = [
                    "USE_NEW_LIST_TASKS", "USE_NEW_DELETE_TASK", "USE_NEW_SEARCH_TASKS",
                    "USE_NEW_NEXT_TASK", "USE_NEW_MANAGE_DEPENDENCIES", "USE_NEW_MANAGE_SUBTASKS"
                ]
            elif phase == "all":
                flags = [
                    "USE_DDD_COMPLIANT_TOOLS", "USE_NEW_CREATE_TASK", "USE_NEW_UPDATE_TASK",
                    "USE_NEW_GET_TASK", "USE_NEW_LIST_TASKS", "USE_NEW_DELETE_TASK",
                    "USE_NEW_SEARCH_TASKS", "USE_NEW_NEXT_TASK", "USE_NEW_MANAGE_DEPENDENCIES",
                    "USE_NEW_MANAGE_SUBTASKS"
                ]
            else:
                logger.error(f"Unknown migration phase: {phase}")
                return False
            
            for flag in flags:
                self.enable_flag(flag, {"migration_phase": phase})
            
            logger.info(f"Enabled migration phase '{phase}' with {len(flags)} flags")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable migration phase '{phase}': {e}")
            return False
    
    def rollback_migration(self) -> bool:
        """Rollback all migration flags to disabled state
        
        Returns:
            True if successful, False otherwise
        """
        try:
            migration_flags = [
                "USE_DDD_COMPLIANT_TOOLS", "USE_NEW_CREATE_TASK", "USE_NEW_UPDATE_TASK",
                "USE_NEW_GET_TASK", "USE_NEW_LIST_TASKS", "USE_NEW_DELETE_TASK",
                "USE_NEW_SEARCH_TASKS", "USE_NEW_NEXT_TASK", "USE_NEW_MANAGE_DEPENDENCIES",
                "USE_NEW_MANAGE_SUBTASKS"
            ]
            
            for flag in migration_flags:
                self.disable_flag(flag, {"rollback_at": datetime.now().isoformat()})
            
            logger.warning(f"ROLLBACK: Disabled all migration flags ({len(migration_flags)} flags)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback migration: {e}")
            return False


# Global instance for easy access
_feature_flag_service: Optional[FeatureFlagService] = None


def get_feature_flag_service() -> FeatureFlagService:
    """Get the global feature flag service instance"""
    global _feature_flag_service
    if _feature_flag_service is None:
        _feature_flag_service = FeatureFlagService()
    return _feature_flag_service


def is_feature_enabled(flag_name: str) -> bool:
    """Convenience function to check if a feature flag is enabled"""
    return get_feature_flag_service().is_enabled(flag_name) 