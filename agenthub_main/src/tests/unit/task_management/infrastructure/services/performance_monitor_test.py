"""
Unit tests for Performance Monitor Infrastructure Service
Generated from performance_monitor.py analysis
Date: 2025-09-26

Tests the performance monitoring service that tracks cache system metrics,
captures snapshots, handles alerts, and exports performance data.
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from collections import deque
from pathlib import Path
import tempfile
import os
from datetime import datetime

from fastmcp.task_management.infrastructure.services.performance_monitor import (
    PerformanceMonitor,
    PerformanceSnapshot,
    CacheBenchmark,
    BenchmarkConfig,
    BenchmarkResult
)


class TestPerformanceMonitor:
    """Test suite for PerformanceMonitor infrastructure service"""
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager for testing"""
        cache_manager = Mock()
        cache_manager.get_performance_metrics.return_value = {
            "cache_statistics": {
                "hit_rate": 0.85,
                "miss_rate": 0.15
            },
            "performance_metrics": {
                "average_response_time_ms": 25.5,
                "operations_per_second": 150.0
            },
            "cache_levels": {
                "memory_size_bytes": 10485760,  # 10MB
                "memory_entries": 1000
            },
            "eviction_statistics": {
                "total_evictions": 50
            }
        }
        return cache_manager
    
    @pytest.fixture
    def monitor(self, mock_cache_manager):
        """Create performance monitor instance for testing"""
        return PerformanceMonitor(
            cache_manager=mock_cache_manager,
            monitoring_interval=0.1,  # Fast interval for tests
            history_size=100
        )
    
    def test_initialization(self, monitor):
        """Test monitor initialization with default values"""
        assert monitor.monitoring_interval == 0.1
        assert monitor.history_size == 100
        assert not monitor.monitoring_active
        assert monitor.monitor_task is None
        assert len(monitor.alert_callbacks) == 0
        assert len(monitor.performance_history) == 0
        
        # Check alert thresholds
        assert monitor.alert_thresholds["hit_rate_min"] == 0.7
        assert monitor.alert_thresholds["response_time_max_ms"] == 100.0
        assert monitor.alert_thresholds["memory_usage_max_mb"] == 1024.0
        assert monitor.alert_thresholds["error_rate_max"] == 0.05
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self, monitor):
        """Test starting performance monitoring"""
        await monitor.start_monitoring()
        
        assert monitor.monitoring_active
        assert monitor.monitor_task is not None
        assert not monitor.monitor_task.done()
        
        # Clean up
        await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_start_monitoring_already_active(self, monitor):
        """Test starting monitoring when already active"""
        await monitor.start_monitoring()
        
        # Try to start again
        with patch('logging.Logger.warning') as mock_warning:
            await monitor.start_monitoring()
            mock_warning.assert_called_once_with("Performance monitoring already active")
        
        # Clean up
        await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self, monitor):
        """Test stopping performance monitoring"""
        await monitor.start_monitoring()
        assert monitor.monitoring_active
        
        await monitor.stop_monitoring()
        
        assert not monitor.monitoring_active
        # Task should be cancelled
        if monitor.monitor_task:
            assert monitor.monitor_task.cancelled() or monitor.monitor_task.done()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring_not_active(self, monitor):
        """Test stopping monitoring when not active"""
        assert not monitor.monitoring_active
        
        # Should not raise error
        await monitor.stop_monitoring()
        
        assert not monitor.monitoring_active
    
    @pytest.mark.asyncio
    async def test_capture_snapshot(self, monitor, mock_cache_manager):
        """Test capturing performance snapshot"""
        # Capture snapshot
        await monitor._capture_snapshot()
        
        # Check snapshot was added to history
        assert len(monitor.performance_history) == 1
        
        snapshot = monitor.performance_history[0]
        assert isinstance(snapshot, PerformanceSnapshot)
        assert snapshot.hit_rate == 0.85
        assert snapshot.miss_rate == 0.15
        assert snapshot.average_response_time_ms == 25.5
        assert snapshot.operations_per_second == 150.0
        assert snapshot.memory_usage_mb == 10.0  # 10MB
        assert snapshot.cache_size == 1000
        assert snapshot.eviction_count == 50
        assert snapshot.timestamp > 0
    
    @pytest.mark.asyncio
    async def test_capture_snapshot_error(self, monitor, mock_cache_manager):
        """Test capturing snapshot with error"""
        mock_cache_manager.get_performance_metrics.side_effect = Exception("Metrics error")
        
        # Should not raise, but log error
        with patch('logging.Logger.error') as mock_error:
            await monitor._capture_snapshot()
            mock_error.assert_called_once()
        
        # No snapshot added
        assert len(monitor.performance_history) == 0
    
    @pytest.mark.asyncio
    async def test_check_alerts_low_hit_rate(self, monitor):
        """Test alert checking for low hit rate"""
        # Add snapshot with low hit rate
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            hit_rate=0.5,  # Below threshold of 0.7
            miss_rate=0.5,
            average_response_time_ms=50.0,
            operations_per_second=100.0,
            memory_usage_mb=100.0,
            cache_size=500,
            eviction_count=10
        )
        monitor.performance_history.append(snapshot)
        
        # Add alert callback
        alert_callback = AsyncMock()
        monitor.add_alert_callback(alert_callback)
        
        # Check alerts
        await monitor._check_alerts()
        
        # Alert should be triggered
        alert_callback.assert_called_once()
        alert_msg, alert_snapshot = alert_callback.call_args[0]
        assert "Low hit rate" in alert_msg
        assert alert_snapshot == snapshot
    
    @pytest.mark.asyncio
    async def test_check_alerts_high_response_time(self, monitor):
        """Test alert checking for high response time"""
        # Add snapshot with high response time
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            hit_rate=0.8,
            miss_rate=0.2,
            average_response_time_ms=150.0,  # Above threshold of 100.0
            operations_per_second=100.0,
            memory_usage_mb=100.0,
            cache_size=500,
            eviction_count=10
        )
        monitor.performance_history.append(snapshot)
        
        alert_callback = AsyncMock()
        monitor.add_alert_callback(alert_callback)
        
        await monitor._check_alerts()
        
        alert_callback.assert_called_once()
        alert_msg, _ = alert_callback.call_args[0]
        assert "High response time" in alert_msg
    
    @pytest.mark.asyncio
    async def test_check_alerts_high_memory_usage(self, monitor):
        """Test alert checking for high memory usage"""
        # Add snapshot with high memory usage
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            hit_rate=0.8,
            miss_rate=0.2,
            average_response_time_ms=50.0,
            operations_per_second=100.0,
            memory_usage_mb=2000.0,  # Above threshold of 1024.0
            cache_size=500,
            eviction_count=10
        )
        monitor.performance_history.append(snapshot)
        
        alert_callback = AsyncMock()
        monitor.add_alert_callback(alert_callback)
        
        await monitor._check_alerts()
        
        alert_callback.assert_called_once()
        alert_msg, _ = alert_callback.call_args[0]
        assert "High memory usage" in alert_msg
    
    @pytest.mark.asyncio
    async def test_check_alerts_multiple_issues(self, monitor):
        """Test alert checking with multiple issues"""
        # Add snapshot with multiple issues
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            hit_rate=0.5,  # Low
            miss_rate=0.5,
            average_response_time_ms=150.0,  # High
            operations_per_second=100.0,
            memory_usage_mb=2000.0,  # High
            cache_size=500,
            eviction_count=10
        )
        monitor.performance_history.append(snapshot)
        
        alert_callback = AsyncMock()
        monitor.add_alert_callback(alert_callback)
        
        await monitor._check_alerts()
        
        # Should be called 3 times (one for each issue)
        assert alert_callback.call_count == 3
    
    @pytest.mark.asyncio
    async def test_check_alerts_callback_error(self, monitor):
        """Test alert checking when callback fails"""
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            hit_rate=0.5,  # Low to trigger alert
            miss_rate=0.5,
            average_response_time_ms=50.0,
            operations_per_second=100.0,
            memory_usage_mb=100.0,
            cache_size=500,
            eviction_count=10
        )
        monitor.performance_history.append(snapshot)
        
        # Add failing callback
        alert_callback = AsyncMock(side_effect=Exception("Callback error"))
        monitor.add_alert_callback(alert_callback)
        
        # Should not raise
        with patch('logging.Logger.error') as mock_error:
            await monitor._check_alerts()
            mock_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitoring_loop(self, monitor, mock_cache_manager):
        """Test the monitoring loop captures snapshots periodically"""
        await monitor.start_monitoring()
        
        # Wait for a few intervals
        await asyncio.sleep(0.35)  # 3.5 intervals
        
        await monitor.stop_monitoring()
        
        # Should have captured multiple snapshots
        assert len(monitor.performance_history) >= 3
    
    def test_get_performance_summary_no_data(self, monitor):
        """Test performance summary with no data"""
        summary = monitor.get_performance_summary(time_window_minutes=60)
        
        assert "error" in summary
        assert summary["error"] == "No data available for specified time window"
    
    def test_get_performance_summary_single_snapshot(self, monitor):
        """Test performance summary with single snapshot"""
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            hit_rate=0.85,
            miss_rate=0.15,
            average_response_time_ms=25.5,
            operations_per_second=150.0,
            memory_usage_mb=100.0,
            cache_size=1000,
            eviction_count=50
        )
        monitor.performance_history.append(snapshot)
        
        summary = monitor.get_performance_summary(time_window_minutes=60)
        
        assert summary["time_window_minutes"] == 60
        assert summary["data_points"] == 1
        assert summary["averages"]["hit_rate"] == 0.85
        assert summary["averages"]["response_time_ms"] == 25.5
        assert summary["trends"]["hit_rate_change"] == 0.0  # No trend with single point
        assert summary["current"]["cache_size"] == 1000
    
    def test_get_performance_summary_multiple_snapshots(self, monitor):
        """Test performance summary with multiple snapshots"""
        # Add snapshots with changing metrics
        base_time = time.time()
        for i in range(5):
            snapshot = PerformanceSnapshot(
                timestamp=base_time + i * 60,  # 1 minute apart
                hit_rate=0.80 + i * 0.02,  # Increasing hit rate
                miss_rate=0.20 - i * 0.02,
                average_response_time_ms=30.0 - i * 2,  # Decreasing response time
                operations_per_second=100.0 + i * 10,
                memory_usage_mb=50.0 + i * 10,
                cache_size=500 + i * 100,
                eviction_count=10 + i * 5
            )
            monitor.performance_history.append(snapshot)
        
        summary = monitor.get_performance_summary(time_window_minutes=10)
        
        assert summary["data_points"] == 5
        assert abs(summary["averages"]["hit_rate"] - 0.84) < 0.0001  # Average of 0.80 to 0.88
        assert abs(summary["trends"]["hit_rate_change"] - 0.08) < 0.0001  # 0.88 - 0.80
        assert abs(summary["trends"]["response_time_change_ms"] - (-8.0)) < 0.0001  # 22 - 30
        assert summary["current"]["hit_rate"] == 0.88
    
    def test_get_performance_summary_time_window(self, monitor):
        """Test performance summary respects time window"""
        current_time = time.time()
        
        # Add old snapshot (outside window)
        old_snapshot = PerformanceSnapshot(
            timestamp=current_time - 7200,  # 2 hours ago
            hit_rate=0.50,
            miss_rate=0.50,
            average_response_time_ms=100.0,
            operations_per_second=50.0,
            memory_usage_mb=200.0,
            cache_size=100,
            eviction_count=100
        )
        monitor.performance_history.append(old_snapshot)
        
        # Add recent snapshot (inside window)
        recent_snapshot = PerformanceSnapshot(
            timestamp=current_time - 1800,  # 30 minutes ago
            hit_rate=0.90,
            miss_rate=0.10,
            average_response_time_ms=20.0,
            operations_per_second=200.0,
            memory_usage_mb=150.0,
            cache_size=2000,
            eviction_count=10
        )
        monitor.performance_history.append(recent_snapshot)
        
        # Get summary for 1 hour window
        summary = monitor.get_performance_summary(time_window_minutes=60)
        
        # Should only include recent snapshot
        assert summary["data_points"] == 1
        assert summary["averages"]["hit_rate"] == 0.90
    
    def test_export_performance_data_json(self, monitor):
        """Test exporting performance data as JSON"""
        # Add test data
        for i in range(3):
            snapshot = PerformanceSnapshot(
                timestamp=time.time() + i,
                hit_rate=0.80 + i * 0.05,
                miss_rate=0.20 - i * 0.05,
                average_response_time_ms=25.0 + i * 5,
                operations_per_second=100.0 + i * 20,
                memory_usage_mb=50.0 + i * 25,
                cache_size=1000 + i * 100,
                eviction_count=10 + i * 5
            )
            monitor.performance_history.append(snapshot)
        
        # Export to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            success = monitor.export_performance_data(temp_path, format="json")
            assert success
            
            # Read and verify exported data
            with open(temp_path) as f:
                exported_data = json.load(f)
            
            assert len(exported_data) == 3
            assert abs(exported_data[0]["hit_rate"] - 0.80) < 0.0001
            assert abs(exported_data[1]["hit_rate"] - 0.85) < 0.0001
            assert abs(exported_data[2]["hit_rate"] - 0.90) < 0.0001
            assert "datetime" in exported_data[0]
            assert exported_data[0]["cache_size"] == 1000
            
        finally:
            os.unlink(temp_path)
    
    def test_export_performance_data_unsupported_format(self, monitor):
        """Test exporting with unsupported format"""
        temp_path = Path("test.xml")
        
        success = monitor.export_performance_data(temp_path, format="xml")
        
        assert not success
    
    def test_export_performance_data_write_error(self, monitor):
        """Test export with write error"""
        # Add test data
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            hit_rate=0.85,
            miss_rate=0.15,
            average_response_time_ms=25.5,
            operations_per_second=150.0,
            memory_usage_mb=100.0,
            cache_size=1000,
            eviction_count=50
        )
        monitor.performance_history.append(snapshot)
        
        # Try to export to invalid path
        invalid_path = Path("/nonexistent/directory/file.json")
        
        with patch('logging.Logger.error') as mock_error:
            success = monitor.export_performance_data(invalid_path)
            assert not success
            mock_error.assert_called_once()
    
    def test_add_alert_callback(self, monitor):
        """Test adding alert callbacks"""
        callback1 = Mock()
        callback2 = Mock()
        
        monitor.add_alert_callback(callback1)
        monitor.add_alert_callback(callback2)
        
        assert len(monitor.alert_callbacks) == 2
        assert callback1 in monitor.alert_callbacks
        assert callback2 in monitor.alert_callbacks


