"""Monitoring Service Interface - Domain Layer"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class IMetric(ABC):
    """Domain interface for metrics"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the metric name"""
        pass
    
    @property
    @abstractmethod
    def value(self) -> Union[int, float]:
        """Get the metric value"""
        pass
    
    @property
    @abstractmethod
    def timestamp(self) -> datetime:
        """Get the metric timestamp"""
        pass
    
    @property
    @abstractmethod
    def labels(self) -> Dict[str, str]:
        """Get the metric labels"""
        pass


class IProcessMonitor(ABC):
    """Domain interface for process monitoring"""
    
    @abstractmethod
    def start_monitoring(self, process_name: str) -> str:
        """Start monitoring a process"""
        pass
    
    @abstractmethod
    def stop_monitoring(self, monitor_id: str) -> bool:
        """Stop monitoring a process"""
        pass
    
    @abstractmethod
    def get_process_metrics(self, process_name: str) -> Dict[str, Any]:
        """Get metrics for a process"""
        pass
    
    @abstractmethod
    def is_process_running(self, process_name: str) -> bool:
        """Check if a process is running"""
        pass
    
    @abstractmethod
    def get_resource_usage(self, process_name: str) -> Dict[str, Union[int, float]]:
        """Get resource usage for a process"""
        pass


class IMonitoringService(ABC):
    """Domain interface for monitoring operations"""
    
    @abstractmethod
    def record_metric(self, name: str, value: Union[int, float], 
                     metric_type: MetricType = MetricType.GAUGE,
                     labels: Optional[Dict[str, str]] = None) -> None:
        """Record a metric"""
        pass
    
    @abstractmethod
    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric"""
        pass
    
    @abstractmethod
    def record_timer(self, name: str, duration: timedelta, 
                    labels: Optional[Dict[str, str]] = None) -> None:
        """Record a timer metric"""
        pass
    
    @abstractmethod
    def get_metrics(self, name_pattern: Optional[str] = None) -> List[IMetric]:
        """Get metrics by name pattern"""
        pass
    
    @abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status"""
        pass
    
    @abstractmethod
    def create_alert(self, name: str, condition: str, threshold: Union[int, float]) -> str:
        """Create a monitoring alert"""
        pass
    
    @abstractmethod
    def remove_alert(self, alert_id: str) -> bool:
        """Remove a monitoring alert"""
        pass