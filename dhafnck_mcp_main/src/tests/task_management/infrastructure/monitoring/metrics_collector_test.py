"""Tests for MetricsCollector - Performance metrics collection system

Tests the comprehensive metrics collection system for monitoring performance,
system health, and optimization effectiveness in real-time and batch modes.
"""

import pytest
import asyncio
import json
import time
import tempfile
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor

from fastmcp.task_management.infrastructure.monitoring.metrics_collector import (
    MetricsCollector,
    MetricPoint,
    MetricSummary,
    TimingContext,
    get_global_collector,
    record_metric,
    timing_context,
    start_global_collection,
    stop_global_collection
)


class TestMetricPoint:
    """Test suite for MetricPoint dataclass"""

    def test_metric_point_creation(self):
        """Test basic metric point creation"""
        timestamp = datetime.utcnow()
        metric = MetricPoint(
            name="test_metric",
            value=42.5,
            unit="ms",
            timestamp=timestamp,
            tags={"service": "test", "version": "1.0"},
            category="timing"
        )
        
        assert metric.name == "test_metric"
        assert metric.value == 42.5
        assert metric.unit == "ms"
        assert metric.timestamp == timestamp
        assert metric.tags["service"] == "test"
        assert metric.category == "timing"

    def test_metric_point_to_dict(self):
        """Test metric point dictionary conversion"""
        timestamp = datetime.utcnow()
        metric = MetricPoint(
            name="test_metric",
            value=100.0,
            unit="count",
            timestamp=timestamp,
            tags={"env": "test"},
            category="counter"
        )
        
        result = metric.to_dict()
        
        assert result["name"] == "test_metric"
        assert result["value"] == 100.0
        assert result["unit"] == "count"
        assert result["timestamp"] == timestamp.isoformat()
        assert result["tags"]["env"] == "test"
        assert result["category"] == "counter"

    def test_metric_point_to_prometheus_format(self):
        """Test conversion to Prometheus format"""
        timestamp = datetime.utcnow()
        metric = MetricPoint(
            name="http_requests_total",
            value=1234.0,
            unit="count",
            timestamp=timestamp,
            tags={"method": "GET", "status": "200"},
            category="counter"
        )
        
        result = metric.to_prometheus_format()
        
        expected_timestamp = int(timestamp.timestamp() * 1000)
        assert "http_requests_total" in result
        assert "1234.0" in result
        assert str(expected_timestamp) in result
        assert 'method="GET"' in result
        assert 'status="200"' in result

    def test_metric_point_prometheus_format_no_tags(self):
        """Test Prometheus format without tags"""
        timestamp = datetime.utcnow()
        metric = MetricPoint(
            name="simple_metric",
            value=5.0,
            unit="count",
            timestamp=timestamp
        )
        
        result = metric.to_prometheus_format()
        
        assert result.startswith("simple_metric 5.0")
        assert "{" not in result  # No tag brackets

    def test_metric_point_default_values(self):
        """Test metric point with default values"""
        timestamp = datetime.utcnow()
        metric = MetricPoint(
            name="test",
            value=1.0,
            unit="count",
            timestamp=timestamp
        )
        
        assert metric.tags == {}
        assert metric.category == "general"


class TestMetricSummary:
    """Test suite for MetricSummary dataclass"""

    def test_metric_summary_creation(self):
        """Test metric summary creation"""
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()
        
        summary = MetricSummary(
            name="response_time",
            count=100,
            min_value=10.0,
            max_value=500.0,
            avg_value=120.5,
            p50_value=115.0,
            p95_value=200.0,
            p99_value=450.0,
            sum_value=12050.0,
            std_dev=85.2,
            unit="ms",
            time_range_start=start_time,
            time_range_end=end_time
        )
        
        assert summary.name == "response_time"
        assert summary.count == 100
        assert summary.min_value == 10.0
        assert summary.max_value == 500.0
        assert summary.avg_value == 120.5
        assert summary.unit == "ms"

    def test_metric_summary_to_dict(self):
        """Test metric summary dictionary conversion"""
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()
        
        summary = MetricSummary(
            name="test_metric",
            count=50,
            min_value=1.0,
            max_value=100.0,
            avg_value=50.0,
            p50_value=45.0,
            p95_value=90.0,
            p99_value=98.0,
            sum_value=2500.0,
            std_dev=25.0,
            unit="count",
            time_range_start=start_time,
            time_range_end=end_time
        )
        
        result = summary.to_dict()
        
        assert result["name"] == "test_metric"
        assert result["count"] == 50
        assert result["avg_value"] == 50.0
        assert result["unit"] == "count"
        assert "time_range_start" in result
        assert "time_range_end" in result