class TestCacheBenchmark:
    """Test suite for CacheBenchmark class"""
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager for benchmark testing"""
        cache_manager = Mock()
        cache_manager.put = AsyncMock(return_value=True)
        cache_manager.get = AsyncMock(return_value="cached_content")
        cache_manager.invalidate = AsyncMock(return_value=True)
        cache_manager.get_performance_metrics = Mock(return_value={
            "cache_statistics": {
                "hit_rate": 0.85,
                "miss_rate": 0.15
            },
            "performance_metrics": {
                "average_response_time_ms": 25.5,
                "operations_per_second": 150.0
            },
            "cache_levels": {
                "memory_size_bytes": 10485760,  # 10MB
                "memory_entries": 1000
            },
            "eviction_statistics": {
                "total_evictions": 50
            }
        })
        return cache_manager
    
    @pytest.fixture
    def benchmark(self, mock_cache_manager):
        """Create benchmark instance"""
        return CacheBenchmark(cache_manager=mock_cache_manager)
    
    @pytest.mark.asyncio
    async def test_run_basic_benchmark(self, benchmark, mock_cache_manager):
        """Test running basic benchmark"""
        num_operations = 10  # Small number for testing
        
        result = await benchmark.run_basic_benchmark(num_operations=num_operations)
        
        assert isinstance(result, dict)
        # Basic checks - the actual implementation should return benchmark results
        assert mock_cache_manager.put.call_count > 0
        assert mock_cache_manager.get.call_count > 0


class TestBenchmarkDataClasses:
    """Test suite for benchmark data classes"""
    
    def test_benchmark_config_defaults(self):
        """Test BenchmarkConfig default values"""
        config = BenchmarkConfig()
        
        assert config.num_operations == 1000
        assert config.concurrent_operations == 10
        assert config.data_size_bytes == 1024
        assert config.test_duration_seconds == 60
        assert config.warmup_operations == 100
        assert config.include_stress_test
        assert config.include_memory_test
        assert config.include_concurrency_test
    
    def test_benchmark_result_initialization(self):
        """Test BenchmarkResult initialization"""
        config = BenchmarkConfig(num_operations=500)
        result = BenchmarkResult(
            config=config,
            start_time=time.time(),
            end_time=time.time() + 60
        )
        
        assert result.config.num_operations == 500
        assert result.total_operations == 0
        assert result.successful_operations == 0
        assert result.operations_per_second == 0.0
        assert result.average_response_time_ms == 0.0
        assert result.final_hit_rate == 0.0
        assert result.recommendations == []