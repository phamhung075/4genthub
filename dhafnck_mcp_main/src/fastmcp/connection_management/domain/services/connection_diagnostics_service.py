"""Connection Diagnostics Service Interface"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List

from ..entities.connection import Connection
from ..value_objects.connection_health import ConnectionHealth


class ConnectionDiagnosticsService(ABC):
    """Domain service interface for connection diagnostics operations"""
    
    @abstractmethod
    def diagnose_connection_health(self, connection: Connection) -> ConnectionHealth:
        """Perform comprehensive connection health diagnosis"""
        pass
    
    @abstractmethod
    def get_connection_statistics(self) -> Dict[str, Any]:
        """Get overall connection statistics"""
        pass
    
    @abstractmethod
    def get_reconnection_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for connection issues"""
        pass
    
    @abstractmethod
    def analyze_connection_patterns(self, connections: List[Connection]) -> Dict[str, Any]:
        """Analyze connection patterns and identify issues"""
        pass
    
    @abstractmethod
    def validate_connection_infrastructure(self) -> Dict[str, Any]:
        """Validate connection infrastructure health"""
        pass 