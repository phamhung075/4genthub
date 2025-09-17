"""
Performance Metrics Collection System

Comprehensive metrics collection for monitoring performance benchmarks,
system health, and optimization effectiveness in real-time and batch modes.
"""

import time
import json
import logging
import asyncio
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
import threading
import psutil
import gc
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric measurement point."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    category: str = "general"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "category": self.category
        }
    
    def to_prometheus_format(self) -> str:
        """Convert to Prometheus metrics format."""
        tags_str = ",".join([f'{k}="{v}"' for k, v in self.tags.items()]) if self.tags else ""
        tags_part = f"{{{tags_str}}}" if tags_str else ""
        return f"{self.name}{tags_part} {self.value} {int(self.timestamp.timestamp() * 1000)}"


@dataclass
class MetricSummary:
    """Statistical summary of metrics."""
    name: str
    count: int
    min_value: float
    max_value: float
    avg_value: float
    p50_value: float
    p95_value: float
    p99_value: float
    sum_value: float
    std_dev: float
    unit: str
    time_range_start: datetime
    time_range_end: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class MetricsCollector:
    """Collects, aggregates and exports performance metrics."""
    
    def __init__(self, 
                 buffer_size: int = 10000,
                 flush_interval_seconds: int = 60,
                 output_directory: Optional[Path] = None):
        """Initialize metrics collector."""
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval_seconds
        self.output_directory = output_directory or Path("/tmp/metrics")
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        # Thread-safe metric storage
        self._metrics_buffer = deque(maxlen=buffer_size)
        self._buffer_lock = threading.RLock()
        
        # Aggregated metrics storage
        self._aggregated_metrics = defaultdict(list)
        self._aggregation_lock = threading.RLock()
        
        # Background tasks
        self._flush_task = None
        self._monitoring_task = None
        self._system_metrics_task = None
        self._running = False
        
        # Performance tracking
        self._start_time = time.time()
        self._metric_counts = defaultdict(int)
        
        # Executors for async operations
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="metrics")
    
    def start_collection(self):
        """Start background metric collection and processing."""
        if self._running:
            return
        
        self._running = True
        self._start_time = time.time()
        
        # Start background tasks
        self._flush_task = asyncio.create_task(self._periodic_flush())
        self._system_metrics_task = asyncio.create_task(self._collect_system_metrics())
        
        logger.info(f"Metrics collection started with {self.buffer_size} buffer size")
    
    async def stop_collection(self):
        """Stop collection and flush remaining metrics."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel background tasks
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
        if self._system_metrics_task and not self._system_metrics_task.done():
            self._system_metrics_task.cancel()
        
        # Final flush
        await self.flush_metrics()
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
        
        logger.info("Metrics collection stopped")
    
    def record_metric(self, 
                     name: str, 
                     value: float, 
                     unit: str = "count",
                     tags: Optional[Dict[str, str]] = None,
                     category: str = "general") -> None:
        """Record a single metric point."""
        metric = MetricPoint(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(timezone.utc),
            tags=tags or {},
            category=category
        )
        
        with self._buffer_lock:
            self._metrics_buffer.append(metric)
            self._metric_counts[name] += 1
        
        # Trigger flush if buffer is full
        if len(self._metrics_buffer) >= self.buffer_size * 0.9:
            asyncio.create_task(self.flush_metrics())
    
    def record_timing_metric(self, 
                           name: str, 
                           start_time: float, 
                           end_time: Optional[float] = None,
                           tags: Optional[Dict[str, str]] = None) -> None:
        """Record timing metric from start/end times."""
        if end_time is None:
            end_time = time.perf_counter()
        
        duration = (end_time - start_time) * 1000  # Convert to milliseconds
        self.record_metric(
            name=name,
            value=duration,
            unit="ms",
            tags=tags,
            category="timing"
        )
    
    def record_size_metric(self,
                          name: str,
                          size_bytes: int,
                          tags: Optional[Dict[str, str]] = None) -> None:
        """Record size metric in bytes."""
        self.record_metric(
            name=name,
            value=float(size_bytes),
            unit="bytes",
            tags=tags,
            category="size"
        )
    
    def record_percentage_metric(self,
                               name: str,
                               percentage: float,
                               tags: Optional[Dict[str, str]] = None) -> None:
        """Record percentage metric (0-100)."""
        self.record_metric(
            name=name,
            value=percentage,
            unit="percent",
            tags=tags,
            category="percentage"
        )
    
    def record_rate_metric(self,
                          name: str,
                          rate: float,
                          tags: Optional[Dict[str, str]] = None) -> None:
        """Record rate metric (operations per second)."""
        self.record_metric(
            name=name,
            value=rate,
            unit="ops/sec",
            tags=tags,
            category="rate"
        )
    
    async def flush_metrics(self) -> int:
        """Flush buffered metrics to storage."""
        if not self._metrics_buffer:
            return 0
        
        # Copy and clear buffer atomically
        with self._buffer_lock:
            metrics_to_flush = list(self._metrics_buffer)
            self._metrics_buffer.clear()
        
        if not metrics_to_flush:
            return 0
        
        # Process metrics in background
        await self._process_metrics_batch(metrics_to_flush)
        
        logger.debug(f"Flushed {len(metrics_to_flush)} metrics")
        return len(metrics_to_flush)
    
    async def _process_metrics_batch(self, metrics: List[MetricPoint]) -> None:
        """Process a batch of metrics."""
        # Aggregate metrics by name
        with self._aggregation_lock:
            for metric in metrics:
                self._aggregated_metrics[metric.name].append(metric)
        
        # Save to file
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = self.output_directory / f"metrics_batch_{timestamp}.json"
        
        def write_metrics():
            with open(filename, 'w') as f:
                json.dump([metric.to_dict() for metric in metrics], f, indent=2, default=str)
        
        # Write in background thread
        await asyncio.get_event_loop().run_in_executor(self._executor, write_metrics)
    
    async def _periodic_flush(self):
        """Periodically flush metrics buffer."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                if self._running:
                    await self.flush_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics."""
        while self._running:
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                self.record_percentage_metric("system_cpu_usage", cpu_percent, {"source": "system"})
                
                # Memory metrics
                memory = psutil.virtual_memory()
                self.record_percentage_metric("system_memory_usage", memory.percent, {"source": "system"})
                self.record_size_metric("system_memory_available", memory.available, {"source": "system"})
                
                # Process metrics
                process = psutil.Process()
                process_memory = process.memory_info()
                self.record_size_metric("process_memory_rss", process_memory.rss, {"source": "process"})
                self.record_size_metric("process_memory_vms", process_memory.vms, {"source": "process"})
                
                # Disk I/O metrics
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    self.record_rate_metric("system_disk_read_rate", disk_io.read_bytes, {"source": "system"})
                    self.record_rate_metric("system_disk_write_rate", disk_io.write_bytes, {"source": "system"})
                
                await asyncio.sleep(10)  # Collect every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(10)
    
    def get_metric_summary(self, 
                          metric_name: str, 
                          time_window_hours: Optional[float] = None) -> Optional[MetricSummary]:
        """Get statistical summary for a metric."""
        with self._aggregation_lock:
            if metric_name not in self._aggregated_metrics:
                return None
            
            metrics = self._aggregated_metrics[metric_name]
            
            # Filter by time window if specified
            if time_window_hours:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
                metrics = [m for m in metrics if m.timestamp >= cutoff_time]
            
            if not metrics:
                return None
            
            values = [m.value for m in metrics]
            
            # Calculate statistics
            return MetricSummary(
                name=metric_name,
                count=len(values),
                min_value=min(values),
                max_value=max(values),
                avg_value=statistics.mean(values),
                p50_value=statistics.median(values),
                p95_value=statistics.quantiles(values, n=20)[18] if len(values) > 1 else values[0],
                p99_value=statistics.quantiles(values, n=100)[98] if len(values) > 2 else values[0],
                sum_value=sum(values),
                std_dev=statistics.stdev(values) if len(values) > 1 else 0.0,
                unit=metrics[0].unit,
                time_range_start=min(m.timestamp for m in metrics),
                time_range_end=max(m.timestamp for m in metrics)
            )
    
    def get_all_metric_names(self) -> List[str]:
        """Get list of all collected metric names."""
        with self._aggregation_lock:
            return list(self._aggregated_metrics.keys())
    
    def export_prometheus_metrics(self, output_file: Optional[Path] = None) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        with self._aggregation_lock:
            for metric_name, metrics_list in self._aggregated_metrics.items():
                # Get latest metric for each tag combination
                latest_metrics = {}
                for metric in metrics_list:
                    tag_key = json.dumps(sorted(metric.tags.items()))
                    if tag_key not in latest_metrics or metric.timestamp > latest_metrics[tag_key].timestamp:
                        latest_metrics[tag_key] = metric
                
                # Add to prometheus output
                for metric in latest_metrics.values():
                    lines.append(metric.to_prometheus_format())
        
        prometheus_content = "\n".join(lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(prometheus_content)
        
        return prometheus_content
    
    def generate_performance_report(self, time_window_hours: float = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        report = {
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "time_window_hours": time_window_hours,
            "metric_summaries": {},
            "system_health": {},
            "performance_targets": {}
        }
        
        # Get summaries for all metrics
        for metric_name in self.get_all_metric_names():
            summary = self.get_metric_summary(metric_name, time_window_hours)
            if summary:
                report["metric_summaries"][metric_name] = summary.to_dict()
        
        # System health indicators
        cpu_summary = self.get_metric_summary("system_cpu_usage", 1)  # Last hour
        memory_summary = self.get_metric_summary("system_memory_usage", 1)
        
        if cpu_summary:
            report["system_health"]["cpu_usage"] = {
                "avg_percent": cpu_summary.avg_value,
                "max_percent": cpu_summary.max_value,
                "status": "healthy" if cpu_summary.avg_value < 80 else "warning" if cpu_summary.avg_value < 95 else "critical"
            }
        
        if memory_summary:
            report["system_health"]["memory_usage"] = {
                "avg_percent": memory_summary.avg_value,
                "max_percent": memory_summary.max_value,
                "status": "healthy" if memory_summary.avg_value < 80 else "warning" if memory_summary.avg_value < 95 else "critical"
            }
        
        # Performance target analysis
        response_time_summary = self.get_metric_summary("mcp_response_time", time_window_hours)
        if response_time_summary:
            report["performance_targets"]["response_time"] = {
                "avg_ms": response_time_summary.avg_value,
                "p95_ms": response_time_summary.p95_value,
                "target_met": response_time_summary.p95_value <= 200,  # 200ms target
                "target_ms": 200
            }
        
        # Collection statistics
        total_metrics = sum(self._metric_counts.values())
        uptime_hours = (time.time() - self._start_time) / 3600
        
        report["collection_stats"] = {
            "total_metrics_collected": total_metrics,
            "metrics_per_hour": total_metrics / uptime_hours if uptime_hours > 0 else 0,
            "unique_metric_names": len(self._metric_counts),
            "uptime_hours": uptime_hours,
            "buffer_utilization": len(self._metrics_buffer) / self.buffer_size
        }
        
        return report
    
    def clear_old_metrics(self, hours_to_keep: float = 24) -> int:
        """Clear metrics older than specified hours."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_to_keep)
        removed_count = 0
        
        with self._aggregation_lock:
            for metric_name in list(self._aggregated_metrics.keys()):
                original_count = len(self._aggregated_metrics[metric_name])
                self._aggregated_metrics[metric_name] = [
                    m for m in self._aggregated_metrics[metric_name]
                    if m.timestamp >= cutoff_time
                ]
                removed_count += original_count - len(self._aggregated_metrics[metric_name])
                
                # Remove empty metric lists
                if not self._aggregated_metrics[metric_name]:
                    del self._aggregated_metrics[metric_name]
        
        if removed_count > 0:
            logger.info(f"Removed {removed_count} old metrics")
        
        return removed_count


# Context manager for timing measurements
class TimingContext:
    """Context manager for measuring execution time."""
    
    def __init__(self, collector: MetricsCollector, metric_name: str, tags: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.metric_name = metric_name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            self.collector.record_timing_metric(
                self.metric_name,
                self.start_time,
                tags=self.tags
            )


# Global metrics collector instance
_global_collector: Optional[MetricsCollector] = None


def get_global_collector() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector


def record_metric(name: str, value: float, unit: str = "count", tags: Optional[Dict[str, str]] = None):
    """Record metric using global collector."""
    get_global_collector().record_metric(name, value, unit, tags)


def timing_context(name: str, tags: Optional[Dict[str, str]] = None) -> TimingContext:
    """Create timing context using global collector."""
    return TimingContext(get_global_collector(), name, tags)


async def start_global_collection():
    """Start global metrics collection."""
    collector = get_global_collector()
    collector.start_collection()


async def stop_global_collection():
    """Stop global metrics collection."""
    global _global_collector
    if _global_collector:
        await _global_collector.stop_collection()
        _global_collector = None