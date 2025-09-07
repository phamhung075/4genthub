"""Label Repository Interface for Dynamic Label Management"""

from abc import ABC, abstractmethod
from typing import List, Optional, Set
from datetime import datetime


class ILabelRepository(ABC):
    """Abstract repository interface for label management"""
    
    @abstractmethod
    async def create_label(self, label: str, category: Optional[str] = None) -> str:
        """Create a new label if it doesn't exist, return normalized label"""
        pass
    
    @abstractmethod
    async def find_label(self, label: str) -> Optional[str]:
        """Find an existing label (case-insensitive), return normalized version"""
        pass
    
    @abstractmethod
    async def get_all_labels(self) -> List[str]:
        """Get all existing labels"""
        pass
    
    @abstractmethod
    async def get_labels_by_category(self, category: str) -> List[str]:
        """Get labels by category"""
        pass
    
    @abstractmethod
    async def search_labels(self, query: str, limit: int = 10) -> List[str]:
        """Search for labels matching query"""
        pass
    
    @abstractmethod
    async def get_label_usage_count(self, label: str) -> int:
        """Get usage count for a label"""
        pass
    
    @abstractmethod
    async def delete_unused_labels(self) -> int:
        """Delete labels with zero usage, return count deleted"""
        pass
    
    @abstractmethod
    async def normalize_label(self, label: str) -> str:
        """Normalize a label to standard format"""
        pass
    
    @abstractmethod
    async def validate_and_create_labels(self, labels: List[str]) -> List[str]:
        """Validate and create multiple labels, return normalized list"""
        pass


class LabelInfo:
    """Label information entity"""
    
    def __init__(self, label: str, category: Optional[str] = None, 
                 usage_count: int = 0, created_at: Optional[datetime] = None):
        self.label = label
        self.category = category
        self.usage_count = usage_count
        self.created_at = created_at or datetime.now()
        self.normalized = self._normalize(label)
    
    def _normalize(self, label: str) -> str:
        """Normalize label to standard format"""
        # Remove extra whitespace, convert to lowercase, replace spaces with hyphens
        normalized = label.strip().lower()
        normalized = ' '.join(normalized.split())  # Remove multiple spaces
        normalized = normalized.replace(' ', '-')
        return normalized
    
    def increment_usage(self) -> None:
        """Increment usage count"""
        self.usage_count += 1
    
    def decrement_usage(self) -> None:
        """Decrement usage count"""
        if self.usage_count > 0:
            self.usage_count -= 1