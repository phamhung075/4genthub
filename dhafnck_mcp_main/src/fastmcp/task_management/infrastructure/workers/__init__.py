"""Workers Infrastructure Package"""

try:
    from .metrics_reporter import MetricsReporter, ReportConfig, get_global_metrics_reporter
    METRICS_REPORTER_AVAILABLE = True
except ImportError as e:
    METRICS_REPORTER_AVAILABLE = False
    print(f"Warning: Metrics reporter not available: {e}")

__all__ = ["METRICS_REPORTER_AVAILABLE"]

if METRICS_REPORTER_AVAILABLE:
    __all__.extend([
        "MetricsReporter",
        "ReportConfig", 
        "get_global_metrics_reporter"
    ])