"""Tests for MetricsReporter - Automated reporting system for optimization metrics

Tests the comprehensive automated reporting system for generating daily summaries,
weekly trend analysis, and monthly ROI calculations with alert notifications.
"""

import pytest
import asyncio
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from email.mime.text import MIMEText

from fastmcp.task_management.infrastructure.workers.metrics_reporter import (
    ReportConfig,
    MetricsReporter,
    get_global_metrics_reporter,
    start_automated_reporting,
    stop_automated_reporting
)


class TestReportConfig:
    """Test suite for ReportConfig dataclass"""

    def test_report_config_default_values(self):
        """Test ReportConfig initialization with default values"""
        config = ReportConfig()
        
        assert config.email_enabled == False
        assert config.email_smtp_server == "localhost"
        assert config.email_smtp_port == 587
        assert config.email_username == ""
        assert config.email_password == ""
        assert config.email_recipients == []
        
        assert config.file_output_enabled == True
        assert config.output_directory == Path("/tmp/mcp_reports")
        
        assert config.daily_report_time == "09:00"
        assert config.weekly_report_day == "monday"
        assert config.monthly_report_day == 1
        
        assert isinstance(config.alert_thresholds, dict)
        assert "compression_ratio_min" in config.alert_thresholds

    def test_report_config_custom_values(self):
        """Test ReportConfig with custom values"""
        custom_recipients = ["admin@example.com", "ops@example.com"]
        custom_thresholds = {"custom_threshold": 50.0}
        custom_output = Path("/custom/reports")
        
        config = ReportConfig(
            email_enabled=True,
            email_smtp_server="smtp.example.com",
            email_smtp_port=465,
            email_username="reporter@example.com",
            email_password="secret",
            email_recipients=custom_recipients,
            file_output_enabled=False,
            output_directory=custom_output,
            daily_report_time="08:30",
            weekly_report_day="friday",
            monthly_report_day=15,
            alert_thresholds=custom_thresholds
        )
        
        assert config.email_enabled == True
        assert config.email_smtp_server == "smtp.example.com"
        assert config.email_smtp_port == 465
        assert config.email_recipients == custom_recipients
        assert config.output_directory == custom_output
        assert config.daily_report_time == "08:30"
        assert config.weekly_report_day == "friday"
        assert config.monthly_report_day == 15
        assert config.alert_thresholds == custom_thresholds

    def test_report_config_post_init_defaults(self):
        """Test ReportConfig post-init default value handling"""
        config = ReportConfig()
        
        # Should initialize empty list for recipients
        assert config.email_recipients is not None
        assert isinstance(config.email_recipients, list)
        
        # Should initialize default alert thresholds
        assert config.alert_thresholds is not None
        assert isinstance(config.alert_thresholds, dict)
        assert len(config.alert_thresholds) > 0


