"""Metrics Dashboard for MCP Response Optimization

This module provides a comprehensive metrics dashboard for monitoring
and visualizing the performance of the MCP optimization system.
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"         # Monotonically increasing
    GAUGE = "gauge"            # Point-in-time value
    HISTOGRAM = "histogram"     # Distribution of values
    TIMER = "timer"            # Duration measurements


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "tags": self.tags
        }


@dataclass
class Metric:
    """Metric definition and data"""
    name: str
    metric_type: MetricType
    description: str
    unit: str
    data_points: List[MetricPoint] = field(default_factory=list)
    
    def add_point(self, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Add a data point"""
        self.data_points.append(MetricPoint(
            timestamp=datetime.now(),
            value=value,
            tags=tags or {}
        ))
    
    def get_latest(self) -> Optional[float]:
        """Get latest value"""
        if self.data_points:
            return self.data_points[-1].value
        return None
    
    def get_average(self, duration_minutes: int = 60) -> Optional[float]:
        """Get average over duration"""
        cutoff = datetime.now() - timedelta(minutes=duration_minutes)
        recent_points = [
            point.value for point in self.data_points
            if point.timestamp > cutoff
        ]
        
        if recent_points:
            return sum(recent_points) / len(recent_points)
        return None


class MetricsDashboard:
    """Comprehensive metrics dashboard"""
    
    def __init__(self, retention_hours: int = 24):
        """
        Initialize metrics dashboard
        
        Args:
            retention_hours: How long to retain metric data
        """
        self.retention_hours = retention_hours
        self.metrics: Dict[str, Metric] = {}
        self.alerts: List[Dict[str, Any]] = []
        
        # Initialize standard metrics
        self._initialize_standard_metrics()
        
        # Performance tracking
        self._performance_windows = {
            "1m": deque(maxlen=60),    # 1 minute of second-by-second data
            "1h": deque(maxlen=60),    # 1 hour of minute-by-minute data
            "24h": deque(maxlen=24),   # 24 hours of hourly data
        }
        
        self._last_cleanup = datetime.now()
    
    def _initialize_standard_metrics(self) -> None:
        """Initialize standard optimization metrics"""
        # Response optimization metrics
        self.register_metric(
            "response_optimization_count",
            MetricType.COUNTER,
            "Total number of response optimizations",
            "count"
        )
        
        self.register_metric(
            "response_compression_ratio",
            MetricType.HISTOGRAM,
            "Response compression ratio percentage",
            "percent"
        )
        
        self.register_metric(
            "response_processing_time",
            MetricType.TIMER,
            "Time to process response optimization",
            "milliseconds"
        )
        
        # Context optimization metrics
        self.register_metric(
            "context_field_reduction",
            MetricType.HISTOGRAM,
            "Context field reduction percentage",
            "percent"
        )
        
        self.register_metric(
            "template_cache_hit_rate",
            MetricType.GAUGE,
            "Template cache hit rate",
            "percent"
        )
        
        # Cache metrics
        self.register_metric(
            "cache_hit_rate",
            MetricType.GAUGE,
            "Overall cache hit rate",
            "percent"
        )
        
        self.register_metric(
            "cache_size",
            MetricType.GAUGE,
            "Current cache size",
            "bytes"
        )
        
        self.register_metric(
            "cache_evictions",
            MetricType.COUNTER,
            "Number of cache evictions",
            "count"
        )
        
        # Performance metrics
        self.register_metric(
            "api_response_time",
            MetricType.TIMER,
            "API response time",
            "milliseconds"
        )
        
        self.register_metric(
            "memory_usage",
            MetricType.GAUGE,
            "Memory usage",
            "megabytes"
        )
        
        # Error metrics
        self.register_metric(
            "optimization_errors",
            MetricType.COUNTER,
            "Number of optimization errors",
            "count"
        )
    
    def register_metric(
        self,
        name: str,
        metric_type: MetricType,
        description: str,
        unit: str
    ) -> None:
        """Register a new metric"""
        self.metrics[name] = Metric(
            name=name,
            metric_type=metric_type,
            description=description,
            unit=unit
        )
    
    def record_metric(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a metric value"""
        if name not in self.metrics:
            logger.warning(f"Metric {name} not registered")
            return
        
        self.metrics[name].add_point(value, tags)
        
        # Update performance windows
        self._update_performance_windows(name, value)
        
        # Check for alerts
        self._check_alerts(name, value)
        
        # Cleanup old data periodically
        self._periodic_cleanup()
    
    def increment_counter(
        self,
        name: str,
        increment: float = 1.0,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter metric"""
        if name in self.metrics and self.metrics[name].metric_type == MetricType.COUNTER:
            current = self.metrics[name].get_latest() or 0
            self.record_metric(name, current + increment, tags)
    
    def set_gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge metric value"""
        if name in self.metrics and self.metrics[name].metric_type == MetricType.GAUGE:
            self.record_metric(name, value, tags)
    
    def record_timer(
        self,
        name: str,
        duration_ms: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a timer metric"""
        if name in self.metrics and self.metrics[name].metric_type == MetricType.TIMER:
            self.record_metric(name, duration_ms, tags)
    
    def record_histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a histogram metric"""
        if name in self.metrics and self.metrics[name].metric_type == MetricType.HISTOGRAM:
            self.record_metric(name, value, tags)
    
    def get_metric_summary(
        self,
        name: str,
        duration_minutes: int = 60
    ) -> Optional[Dict[str, Any]]:
        """Get metric summary"""
        if name not in self.metrics:
            return None
        
        metric = self.metrics[name]
        cutoff = datetime.now() - timedelta(minutes=duration_minutes)
        
        recent_points = [
            point for point in metric.data_points
            if point.timestamp > cutoff
        ]
        
        if not recent_points:
            return {
                "name": name,
                "type": metric.metric_type.value,
                "description": metric.description,
                "unit": metric.unit,
                "no_data": True
            }
        
        values = [point.value for point in recent_points]
        
        summary = {
            "name": name,
            "type": metric.metric_type.value,
            "description": metric.description,
            "unit": metric.unit,
            "data_points": len(recent_points),
            "duration_minutes": duration_minutes,
            "latest_value": values[-1],
            "first_timestamp": recent_points[0].timestamp.isoformat(),
            "last_timestamp": recent_points[-1].timestamp.isoformat()
        }
        
        if metric.metric_type in [MetricType.GAUGE, MetricType.HISTOGRAM, MetricType.TIMER]:
            summary.update({
                "min_value": min(values),
                "max_value": max(values),
                "avg_value": sum(values) / len(values),
                "median_value": sorted(values)[len(values) // 2]
            })
            
            # Percentiles for histograms and timers
            if metric.metric_type in [MetricType.HISTOGRAM, MetricType.TIMER]:
                sorted_values = sorted(values)
                summary.update({
                    "p50": sorted_values[int(len(values) * 0.5)],
                    "p90": sorted_values[int(len(values) * 0.9)],
                    "p95": sorted_values[int(len(values) * 0.95)],
                    "p99": sorted_values[int(len(values) * 0.99)] if len(values) >= 100 else sorted_values[-1]
                })
        
        elif metric.metric_type == MetricType.COUNTER:
            # For counters, calculate rate
            if len(recent_points) >= 2:
                duration_seconds = (recent_points[-1].timestamp - recent_points[0].timestamp).total_seconds()
                if duration_seconds > 0:
                    rate = (values[-1] - values[0]) / duration_seconds
                    summary["rate_per_second"] = rate
        
        return summary
    
    def get_dashboard_data(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """Get complete dashboard data"""
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "duration_minutes": duration_minutes,
            "metrics": {},
            "summary": self._get_performance_summary(duration_minutes),
            "alerts": self.alerts[-10:],  # Last 10 alerts
            "health_status": self._get_health_status()
        }
        
        # Get all metric summaries
        for metric_name in self.metrics:
            summary = self.get_metric_summary(metric_name, duration_minutes)
            if summary:
                dashboard["metrics"][metric_name] = summary
        
        return dashboard
    
    def _get_performance_summary(self, duration_minutes: int) -> Dict[str, Any]:
        """Get performance summary"""
        summary = {
            "optimization_performance": {},
            "system_performance": {},
            "error_rates": {}
        }
        
        # Optimization metrics
        compression_summary = self.get_metric_summary("response_compression_ratio", duration_minutes)
        if compression_summary and not compression_summary.get("no_data"):
            summary["optimization_performance"]["avg_compression_ratio"] = compression_summary.get("avg_value", 0)
            summary["optimization_performance"]["p95_compression_ratio"] = compression_summary.get("p95", 0)
        
        field_reduction_summary = self.get_metric_summary("context_field_reduction", duration_minutes)
        if field_reduction_summary and not field_reduction_summary.get("no_data"):
            summary["optimization_performance"]["avg_field_reduction"] = field_reduction_summary.get("avg_value", 0)
        
        # System performance
        response_time_summary = self.get_metric_summary("api_response_time", duration_minutes)
        if response_time_summary and not response_time_summary.get("no_data"):
            summary["system_performance"]["avg_response_time_ms"] = response_time_summary.get("avg_value", 0)
            summary["system_performance"]["p95_response_time_ms"] = response_time_summary.get("p95", 0)
        
        cache_hit_summary = self.get_metric_summary("cache_hit_rate", duration_minutes)
        if cache_hit_summary and not cache_hit_summary.get("no_data"):
            summary["system_performance"]["cache_hit_rate"] = cache_hit_summary.get("latest_value", 0)
        
        # Error rates
        error_summary = self.get_metric_summary("optimization_errors", duration_minutes)
        if error_summary and not error_summary.get("no_data"):
            summary["error_rates"]["optimization_error_rate"] = error_summary.get("rate_per_second", 0)
        
        return summary
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        health = {
            "status": "healthy",
            "issues": [],
            "score": 100
        }
        
        # Check response optimization performance
        compression_avg = self.metrics["response_compression_ratio"].get_average(60)
        if compression_avg and compression_avg < 30:  # Less than 30% compression
            health["issues"].append("Low compression ratio - optimization may be underperforming")
            health["score"] -= 20
        
        # Check cache performance
        cache_hit_rate = self.metrics["cache_hit_rate"].get_latest()
        if cache_hit_rate and cache_hit_rate < 50:  # Less than 50% hit rate
            health["issues"].append("Low cache hit rate - consider cache optimization")
            health["score"] -= 15
        
        # Check response times
        response_time_avg = self.metrics["api_response_time"].get_average(15)  # Last 15 minutes
        if response_time_avg and response_time_avg > 100:  # Over 100ms average
            health["issues"].append("High response times detected")
            health["score"] -= 25
        
        # Check error rates
        error_rate = self.metrics["optimization_errors"].get_average(15)
        if error_rate and error_rate > 0:  # Any errors in last 15 minutes
            health["issues"].append("Optimization errors detected")
            health["score"] -= 30
        
        # Determine overall status
        if health["score"] >= 90:
            health["status"] = "healthy"
        elif health["score"] >= 70:
            health["status"] = "warning"
        else:
            health["status"] = "critical"
        
        return health
    
    def _update_performance_windows(self, metric_name: str, value: float) -> None:
        """Update performance windows for trending"""
        timestamp = int(time.time())
        
        # Add to 1-minute window
        self._performance_windows["1m"].append({
            "timestamp": timestamp,
            "metric": metric_name,
            "value": value
        })
    
    def _check_alerts(self, metric_name: str, value: float) -> None:
        """Check for alert conditions"""
        alert_rules = {
            "response_compression_ratio": {"min": 40, "message": "Low compression ratio"},
            "cache_hit_rate": {"min": 60, "message": "Low cache hit rate"},
            "api_response_time": {"max": 200, "message": "High response time"},
            "memory_usage": {"max": 500, "message": "High memory usage"}
        }
        
        if metric_name in alert_rules:
            rule = alert_rules[metric_name]
            
            if "min" in rule and value < rule["min"]:
                self._add_alert("warning", rule["message"], metric_name, value)
            elif "max" in rule and value > rule["max"]:
                self._add_alert("critical", rule["message"], metric_name, value)
    
    def _add_alert(self, level: str, message: str, metric_name: str, value: float) -> None:
        """Add an alert"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "metric": metric_name,
            "value": value
        }
        
        self.alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        
        logger.warning(f"Alert: {level} - {message} ({metric_name}={value})")
    
    def _periodic_cleanup(self) -> None:
        """Clean up old metric data"""
        now = datetime.now()
        
        # Only cleanup every 5 minutes
        if (now - self._last_cleanup).total_seconds() < 300:
            return
        
        cutoff = now - timedelta(hours=self.retention_hours)
        
        for metric in self.metrics.values():
            original_count = len(metric.data_points)
            metric.data_points = [
                point for point in metric.data_points
                if point.timestamp > cutoff
            ]
            
            cleaned = original_count - len(metric.data_points)
            if cleaned > 0:
                logger.debug(f"Cleaned {cleaned} old data points from {metric.name}")
        
        self._last_cleanup = now
    
    def export_metrics(
        self,
        format_type: str = "json",
        duration_minutes: int = 60
    ) -> str:
        """Export metrics in specified format"""
        dashboard_data = self.get_dashboard_data(duration_minutes)
        
        if format_type.lower() == "json":
            return json.dumps(dashboard_data, indent=2, default=str)
        elif format_type.lower() == "prometheus":
            return self._export_prometheus_format(dashboard_data)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def _export_prometheus_format(self, data: Dict[str, Any]) -> str:
        """Export in Prometheus format"""
        lines = []
        
        for metric_name, metric_data in data["metrics"].items():
            if metric_data.get("no_data"):
                continue
            
            # Add help and type
            lines.append(f"# HELP {metric_name} {metric_data['description']}")
            lines.append(f"# TYPE {metric_name} {metric_data['type']}")
            
            # Add latest value
            latest_value = metric_data.get("latest_value", 0)
            lines.append(f"{metric_name} {latest_value}")
            
            # Add additional metrics for histograms
            if metric_data["type"] in ["histogram", "timer"]:
                for percentile in ["p50", "p90", "p95", "p99"]:
                    if percentile in metric_data:
                        lines.append(f"{metric_name}_{percentile} {metric_data[percentile]}")
        
        return "\n".join(lines)
    
    def reset_metrics(self) -> None:
        """Reset all metrics data"""
        for metric in self.metrics.values():
            metric.data_points.clear()
        
        self.alerts.clear()
        self._performance_windows = {
            "1m": deque(maxlen=60),
            "1h": deque(maxlen=60),
            "24h": deque(maxlen=24),
        }
        
        logger.info("All metrics data reset")