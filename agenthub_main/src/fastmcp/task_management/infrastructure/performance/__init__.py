"""Performance optimization module for task management

This module provides performance enhancements for task loading including:
- Query optimization
- Result caching
- Pagination improvements
- Response payload optimization
"""

from .task_performance_optimizer import TaskPerformanceOptimizer, get_performance_optimizer
from .performance_config import PerformanceConfig

__all__ = [
    'TaskPerformanceOptimizer',
    'get_performance_optimizer',
    'PerformanceConfig'
]