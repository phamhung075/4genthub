"""ServerCapabilities Value Object"""

from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass(frozen=True)
class ServerCapabilities:
    """Immutable value object representing server capabilities"""
    
    core_features: List[str]
    available_actions: Dict[str, List[str]]
    authentication_enabled: bool
    mvp_mode: bool
    version: str
    
    def __post_init__(self):
        """Validate server capabilities"""
        if not self.core_features:
            raise ValueError("Core features cannot be empty")
        
        if not self.available_actions:
            raise ValueError("Available actions cannot be empty")
        
        if not self.version:
            raise ValueError("Version cannot be empty")
    
    def get_total_actions_count(self) -> int:
        """Get total number of available actions"""
        return sum(len(actions) for actions in self.available_actions.values())
    
    def has_feature(self, feature: str) -> bool:
        """Check if server has a specific feature"""
        return feature in self.core_features
    
    def has_action_category(self, category: str) -> bool:
        """Check if server supports a specific action category"""
        return category in self.available_actions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "success": True,
            "core_features": self.core_features,
            "available_actions": self.available_actions,
            "authentication_enabled": self.authentication_enabled,
            "mvp_mode": self.mvp_mode,
            "version": self.version,
            "total_actions": self.get_total_actions_count()
        } 