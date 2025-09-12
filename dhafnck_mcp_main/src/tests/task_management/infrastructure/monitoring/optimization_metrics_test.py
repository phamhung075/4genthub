"""Tests for OptimizationMetrics - Advanced optimization metrics collection system

Tests the comprehensive optimization metrics collection system for tracking response
optimization, performance benchmarks, and AI comprehension effectiveness.
"""

import pytest
import asyncio
import time
import tempfile
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from collections import defaultdict

from fastmcp.task_management.infrastructure.monitoring.optimization_metrics import (
    OptimizationMetric,
    OptimizationMetricsCollector,
    get_global_optimization_collector,
    record_response_optimization,
    record_context_metrics,
    record_ai_metrics,
    start_optimization_monitoring,
    stop_optimization_monitoring
)


class TestOptimizationMetric:
    """Test suite for OptimizationMetric dataclass"""

    def test_optimization_metric_creation(self):
        """Test basic optimization metric creation"""
        timestamp = datetime.utcnow()
        metric = OptimizationMetric(
            name="response_optimization",
            value=75.5,
            unit="percent",
            timestamp=timestamp,
            optimization_type="STANDARD",
            operation="response_format",
            original_size=1000,
            optimized_size=300,
            tags={"service": "mcp", "version": "1.0"}
        )
        
        assert metric.name == "response_optimization"
        assert metric.value == 75.5
        assert metric.optimization_type == "STANDARD"
        assert metric.operation == "response_format"
        assert metric.original_size == 1000
        assert metric.optimized_size == 300

    def test_compression_ratio_calculation(self):
        """Test compression ratio property calculation"""
        metric = OptimizationMetric(
            name="test_metric",
            value=0.0,
            unit="percent",
            timestamp=datetime.utcnow(),
            optimization_type="MINIMAL",
            operation="test",
            original_size=1000,
            optimized_size=700
        )
        
        # (1000 - 700) / 1000 * 100 = 30%
        assert metric.compression_ratio == 30.0

    def test_compression_ratio_no_sizes(self):
        """Test compression ratio when sizes not available"""
        metric = OptimizationMetric(
            name="test_metric",
            value=0.0,
            unit="percent",
            timestamp=datetime.utcnow(),
            optimization_type="STANDARD",
            operation="test"
        )
        
        assert metric.compression_ratio == 0.0

    def test_prometheus_format_with_optimization_context(self):
        """Test Prometheus format includes optimization context"""
        timestamp = datetime.utcnow()
        metric = OptimizationMetric(
            name="response_opt",
            value=85.0,
            unit="percent",
            timestamp=timestamp,
            optimization_type="DETAILED",
            operation="api_response",
            tags={"service": "mcp"}
        )
        
        result = metric.to_prometheus_format()
        
        assert "response_opt" in result
        assert "85.0" in result
        assert 'optimization_type="DETAILED"' in result
        assert 'operation="api_response"' in result
        assert 'service="mcp"' in result