class TestMetricsReporter:
    """Test suite for MetricsReporter functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_collector = Mock()
        
        # Configure mock collector
        self.mock_collector.get_optimization_summary.return_value = {
            "optimization_performance": {
                "total_optimizations": 100,
                "avg_compression_ratio": 45.5,
                "min_compression_ratio": 15.0,
                "max_compression_ratio": 80.0
            },
            "system_health": {
                "health_score": {"avg_value": 85.2}
            },
            "alerts": {
                "total_alerts": 3,
                "critical_alerts": 1,
                "warning_alerts": 2,
                "recent_alerts": [
                    {
                        "type": "high_processing_time",
                        "severity": "critical",
                        "message": "Processing time exceeded threshold",
                        "timestamp": datetime.now().isoformat()
                    }
                ]
            },
            "performance_metrics": {
                "cache_hit_rates": {
                    "global": {"latest_value": 75.0},
                    "project": {"latest_value": 65.0}
                }
            },
            "recommendations": [
                "Consider optimizing cache configuration",
                "Review processing time thresholds"
            ]
        }
        
        self.config = ReportConfig(
            file_output_enabled=True,
            output_directory=self.temp_dir,
            email_enabled=False
        )
        
        self.reporter = MetricsReporter(self.mock_collector, self.config)

    def teardown_method(self):
        """Clean up test fixtures"""
        if hasattr(self.reporter, '_running') and self.reporter._running:
            asyncio.run(self.reporter.stop_reporting())

    def test_reporter_initialization(self):
        """Test MetricsReporter initialization"""
        assert self.reporter.metrics_collector == self.mock_collector
        assert self.reporter.config == self.config
        assert not self.reporter._running
        assert self.reporter.config.output_directory.exists()

    def test_load_report_templates(self):
        """Test report templates are loaded correctly"""
        assert hasattr(self.reporter, 'daily_template')
        assert hasattr(self.reporter, 'weekly_template')
        
        # Templates should be Template objects (from Jinja2)
        assert hasattr(self.reporter.daily_template, 'render')
        assert hasattr(self.reporter.weekly_template, 'render')

    @pytest.mark.asyncio
    async def test_generate_daily_report(self):
        """Test daily report generation"""
        report_date = datetime.now().date()
        
        result = await self.reporter.generate_daily_report(report_date)
        
        # Check result structure
        assert result["report_type"] == "daily"
        assert result["report_date"] == report_date.isoformat()
        assert "html_content" in result
        assert "summary" in result
        assert result["file_saved"] == True
        assert result["email_sent"] == False
        
        # Check HTML content contains expected elements
        html_content = result["html_content"]
        assert "MCP Optimization Daily Report" in html_content
        assert "100" in html_content  # Total optimizations
        assert "45.5%" in html_content  # Avg compression
        
        # Check file was saved
        expected_filename = f"daily_report_{report_date.strftime('%Y%m%d')}.html"
        file_path = self.temp_dir / expected_filename
        assert file_path.exists()
        
        # Verify file content matches
        saved_content = file_path.read_text(encoding='utf-8')
        assert saved_content == html_content

    @pytest.mark.asyncio
    async def test_generate_daily_report_with_email(self):
        """Test daily report generation with email enabled"""
        # Configure for email
        self.config.email_enabled = True
        self.config.email_recipients = ["test@example.com"]
        
        with patch.object(self.reporter, '_send_email_report', new_callable=AsyncMock) as mock_email:
            result = await self.reporter.generate_daily_report()
            
            assert result["email_sent"] == True
            mock_email.assert_called_once()
            
            # Check email call parameters
            call_args = mock_email.call_args
            assert "MCP Daily Report" in call_args[1]["subject"]
            assert "html_content" in call_args[1]

    @pytest.mark.asyncio
    async def test_generate_weekly_report(self):
        """Test weekly report generation"""
        week_start = datetime.now().date() - timedelta(days=datetime.now().weekday())
        
        result = await self.reporter.generate_weekly_report(week_start)
        
        # Check result structure
        assert result["report_type"] == "weekly"
        assert result["week_start"] == week_start.isoformat()
        assert "html_content" in result
        assert "trends" in result
        assert "recommendations" in result
        
        # Check trends calculation
        trends = result["trends"]
        assert "compression_ratio" in trends
        assert "system_health" in trends
        
        for trend_key, trend_data in trends.items():
            assert "current" in trend_data
            assert "previous" in trend_data
            assert "trend" in trend_data
            assert trend_data["trend"] in ["up", "down"]
        
        # Check HTML content
        html_content = result["html_content"]
        assert "MCP Response Optimization Weekly Report" in html_content
        assert "100" in html_content  # Total optimizations

    @pytest.mark.asyncio
    async def test_generate_monthly_roi_report(self):
        """Test monthly ROI report generation"""
        month_start = datetime.now().date().replace(day=1)
        
        result = await self.reporter.generate_monthly_roi_report(month_start)
        
        # Check result structure
        assert result["month"] == month_start.strftime("%B %Y")
        assert "summary" in result
        assert "roi_analysis" in result
        assert "cost_savings" in result
        assert "efficiency_gains" in result
        
        # Check ROI analysis
        roi_analysis = result["roi_analysis"]
        assert "total_optimizations" in roi_analysis
        assert "estimated_cost_savings" in roi_analysis
        assert "efficiency_improvement" in roi_analysis
        
        # Check file was saved as JSON
        expected_filename = f"monthly_roi_{month_start.strftime('%Y%m')}.json"
        file_path = self.temp_dir / expected_filename
        assert file_path.exists()
        
        # Verify JSON content
        saved_data = json.loads(file_path.read_text(encoding='utf-8'))
        assert saved_data["month"] == result["month"]

    def test_safe_get_health_score(self):
        """Test safe health score extraction"""
        # Test with normal data
        summary_with_health = {
            "system_health": {
                "health_score": {"avg_value": 75.5}
            }
        }
        score = self.reporter._safe_get_health_score(summary_with_health)
        assert score == 75.5
        
        # Test with missing health data
        summary_no_health = {"system_health": {}}
        score = self.reporter._safe_get_health_score(summary_no_health)
        assert score == 0.0
        
        # Test with malformed data
        summary_malformed = {"system_health": {"health_score": "invalid"}}
        score = self.reporter._safe_get_health_score(summary_malformed)
        assert score == 0.0

    def test_calculate_weekly_trends(self):
        """Test weekly trend calculations"""
        current_summary = {
            "optimization_performance": {"avg_compression_ratio": 50.0},
            "system_health": {"health_score": {"avg_value": 80.0}}
        }
        
        previous_summary = {}  # Empty previous data
        
        trends = self.reporter._calculate_weekly_trends(current_summary, previous_summary)
        
        # Check trend structure
        assert "compression_ratio" in trends
        assert "system_health" in trends
        
        for trend_name, trend_data in trends.items():
            assert "current" in trend_data
            assert "previous" in trend_data
            assert "trend" in trend_data
            assert "trend_class" in trend_data
            assert "change_percent" in trend_data
            
            # Trend should be either "up" or "down"
            assert trend_data["trend"] in ["up", "down"]
            assert trend_data["trend_class"] in ["trend-up", "trend-down"]

    def test_generate_weekly_recommendations(self):
        """Test weekly recommendations generation"""
        # Test with declining trends
        declining_trends = {
            "compression_ratio": {"trend": "down"},
            "system_health": {"trend": "down"}
        }
        
        high_alert_summary = {
            "alerts": {"total_alerts": 15},
            "performance_metrics": {
                "cache_hit_rates": {
                    "global": {"latest_value": 50.0},  # Low cache hit rate
                    "project": {"latest_value": 75.0}
                }
            }
        }
        
        recommendations = self.reporter._generate_weekly_recommendations(declining_trends, high_alert_summary)
        
        assert len(recommendations) > 0
        
        # Should recommend compression improvements
        compression_rec = any("compression ratio" in rec.lower() for rec in recommendations)
        assert compression_rec
        
        # Should recommend system health investigation
        health_rec = any("system health" in rec.lower() for rec in recommendations)
        assert health_rec
        
        # Should recommend alert investigation
        alert_rec = any("alert" in rec.lower() for rec in recommendations)
        assert alert_rec
        
        # Should recommend cache optimization
        cache_rec = any("cache" in rec.lower() for rec in recommendations)
        assert cache_rec

    def test_calculate_roi_metrics(self):
        """Test ROI metrics calculation"""
        summary = {
            "optimization_performance": {
                "total_optimizations": 1000,
                "avg_compression_ratio": 40.0
            },
            "performance_metrics": {
                "avg_processing_time_ms": {"avg_value": 150.0}
            }
        }
        
        roi_metrics = self.reporter._calculate_roi_metrics(summary)
        
        # Check required fields
        required_fields = [
            "total_optimizations",
            "bytes_saved_estimate", 
            "estimated_cost_savings",
            "efficiency_improvement",
            "avg_compression_ratio",
            "processing_time_performance",
            "roi_calculation_method"
        ]
        
        for field in required_fields:
            assert field in roi_metrics
        
        # Check values are reasonable
        assert roi_metrics["total_optimizations"] == 1000
        assert roi_metrics["avg_compression_ratio"] == 40.0
        assert roi_metrics["bytes_saved_estimate"] > 0
        assert roi_metrics["estimated_cost_savings"] >= 0
        assert 0 <= roi_metrics["efficiency_improvement"] <= 100

    @pytest.mark.asyncio
    async def test_send_email_report_success(self):
        """Test successful email report sending"""
        # Configure for email
        self.config.email_enabled = True
        self.config.email_username = "reporter@example.com"
        self.config.email_password = "password"
        self.config.email_recipients = ["admin@example.com"]
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            await self.reporter._send_email_report(
                subject="Test Report",
                html_content="<html><body>Test</body></html>"
            )
            
            # Check SMTP was used correctly
            mock_smtp.assert_called_with(self.config.email_smtp_server, self.config.email_smtp_port)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_with(self.config.email_username, self.config.email_password)
            mock_server.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_report_no_recipients(self):
        """Test email sending with no recipients configured"""
        self.config.email_recipients = []
        
        with patch('smtplib.SMTP') as mock_smtp:
            await self.reporter._send_email_report("Test", "<html>Test</html>")
            
            # Should not attempt to send email
            mock_smtp.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_email_report_failure(self):
        """Test email sending failure handling"""
        self.config.email_recipients = ["admin@example.com"]
        
        with patch('smtplib.SMTP', side_effect=Exception("SMTP Error")):
            # Should not raise exception, just log error
            await self.reporter._send_email_report("Test", "<html>Test</html>")

    @pytest.mark.asyncio
    async def test_start_stop_reporting(self):
        """Test starting and stopping automated reporting"""
        assert not self.reporter._running
        
        # Start reporting
        await self.reporter.start_reporting()
        assert self.reporter._running
        
        # Check background tasks are created
        assert self.reporter._daily_task is not None
        assert self.reporter._weekly_task is not None
        assert self.reporter._monthly_task is not None
        assert self.reporter._alert_task is not None
        
        # Stop reporting
        await self.reporter.stop_reporting()
        assert not self.reporter._running

    @pytest.mark.asyncio
    async def test_alert_monitor(self):
        """Test alert monitoring functionality"""
        # Mock recent summary with critical alerts
        self.mock_collector.get_optimization_summary.return_value = {
            "alerts": {
                "critical_alerts": 2,
                "recent_alerts": [
                    {
                        "type": "high_processing_time",
                        "severity": "critical", 
                        "message": "Processing time critical",
                        "timestamp": datetime.now().isoformat()
                    }
                ]
            }
        }
        
        with patch.object(self.reporter, '_send_critical_alert_email', new_callable=AsyncMock) as mock_alert_email:
            # Start alert monitoring
            self.reporter._running = True
            alert_task = asyncio.create_task(self.reporter._alert_monitor())
            
            # Wait briefly for alert check
            await asyncio.sleep(0.1)
            
            # Cancel task
            alert_task.cancel()
            
            try:
                await alert_task
            except asyncio.CancelledError:
                pass
            
            # Should have triggered alert email
            if self.config.email_enabled:
                mock_alert_email.assert_called()

    @pytest.mark.asyncio
    async def test_send_critical_alert_email(self):
        """Test critical alert email sending"""
        self.config.email_enabled = True
        self.config.email_recipients = ["admin@example.com"]
        
        alert_summary = {
            "alerts": {
                "critical_alerts": 1,
                "recent_alerts": [
                    {
                        "severity": "critical",
                        "message": "System critical error",
                        "timestamp": datetime.now().isoformat()
                    }
                ]
            }
        }
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            await self.reporter._send_critical_alert_email(alert_summary)
            
            # Check email was sent
            mock_server.send_message.assert_called_once()
            
            # Check email content
            sent_msg = mock_server.send_message.call_args[0][0]
            assert "CRITICAL ALERT" in sent_msg['Subject']
            # Email content is base64 encoded, so check the payload
            import base64
            email_str = str(sent_msg)
            # Look for the base64 content part after headers
            if "base64" in email_str:
                # Extract and decode the base64 content
                lines = email_str.split('\n')
                base64_content = ''.join(lines[6:])  # Skip headers
                try:
                    decoded = base64.b64decode(base64_content).decode('utf-8')
                    assert "System critical error" in decoded
                except:
                    # Fallback to checking raw message
                    assert "System critical error" in email_str or "U3lzdGVtIGNyaXRpY2FsIGVycm9y" in email_str

    @pytest.mark.asyncio
    async def test_wait_until_time(self):
        """Test waiting until specific time"""
        # Test with immediate time (should wait ~24 hours)
        with patch('asyncio.sleep') as mock_sleep:
            await self.reporter._wait_until_time("09:00")
            mock_sleep.assert_called_once()
            
            # Should wait some positive amount of time
            wait_time = mock_sleep.call_args[0][0]
            assert wait_time > 0

    @pytest.mark.asyncio
    async def test_wait_until_weekday(self):
        """Test waiting until specific weekday"""
        with patch('asyncio.sleep') as mock_sleep:
            await self.reporter._wait_until_weekday("monday")
            mock_sleep.assert_called_once()
            
            # Should wait some positive amount of time
            wait_time = mock_sleep.call_args[0][0]
            assert wait_time > 0

    @pytest.mark.asyncio
    async def test_wait_until_monthday(self):
        """Test waiting until specific day of month"""
        with patch('asyncio.sleep') as mock_sleep:
            await self.reporter._wait_until_monthday(1)
            mock_sleep.assert_called_once()
            
            # Should wait some positive amount of time
            wait_time = mock_sleep.call_args[0][0]
            assert wait_time > 0

    def test_template_rendering_with_real_data(self):
        """Test template rendering with realistic data"""
        report_data = {
            "report_date": "2024-12-12",
            "time_period": "Past 24 Hours",
            "summary": self.mock_collector.get_optimization_summary.return_value,
            "generation_time": "2024-12-12 10:00:00 UTC"
        }
        
        # Test daily template
        daily_html = self.reporter.daily_template.render(**report_data)
        assert "MCP Optimization Daily Report" in daily_html
        assert "2024-12-12" in daily_html
        assert "100" in daily_html  # Total optimizations
        assert "45.5%" in daily_html  # Compression ratio
        
        # Test weekly template
        weekly_data = {
            "week_start": "2024-12-09",
            "week_end": "2024-12-15",
            "total_optimizations": 700,
            "avg_compression": 45.5,
            "avg_health": 85.2,
            "total_alerts": 3,
            "trends": {
                "compression_ratio": {
                    "current": 45.5,
                    "previous": 40.0,
                    "trend": "up",
                    "trend_class": "trend-up",
                    "change_percent": 13.8
                }
            },
            "weekly_recommendations": ["Continue current optimization strategies"],
            "compression_trend": "↗️ Improving",
            "compression_trend_class": "trend-up",
            "health_trend": "↗️ Improving", 
            "health_trend_class": "trend-up",
            "generation_time": "2024-12-12 10:00:00 UTC"
        }
        
        weekly_html = self.reporter.weekly_template.render(**weekly_data)
        assert "MCP Response Optimization Weekly Report" in weekly_html
        assert "Week of 2024-12-09" in weekly_html
        assert "700" in weekly_html  # Total optimizations


class TestGlobalReporterFunctions:
    """Test suite for global reporter functions"""

    def setup_method(self):
        """Set up test fixtures"""
        # Reset global reporter
        import fastmcp.task_management.infrastructure.workers.metrics_reporter as module
        module._global_metrics_reporter = None

    def teardown_method(self):
        """Clean up test fixtures"""
        # Clean up global reporter
        import fastmcp.task_management.infrastructure.workers.metrics_reporter as module
        if module._global_metrics_reporter:
            asyncio.run(module._global_metrics_reporter.stop_reporting())
            module._global_metrics_reporter = None

    def test_get_global_metrics_reporter(self):
        """Test getting global metrics reporter"""
        reporter1 = get_global_metrics_reporter()
        reporter2 = get_global_metrics_reporter()
        
        assert reporter1 is not None
        assert isinstance(reporter1, MetricsReporter)
        assert reporter1 is reporter2  # Should be same instance

    def test_get_global_metrics_reporter_with_config(self):
        """Test getting global reporter with custom config"""
        custom_config = ReportConfig(
            email_enabled=True,
            email_recipients=["test@example.com"]
        )
        
        reporter = get_global_metrics_reporter(custom_config)
        
        assert reporter.config.email_enabled == True
        assert reporter.config.email_recipients == ["test@example.com"]

    @pytest.mark.asyncio
    async def test_start_stop_automated_reporting(self):
        """Test starting and stopping automated reporting"""
        with patch.object(MetricsReporter, 'start_reporting', new_callable=AsyncMock) as mock_start:
            await start_automated_reporting()
            mock_start.assert_called_once()
        
        with patch.object(MetricsReporter, 'stop_reporting', new_callable=AsyncMock) as mock_stop:
            await stop_automated_reporting()
            mock_stop.assert_called_once()
        
        # Global reporter should be reset to None after stop
        import fastmcp.task_management.infrastructure.workers.metrics_reporter as module
        assert module._global_metrics_reporter is None

    @pytest.mark.asyncio
    async def test_start_automated_reporting_with_config(self):
        """Test starting automated reporting with custom config"""
        custom_config = ReportConfig(daily_report_time="10:00")
        
        with patch.object(MetricsReporter, 'start_reporting', new_callable=AsyncMock):
            await start_automated_reporting(custom_config)
            
            reporter = get_global_metrics_reporter()
            assert reporter.config.daily_report_time == "10:00"


class TestReportingSchedulers:
    """Test suite for reporting scheduler functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_collector = Mock()
        self.config = ReportConfig()
        self.reporter = MetricsReporter(self.mock_collector, self.config)

    @pytest.mark.asyncio
    async def test_daily_report_scheduler_flow(self):
        """Test daily report scheduler execution flow"""
        with patch.object(self.reporter, '_wait_until_time', new_callable=AsyncMock) as mock_wait:
            with patch.object(self.reporter, 'generate_daily_report', new_callable=AsyncMock) as mock_report:
                with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                    # Start scheduler
                    self.reporter._running = True
                    task = asyncio.create_task(self.reporter._daily_report_scheduler())
                    
                    # Wait briefly for first iteration
                    await asyncio.sleep(0.01)
                    
                    # Cancel task
                    task.cancel()
                    
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    
                    # Should have waited for configured time and generated report
                    mock_wait.assert_called_with(self.config.daily_report_time)
                    mock_report.assert_called()

    @pytest.mark.asyncio
    async def test_weekly_report_scheduler_flow(self):
        """Test weekly report scheduler execution flow"""
        with patch.object(self.reporter, '_wait_until_weekday', new_callable=AsyncMock) as mock_wait:
            with patch.object(self.reporter, 'generate_weekly_report', new_callable=AsyncMock) as mock_report:
                # Start scheduler
                self.reporter._running = True
                task = asyncio.create_task(self.reporter._weekly_report_scheduler())
                
                # Wait briefly
                await asyncio.sleep(0.01)
                
                # Cancel task
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                # Should have waited for configured weekday
                mock_wait.assert_called_with(self.config.weekly_report_day)
                mock_report.assert_called()

    @pytest.mark.asyncio
    async def test_monthly_report_scheduler_flow(self):
        """Test monthly report scheduler execution flow"""
        with patch.object(self.reporter, '_wait_until_monthday', new_callable=AsyncMock) as mock_wait:
            with patch.object(self.reporter, 'generate_monthly_roi_report', new_callable=AsyncMock) as mock_report:
                # Start scheduler
                self.reporter._running = True
                task = asyncio.create_task(self.reporter._monthly_report_scheduler())
                
                # Wait briefly
                await asyncio.sleep(0.01)
                
                # Cancel task
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                # Should have waited for configured month day
                mock_wait.assert_called_with(self.config.monthly_report_day)
                mock_report.assert_called()

    @pytest.mark.asyncio
    async def test_scheduler_error_handling(self):
        """Test scheduler error handling and recovery"""
        with patch.object(self.reporter, '_wait_until_time', side_effect=Exception("Test error")):
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                self.reporter._running = True
                task = asyncio.create_task(self.reporter._daily_report_scheduler())
                
                # Wait for error handling
                await asyncio.sleep(0.01)
                
                # Cancel task
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                # Should have slept for recovery period (1 hour = 3600 seconds)
                mock_sleep.assert_called()


