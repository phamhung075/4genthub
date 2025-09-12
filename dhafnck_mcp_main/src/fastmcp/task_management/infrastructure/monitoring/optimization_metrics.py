#!/usr/bin/env python3
"""
Optimization Metrics Collector

Comprehensive metrics collection system for tracking response optimization,
performance benchmarks, and AI comprehension effectiveness.
"""

import time
import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
import threading
import psutil
from concurrent.futures import ThreadPoolExecutor

from .metrics_collector import MetricsCollector, MetricPoint, MetricSummary

logger = logging.getLogger(__name__)


@dataclass
class OptimizationMetric:
    """Optimization-specific metric point with additional context."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    optimization_type: str  # MINIMAL, STANDARD, DETAILED, DEBUG
    operation: str  # response_format, context_injection, cache_operation, etc.
    original_size: Optional[int] = None
    optimized_size: Optional[int] = None
    tags: Dict[str, str] = field(default_factory=dict)
    
    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio if sizes available."""
        if self.original_size and self.optimized_size:
            return ((self.original_size - self.optimized_size) / self.original_size) * 100
        return 0.0
    
    def to_prometheus_format(self) -> str:
        """Convert to Prometheus metrics format with optimization context."""
        tags = {
            **self.tags,
            "optimization_type": self.optimization_type,
            "operation": self.operation
        }
        tags_str = ",".join([f'{k}="{v}"' for k, v in tags.items()])
        tags_part = f"{{{tags_str}}}" if tags_str else ""
        return f"{self.name}{tags_part} {self.value} {int(self.timestamp.timestamp() * 1000)}"