class TestOptimizationMetricsCollector:
    """Test suite for OptimizationMetricsCollector functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.collector = OptimizationMetricsCollector(
            buffer_size=1000,
            flush_interval_seconds=1,
            output_directory=self.temp_dir
        )

    def teardown_method(self):
        """Clean up test fixtures"""
        if hasattr(self.collector, '_running') and self.collector._running:
            asyncio.run(self.collector.stop_collection())

    def test_collector_initialization(self):
        """Test collector initialization with optimization features"""
        assert self.collector.buffer_size == 1000
        assert self.collector.enable_prometheus == True
        assert len(self.collector.optimization_metrics) == 0
        assert "response_size_threshold" in self.collector.performance_baselines
        assert len(self.collector.aggregation_windows) == 4

    def test_record_response_optimization(self):
        """Test recording response optimization metrics"""
        self.collector.record_response_optimization(
            original_size=2000,
            optimized_size=800,
            processing_time_ms=150.5,
            optimization_type="STANDARD",
            operation="json_response",
            tags={"api": "v1"}
        )
        
        # Check optimization metric was recorded
        assert len(self.collector.optimization_metrics) == 1
        opt_metric = self.collector.optimization_metrics[0]
        assert opt_metric.original_size == 2000
        assert opt_metric.optimized_size == 800
        assert opt_metric.compression_ratio == 60.0  # (2000-800)/2000*100
        assert opt_metric.optimization_type == "STANDARD"
        
        # Check individual metrics were recorded
        assert len(self.collector._metrics_buffer) >= 4  # At least size, compression, timing metrics

    def test_record_context_injection_metrics(self):
        """Test recording context injection performance metrics"""
        self.collector.record_context_injection_metrics(
            fields_requested=10,
            fields_returned=6,
            query_time_ms=75.2,
            cache_hit=True,
            tier="project",
            tags={"context": "task_creation"}
        )
        
        # Verify metrics were recorded
        metrics = list(self.collector._metrics_buffer)
        
        # Should have context-related metrics
        context_metrics = [m for m in metrics if "context" in m.name]
        assert len(context_metrics) >= 4
        
        # Check field reduction calculation: (10-6)/10*100 = 40%
        reduction_metrics = [m for m in metrics if "field_reduction" in m.name]
        assert len(reduction_metrics) == 1
        assert reduction_metrics[0].value == 40.0

    def test_record_ai_performance_metrics(self):
        """Test recording AI performance and comprehension metrics"""
        self.collector.record_ai_performance_metrics(
            parse_success=True,
            extraction_time_ms=45.7,
            response_format="json",
            agent_operation="task_delegation",
            tags={"agent": "coding-agent"}
        )
        
        metrics = list(self.collector._metrics_buffer)
        
        # Should record success, timing, and operation metrics
        ai_metrics = [m for m in metrics if "ai_" in m.name]
        assert len(ai_metrics) >= 2
        
        # Check success metric
        success_metrics = [m for m in metrics if "parse_success" in m.name]
        assert len(success_metrics) == 1
        assert success_metrics[0].value == 1.0  # Success

    def test_record_ai_performance_metrics_with_error(self):
        """Test recording AI metrics with parse error"""
        self.collector.record_ai_performance_metrics(
            parse_success=False,
            extraction_time_ms=25.3,
            response_format="complex_json",
            agent_operation="hint_extraction",
            error_type="JSONDecodeError",
            tags={"agent": "debugger-agent"}
        )
        
        metrics = list(self.collector._metrics_buffer)
        
        # Should record failure and error metrics
        success_metrics = [m for m in metrics if "parse_success" in m.name]
        assert len(success_metrics) == 1
        assert success_metrics[0].value == 0.0  # Failure
        
        error_metrics = [m for m in metrics if "parse_errors" in m.name]
        assert len(error_metrics) == 1
        assert error_metrics[0].value == 1.0

    def test_record_system_health_metrics(self):
        """Test recording system health and resource metrics"""
        self.collector.record_system_health_metrics(
            cpu_usage=75.5,
            memory_usage=60.2,
            network_bandwidth_kbps=1024.5,
            db_query_count=15,
            db_query_time_ms=125.7,
            tags={"environment": "production"}
        )
        
        metrics = list(self.collector._metrics_buffer)
        
        # Should record system metrics and health score
        system_metrics = [m for m in metrics if "system_" in m.name]
        assert len(system_metrics) >= 6  # CPU, memory, network, DB queries, DB time, health score
        
        # Check health score calculation
        health_metrics = [m for m in metrics if "health_score" in m.name]
        assert len(health_metrics) == 1
        health_score = health_metrics[0].value
        assert 0 <= health_score <= 100

    def test_cache_hit_rate_tracking(self):
        """Test cache hit rate tracking and alerting"""
        tier = "project"
        
        # Record several cache operations
        for i in range(10):
            cache_hit = i % 3 == 0  # 33% hit rate (below threshold)
            self.collector.record_context_injection_metrics(
                fields_requested=5,
                fields_returned=3,
                query_time_ms=50.0,
                cache_hit=cache_hit,
                tier=tier
            )
        
        # Check that hit rate was calculated and alerts triggered
        hit_rate_attr = f"_cache_hits_{tier}"
        total_attr = f"_cache_total_{tier}"
        
        assert hasattr(self.collector, hit_rate_attr)
        assert hasattr(self.collector, total_attr)
        
        hits = getattr(self.collector, hit_rate_attr)
        total = getattr(self.collector, total_attr)
        hit_rate = (hits / total) * 100
        
        assert hit_rate == 30.0  # 3 hits out of 10
        
        # Check if alert was triggered (hit rate below 70% threshold)
        assert len(self.collector.alerts_triggered) > 0
        cache_alerts = self.collector.alerts_triggered.get("cache_hit_rate_low", [])
        assert len(cache_alerts) >= 1

    def test_ai_success_rate_tracking(self):
        """Test AI operation success rate tracking"""
        operation = "response_parsing"
        
        # Record mixed success/failure operations
        success_results = [True, True, False, True, False, False, True, True]
        
        for success in success_results:
            self.collector.record_ai_performance_metrics(
                parse_success=success,
                extraction_time_ms=30.0,
                response_format="json",
                agent_operation=operation
            )
        
        # Check success rate calculation: 5 successes out of 8 = 62.5%
        success_attr = f"_ai_success_{operation}"
        total_attr = f"_ai_total_{operation}"
        
        assert hasattr(self.collector, success_attr)
        assert hasattr(self.collector, total_attr)
        
        successes = getattr(self.collector, success_attr)
        total = getattr(self.collector, total_attr)
        success_rate = (successes / total) * 100
        
        assert successes == 5
        assert total == 8
        assert success_rate == 62.5

    def test_system_health_score_calculation(self):
        """Test system health score calculation algorithm"""
        # Test perfect system (low resource usage, fast DB)
        perfect_score = self.collector._calculate_system_health_score(10.0, 20.0, 50.0)
        assert perfect_score >= 80  # Should be high score
        
        # Test stressed system (high resource usage, slow DB)
        stressed_score = self.collector._calculate_system_health_score(90.0, 95.0, 1000.0)
        assert stressed_score <= 40  # Should be low score
        
        # Test moderate system
        moderate_score = self.collector._calculate_system_health_score(50.0, 60.0, 200.0)
        assert 40 <= moderate_score <= 80  # Should be moderate score

    def test_optimization_alerts_low_compression(self):
        """Test alerts for low compression ratios"""
        # Record optimization with low compression (below 30% threshold)
        self.collector.record_response_optimization(
            original_size=1000,
            optimized_size=900,  # Only 10% compression
            processing_time_ms=100.0,
            optimization_type="MINIMAL"
        )
        
        # Should trigger low compression alert
        compression_alerts = self.collector.alerts_triggered.get("low_compression_ratio", [])
        assert len(compression_alerts) >= 1
        
        alert = compression_alerts[0]
        assert alert["type"] == "low_compression_ratio"
        assert alert["severity"] == "warning"
        assert "10.0%" in alert["message"]

    def test_optimization_alerts_high_processing_time(self):
        """Test alerts for high processing times"""
        # Record optimization with high processing time (above 300ms threshold)
        self.collector.record_response_optimization(
            original_size=1000,
            optimized_size=500,
            processing_time_ms=450.0,  # Above threshold
            optimization_type="DETAILED"
        )
        
        # Should trigger high processing time alert
        time_alerts = self.collector.alerts_triggered.get("high_processing_time", [])
        assert len(time_alerts) >= 1
        
        alert = time_alerts[0]
        assert alert["type"] == "high_processing_time"
        assert alert["severity"] == "critical"
        assert "450.0ms" in alert["message"]

    def test_alert_severity_classification(self):
        """Test alert severity classification"""
        assert self.collector._get_alert_severity("high_processing_time") == "critical"
        assert self.collector._get_alert_severity("system_health_critical") == "critical"
        assert self.collector._get_alert_severity("low_compression_ratio") == "warning"
        assert self.collector._get_alert_severity("cache_hit_rate_low") == "warning"
        assert self.collector._get_alert_severity("unknown_alert") == "info"

    def test_aggregation_windows_updates(self):
        """Test real-time aggregation windows updates"""
        initial_window_sizes = {k: len(v) for k, v in self.collector.aggregation_windows.items()}
        
        # Record some metrics
        self.collector.record_response_optimization(
            original_size=1000,
            optimized_size=600,
            processing_time_ms=150.0,
            optimization_type="STANDARD"
        )
        
        # Check that aggregation windows were updated
        for window_name, window in self.collector.aggregation_windows.items():
            if len(window) > initial_window_sizes[window_name]:
                # Found updated window
                assert len(window) > 0
                # Check structure of window entries
                if window:
                    entry = window[-1]  # Latest entry
                    assert "timestamp" in entry
                    assert "metric" in entry
                    assert "value" in entry

    def test_get_optimization_summary_no_data(self):
        """Test optimization summary when no data available"""
        summary = self.collector.get_optimization_summary(1.0)
        
        assert summary["no_data"] == True
        assert "No optimization data" in summary["message"]
        assert summary["time_window_hours"] == 1.0

    def test_get_optimization_summary_with_data(self):
        """Test optimization summary with actual data"""
        # Record some optimization metrics
        optimizations = [
            (2000, 1000, 100.0, "STANDARD"),
            (1500, 600, 150.0, "DETAILED"),
            (1000, 800, 75.0, "MINIMAL"),
            (3000, 1200, 200.0, "STANDARD")
        ]
        
        for original, optimized, time_ms, opt_type in optimizations:
            self.collector.record_response_optimization(
                original_size=original,
                optimized_size=optimized,
                processing_time_ms=time_ms,
                optimization_type=opt_type
            )
        
        summary = self.collector.get_optimization_summary(1.0)
        
        assert summary["no_data"] != True
        
        # Check optimization performance stats
        opt_perf = summary["optimization_performance"]
        assert opt_perf["total_optimizations"] == 4
        assert opt_perf["avg_compression_ratio"] > 0
        assert opt_perf["min_compression_ratio"] >= 0
        assert opt_perf["max_compression_ratio"] <= 100
        
        # Check profile distribution
        profile_dist = opt_perf["profile_distribution"]
        assert "STANDARD" in profile_dist
        assert profile_dist["STANDARD"] == 2  # Two STANDARD optimizations

    def test_optimization_recommendations_generation(self):
        """Test generation of optimization recommendations"""
        # Create scenario with poor compression
        poor_optimizations = [
            OptimizationMetric(
                name="test", value=0.0, unit="percent", timestamp=datetime.utcnow(),
                optimization_type="DEBUG", operation="test",
                original_size=1000, optimized_size=950  # Only 5% compression
            ) for _ in range(5)
        ]
        
        alerts = [
            {"type": "cache_hit_rate_low", "severity": "warning", "timestamp": datetime.utcnow().isoformat()},
            {"type": "high_processing_time", "severity": "critical", "timestamp": datetime.utcnow().isoformat()}
        ]
        
        recommendations = self.collector._generate_optimization_recommendations(poor_optimizations, alerts)
        
        assert len(recommendations) > 0
        
        # Should recommend more aggressive optimization
        assert any("aggressive response optimization" in rec for rec in recommendations)
        
        # Should recommend switching from DEBUG profile
        assert any("DEBUG profile usage" in rec for rec in recommendations)
        
        # Should recommend addressing critical issues
        assert any("Critical performance issues" in rec for rec in recommendations)
        
        # Should recommend cache improvements
        assert any("Cache performance issues" in rec for rec in recommendations)

    def test_export_optimization_dashboard_data(self):
        """Test exporting data for Grafana dashboard"""
        # Record some data first
        self.collector.record_response_optimization(
            original_size=1000, optimized_size=600, processing_time_ms=100.0, optimization_type="STANDARD"
        )
        
        dashboard_data = self.collector.export_optimization_dashboard_data(24)
        
        assert "dashboard" in dashboard_data
        assert "metrics" in dashboard_data
        assert "summary" in dashboard_data
        
        # Check dashboard structure
        dashboard = dashboard_data["dashboard"]
        assert dashboard["title"] == "MCP Response Optimization Dashboard"
        assert "time" in dashboard
        assert "from" in dashboard["time"]
        assert "to" in dashboard["time"]
        
        # Check metrics panels
        metrics = dashboard_data["metrics"]
        expected_panels = ["response_optimization", "cache_performance", "system_health", "alerts"]
        for panel in expected_panels:
            assert panel in metrics
            
        # Check panel structure
        response_panel = metrics["response_optimization"]
        assert response_panel["type"] == "graph"
        assert "targets" in response_panel
        assert len(response_panel["targets"]) >= 2

    @pytest.mark.asyncio
    async def test_generate_optimization_report(self):
        """Test comprehensive optimization report generation"""
        # Record some data
        self.collector.record_response_optimization(
            original_size=1000, optimized_size=700, processing_time_ms=120.0, optimization_type="STANDARD"
        )
        
        self.collector.record_system_health_metrics(
            cpu_usage=45.0, memory_usage=55.0, network_bandwidth_kbps=512.0,
            db_query_count=5, db_query_time_ms=80.0
        )
        
        report = await self.collector.generate_optimization_report(24)
        
        # Check report structure
        assert "report_metadata" in report
        assert "executive_summary" in report
        assert "detailed_metrics" in report
        assert "system_performance" in report
        assert "recommendations" in report
        assert "next_actions" in report
        
        # Check metadata
        metadata = report["report_metadata"]
        assert metadata["report_type"] == "optimization_performance"
        assert metadata["time_window_hours"] == 24
        assert "generated_at" in metadata
        
        # Check executive summary
        exec_summary = report["executive_summary"]
        assert exec_summary["total_optimizations"] >= 1
        assert "avg_compression_achieved" in exec_summary
        assert "system_health_status" in exec_summary
        
        # Check recommendations and next actions
        assert isinstance(report["recommendations"], list)
        assert isinstance(report["next_actions"], list)
        assert len(report["next_actions"]) >= 4


class TestGlobalOptimizationCollectorFunctions:
    """Test suite for global collector functions"""

    def setup_method(self):
        """Set up test fixtures"""
        # Reset global collector
        import fastmcp.task_management.infrastructure.monitoring.optimization_metrics as module
        module._global_optimization_collector = None

    def teardown_method(self):
        """Clean up test fixtures"""
        # Clean up global collector
        import fastmcp.task_management.infrastructure.monitoring.optimization_metrics as module
        if module._global_optimization_collector:
            asyncio.run(module._global_optimization_collector.stop_collection())
            module._global_optimization_collector = None

    def test_get_global_optimization_collector(self):
        """Test getting global optimization collector"""
        collector1 = get_global_optimization_collector()
        collector2 = get_global_optimization_collector()
        
        assert collector1 is not None
        assert isinstance(collector1, OptimizationMetricsCollector)
        assert collector1 is collector2  # Should be same instance

    def test_record_response_optimization_global(self):
        """Test recording response optimization using global function"""
        record_response_optimization(
            original_size=1500,
            optimized_size=900,
            processing_time_ms=125.0,
            optimization_type="STANDARD",
            operation="api_response",
            tags={"global": "true"}
        )
        
        collector = get_global_optimization_collector()
        assert len(collector.optimization_metrics) == 1
        
        opt_metric = collector.optimization_metrics[0]
        assert opt_metric.original_size == 1500
        assert opt_metric.optimized_size == 900
        assert opt_metric.compression_ratio == 40.0  # (1500-900)/1500*100

    def test_record_context_metrics_global(self):
        """Test recording context metrics using global function"""
        record_context_metrics(
            fields_requested=8,
            fields_returned=5,
            query_time_ms=65.3,
            cache_hit=True,
            tier="branch",
            tags={"global": "context"}
        )
        
        collector = get_global_optimization_collector()
        metrics = list(collector._metrics_buffer)
        
        # Should have context-related metrics
        context_metrics = [m for m in metrics if "context" in m.name]
        assert len(context_metrics) >= 4

    def test_record_ai_metrics_global(self):
        """Test recording AI metrics using global function"""
        record_ai_metrics(
            parse_success=True,
            extraction_time_ms=42.8,
            response_format="optimized_json",
            agent_operation="task_creation",
            tags={"global": "ai"}
        )
        
        collector = get_global_optimization_collector()
        metrics = list(collector._metrics_buffer)
        
        # Should have AI-related metrics
        ai_metrics = [m for m in metrics if "ai_" in m.name]
        assert len(ai_metrics) >= 2

    @pytest.mark.asyncio
    async def test_start_stop_optimization_monitoring(self):
        """Test starting and stopping optimization monitoring"""
        await start_optimization_monitoring()
        
        collector = get_global_optimization_collector()
        assert collector._running
        
        await stop_optimization_monitoring()
        
        # Global collector should be reset to None after stop
        import fastmcp.task_management.infrastructure.monitoring.optimization_metrics as module
        assert module._global_optimization_collector is None


class TestPerformanceBaselinesAndAlerting:
    """Test suite for performance baselines and alerting system"""

    def setup_method(self):
        """Set up test fixtures"""
        self.collector = OptimizationMetricsCollector()

    def test_performance_baselines_initialization(self):
        """Test performance baselines are properly initialized"""
        baselines = self.collector.performance_baselines
        
        expected_keys = [
            "response_size_threshold",
            "processing_time_threshold", 
            "cache_hit_rate_minimum",
            "compression_ratio_minimum"
        ]
        
        for key in expected_keys:
            assert key in baselines
            assert isinstance(baselines[key], (int, float))
            assert baselines[key] > 0

    def test_alert_lifecycle(self):
        """Test complete alert lifecycle"""
        # Trigger an alert
        self.collector._trigger_alert(
            "test_alert",
            "Test alert message",
            {"test_key": "test_value", "numeric_value": 42.5}
        )
        
        # Check alert was stored
        assert "test_alert" in self.collector.alerts_triggered
        alerts = self.collector.alerts_triggered["test_alert"]
        assert len(alerts) == 1
        
        alert = alerts[0]
        assert alert["type"] == "test_alert"
        assert alert["message"] == "Test alert message"
        assert alert["context"]["test_key"] == "test_value"
        assert alert["context"]["numeric_value"] == 42.5
        assert "timestamp" in alert
        assert alert["severity"] == "info"  # Default severity

    def test_alert_overflow_management(self):
        """Test alert list doesn't grow indefinitely"""
        # Generate many alerts to test overflow
        for i in range(60):  # More than 50 limit
            self.collector._trigger_alert(
                "overflow_test",
                f"Alert message {i}",
                {"sequence": i}
            )
        
        # Should keep only last 50 alerts
        alerts = self.collector.alerts_triggered["overflow_test"]
        assert len(alerts) == 50
        
        # Should have the most recent alerts (10-59)
        sequences = [alert["context"]["sequence"] for alert in alerts]
        assert min(sequences) == 10
        assert max(sequences) == 59

    def test_multiple_alert_types_tracking(self):
        """Test tracking multiple different alert types"""
        alert_types = ["compression_low", "processing_high", "cache_miss", "system_health"]
        
        for alert_type in alert_types:
            for i in range(3):
                self.collector._trigger_alert(
                    alert_type,
                    f"Test {alert_type} alert {i}",
                    {"iteration": i}
                )
        
        # All alert types should be tracked separately
        assert len(self.collector.alerts_triggered) == 4
        
        for alert_type in alert_types:
            assert alert_type in self.collector.alerts_triggered
            assert len(self.collector.alerts_triggered[alert_type]) == 3