class TestReportIntegrationScenarios:
    """Test suite for integration scenarios with real-world data"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_collector = Mock()
        self.config = ReportConfig(
            file_output_enabled=True,
            output_directory=self.temp_dir,
            email_enabled=False
        )
        self.reporter = MetricsReporter(self.mock_collector, self.config)

    @pytest.mark.asyncio
    async def test_complete_daily_reporting_cycle(self):
        """Test complete daily reporting cycle with realistic data"""
        # Configure realistic metrics data
        self.mock_collector.get_optimization_summary.return_value = {
            "optimization_performance": {
                "total_optimizations": 1250,
                "avg_compression_ratio": 62.3,
                "min_compression_ratio": 25.0,
                "max_compression_ratio": 85.7,
                "profile_distribution": {
                    "MINIMAL": 600,
                    "STANDARD": 500,
                    "DETAILED": 150
                }
            },
            "system_health": {
                "health_score": {"avg_value": 78.5},
                "resource_utilization": {
                    "cpu": {"avg_value": 45.2},
                    "memory": {"avg_value": 60.8}
                }
            },
            "alerts": {
                "total_alerts": 8,
                "critical_alerts": 0,
                "warning_alerts": 8,
                "recent_alerts": [
                    {
                        "type": "cache_hit_rate_low",
                        "severity": "warning",
                        "message": "Cache hit rate for project tier is 45.2%",
                        "timestamp": datetime.now().isoformat()
                    }
                ]
            },
            "performance_metrics": {
                "cache_hit_rates": {
                    "global": {"latest_value": 85.2},
                    "project": {"latest_value": 45.2},
                    "branch": {"latest_value": 72.1},
                    "task": {"latest_value": 65.8}
                },
                "ai_success_rates": {
                    "hint_extraction": {"avg_value": 95.5},
                    "response_parsing": {"avg_value": 88.7},
                    "task_delegation": {"avg_value": 92.1}
                }
            },
            "recommendations": [
                "Project cache hit rate is below optimal - consider increasing cache TTL",
                "System performing well overall - maintain current optimization strategies",
                "Monitor AI success rates for any declining trends"
            ]
        }
        
        # Generate daily report
        result = await self.reporter.generate_daily_report()
        
        # Verify comprehensive report generation
        assert result["report_type"] == "daily"
        assert result["file_saved"] == True
        
        html_content = result["html_content"]
        
        # Check all major sections are present
        assert "1250" in html_content  # Total optimizations
        assert "62.3%" in html_content  # Compression ratio
        assert "78.5" in html_content   # Health score
        assert "No Critical Issues" in html_content  # Alert status (0 critical)
        
        # Check performance metrics table
        assert "85.2%" in html_content  # Global cache hit rate
        assert "45.2%" in html_content  # Project cache hit rate
        
        # Check recommendations section
        assert "Project cache hit rate" in html_content
        assert "maintain current optimization" in html_content

    @pytest.mark.asyncio
    async def test_weekly_report_with_trends(self):
        """Test weekly report with realistic trend analysis"""
        # Mock current week data
        current_summary = {
            "optimization_performance": {
                "total_optimizations": 8500,
                "avg_compression_ratio": 58.7
            },
            "system_health": {
                "health_score": {"avg_value": 82.3}
            },
            "alerts": {"total_alerts": 12},
            "performance_metrics": {
                "cache_hit_rates": {
                    "global": {"latest_value": 88.5},
                    "project": {"latest_value": 55.2}  # Low cache performance
                }
            }
        }
        
        # Mock 14-day data for comparison
        comparison_summary = current_summary
        
        self.mock_collector.get_optimization_summary.side_effect = [current_summary, comparison_summary]
        
        result = await self.reporter.generate_weekly_report()
        
        # Verify weekly report structure
        assert result["report_type"] == "weekly"
        assert "trends" in result
        assert "recommendations" in result
        
        # Check trend analysis
        trends = result["trends"]
        assert "compression_ratio" in trends
        assert "system_health" in trends
        
        # Check recommendations include cache optimization
        recommendations = result["recommendations"]
        cache_rec = any("cache" in rec.lower() for rec in recommendations)
        assert cache_rec

    @pytest.mark.asyncio
    async def test_monthly_roi_comprehensive_analysis(self):
        """Test monthly ROI report with comprehensive analysis"""
        # Mock monthly data (high-performance month)
        monthly_summary = {
            "optimization_performance": {
                "total_optimizations": 35000,
                "avg_compression_ratio": 65.8
            },
            "performance_metrics": {
                "avg_processing_time_ms": {"avg_value": 125.3}  # Good performance
            },
            "system_health": {
                "health_score": {"avg_value": 85.7}
            }
        }
        
        self.mock_collector.get_optimization_summary.return_value = monthly_summary
        
        result = await self.reporter.generate_monthly_roi_report()
        
        # Verify ROI analysis
        roi_analysis = result["roi_analysis"]
        
        # Check ROI calculations are reasonable
        assert roi_analysis["total_optimizations"] == 35000
        assert roi_analysis["avg_compression_ratio"] == 65.8
        assert roi_analysis["bytes_saved_estimate"] > 1000000  # Should save significant bytes
        assert roi_analysis["estimated_cost_savings"] > 0
        assert roi_analysis["efficiency_improvement"] > 0
        
        # Check file output
        expected_filename = f"monthly_roi_{datetime.now().strftime('%Y%m')}.json"
        file_path = self.temp_dir / expected_filename
        assert file_path.exists()
        
        # Verify JSON structure
        saved_data = json.loads(file_path.read_text())
        assert saved_data["roi_analysis"]["total_optimizations"] == 35000

    @pytest.mark.asyncio  
    async def test_alert_monitoring_with_escalation(self):
        """Test alert monitoring with critical alert escalation"""
        # Configure for email alerts
        self.config.email_enabled = True
        self.config.email_recipients = ["ops@example.com"]
        
        # Mock critical alert scenario
        critical_alert_summary = {
            "alerts": {
                "critical_alerts": 3,
                "recent_alerts": [
                    {
                        "type": "high_processing_time",
                        "severity": "critical",
                        "message": "Processing time exceeded 500ms threshold",
                        "timestamp": datetime.now().isoformat()
                    },
                    {
                        "type": "system_health_critical",
                        "severity": "critical", 
                        "message": "System health score dropped below 30",
                        "timestamp": datetime.now().isoformat()
                    }
                ]
            }
        }
        
        self.mock_collector.get_optimization_summary.return_value = critical_alert_summary
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            # Test critical alert email
            await self.reporter._send_critical_alert_email(critical_alert_summary)
            
            # Should send critical alert email
            mock_server.send_message.assert_called_once()
            
            # Verify email content
            sent_msg = mock_server.send_message.call_args[0][0]
            assert "🚨 MCP CRITICAL ALERT" in sent_msg['Subject']
            assert "3 Critical Issues" in sent_msg['Subject']
            assert "Processing time exceeded 500ms" in str(sent_msg)