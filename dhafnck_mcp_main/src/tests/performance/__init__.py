"""
Performance Testing Suite for Session Hook Auto-Injection System

This package contains comprehensive performance validation tests for the MCP HTTP client,
session hooks, and auto-injection system implemented in Phase 1.

Key Performance Metrics:
- 40% improvement in task completion rate
- <100 tokens per injection
- Response times and cache performance
- Authentication reliability
- Fallback strategy effectiveness

Test Categories:
- Unit: Individual component performance
- Integration: Cross-component integration testing
- E2E: End-to-end workflow validation
- Benchmarks: Performance metrics collection
- Mocks: Controlled testing environment

Architecture Reference: mcp-auto-injection-architecture.md
Task ID: 91c86fd9-7f74-400e-8720-7f12f799daa3
"""

import logging
import os
from pathlib import Path

# Configure performance testing logger
def setup_performance_logger():
    """Setup performance testing logger with detailed metrics output."""
    logger = logging.getLogger('performance_tests')
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # File handler for detailed logs
        log_dir = Path(__file__).parent.parent.parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_dir / "performance_tests.log")
        file_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger

# Performance test configuration
PERFORMANCE_CONFIG = {
    "target_improvement": 0.40,  # 40% improvement target
    "max_tokens_per_injection": 100,
    "response_time_targets": {
        "mcp_query": 0.5,  # 500ms max for MCP queries
        "token_refresh": 1.0,  # 1s max for token refresh
        "cache_hit": 0.01,  # 10ms max for cache hits
        "full_injection": 2.0  # 2s max for full auto-injection
    },
    "cache_hit_rate_target": 0.80,  # 80% cache hit rate
    "test_iterations": 100,  # Number of iterations for statistical significance
    "concurrent_sessions": 10,  # Concurrent session testing
}

__all__ = [
    'setup_performance_logger',
    'PERFORMANCE_CONFIG'
]