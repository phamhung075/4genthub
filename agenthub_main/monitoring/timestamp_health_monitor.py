#!/usr/bin/env python3
"""
Production Health Monitor for Clean Timestamp Implementation
Real-time monitoring, alerting, and performance tracking for automated timestamp systems.
"""

import asyncio
import json
import logging
import psutil
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import sqlite3


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthMetric:
    name: str
    value: float
    unit: str
    threshold_warning: float
    threshold_critical: float
    status: HealthStatus
    timestamp: datetime
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'threshold_warning': self.threshold_warning,
            'threshold_critical': self.threshold_critical,
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details
        }


@dataclass
class HealthReport:
    timestamp: datetime
    overall_status: HealthStatus
    metrics: List[HealthMetric]
    alerts: List[str]
    recommendations: List[str]
    system_info: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'overall_status': self.overall_status.value,
            'metrics': [m.to_dict() for m in self.metrics],
            'alerts': self.alerts,
            'recommendations': self.recommendations,
            'system_info': self.system_info
        }


class TimestampHealthMonitor:
    """Comprehensive health monitoring for clean timestamp implementation"""

    def __init__(
        self,
        api_base_url: str = "http://localhost:8000",
        check_interval_seconds: int = 60,
        data_retention_days: int = 30,
        log_level: str = "INFO"
    ):
        self.api_base_url = api_base_url.rstrip('/')
        self.check_interval = check_interval_seconds
        self.data_retention_days = data_retention_days

        # Setup logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('timestamp_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Health tracking
        self.health_history: List[HealthReport] = []
        self.alert_cooldown: Dict[str, datetime] = {}
        self.cooldown_minutes = 15

        # Initialize monitoring database
        self.init_monitoring_db()

    def init_monitoring_db(self):
        """Initialize SQLite database for monitoring data"""
        self.db_path = Path("monitoring_data.db")

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS health_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    overall_status TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    alerts_json TEXT NOT NULL,
                    system_info_json TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_health_reports_timestamp
                ON health_reports(timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp
                ON performance_metrics(timestamp, metric_name)
            """)

    async def check_api_health(self) -> List[HealthMetric]:
        """Check API endpoint health and performance"""
        metrics = []

        try:
            # Health endpoint check
            start_time = time.time()
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.api_base_url}/health") as response:
                    response_time_ms = (time.time() - start_time) * 1000

                    # Response time metric
                    response_status = HealthStatus.HEALTHY
                    if response_time_ms > 1000:
                        response_status = HealthStatus.CRITICAL
                    elif response_time_ms > 500:
                        response_status = HealthStatus.DEGRADED

                    metrics.append(HealthMetric(
                        name="api_response_time",
                        value=response_time_ms,
                        unit="ms",
                        threshold_warning=500,
                        threshold_critical=1000,
                        status=response_status,
                        timestamp=datetime.now(timezone.utc),
                        details=f"GET {self.api_base_url}/health"
                    ))

                    # HTTP status metric
                    status_health = HealthStatus.HEALTHY if response.status == 200 else HealthStatus.CRITICAL

                    metrics.append(HealthMetric(
                        name="api_http_status",
                        value=response.status,
                        unit="status_code",
                        threshold_warning=300,
                        threshold_critical=400,
                        status=status_health,
                        timestamp=datetime.now(timezone.utc),
                        details=f"HTTP {response.status}"
                    ))

        except asyncio.TimeoutError:
            metrics.append(HealthMetric(
                name="api_response_time",
                value=10000,  # 10 seconds timeout
                unit="ms",
                threshold_warning=500,
                threshold_critical=1000,
                status=HealthStatus.CRITICAL,
                timestamp=datetime.now(timezone.utc),
                details="API timeout"
            ))

        except Exception as e:
            self.logger.error(f"API health check failed: {e}")
            metrics.append(HealthMetric(
                name="api_availability",
                value=0,
                unit="boolean",
                threshold_warning=0.5,
                threshold_critical=0,
                status=HealthStatus.CRITICAL,
                timestamp=datetime.now(timezone.utc),
                details=str(e)
            ))

        return metrics

    async def check_timestamp_performance(self) -> List[HealthMetric]:
        """Test timestamp creation and update performance"""
        metrics = []

        try:
            timeout = aiohttp.ClientTimeout(total=30)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Test task creation with timestamps
                test_tasks_data = []
                creation_times = []

                # Create batch of test tasks
                batch_size = 10
                batch_start_time = time.time()

                for i in range(batch_size):
                    start_time = time.time()

                    task_data = {
                        'title': f'Timestamp Monitor Test {datetime.now().isoformat()}_{i}',
                        'description': f'Performance monitoring test task {i}',
                        'priority': 'low'
                    }

                    async with session.post(
                        f"{self.api_base_url}/api/v1/tasks",
                        json=task_data
                    ) as response:
                        if response.status == 201:
                            task_result = await response.json()
                            test_tasks_data.append(task_result)
                            creation_time_ms = (time.time() - start_time) * 1000
                            creation_times.append(creation_time_ms)

                batch_total_time = time.time() - batch_start_time

                if creation_times:
                    avg_creation_time = sum(creation_times) / len(creation_times)

                    # Task creation performance metric
                    creation_status = HealthStatus.HEALTHY
                    if avg_creation_time > 1000:
                        creation_status = HealthStatus.CRITICAL
                    elif avg_creation_time > 500:
                        creation_status = HealthStatus.DEGRADED

                    metrics.append(HealthMetric(
                        name="timestamp_task_creation_avg",
                        value=avg_creation_time,
                        unit="ms",
                        threshold_warning=500,
                        threshold_critical=1000,
                        status=creation_status,
                        timestamp=datetime.now(timezone.utc),
                        details=f"Average of {len(creation_times)} task creations"
                    ))

                    # Batch throughput metric
                    throughput = len(creation_times) / batch_total_time

                    throughput_status = HealthStatus.HEALTHY
                    if throughput < 1:  # Less than 1 task per second is critical
                        throughput_status = HealthStatus.CRITICAL
                    elif throughput < 3:  # Less than 3 tasks per second is degraded
                        throughput_status = HealthStatus.DEGRADED

                    metrics.append(HealthMetric(
                        name="timestamp_task_throughput",
                        value=throughput,
                        unit="tasks/sec",
                        threshold_warning=3,
                        threshold_critical=1,
                        status=throughput_status,
                        timestamp=datetime.now(timezone.utc),
                        details=f"Batch of {batch_size} tasks in {batch_total_time:.2f}s"
                    ))

                # Test timestamp update performance
                if test_tasks_data:
                    update_times = []

                    for task_data in test_tasks_data[:5]:  # Test first 5 tasks
                        task_id = task_data.get('id')
                        if not task_id:
                            continue

                        start_time = time.time()

                        update_data = {
                            'description': f'Updated at {datetime.now().isoformat()}'
                        }

                        async with session.put(
                            f"{self.api_base_url}/api/v1/tasks/{task_id}",
                            json=update_data
                        ) as update_response:
                            if update_response.status == 200:
                                update_time_ms = (time.time() - start_time) * 1000
                                update_times.append(update_time_ms)

                    if update_times:
                        avg_update_time = sum(update_times) / len(update_times)

                        update_status = HealthStatus.HEALTHY
                        if avg_update_time > 800:
                            update_status = HealthStatus.CRITICAL
                        elif avg_update_time > 400:
                            update_status = HealthStatus.DEGRADED

                        metrics.append(HealthMetric(
                            name="timestamp_task_update_avg",
                            value=avg_update_time,
                            unit="ms",
                            threshold_warning=400,
                            threshold_critical=800,
                            status=update_status,
                            timestamp=datetime.now(timezone.utc),
                            details=f"Average of {len(update_times)} task updates"
                        ))

                # Cleanup test tasks
                for task_data in test_tasks_data:
                    task_id = task_data.get('id')
                    if task_id:
                        try:
                            async with session.delete(
                                f"{self.api_base_url}/api/v1/tasks/{task_id}"
                            ) as delete_response:
                                pass  # Best effort cleanup
                        except:
                            pass  # Ignore cleanup errors

        except Exception as e:
            self.logger.error(f"Timestamp performance check failed: {e}")
            metrics.append(HealthMetric(
                name="timestamp_performance_check",
                value=0,
                unit="success",
                threshold_warning=0.5,
                threshold_critical=0,
                status=HealthStatus.CRITICAL,
                timestamp=datetime.now(timezone.utc),
                details=f"Performance check failed: {str(e)}"
            ))

        return metrics

    def check_system_resources(self) -> List[HealthMetric]:
        """Check system resource utilization"""
        metrics = []

        try:
            # CPU utilization
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_status = HealthStatus.HEALTHY
            if cpu_percent > 90:
                cpu_status = HealthStatus.CRITICAL
            elif cpu_percent > 75:
                cpu_status = HealthStatus.DEGRADED

            metrics.append(HealthMetric(
                name="system_cpu_utilization",
                value=cpu_percent,
                unit="percent",
                threshold_warning=75,
                threshold_critical=90,
                status=cpu_status,
                timestamp=datetime.now(timezone.utc),
                details=f"CPU utilization over 1 second interval"
            ))

            # Memory utilization
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_status = HealthStatus.HEALTHY
            if memory_percent > 90:
                memory_status = HealthStatus.CRITICAL
            elif memory_percent > 80:
                memory_status = HealthStatus.DEGRADED

            metrics.append(HealthMetric(
                name="system_memory_utilization",
                value=memory_percent,
                unit="percent",
                threshold_warning=80,
                threshold_critical=90,
                status=memory_status,
                timestamp=datetime.now(timezone.utc),
                details=f"Available: {memory.available / (1024**3):.2f}GB / {memory.total / (1024**3):.2f}GB"
            ))

            # Disk utilization
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_status = HealthStatus.HEALTHY
            if disk_percent > 90:
                disk_status = HealthStatus.CRITICAL
            elif disk_percent > 85:
                disk_status = HealthStatus.DEGRADED

            metrics.append(HealthMetric(
                name="system_disk_utilization",
                value=disk_percent,
                unit="percent",
                threshold_warning=85,
                threshold_critical=90,
                status=disk_status,
                timestamp=datetime.now(timezone.utc),
                details=f"Used: {disk.used / (1024**3):.2f}GB / {disk.total / (1024**3):.2f}GB"
            ))

        except Exception as e:
            self.logger.error(f"System resource check failed: {e}")
            metrics.append(HealthMetric(
                name="system_resource_check",
                value=0,
                unit="success",
                threshold_warning=0.5,
                threshold_critical=0,
                status=HealthStatus.CRITICAL,
                timestamp=datetime.now(timezone.utc),
                details=f"Resource check failed: {str(e)}"
            ))

        return metrics

    async def generate_health_report(self) -> HealthReport:
        """Generate comprehensive health report"""
        timestamp = datetime.now(timezone.utc)
        all_metrics = []
        alerts = []
        recommendations = []

        # Collect all health metrics
        api_metrics = await self.check_api_health()
        timestamp_metrics = await self.check_timestamp_performance()
        system_metrics = self.check_system_resources()

        all_metrics.extend(api_metrics)
        all_metrics.extend(timestamp_metrics)
        all_metrics.extend(system_metrics)

        # Determine overall status
        critical_count = sum(1 for m in all_metrics if m.status == HealthStatus.CRITICAL)
        degraded_count = sum(1 for m in all_metrics if m.status == HealthStatus.DEGRADED)

        if critical_count > 0:
            overall_status = HealthStatus.CRITICAL
        elif degraded_count > 2:  # More than 2 degraded metrics is concerning
            overall_status = HealthStatus.DEGRADED
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        # Generate alerts for critical and degraded metrics
        for metric in all_metrics:
            if metric.status == HealthStatus.CRITICAL:
                alerts.append(f"CRITICAL: {metric.name} = {metric.value}{metric.unit} (threshold: {metric.threshold_critical})")
            elif metric.status == HealthStatus.DEGRADED:
                alerts.append(f"WARNING: {metric.name} = {metric.value}{metric.unit} (threshold: {metric.threshold_warning})")

        # Generate recommendations
        if critical_count > 0:
            recommendations.append("Immediate attention required - critical system issues detected")

        if any(m.name.startswith("timestamp_") and m.status != HealthStatus.HEALTHY for m in all_metrics):
            recommendations.append("Timestamp performance issues detected - review clean implementation")

        if any(m.name.startswith("system_") and m.status != HealthStatus.HEALTHY for m in all_metrics):
            recommendations.append("System resource constraints detected - consider scaling")

        if any(m.name.startswith("api_") and m.status != HealthStatus.HEALTHY for m in all_metrics):
            recommendations.append("API performance issues detected - review service health")

        # System info
        system_info = {
            'hostname': psutil.Process().name(),
            'python_version': f"{psutil.PYTHON_VERSION[0]}.{psutil.PYTHON_VERSION[1]}.{psutil.PYTHON_VERSION[2]}",
            'monitoring_version': '1.0.0',
            'check_interval_seconds': self.check_interval,
            'api_base_url': self.api_base_url
        }

        report = HealthReport(
            timestamp=timestamp,
            overall_status=overall_status,
            metrics=all_metrics,
            alerts=alerts,
            recommendations=recommendations,
            system_info=system_info
        )

        # Store in database
        self.store_health_report(report)

        return report

    def store_health_report(self, report: HealthReport):
        """Store health report in monitoring database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Store health report
                conn.execute("""
                    INSERT INTO health_reports
                    (timestamp, overall_status, metrics_json, alerts_json, system_info_json)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    report.timestamp.isoformat(),
                    report.overall_status.value,
                    json.dumps([m.to_dict() for m in report.metrics]),
                    json.dumps(report.alerts),
                    json.dumps(report.system_info)
                ))

                # Store individual metrics
                for metric in report.metrics:
                    conn.execute("""
                        INSERT INTO performance_metrics
                        (timestamp, metric_name, value, unit, status, details)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        metric.timestamp.isoformat(),
                        metric.name,
                        metric.value,
                        metric.unit,
                        metric.status.value,
                        metric.details
                    ))

        except Exception as e:
            self.logger.error(f"Failed to store health report: {e}")

    def send_alert(self, report: HealthReport):
        """Send alerts for critical issues"""
        if not report.alerts:
            return

        current_time = datetime.now(timezone.utc)

        for alert in report.alerts:
            alert_key = alert[:50]  # Use first 50 chars as key

            # Check cooldown
            if alert_key in self.alert_cooldown:
                last_sent = self.alert_cooldown[alert_key]
                if current_time - last_sent < timedelta(minutes=self.cooldown_minutes):
                    continue  # Skip duplicate alert

            # Log alert
            if alert.startswith("CRITICAL"):
                self.logger.critical(f"🚨 PRODUCTION ALERT: {alert}")
            else:
                self.logger.warning(f"⚠️ PRODUCTION WARNING: {alert}")

            # Update cooldown
            self.alert_cooldown[alert_key] = current_time

            # In production, integrate with:
            # - Slack notifications
            # - PagerDuty alerts
            # - Email notifications
            # - SMS for critical alerts
            print(f"🚨 ALERT: {alert}")

    async def run_continuous_monitoring(self):
        """Run continuous health monitoring"""
        self.logger.info(f"🔄 Starting continuous timestamp health monitoring")
        self.logger.info(f"Check interval: {self.check_interval} seconds")
        self.logger.info(f"API endpoint: {self.api_base_url}")

        while True:
            try:
                # Generate health report
                report = await self.generate_health_report()

                # Log status
                self.logger.info(
                    f"Health Status: {report.overall_status.value.upper()} "
                    f"({len(report.alerts)} alerts, {len(report.recommendations)} recommendations)"
                )

                # Send alerts
                self.send_alert(report)

                # Print summary
                if report.overall_status != HealthStatus.HEALTHY:
                    print(f"\n📊 Health Summary [{report.timestamp.strftime('%H:%M:%S')}]")
                    print(f"Status: {report.overall_status.value.upper()}")

                    if report.alerts:
                        print("Alerts:")
                        for alert in report.alerts:
                            print(f"  • {alert}")

                    if report.recommendations:
                        print("Recommendations:")
                        for rec in report.recommendations:
                            print(f"  → {rec}")
                    print()

                # Clean old data
                await self.cleanup_old_data()

            except Exception as e:
                self.logger.error(f"Monitoring cycle failed: {e}")
                self.logger.error(traceback.format_exc())

            # Wait for next check
            await asyncio.sleep(self.check_interval)

    async def cleanup_old_data(self):
        """Clean up old monitoring data"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.data_retention_days)

            with sqlite3.connect(self.db_path) as conn:
                # Clean old health reports
                conn.execute("""
                    DELETE FROM health_reports
                    WHERE created_at < ?
                """, (cutoff_date.isoformat(),))

                # Clean old performance metrics
                conn.execute("""
                    DELETE FROM performance_metrics
                    WHERE created_at < ?
                """, (cutoff_date.isoformat(),))

        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")

    async def get_health_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get health summary for the last N hours"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            with sqlite3.connect(self.db_path) as conn:
                # Get recent health reports
                cursor = conn.execute("""
                    SELECT overall_status, COUNT(*) as count
                    FROM health_reports
                    WHERE timestamp > ?
                    GROUP BY overall_status
                    ORDER BY count DESC
                """, (cutoff_time.isoformat(),))

                status_counts = dict(cursor.fetchall())

                # Get performance trends
                cursor = conn.execute("""
                    SELECT metric_name, AVG(value) as avg_value, unit, status
                    FROM performance_metrics
                    WHERE timestamp > ? AND metric_name LIKE 'timestamp_%'
                    GROUP BY metric_name, unit, status
                    ORDER BY metric_name
                """, (cutoff_time.isoformat(),))

                performance_trends = cursor.fetchall()

                return {
                    'period_hours': hours,
                    'status_distribution': status_counts,
                    'performance_trends': [
                        {
                            'metric': row[0],
                            'average_value': row[1],
                            'unit': row[2],
                            'predominant_status': row[3]
                        }
                        for row in performance_trends
                    ],
                    'generated_at': datetime.now(timezone.utc).isoformat()
                }

        except Exception as e:
            self.logger.error(f"Failed to generate health summary: {e}")
            return {'error': str(e)}


async def main():
    """Main monitoring function"""
    import argparse

    parser = argparse.ArgumentParser(description="Timestamp Health Monitor")
    parser.add_argument('--api-url', default='http://localhost:8000', help='API base URL')
    parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds')
    parser.add_argument('--retention-days', type=int, default=30, help='Data retention days')
    parser.add_argument('--log-level', default='INFO', help='Log level')

    args = parser.parse_args()

    # Create monitor instance
    monitor = TimestampHealthMonitor(
        api_base_url=args.api_url,
        check_interval_seconds=args.interval,
        data_retention_days=args.retention_days,
        log_level=args.log_level
    )

    try:
        # Run initial health check
        print("🏥 Running initial health assessment...")
        initial_report = await monitor.generate_health_report()

        print(f"Initial Status: {initial_report.overall_status.value.upper()}")
        if initial_report.alerts:
            print("Initial Alerts:")
            for alert in initial_report.alerts:
                print(f"  • {alert}")

        if initial_report.recommendations:
            print("Initial Recommendations:")
            for rec in initial_report.recommendations:
                print(f"  → {rec}")

        print(f"\n🚀 Starting continuous monitoring (interval: {args.interval}s)")
        print("Press Ctrl+C to stop monitoring...")

        # Start continuous monitoring
        await monitor.run_continuous_monitoring()

    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")
    except Exception as e:
        print(f"❌ Monitoring failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())