class TestRealWorldOptimizationScenarios:
    """Test suite for real-world optimization scenarios"""

    def setup_method(self):
        """Set up test fixtures"""
        self.collector = OptimizationMetricsCollector()

    def test_api_response_optimization_lifecycle(self):
        """Test complete API response optimization lifecycle"""
        # Simulate API response processing
        scenarios = [
            # (original_size, optimized_size, processing_time, opt_type)
            (5000, 2000, 120.0, "STANDARD"),  # Good optimization
            (3000, 2900, 80.0, "MINIMAL"),    # Poor optimization 
            (8000, 2400, 250.0, "DETAILED"),  # Great optimization, slow
            (1000, 200, 45.0, "MINIMAL"),     # Excellent optimization
            (10000, 9800, 400.0, "STANDARD") # Poor optimization, slow
        ]
        
        for original, optimized, time_ms, opt_type in scenarios:
            self.collector.record_response_optimization(
                original_size=original,
                optimized_size=optimized,
                processing_time_ms=time_ms,
                optimization_type=opt_type,
                operation="api_response",
                tags={"endpoint": "/api/v1/task"}
            )
        
        # Get summary and check results
        summary = self.collector.get_optimization_summary(1.0)
        
        opt_perf = summary["optimization_performance"]
        assert opt_perf["total_optimizations"] == 5
        
        # Calculate expected average compression
        expected_compressions = []
        for original, optimized, _, _ in scenarios:
            compression = ((original - optimized) / original) * 100
            expected_compressions.append(compression)
        
        expected_avg = sum(expected_compressions) / len(expected_compressions)
        assert abs(opt_perf["avg_compression_ratio"] - expected_avg) < 1.0
        
        # Check alerts were triggered for poor performance
        assert len(self.collector.alerts_triggered) > 0

    def test_context_injection_performance_patterns(self):
        """Test context injection with different performance patterns"""
        # Simulate different tiers with varying performance
        tier_scenarios = [
            # (tier, cache_hit_rate, field_efficiency, query_time_range)
            ("global", 0.9, 0.8, (10, 30)),   # High cache hit, efficient
            ("project", 0.7, 0.6, (20, 50)),  # Medium performance
            ("branch", 0.5, 0.4, (30, 80)),   # Lower performance
            ("task", 0.3, 0.2, (50, 120))     # Poor performance
        ]
        
        for tier, hit_rate, efficiency, (min_time, max_time) in tier_scenarios:
            # Simulate multiple operations for this tier
            for i in range(20):
                cache_hit = i < (20 * hit_rate)  # Simulate hit rate
                
                fields_requested = 10
                fields_returned = int(fields_requested * efficiency)
                query_time = min_time + (i % (max_time - min_time))
                
                self.collector.record_context_injection_metrics(
                    fields_requested=fields_requested,
                    fields_returned=fields_returned,
                    query_time_ms=query_time,
                    cache_hit=cache_hit,
                    tier=tier,
                    tags={"operation": "context_injection"}
                )
        
        # Verify tier-specific performance tracking
        for tier, expected_hit_rate, _, _ in tier_scenarios:
            hit_attr = f"_cache_hits_{tier}"
            total_attr = f"_cache_total_{tier}"
            
            if hasattr(self.collector, hit_attr) and hasattr(self.collector, total_attr):
                hits = getattr(self.collector, hit_attr)
                total = getattr(self.collector, total_attr)
                actual_hit_rate = (hits / total) if total > 0 else 0
                
                # Should be close to expected hit rate
                assert abs(actual_hit_rate - expected_hit_rate) < 0.1

    def test_ai_agent_performance_tracking(self):
        """Test AI agent performance across different operations"""
        agent_operations = [
            ("hint_extraction", [True, True, False, True, True]),
            ("response_parsing", [True, True, True, False, True]),
            ("task_delegation", [True, False, True, True, False]),
            ("context_optimization", [True, True, True, True, True])
        ]
        
        extraction_times = [25.0, 45.0, 35.0, 60.0, 30.0]
        
        for operation, success_pattern in agent_operations:
            for i, (success, time_ms) in enumerate(zip(success_pattern, extraction_times)):
                error_type = None if success else "ParseError"
                
                self.collector.record_ai_performance_metrics(
                    parse_success=success,
                    extraction_time_ms=time_ms,
                    response_format="json",
                    agent_operation=operation,
                    error_type=error_type,
                    tags={"agent": f"agent_{i}"}
                )
        
        # Check success rate tracking for each operation
        for operation, success_pattern in agent_operations:
            success_attr = f"_ai_success_{operation}"
            total_attr = f"_ai_total_{operation}"
            
            if hasattr(self.collector, success_attr) and hasattr(self.collector, total_attr):
                successes = getattr(self.collector, success_attr)
                total = getattr(self.collector, total_attr)
                expected_successes = sum(success_pattern)
                
                assert successes == expected_successes
                assert total == len(success_pattern)

    def test_comprehensive_system_monitoring(self):
        """Test comprehensive system monitoring scenario"""
        # Simulate system under various loads
        time_points = 24  # 24 data points for 24-hour monitoring
        
        for hour in range(time_points):
            # Simulate daily load patterns (higher during work hours)
            if 9 <= hour <= 17:  # Work hours
                cpu_base, memory_base = 60.0, 70.0
                query_count_base, query_time_base = 50, 150.0
            elif 6 <= hour <= 9 or 17 <= hour <= 22:  # Peak transition
                cpu_base, memory_base = 40.0, 50.0
                query_count_base, query_time_base = 25, 100.0
            else:  # Off hours
                cpu_base, memory_base = 20.0, 30.0
                query_count_base, query_time_base = 10, 50.0
            
            # Add some randomness
            cpu = cpu_base + (hour % 5) * 2
            memory = memory_base + (hour % 7) * 3
            query_count = query_count_base + (hour % 3) * 5
            query_time = query_time_base + (hour % 4) * 10
            
            self.collector.record_system_health_metrics(
                cpu_usage=cpu,
                memory_usage=memory,
                network_bandwidth_kbps=1024.0 + hour * 10,
                db_query_count=query_count,
                db_query_time_ms=query_time,
                tags={"hour": str(hour), "period": "24h_monitoring"}
            )
        
        # Verify health scores correlate with load patterns
        metrics = list(self.collector._metrics_buffer)
        health_scores = [m.value for m in metrics if "health_score" in m.name]
        
        assert len(health_scores) == time_points
        
        # Work hours should have lower health scores on average
        work_hours_scores = health_scores[9:18]  # Hours 9-17
        off_hours_scores = health_scores[:6] + health_scores[22:]  # Hours 0-5, 22-23
        
        if work_hours_scores and off_hours_scores:
            work_avg = sum(work_hours_scores) / len(work_hours_scores)
            off_avg = sum(off_hours_scores) / len(off_hours_scores)
            
            # Off hours should have better health scores
            assert off_avg > work_avg

    @pytest.mark.asyncio
    async def test_optimization_report_comprehensive_scenario(self):
        """Test comprehensive optimization report with mixed performance"""
        # Record diverse optimization scenarios
        scenarios = [
            # High-performance scenarios
            (2000, 600, 80.0, "STANDARD"),
            (1500, 450, 60.0, "MINIMAL"),
            (3000, 900, 120.0, "STANDARD"),
            
            # Medium-performance scenarios  
            (1000, 700, 150.0, "DETAILED"),
            (2500, 1500, 200.0, "STANDARD"),
            
            # Poor-performance scenarios (should trigger alerts)
            (1000, 950, 400.0, "DEBUG"),
            (2000, 1900, 500.0, "DEBUG")
        ]
        
        for original, optimized, time_ms, opt_type in scenarios:
            self.collector.record_response_optimization(
                original_size=original,
                optimized_size=optimized,
                processing_time_ms=time_ms,
                optimization_type=opt_type
            )
        
        # Add system health data
        self.collector.record_system_health_metrics(
            cpu_usage=85.0,  # High CPU
            memory_usage=75.0,
            network_bandwidth_kbps=2048.0,
            db_query_count=100,
            db_query_time_ms=300.0  # Slow queries
        )
        
        # Generate comprehensive report
        report = await self.collector.generate_optimization_report(1.0)
        
        # Verify report completeness
        assert report["report_metadata"]["report_type"] == "optimization_performance"
        
        exec_summary = report["executive_summary"]
        assert exec_summary["total_optimizations"] == 7
        assert exec_summary["critical_issues"] > 0  # Should have alerts
        
        # Check system health status
        health_status = exec_summary["system_health_status"]
        assert health_status in ["healthy", "needs_attention"]
        
        # Verify recommendations are relevant
        recommendations = report["recommendations"]
        assert len(recommendations) > 0
        
        # Should recommend addressing DEBUG profile usage
        debug_rec = any("DEBUG profile" in rec for rec in recommendations)
        assert debug_rec
        
        # Should have actionable next steps
        next_actions = report["next_actions"]
        assert len(next_actions) >= 4
        assert all(isinstance(action, str) for action in next_actions)