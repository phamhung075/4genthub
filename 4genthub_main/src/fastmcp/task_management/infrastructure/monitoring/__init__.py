"""Monitoring Infrastructure Package"""

# Import our optimization metrics components
try:
    from .optimization_metrics import OptimizationMetricsCollector, get_global_optimization_collector
    from .metrics_collector import MetricsCollector, MetricPoint, MetricSummary
    from .metrics_integration import MetricsCollectionService, get_metrics_service, initialize_metrics_system
    OPTIMIZATION_METRICS_AVAILABLE = True
except ImportError as e:
    # Gracefully handle missing dependencies
    OPTIMIZATION_METRICS_AVAILABLE = False
    print(f"Warning: Optimization metrics not available: {e}")

# Import process monitor if dependencies are available
try:
    from .process_monitor import ProcessMonitor
    PROCESS_MONITOR_AVAILABLE = True
except ImportError:
    PROCESS_MONITOR_AVAILABLE = False
    ProcessMonitor = None

# Dynamic exports based on what's available
__all__ = ["OPTIMIZATION_METRICS_AVAILABLE"]

if OPTIMIZATION_METRICS_AVAILABLE:
    __all__.extend([
        "OptimizationMetricsCollector",
        "get_global_optimization_collector", 
        "MetricsCollector",
        "MetricPoint",
        "MetricSummary",
        "MetricsCollectionService",
        "get_metrics_service",
        "initialize_metrics_system"
    ])

if PROCESS_MONITOR_AVAILABLE:
    __all__.append("ProcessMonitor")