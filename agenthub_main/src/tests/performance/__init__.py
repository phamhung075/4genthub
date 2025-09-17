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

# Performance test configuration - Phase 4 Optimization Targets
PERFORMANCE_CONFIG = {
    "target_improvement": 0.40,  # 40% improvement target
    "max_tokens_per_injection": 100,
    "response_time_targets": {
        "mcp_query": 0.5,  # 500ms max for MCP queries
        "token_refresh": 1.0,  # 1s max for token refresh
        "cache_hit": 0.01,  # 10ms max for cache hits
        "full_injection": 2.0,  # 2s max for full auto-injection
        "context_injection": 0.2,  # 200ms max for context injection (from 500ms)
        "ai_processing": 0.6  # 40% faster than baseline (multiply baseline by 0.6)
    },
    "response_size_targets": {
        "min_reduction_percent": 50.0,  # Minimum 50% response size reduction
        "target_reduction_percent": 60.0,  # Target 60% response size reduction 
        "max_reduction_percent": 70.0,  # Maximum expected 70% response size reduction
        "baseline_vs_optimized": True  # Compare baseline vs optimized responses
    },
    "ai_comprehension_targets": {
        "min_accuracy_retention": 0.95,  # 95% minimum accuracy retention
        "parsing_success_rate": 0.95,  # 95% parsing success rate
        "speed_improvement": 0.40,  # 40% faster AI processing
        "essential_info_preserved": True  # Essential information must be preserved
    },
    "cache_hit_rate_target": 0.80,  # 80% cache hit rate
    "test_iterations": 100,  # Number of iterations for statistical significance
    "concurrent_sessions": 10,  # Concurrent session testing
    "load_testing": {
        "max_concurrent_requests": 50,  # Maximum concurrent requests to test
        "request_rate_per_second": 10,  # Requests per second for load testing
        "test_duration_seconds": 300,  # 5 minutes load test duration
        "memory_usage_limit_mb": 512,  # Memory usage limit during load testing
        "cpu_usage_limit_percent": 85  # CPU usage limit during load testing
    }
}

__all__ = [
    'setup_performance_logger',
    'PERFORMANCE_CONFIG'
]