class OptimizationMetricsCollector(MetricsCollector):
    """Enhanced metrics collector specifically for response optimization tracking."""
    
    def __init__(self, 
                 buffer_size: int = 15000,
                 flush_interval_seconds: int = 30,
                 output_directory: Optional[Path] = None,
                 enable_prometheus: bool = True):
        """Initialize optimization metrics collector."""
        super().__init__(buffer_size, flush_interval_seconds, output_directory)
        
        self.enable_prometheus = enable_prometheus
        self.optimization_metrics = deque(maxlen=buffer_size)
        self._optimization_lock = threading.RLock()
        
        # Performance baselines for alerts
        self.performance_baselines = {
            "response_size_threshold": 10000,  # bytes
            "processing_time_threshold": 300,  # milliseconds
            "cache_hit_rate_minimum": 70,      # percent
            "compression_ratio_minimum": 30    # percent
        }
        
        # Alert tracking
        self.alerts_triggered = defaultdict(list)
        self._alert_lock = threading.RLock()
        
        # Real-time aggregation windows
        self.aggregation_windows = {
            "1m": deque(maxlen=60),    # 1-second intervals for 1 minute
            "5m": deque(maxlen=60),    # 5-second intervals for 5 minutes
            "1h": deque(maxlen=60),    # 1-minute intervals for 1 hour
            "24h": deque(maxlen=24)    # 1-hour intervals for 24 hours
        }
    
    def record_response_optimization(self,
                                   original_size: int,
                                   optimized_size: int,
                                   processing_time_ms: float,
                                   optimization_type: str,
                                   operation: str = "response_format",
                                   tags: Optional[Dict[str, str]] = None) -> None:
        """Record response optimization metrics."""
        
        compression_ratio = ((original_size - optimized_size) / original_size) * 100
        
        # Create optimization metric
        opt_metric = OptimizationMetric(
            name="response_optimization",
            value=compression_ratio,
            unit="percent",
            timestamp=datetime.now(timezone.utc),
            optimization_type=optimization_type,
            operation=operation,
            original_size=original_size,
            optimized_size=optimized_size,
            tags=tags or {}
        )
        
        with self._optimization_lock:
            self.optimization_metrics.append(opt_metric)
        
        # Record individual metrics
        self.record_size_metric("response_original_size", original_size, tags)
        self.record_size_metric("response_optimized_size", optimized_size, tags)
        self.record_percentage_metric("response_compression_ratio", compression_ratio, tags)
        self.record_timing_metric("response_processing_time", processing_time_ms / 1000, tags=tags)
        
        # Update aggregation windows
        self._update_aggregation_windows("response_optimization", compression_ratio)
        self._update_aggregation_windows("response_processing_time", processing_time_ms)
        
        # Check alert conditions
        self._check_optimization_alerts(compression_ratio, processing_time_ms, optimization_type)
        
        logger.debug(f"Response optimization recorded: {compression_ratio:.1f}% compression, "
                    f"{processing_time_ms:.1f}ms processing time")
    
    def record_context_injection_metrics(self,
                                        fields_requested: int,
                                        fields_returned: int,
                                        query_time_ms: float,
                                        cache_hit: bool,
                                        tier: str = "unknown",
                                        tags: Optional[Dict[str, str]] = None) -> None:
        """Record context injection performance metrics."""
        
        field_reduction_ratio = ((fields_requested - fields_returned) / max(fields_requested, 1)) * 100
        
        # Enhanced tags
        context_tags = {
            **(tags or {}),
            "cache_hit": str(cache_hit),
            "tier": tier
        }
        
        # Record metrics
        self.record_metric("context_fields_requested", float(fields_requested), "count", context_tags)
        self.record_metric("context_fields_returned", float(fields_returned), "count", context_tags)
        self.record_percentage_metric("context_field_reduction", field_reduction_ratio, context_tags)
        self.record_timing_metric("context_query_time", query_time_ms / 1000, tags=context_tags)
        self.record_metric("context_cache_hit", 1.0 if cache_hit else 0.0, "boolean", context_tags)
        
        # Update cache hit rate
        self._update_cache_hit_rate(cache_hit, tier)
        
        logger.debug(f"Context injection recorded: {field_reduction_ratio:.1f}% field reduction, "
                    f"{'HIT' if cache_hit else 'MISS'} cache, {query_time_ms:.1f}ms query time")
    
    def record_ai_performance_metrics(self,
                                    parse_success: bool,
                                    extraction_time_ms: float,
                                    response_format: str,
                                    agent_operation: str,
                                    error_type: Optional[str] = None,
                                    tags: Optional[Dict[str, str]] = None) -> None:
        """Record AI performance and comprehension metrics."""
        
        ai_tags = {
            **(tags or {}),
            "response_format": response_format,
            "agent_operation": agent_operation
        }
        
        if error_type:
            ai_tags["error_type"] = error_type
        
        # Record metrics
        self.record_metric("ai_parse_success", 1.0 if parse_success else 0.0, "boolean", ai_tags)
        self.record_timing_metric("ai_extraction_time", extraction_time_ms / 1000, tags=ai_tags)
        
        if not parse_success:
            self.record_metric("ai_parse_errors", 1.0, "count", ai_tags, category="errors")
        
        self.record_metric("ai_agent_operations", 1.0, "count", ai_tags, category="operations")
        
        # Update success rate tracking
        self._update_ai_success_rate(parse_success, agent_operation)
        
        logger.debug(f"AI performance recorded: {'SUCCESS' if parse_success else 'FAILED'} parse, "
                    f"{extraction_time_ms:.1f}ms extraction time")
    
    def record_system_health_metrics(self,
                                   cpu_usage: float,
                                   memory_usage: float,
                                   network_bandwidth_kbps: float,
                                   db_query_count: int,
                                   db_query_time_ms: float,
                                   tags: Optional[Dict[str, str]] = None) -> None:
        """Record system health and resource utilization metrics."""
        
        system_tags = {**(tags or {}), "source": "optimization_system"}
        
        # Record system metrics
        self.record_percentage_metric("system_cpu_usage", cpu_usage, system_tags)
        self.record_percentage_metric("system_memory_usage", memory_usage, system_tags)
        self.record_metric("system_network_bandwidth", network_bandwidth_kbps, "kbps", system_tags)
        self.record_metric("system_db_queries", float(db_query_count), "count", system_tags)
        self.record_timing_metric("system_db_query_time", db_query_time_ms / 1000, tags=system_tags)
        
        # Calculate system health score
        health_score = self._calculate_system_health_score(cpu_usage, memory_usage, db_query_time_ms)
        self.record_metric("system_health_score", health_score, "score", system_tags)
        
        logger.debug(f"System health recorded: {health_score:.1f} health score, "
                    f"{cpu_usage:.1f}% CPU, {memory_usage:.1f}% memory")
    
    def _update_aggregation_windows(self, metric_name: str, value: float) -> None:
        """Update real-time aggregation windows."""
        timestamp = int(time.time())
        
        # Update all windows
        for window_name, window in self.aggregation_windows.items():
            window.append({
                "timestamp": timestamp,
                "metric": metric_name,
                "value": value
            })
    
    def _update_cache_hit_rate(self, cache_hit: bool, tier: str) -> None:
        """Update cache hit rate tracking."""
        cache_key = f"cache_hit_rate_{tier}"
        
        # Get current hit rate or initialize
        current_hits = getattr(self, f"_cache_hits_{tier}", 0)
        current_total = getattr(self, f"_cache_total_{tier}", 0)
        
        # Update counters
        current_total += 1
        if cache_hit:
            current_hits += 1
        
        # Store updated counters
        setattr(self, f"_cache_hits_{tier}", current_hits)
        setattr(self, f"_cache_total_{tier}", current_total)
        
        # Calculate and record hit rate
        hit_rate = (current_hits / current_total) * 100
        self.record_percentage_metric(cache_key, hit_rate, {"tier": tier})
        
        # Check alert threshold
        if hit_rate < self.performance_baselines["cache_hit_rate_minimum"]:
            self._trigger_alert("cache_hit_rate_low", f"Cache hit rate for {tier} is {hit_rate:.1f}%", 
                              {"tier": tier, "hit_rate": hit_rate})
    
    def _update_ai_success_rate(self, success: bool, operation: str) -> None:
        """Update AI operation success rate tracking."""
        success_key = f"_ai_success_{operation}"
        total_key = f"_ai_total_{operation}"
        
        # Get current counters
        current_success = getattr(self, success_key, 0)
        current_total = getattr(self, total_key, 0)
        
        # Update counters
        current_total += 1
        if success:
            current_success += 1
        
        # Store updated counters
        setattr(self, success_key, current_success)
        setattr(self, total_key, current_total)
        
        # Calculate and record success rate
        success_rate = (current_success / current_total) * 100
        self.record_percentage_metric(f"ai_success_rate_{operation}", success_rate, {"operation": operation})
    
    def _calculate_system_health_score(self, cpu: float, memory: float, db_time: float) -> float:
        """Calculate overall system health score (0-100)."""
        
        # CPU score (0-30 points)
        cpu_score = max(0, 30 - (cpu / 100) * 30)
        
        # Memory score (0-30 points)
        memory_score = max(0, 30 - (memory / 100) * 30)
        
        # Database performance score (0-40 points)
        db_score = max(0, 40 - (db_time / 1000) * 20)  # Penalty for slow queries
        
        return cpu_score + memory_score + db_score
    
    def _check_optimization_alerts(self, compression_ratio: float, processing_time: float, opt_type: str) -> None:
        """Check for optimization performance alert conditions."""
        
        # Low compression ratio alert
        if compression_ratio < self.performance_baselines["compression_ratio_minimum"]:
            self._trigger_alert(
                "low_compression_ratio",
                f"Compression ratio {compression_ratio:.1f}% below minimum {self.performance_baselines['compression_ratio_minimum']}%",
                {"compression_ratio": compression_ratio, "optimization_type": opt_type}
            )
        
        # High processing time alert
        if processing_time > self.performance_baselines["processing_time_threshold"]:
            self._trigger_alert(
                "high_processing_time", 
                f"Processing time {processing_time:.1f}ms exceeds threshold {self.performance_baselines['processing_time_threshold']}ms",
                {"processing_time": processing_time, "optimization_type": opt_type}
            )
    
    def _trigger_alert(self, alert_type: str, message: str, context: Dict[str, Any]) -> None:
        """Trigger and log an alert."""
        alert = {
            "type": alert_type,
            "message": message,
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": self._get_alert_severity(alert_type)
        }
        
        with self._alert_lock:
            self.alerts_triggered[alert_type].append(alert)
            
            # Keep only last 50 alerts per type
            if len(self.alerts_triggered[alert_type]) > 50:
                self.alerts_triggered[alert_type] = self.alerts_triggered[alert_type][-50:]
        
        logger.warning(f"OPTIMIZATION ALERT [{alert['severity']}]: {message}")
    
    def _get_alert_severity(self, alert_type: str) -> str:
        """Determine alert severity level."""
        critical_alerts = ["high_processing_time", "system_health_critical"]
        warning_alerts = ["low_compression_ratio", "cache_hit_rate_low"]
        
        if alert_type in critical_alerts:
            return "critical"
        elif alert_type in warning_alerts:
            return "warning"
        else:
            return "info"
    
    def get_optimization_summary(self, time_window_hours: float = 1) -> Dict[str, Any]:
        """Get comprehensive optimization performance summary."""
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
        
        # Filter recent optimization metrics
        with self._optimization_lock:
            recent_optimizations = [
                opt for opt in self.optimization_metrics
                if opt.timestamp >= cutoff_time
            ]
        
        if not recent_optimizations:
            return {
                "time_window_hours": time_window_hours,
                "no_data": True,
                "message": "No optimization data in specified time window"
            }
        
        # Calculate optimization statistics
        compression_ratios = [opt.compression_ratio for opt in recent_optimizations]
        processing_times = [self.get_metric_summary("response_processing_time", time_window_hours)]
        
        # Profile distribution
        profile_counts = defaultdict(int)
        for opt in recent_optimizations:
            profile_counts[opt.optimization_type] += 1
        
        # Recent alerts
        with self._alert_lock:
            recent_alerts = []
            for alert_type, alerts in self.alerts_triggered.items():
                recent_alerts.extend([
                    alert for alert in alerts
                    if datetime.fromisoformat(alert["timestamp"]) >= cutoff_time
                ])
        
        return {
            "time_window_hours": time_window_hours,
            "optimization_performance": {
                "total_optimizations": len(recent_optimizations),
                "avg_compression_ratio": sum(compression_ratios) / len(compression_ratios),
                "min_compression_ratio": min(compression_ratios),
                "max_compression_ratio": max(compression_ratios),
                "profile_distribution": dict(profile_counts)
            },
            "performance_metrics": {
                "avg_processing_time_ms": self.get_metric_summary("response_processing_time", time_window_hours),
                "cache_hit_rates": {
                    tier: self.get_metric_summary(f"cache_hit_rate_{tier}", time_window_hours)
                    for tier in ["global", "project", "branch", "task"]
                },
                "ai_success_rates": {
                    op: self.get_metric_summary(f"ai_success_rate_{op}", time_window_hours)
                    for op in ["hint_extraction", "response_parsing", "task_delegation"]
                }
            },
            "system_health": {
                "health_score": self.get_metric_summary("system_health_score", time_window_hours),
                "resource_utilization": {
                    "cpu": self.get_metric_summary("system_cpu_usage", time_window_hours),
                    "memory": self.get_metric_summary("system_memory_usage", time_window_hours)
                }
            },
            "alerts": {
                "total_alerts": len(recent_alerts),
                "critical_alerts": len([a for a in recent_alerts if a["severity"] == "critical"]),
                "warning_alerts": len([a for a in recent_alerts if a["severity"] == "warning"]),
                "recent_alerts": sorted(recent_alerts, key=lambda x: x["timestamp"], reverse=True)[:10]
            },
            "recommendations": self._generate_optimization_recommendations(recent_optimizations, recent_alerts)
        }
    
    def _generate_optimization_recommendations(self, 
                                            optimizations: List[OptimizationMetric], 
                                            alerts: List[Dict]) -> List[str]:
        """Generate actionable optimization recommendations."""
        
        recommendations = []
        
        if not optimizations:
            recommendations.append("No optimization data available - enable metrics collection")
            return recommendations
        
        # Compression ratio recommendations
        avg_compression = sum(opt.compression_ratio for opt in optimizations) / len(optimizations)
        if avg_compression < 40:
            recommendations.append("Consider implementing more aggressive response optimization strategies")
        
        # Profile distribution recommendations
        profile_counts = defaultdict(int)
        for opt in optimizations:
            profile_counts[opt.optimization_type] += 1
        
        if profile_counts.get("DEBUG", 0) > profile_counts.get("MINIMAL", 0):
            recommendations.append("High DEBUG profile usage detected - consider switching to MINIMAL for better performance")
        
        # Alert-based recommendations
        critical_alerts = [a for a in alerts if a["severity"] == "critical"]
        if critical_alerts:
            recommendations.append("Critical performance issues detected - review system resources and optimization settings")
        
        # Cache recommendations
        cache_alerts = [a for a in alerts if "cache" in a["type"]]
        if cache_alerts:
            recommendations.append("Cache performance issues detected - consider increasing cache sizes or TTL values")
        
        return recommendations
    
    def export_optimization_dashboard_data(self, time_window_hours: float = 24) -> Dict[str, Any]:
        """Export data in format suitable for Grafana dashboard."""
        
        summary = self.get_optimization_summary(time_window_hours)
        
        # Create Grafana-compatible time series data
        dashboard_data = {
            "dashboard": {
                "title": "MCP Response Optimization Dashboard",
                "time": {
                    "from": f"now-{int(time_window_hours)}h",
                    "to": "now"
                },
                "panels": []
            },
            "metrics": {
                # Response optimization panel
                "response_optimization": {
                    "title": "Response Optimization Performance",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "response_compression_ratio",
                            "legendFormat": "Compression Ratio %"
                        },
                        {
                            "expr": "response_processing_time",
                            "legendFormat": "Processing Time (ms)"
                        }
                    ]
                },
                
                # Cache performance panel
                "cache_performance": {
                    "title": "Cache Hit Rates",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": f"cache_hit_rate_{tier}",
                            "legendFormat": f"{tier.title()} Cache"
                        }
                        for tier in ["global", "project", "branch", "task"]
                    ]
                },
                
                # System health panel
                "system_health": {
                    "title": "System Health Metrics",
                    "type": "gauge",
                    "targets": [
                        {
                            "expr": "system_health_score",
                            "legendFormat": "Health Score"
                        },
                        {
                            "expr": "system_cpu_usage",
                            "legendFormat": "CPU Usage %"
                        },
                        {
                            "expr": "system_memory_usage", 
                            "legendFormat": "Memory Usage %"
                        }
                    ]
                },
                
                # Alert status panel
                "alerts": {
                    "title": "Alert Status",
                    "type": "table",
                    "data": summary.get("alerts", {})
                }
            },
            "summary": summary
        }
        
        return dashboard_data
    
    async def generate_optimization_report(self, time_window_hours: float = 24) -> Dict[str, Any]:
        """Generate comprehensive optimization performance report."""
        
        summary = self.get_optimization_summary(time_window_hours)
        system_report = self.generate_performance_report(time_window_hours)
        
        report = {
            "report_metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "time_window_hours": time_window_hours,
                "report_type": "optimization_performance"
            },
            "executive_summary": {
                "total_optimizations": summary.get("optimization_performance", {}).get("total_optimizations", 0),
                "avg_compression_achieved": summary.get("optimization_performance", {}).get("avg_compression_ratio", 0),
                "system_health_status": "healthy" if summary.get("system_health", {}).get("health_score", {}).get("avg_value", 0) > 70 else "needs_attention",
                "critical_issues": summary.get("alerts", {}).get("critical_alerts", 0)
            },
            "detailed_metrics": summary,
            "system_performance": system_report,
            "recommendations": summary.get("recommendations", []),
            "next_actions": [
                "Monitor critical alerts and address root causes",
                "Optimize cache configuration if hit rates are low",
                "Consider profile adjustments based on performance patterns",
                "Review system resource allocation if health score is declining"
            ]
        }
        
        return report


