"""
Tests for Metrics Dashboard Service
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from typing import Dict, List, Any

from fastmcp.task_management.application.services.metrics_dashboard import (
    MetricsDashboard,
    MetricType,
    MetricPoint,
    Metric,
    DashboardWidget,
    AggregationType,
    TimeRange,
    MetricAlert
)


class TestMetricsDashboard:
    """Test Metrics Dashboard functionality"""

    @pytest.fixture
    def dashboard(self):
        """Create metrics dashboard instance"""
        return MetricsDashboard()

    @pytest.fixture
    def sample_metrics_data(self):
        """Sample metrics data for testing"""
        now = datetime.now()
        return [
            {"timestamp": now - timedelta(hours=2), "value": 95, "type": "task_completion_rate"},
            {"timestamp": now - timedelta(hours=1), "value": 87, "type": "task_completion_rate"},
            {"timestamp": now, "value": 92, "type": "task_completion_rate"},
            {"timestamp": now - timedelta(hours=2), "value": 1200, "type": "api_response_time"},
            {"timestamp": now - timedelta(hours=1), "value": 800, "type": "api_response_time"},
            {"timestamp": now, "value": 950, "type": "api_response_time"},
        ]

    def test_dashboard_initialization(self):
        """Test dashboard initialization"""
        dashboard = MetricsDashboard()
        assert dashboard.widgets == []
        assert dashboard.alerts == []
        assert dashboard.refresh_interval == 60  # Default 60 seconds

    def test_add_widget(self, dashboard):
        """Test adding widgets to dashboard"""
        widget = DashboardWidget(
            id="widget1",
            title="Task Completion Rate",
            metric_type=MetricType.TASK_COMPLETION,
            visualization="line_chart",
            position={"x": 0, "y": 0, "width": 6, "height": 4}
        )
        
        dashboard.add_widget(widget)
        assert len(dashboard.widgets) == 1
        assert dashboard.widgets[0].title == "Task Completion Rate"

    def test_record_metric(self, dashboard):
        """Test recording metrics"""
        dashboard.record_metric(
            metric_type=MetricType.API_RESPONSE_TIME,
            value=250.5,
            tags={"endpoint": "/api/tasks", "method": "GET"}
        )
        
        metrics = dashboard.get_metrics(MetricType.API_RESPONSE_TIME)
        assert len(metrics) > 0
        assert metrics[-1]["value"] == 250.5
        assert metrics[-1]["tags"]["endpoint"] == "/api/tasks"

    def test_get_metrics_with_time_range(self, dashboard, sample_metrics_data):
        """Test getting metrics with time range filter"""
        # Record sample metrics
        for metric in sample_metrics_data:
            dashboard.metrics_store.append(metric)
        
        # Get metrics from last hour
        now = datetime.now()
        metrics = dashboard.get_metrics(
            metric_type=MetricType.TASK_COMPLETION,
            time_range=TimeRange(
                start=now - timedelta(hours=1),
                end=now
            )
        )
        
        # Should only include metrics from last hour
        assert len(metrics) == 1
        assert metrics[0]["value"] == 92

    def test_aggregate_metrics(self, dashboard, sample_metrics_data):
        """Test metric aggregation"""
        # Record sample metrics
        for metric in sample_metrics_data:
            dashboard.metrics_store.append(metric)
        
        # Test different aggregation types
        avg = dashboard.aggregate_metrics(
            metric_type=MetricType.TASK_COMPLETION,
            aggregation=AggregationType.AVERAGE
        )
        assert avg == 91.33333333333333  # (95 + 87 + 92) / 3
        
        max_val = dashboard.aggregate_metrics(
            metric_type=MetricType.TASK_COMPLETION,
            aggregation=AggregationType.MAX
        )
        assert max_val == 95
        
        min_val = dashboard.aggregate_metrics(
            metric_type=MetricType.TASK_COMPLETION,
            aggregation=AggregationType.MIN
        )
        assert min_val == 87

    def test_calculate_trends(self, dashboard, sample_metrics_data):
        """Test trend calculation"""
        # Record sample metrics
        for metric in sample_metrics_data:
            dashboard.metrics_store.append(metric)
        
        trend = dashboard.calculate_trend(
            metric_type=MetricType.TASK_COMPLETION,
            time_range=TimeRange(
                start=datetime.now() - timedelta(hours=3),
                end=datetime.now()
            )
        )
        
        assert "direction" in trend
        assert "change_percentage" in trend
        assert "slope" in trend

    def test_set_alert(self, dashboard):
        """Test setting metric alerts"""
        alert = MetricAlert(
            id="alert1",
            name="High Response Time",
            metric_type=MetricType.API_RESPONSE_TIME,
            condition="greater_than",
            threshold=1000,
            action="notify",
            enabled=True
        )
        
        dashboard.set_alert(alert)
        assert len(dashboard.alerts) == 1
        
        # Record metric that triggers alert
        dashboard.record_metric(
            metric_type=MetricType.API_RESPONSE_TIME,
            value=1500
        )
        
        # Check triggered alerts
        triggered = dashboard.check_alerts()
        assert len(triggered) > 0
        assert triggered[0].name == "High Response Time"

    def test_dashboard_snapshot(self, dashboard, sample_metrics_data):
        """Test creating dashboard snapshot"""
        # Setup dashboard with widgets and metrics
        widget = DashboardWidget(
            id="w1",
            title="Performance Overview",
            metric_type=MetricType.API_RESPONSE_TIME,
            visualization="gauge"
        )
        dashboard.add_widget(widget)
        
        for metric in sample_metrics_data:
            dashboard.metrics_store.append(metric)
        
        # Create snapshot
        snapshot = dashboard.create_snapshot()
        
        assert "timestamp" in snapshot
        assert "widgets" in snapshot
        assert "metrics_summary" in snapshot
        assert len(snapshot["widgets"]) == 1

    def test_export_metrics(self, dashboard, sample_metrics_data):
        """Test exporting metrics data"""
        # Record metrics
        for metric in sample_metrics_data:
            dashboard.metrics_store.append(metric)
        
        # Export as CSV
        csv_data = dashboard.export_metrics(
            format="csv",
            metric_types=[MetricType.TASK_COMPLETION]
        )
        assert "timestamp,value,type" in csv_data
        assert "task_completion_rate" in csv_data
        
        # Export as JSON
        json_data = dashboard.export_metrics(
            format="json",
            metric_types=[MetricType.API_RESPONSE_TIME]
        )
        import json
        parsed = json.loads(json_data)
        assert len(parsed) == 3  # 3 API response time metrics

    def test_realtime_metrics_stream(self, dashboard):
        """Test real-time metrics streaming"""
        received_metrics = []
        
        def metric_handler(metric):
            received_metrics.append(metric)
        
        # Subscribe to metrics stream
        dashboard.subscribe_to_metrics(
            metric_type=MetricType.TASK_COMPLETION,
            handler=metric_handler
        )
        
        # Record new metric
        dashboard.record_metric(
            metric_type=MetricType.TASK_COMPLETION,
            value=95
        )
        
        # Handler should receive the metric
        assert len(received_metrics) == 1
        assert received_metrics[0]["value"] == 95

    def test_metric_percentiles(self, dashboard):
        """Test calculating metric percentiles"""
        # Record multiple values
        values = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        for v in values:
            dashboard.record_metric(
                metric_type=MetricType.API_RESPONSE_TIME,
                value=v
            )
        
        # Calculate percentiles
        p50 = dashboard.calculate_percentile(
            metric_type=MetricType.API_RESPONSE_TIME,
            percentile=50
        )
        assert p50 == 550  # Median
        
        p95 = dashboard.calculate_percentile(
            metric_type=MetricType.API_RESPONSE_TIME,
            percentile=95
        )
        assert p95 == 950

    def test_metric_correlations(self, dashboard):
        """Test finding correlations between metrics"""
        # Record correlated metrics
        for i in range(10):
            dashboard.record_metric(
                metric_type=MetricType.TASK_COMPLETION,
                value=80 + i * 2
            )
            dashboard.record_metric(
                metric_type=MetricType.AGENT_UTILIZATION,
                value=60 + i * 1.5
            )
        
        correlation = dashboard.calculate_correlation(
            metric_type1=MetricType.TASK_COMPLETION,
            metric_type2=MetricType.AGENT_UTILIZATION
        )
        
        assert correlation > 0.9  # Strong positive correlation

    def test_dashboard_templates(self, dashboard):
        """Test dashboard template functionality"""
        # Load predefined template
        dashboard.load_template("project_overview")
        
        # Should have standard widgets
        widget_titles = [w.title for w in dashboard.widgets]
        assert "Task Completion Rate" in widget_titles
        assert "Average Response Time" in widget_titles
        assert "Active Agents" in widget_titles

    def test_custom_metrics(self, dashboard):
        """Test custom metric definitions"""
        # Define custom metric
        dashboard.define_custom_metric(
            name="code_quality_score",
            description="Composite score for code quality",
            calculation=lambda metrics: (
                metrics.get("test_coverage", 0) * 0.3 +
                metrics.get("code_complexity", 0) * 0.3 +
                metrics.get("documentation_score", 0) * 0.4
            )
        )
        
        # Record component metrics
        dashboard.record_metric("test_coverage", 85)
        dashboard.record_metric("code_complexity", 90)
        dashboard.record_metric("documentation_score", 75)
        
        # Calculate custom metric
        score = dashboard.calculate_custom_metric("code_quality_score")
        assert score == 82.5  # (85*0.3 + 90*0.3 + 75*0.4)

    def test_metric_anomaly_detection(self, dashboard):
        """Test anomaly detection in metrics"""
        # Record normal values
        for _ in range(20):
            dashboard.record_metric(
                metric_type=MetricType.API_RESPONSE_TIME,
                value=200 + (50 * (0.5 - float(hash(str(_))) % 100 / 100))
            )
        
        # Record anomaly
        dashboard.record_metric(
            metric_type=MetricType.API_RESPONSE_TIME,
            value=2000  # 10x normal
        )
        
        anomalies = dashboard.detect_anomalies(
            metric_type=MetricType.API_RESPONSE_TIME,
            method="statistical",
            threshold=3  # 3 standard deviations
        )
        
        assert len(anomalies) > 0
        assert anomalies[0]["value"] == 2000

    def test_dashboard_sharing(self, dashboard):
        """Test dashboard sharing functionality"""
        # Configure dashboard
        dashboard.add_widget(DashboardWidget(
            id="w1",
            title="Test Widget",
            metric_type=MetricType.TASK_COMPLETION
        ))
        
        # Generate shareable link
        share_link = dashboard.generate_share_link(
            expires_in=timedelta(days=7),
            read_only=True
        )
        
        assert "token" in share_link
        assert "expires_at" in share_link
        assert share_link["read_only"] is True

    def test_metric_forecasting(self, dashboard):
        """Test metric forecasting"""
        # Record historical data with trend
        base_value = 100
        for i in range(30):
            value = base_value + (i * 2) + (10 * (0.5 - float(hash(str(i))) % 100 / 100))
            dashboard.record_metric(
                metric_type=MetricType.TASK_COMPLETION,
                value=value,
                timestamp=datetime.now() - timedelta(days=30-i)
            )
        
        # Forecast future values
        forecast = dashboard.forecast_metric(
            metric_type=MetricType.TASK_COMPLETION,
            periods=7,  # Next 7 days
            method="linear_regression"
        )
        
        assert len(forecast) == 7
        assert all("timestamp" in f and "predicted_value" in f for f in forecast)
        assert all("confidence_interval" in f for f in forecast)

    def test_dashboard_performance(self, dashboard):
        """Test dashboard performance with large datasets"""
        import time
        
        # Record large number of metrics
        start_time = time.time()
        for i in range(10000):
            dashboard.record_metric(
                metric_type=MetricType.API_RESPONSE_TIME,
                value=100 + (i % 100)
            )
        record_time = time.time() - start_time
        
        # Query performance
        start_time = time.time()
        metrics = dashboard.get_metrics(
            metric_type=MetricType.API_RESPONSE_TIME,
            time_range=TimeRange(
                start=datetime.now() - timedelta(hours=1),
                end=datetime.now()
            )
        )
        query_time = time.time() - start_time
        
        # Should handle large datasets efficiently
        assert record_time < 1.0  # Recording 10k metrics < 1 second
        assert query_time < 0.1   # Querying < 100ms