class TestMetricsCollector:
    """Test suite for MetricsCollector functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.collector = MetricsCollector(
            buffer_size=100,
            flush_interval_seconds=1,
            output_directory=self.temp_dir
        )

    def teardown_method(self):
        """Clean up test fixtures"""
        # Ensure collector is stopped
        if hasattr(self.collector, '_running') and self.collector._running:
            asyncio.run(self.collector.stop_collection())

    def test_collector_initialization(self):
        """Test collector initialization"""
        assert self.collector.buffer_size == 100
        assert self.collector.flush_interval == 1
        assert self.collector.output_directory == self.temp_dir
        assert not self.collector._running
        assert len(self.collector._metrics_buffer) == 0

    def test_record_basic_metric(self):
        """Test recording a basic metric"""
        self.collector.record_metric("test_counter", 42.0, "count", {"env": "test"}, "counter")
        
        assert len(self.collector._metrics_buffer) == 1
        metric = self.collector._metrics_buffer[0]
        assert metric.name == "test_counter"
        assert metric.value == 42.0
        assert metric.unit == "count"
        assert metric.tags["env"] == "test"
        assert metric.category == "counter"

    def test_record_timing_metric(self):
        """Test recording timing metrics"""
        start_time = time.perf_counter()
        time.sleep(0.01)  # 10ms delay
        
        self.collector.record_timing_metric("operation_time", start_time, tags={"operation": "test"})
        
        assert len(self.collector._metrics_buffer) == 1
        metric = self.collector._metrics_buffer[0]
        assert metric.name == "operation_time"
        assert metric.value >= 10  # At least 10ms
        assert metric.unit == "ms"
        assert metric.category == "timing"

    def test_record_timing_metric_auto_end_time(self):
        """Test timing metric with automatic end time"""
        start_time = time.perf_counter()
        time.sleep(0.005)  # 5ms delay
        
        self.collector.record_timing_metric("auto_timing", start_time)
        
        metric = self.collector._metrics_buffer[0]
        assert metric.value >= 5  # At least 5ms

    def test_record_size_metric(self):
        """Test recording size metrics"""
        self.collector.record_size_metric("payload_size", 1024, {"type": "request"})
        
        metric = self.collector._metrics_buffer[0]
        assert metric.name == "payload_size"
        assert metric.value == 1024.0
        assert metric.unit == "bytes"
        assert metric.category == "size"

    def test_record_percentage_metric(self):
        """Test recording percentage metrics"""
        self.collector.record_percentage_metric("cpu_usage", 85.5, {"host": "server1"})
        
        metric = self.collector._metrics_buffer[0]
        assert metric.name == "cpu_usage"
        assert metric.value == 85.5
        assert metric.unit == "percent"
        assert metric.category == "percentage"

    def test_record_rate_metric(self):
        """Test recording rate metrics"""
        self.collector.record_rate_metric("requests_per_sec", 150.2, {"service": "api"})
        
        metric = self.collector._metrics_buffer[0]
        assert metric.name == "requests_per_sec"
        assert metric.value == 150.2
        assert metric.unit == "ops/sec"
        assert metric.category == "rate"

    @pytest.mark.asyncio
    async def test_flush_metrics_empty_buffer(self):
        """Test flushing empty metrics buffer"""
        result = await self.collector.flush_metrics()
        assert result == 0

    @pytest.mark.asyncio
    async def test_flush_metrics_with_data(self):
        """Test flushing metrics with data"""
        # Add some metrics
        self.collector.record_metric("test1", 1.0)
        self.collector.record_metric("test2", 2.0)
        
        result = await self.collector.flush_metrics()
        assert result == 2
        assert len(self.collector._metrics_buffer) == 0

    @pytest.mark.asyncio
    async def test_start_stop_collection(self):
        """Test starting and stopping collection"""
        assert not self.collector._running
        
        # Start collection
        self.collector.start_collection()
        assert self.collector._running
        
        # Stop collection
        await self.collector.stop_collection()
        assert not self.collector._running

    @pytest.mark.asyncio
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.Process')
    @patch('psutil.disk_io_counters')
    async def test_system_metrics_collection(self, mock_disk, mock_process, mock_memory, mock_cpu):
        """Test system metrics collection"""
        # Mock system data
        mock_cpu.return_value = 75.5
        
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 60.2
        mock_memory_obj.available = 4096 * 1024 * 1024
        mock_memory.return_value = mock_memory_obj
        
        mock_process_obj = Mock()
        mock_process_memory = Mock()
        mock_process_memory.rss = 256 * 1024 * 1024
        mock_process_memory.vms = 512 * 1024 * 1024
        mock_process_obj.memory_info.return_value = mock_process_memory
        mock_process.return_value = mock_process_obj
        
        mock_disk_obj = Mock()
        mock_disk_obj.read_bytes = 1024 * 1024
        mock_disk_obj.write_bytes = 512 * 1024
        mock_disk.return_value = mock_disk_obj
        
        # Start collection briefly
        collector = MetricsCollector(buffer_size=1000, flush_interval_seconds=60)
        collector.start_collection()
        
        # Wait for system metrics to be collected
        await asyncio.sleep(0.1)
        
        # Stop collection
        await collector.stop_collection()
        
        # Check if system metrics were recorded
        metrics = list(collector._metrics_buffer)
        system_metrics = [m for m in metrics if m.tags.get("source") in ["system", "process"]]
        assert len(system_metrics) > 0

    def test_get_metric_summary_nonexistent(self):
        """Test getting summary for non-existent metric"""
        result = self.collector.get_metric_summary("nonexistent_metric")
        assert result is None

    def test_get_metric_summary_with_data(self):
        """Test getting summary with actual data"""
        # Add test metrics
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for i, value in enumerate(values):
            self.collector.record_metric(f"test_metric", value, "ms")
        
        # Flush to aggregated storage
        asyncio.run(self.collector.flush_metrics())
        
        summary = self.collector.get_metric_summary("test_metric")
        
        assert summary is not None
        assert summary.count == 5
        assert summary.min_value == 10.0
        assert summary.max_value == 50.0
        assert summary.avg_value == 30.0
        assert summary.p50_value == 30.0
        assert summary.unit == "ms"

    def test_get_metric_summary_with_time_window(self):
        """Test getting summary with time window filter"""
        # Add old metric (simulate by manually adding to aggregated metrics)
        old_metric = MetricPoint(
            name="test_metric",
            value=100.0,
            unit="count",
            timestamp=datetime.utcnow() - timedelta(hours=25)  # 25 hours ago
        )
        
        recent_metric = MetricPoint(
            name="test_metric", 
            value=200.0,
            unit="count",
            timestamp=datetime.utcnow()
        )
        
        self.collector._aggregated_metrics["test_metric"] = [old_metric, recent_metric]
        
        # Get summary with 24-hour window
        summary = self.collector.get_metric_summary("test_metric", time_window_hours=24)
        
        assert summary is not None
        assert summary.count == 1  # Only recent metric should be included
        assert summary.avg_value == 200.0

    def test_get_all_metric_names(self):
        """Test getting all metric names"""
        # Add some metrics and flush
        self.collector.record_metric("metric_a", 1.0)
        self.collector.record_metric("metric_b", 2.0)
        self.collector.record_metric("metric_c", 3.0)
        
        asyncio.run(self.collector.flush_metrics())
        
        names = self.collector.get_all_metric_names()
        assert "metric_a" in names
        assert "metric_b" in names
        assert "metric_c" in names

    def test_export_prometheus_metrics(self):
        """Test exporting metrics in Prometheus format"""
        # Add test metrics and flush
        self.collector.record_metric("http_requests", 100, "count", {"method": "GET"})
        self.collector.record_metric("http_requests", 50, "count", {"method": "POST"})
        asyncio.run(self.collector.flush_metrics())
        
        prometheus_output = self.collector.export_prometheus_metrics()
        
        assert "http_requests" in prometheus_output
        assert 'method="GET"' in prometheus_output
        assert 'method="POST"' in prometheus_output

    def test_export_prometheus_to_file(self):
        """Test exporting Prometheus metrics to file"""
        self.collector.record_metric("test_metric", 42.0)
        asyncio.run(self.collector.flush_metrics())
        
        output_file = self.temp_dir / "prometheus_metrics.txt"
        result = self.collector.export_prometheus_metrics(output_file)
        
        assert output_file.exists()
        content = output_file.read_text()
        assert "test_metric" in content
        assert content == result

    def test_generate_performance_report(self):
        """Test generating comprehensive performance report"""
        # Add various metrics
        self.collector.record_percentage_metric("system_cpu_usage", 65.0, {"source": "system"})
        self.collector.record_percentage_metric("system_memory_usage", 70.0, {"source": "system"})
        self.collector.record_timing_metric("mcp_response_time", 0, 0.15)  # 150ms
        
        asyncio.run(self.collector.flush_metrics())
        
        report = self.collector.generate_performance_report(24)
        
        assert "report_timestamp" in report
        assert "time_window_hours" in report
        assert "metric_summaries" in report
        assert "system_health" in report
        assert "performance_targets" in report
        assert "collection_stats" in report

    def test_clear_old_metrics(self):
        """Test clearing old metrics"""
        # Add old and new metrics
        old_metric = MetricPoint(
            name="old_metric",
            value=1.0,
            unit="count", 
            timestamp=datetime.utcnow() - timedelta(hours=25)
        )
        
        new_metric = MetricPoint(
            name="new_metric",
            value=2.0,
            unit="count",
            timestamp=datetime.utcnow()
        )
        
        self.collector._aggregated_metrics["old_metric"] = [old_metric]
        self.collector._aggregated_metrics["new_metric"] = [new_metric]
        
        removed_count = self.collector.clear_old_metrics(24)
        
        assert removed_count == 1
        assert "old_metric" not in self.collector._aggregated_metrics
        assert "new_metric" in self.collector._aggregated_metrics

    def test_buffer_full_triggers_flush(self):
        """Test that buffer full triggers automatic flush"""
        # Create small buffer collector
        small_collector = MetricsCollector(buffer_size=5)
        
        # Fill buffer beyond 90%
        for i in range(5):
            small_collector.record_metric(f"metric_{i}", float(i))
        
        # Buffer should trigger flush (mocked async task creation)
        with patch('asyncio.create_task') as mock_create_task:
            small_collector.record_metric("trigger_metric", 999.0)
            mock_create_task.assert_called()

    def test_metric_counts_tracking(self):
        """Test that metric counts are properly tracked"""
        self.collector.record_metric("counter_a", 1.0)
        self.collector.record_metric("counter_a", 2.0)
        self.collector.record_metric("counter_b", 3.0)
        
        assert self.collector._metric_counts["counter_a"] == 2
        assert self.collector._metric_counts["counter_b"] == 1


class TestTimingContext:
    """Test suite for TimingContext context manager"""

    def test_timing_context_basic_usage(self):
        """Test basic timing context usage"""
        collector = MetricsCollector()
        
        with TimingContext(collector, "test_operation", {"service": "test"}):
            time.sleep(0.01)  # 10ms delay
        
        assert len(collector._metrics_buffer) == 1
        metric = collector._metrics_buffer[0]
        assert metric.name == "test_operation"
        assert metric.value >= 10  # At least 10ms
        assert metric.unit == "ms"
        assert metric.tags["service"] == "test"

    def test_timing_context_with_exception(self):
        """Test timing context handles exceptions properly"""
        collector = MetricsCollector()
        
        try:
            with TimingContext(collector, "failing_operation"):
                time.sleep(0.005)
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Should still record timing even with exception
        assert len(collector._metrics_buffer) == 1
        metric = collector._metrics_buffer[0]
        assert metric.name == "failing_operation"
        assert metric.value >= 5  # At least 5ms

    def test_timing_context_no_tags(self):
        """Test timing context without tags"""
        collector = MetricsCollector()
        
        with TimingContext(collector, "simple_operation"):
            time.sleep(0.001)
        
        metric = collector._metrics_buffer[0]
        assert metric.name == "simple_operation"
        assert metric.tags == {}


class TestGlobalCollectorFunctions:
    """Test suite for global collector functions"""

    def setup_method(self):
        """Set up test fixtures"""
        # Reset global collector
        import fastmcp.task_management.infrastructure.monitoring.metrics_collector as module
        module._global_collector = None

    def teardown_method(self):
        """Clean up test fixtures"""
        # Clean up global collector
        import fastmcp.task_management.infrastructure.monitoring.metrics_collector as module
        if module._global_collector:
            asyncio.run(module._global_collector.stop_collection())
            module._global_collector = None

    def test_get_global_collector(self):
        """Test getting global collector instance"""
        collector1 = get_global_collector()
        collector2 = get_global_collector()
        
        assert collector1 is not None
        assert collector1 is collector2  # Should be same instance

    def test_record_metric_global(self):
        """Test recording metric using global function"""
        record_metric("global_test", 42.0, "count", {"global": "true"})
        
        collector = get_global_collector()
        assert len(collector._metrics_buffer) == 1
        
        metric = collector._metrics_buffer[0]
        assert metric.name == "global_test"
        assert metric.value == 42.0
        assert metric.tags["global"] == "true"

    def test_timing_context_global(self):
        """Test timing context using global function"""
        with timing_context("global_timing", {"test": "true"}):
            time.sleep(0.005)
        
        collector = get_global_collector()
        assert len(collector._metrics_buffer) == 1
        
        metric = collector._metrics_buffer[0]
        assert metric.name == "global_timing"
        assert metric.value >= 5

    @pytest.mark.asyncio
    async def test_start_stop_global_collection(self):
        """Test starting and stopping global collection"""
        await start_global_collection()
        
        collector = get_global_collector()
        assert collector._running
        
        await stop_global_collection()
        # Global collector should be reset to None after stop
        
        import fastmcp.task_management.infrastructure.monitoring.metrics_collector as module
        assert module._global_collector is None

    @pytest.mark.asyncio
    async def test_stop_global_collection_no_collector(self):
        """Test stopping global collection when no collector exists"""
        # Should not raise exception
        await stop_global_collection()


class TestStatisticalCalculations:
    """Test suite for statistical calculations in metric summaries"""

    def test_percentile_calculations(self):
        """Test percentile calculations in metric summaries"""
        collector = MetricsCollector()
        
        # Add metrics with known distribution
        values = list(range(1, 101))  # 1 to 100
        for value in values:
            collector.record_metric("percentile_test", float(value), "count")
        
        asyncio.run(collector.flush_metrics())
        summary = collector.get_metric_summary("percentile_test")
        
        assert summary.count == 100
        assert summary.min_value == 1.0
        assert summary.max_value == 100.0
        assert summary.avg_value == 50.5
        assert summary.p50_value == 50.5  # Median
        assert summary.p95_value >= 95.0  # 95th percentile
        assert summary.p99_value >= 99.0  # 99th percentile

    def test_single_value_statistics(self):
        """Test statistics with single value"""
        collector = MetricsCollector()
        collector.record_metric("single_test", 42.0, "count")
        
        asyncio.run(collector.flush_metrics())
        summary = collector.get_metric_summary("single_test")
        
        assert summary.count == 1
        assert summary.min_value == 42.0
        assert summary.max_value == 42.0
        assert summary.avg_value == 42.0
        assert summary.p50_value == 42.0
        assert summary.p95_value == 42.0
        assert summary.p99_value == 42.0
        assert summary.std_dev == 0.0

    def test_two_value_statistics(self):
        """Test statistics with two values"""
        collector = MetricsCollector()
        collector.record_metric("two_test", 10.0, "count")
        collector.record_metric("two_test", 20.0, "count")
        
        asyncio.run(collector.flush_metrics())
        summary = collector.get_metric_summary("two_test")
        
        assert summary.count == 2
        assert summary.min_value == 10.0
        assert summary.max_value == 20.0
        assert summary.avg_value == 15.0
        assert summary.p50_value == 15.0  # Median of 10, 20
        assert summary.std_dev > 0  # Should have standard deviation


class TestErrorHandling:
    """Test suite for error handling scenarios"""

    def test_invalid_metric_values(self):
        """Test handling of invalid metric values"""
        collector = MetricsCollector()
        
        # Should handle without crashing
        collector.record_metric("test", float('inf'), "count")
        collector.record_metric("test", float('nan'), "count")
        
        # Buffer should still contain metrics
        assert len(collector._metrics_buffer) == 2

    @pytest.mark.asyncio
    async def test_file_write_error_handling(self):
        """Test handling of file write errors during flush"""
        # Create collector with invalid output directory
        invalid_path = Path("/invalid/path/that/does/not/exist")
        collector = MetricsCollector(output_directory=invalid_path)
        
        collector.record_metric("test", 1.0, "count")
        
        # Should handle file write errors gracefully
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            try:
                await collector.flush_metrics()
                # Should not raise exception, just log error
            except Exception as e:
                pytest.fail(f"Flush should handle file errors gracefully: {e}")

    @pytest.mark.asyncio
    async def test_system_metrics_collection_error(self):
        """Test handling of system metrics collection errors"""
        collector = MetricsCollector()
        
        with patch('psutil.cpu_percent', side_effect=Exception("System error")):
            # Start collection
            collector.start_collection()
            
            # Wait briefly for system metrics task to run
            await asyncio.sleep(0.1)
            
            # Stop collection
            await collector.stop_collection()
            
            # Should not crash, just log error

    def test_empty_metrics_list_statistics(self):
        """Test statistics calculation with empty metrics list"""
        collector = MetricsCollector()
        
        # Add and then filter out all metrics with time window
        collector._aggregated_metrics["test"] = []
        
        summary = collector.get_metric_summary("test")
        assert summary is None