# Global optimization metrics collector instance
_global_optimization_collector: Optional[OptimizationMetricsCollector] = None


def get_global_optimization_collector() -> OptimizationMetricsCollector:
    """Get or create the global optimization metrics collector."""
    global _global_optimization_collector
    if _global_optimization_collector is None:
        _global_optimization_collector = OptimizationMetricsCollector()
    return _global_optimization_collector


# Convenience functions for common optimization metrics
def record_response_optimization(original_size: int, optimized_size: int, processing_time_ms: float, 
                                optimization_type: str, **kwargs):
    """Record response optimization using global collector."""
    get_global_optimization_collector().record_response_optimization(
        original_size, optimized_size, processing_time_ms, optimization_type, **kwargs
    )


def record_context_metrics(fields_requested: int, fields_returned: int, query_time_ms: float, 
                          cache_hit: bool, **kwargs):
    """Record context injection metrics using global collector."""
    get_global_optimization_collector().record_context_injection_metrics(
        fields_requested, fields_returned, query_time_ms, cache_hit, **kwargs
    )


def record_ai_metrics(parse_success: bool, extraction_time_ms: float, response_format: str, 
                     agent_operation: str, **kwargs):
    """Record AI performance metrics using global collector."""
    get_global_optimization_collector().record_ai_performance_metrics(
        parse_success, extraction_time_ms, response_format, agent_operation, **kwargs
    )


async def start_optimization_monitoring():
    """Start global optimization metrics collection."""
    collector = get_global_optimization_collector()
    collector.start_collection()
    logger.info("Optimization metrics collection started")


async def stop_optimization_monitoring():
    """Stop global optimization metrics collection."""
    global _global_optimization_collector
    if _global_optimization_collector:
        await _global_optimization_collector.stop_collection()
        _global_optimization_collector = None
        logger.info("Optimization metrics collection stopped")