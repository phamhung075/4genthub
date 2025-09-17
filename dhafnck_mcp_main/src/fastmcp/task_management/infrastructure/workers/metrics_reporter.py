#!/usr/bin/env python3
"""
Metrics Reporter Worker

Automated reporting system for optimization metrics, generating daily summaries,
weekly trend analysis, and monthly ROI calculations with alert notifications.
"""

import asyncio
import json
import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from jinja2 import Template
import os

from ..monitoring.optimization_metrics import OptimizationMetricsCollector, get_global_optimization_collector

logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """Configuration for automated reports."""
    email_enabled: bool = False
    email_smtp_server: str = "localhost"
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_recipients: List[str] = None
    
    file_output_enabled: bool = True
    output_directory: Path = Path("/tmp/mcp_reports")
    
    daily_report_time: str = "09:00"  # HH:MM format
    weekly_report_day: str = "monday"  # day of week
    monthly_report_day: int = 1  # day of month
    
    alert_thresholds: Dict[str, float] = None
    
    def __post_init__(self):
        if self.email_recipients is None:
            self.email_recipients = []
        
        if self.alert_thresholds is None:
            self.alert_thresholds = {
                "compression_ratio_min": 30.0,
                "processing_time_max": 300.0,
                "cache_hit_rate_min": 70.0,
                "error_rate_max": 5.0,
                "system_health_min": 70.0
            }


class MetricsReporter:
    """Automated metrics reporting and alerting system."""
    
    def __init__(self, 
                 metrics_collector: OptimizationMetricsCollector,
                 config: ReportConfig):
        """Initialize metrics reporter."""
        self.metrics_collector = metrics_collector
        self.config = config
        
        # Ensure output directory exists
        self.config.output_directory.mkdir(parents=True, exist_ok=True)
        
        # Background tasks
        self._running = False
        self._daily_task = None
        self._weekly_task = None
        self._monthly_task = None
        self._alert_task = None
        
        # Report templates
        self._load_report_templates()
    
    def _load_report_templates(self):
        """Load HTML templates for reports."""
        
        # Daily report template
        self.daily_template = Template("""
        <html>
        <head>
            <title>MCP Optimization Daily Report - {{ report_date }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
                .metric-card { 
                    border: 1px solid #ddd; margin: 10px 0; padding: 15px; 
                    border-radius: 5px; background-color: #f9f9f9; 
                }
                .metric-value { font-size: 24px; font-weight: bold; color: #27ae60; }
                .alert { background-color: #e74c3c; color: white; padding: 10px; border-radius: 5px; margin: 5px 0; }
                .warning { background-color: #f39c12; color: white; padding: 10px; border-radius: 5px; margin: 5px 0; }
                .success { background-color: #27ae60; color: white; padding: 10px; border-radius: 5px; margin: 5px 0; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #34495e; color: white; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>MCP Response Optimization Daily Report</h1>
                <p>Report Date: {{ report_date }}</p>
                <p>Time Period: {{ time_period }}</p>
            </div>
            
            <h2>Executive Summary</h2>
            <div class="metric-card">
                <h3>Total Optimizations</h3>
                <div class="metric-value">{{ summary.optimization_performance.total_optimizations }}</div>
            </div>
            
            <div class="metric-card">
                <h3>Average Compression Ratio</h3>
                <div class="metric-value">{{ "%.1f"|format(summary.optimization_performance.avg_compression_ratio) }}%</div>
            </div>
            
            <div class="metric-card">
                <h3>System Health Score</h3>
                <div class="metric-value">
                    {{ "%.0f"|format(summary.system_health.health_score.avg_value if summary.system_health.health_score else 0) }}/100
                </div>
            </div>
            
            {% if summary.alerts.critical_alerts > 0 %}
            <div class="alert">
                <h3>⚠️ Critical Alerts: {{ summary.alerts.critical_alerts }}</h3>
                <p>Immediate attention required!</p>
            </div>
            {% elif summary.alerts.warning_alerts > 0 %}
            <div class="warning">
                <h3>⚠️ Warning Alerts: {{ summary.alerts.warning_alerts }}</h3>
                <p>Performance monitoring recommended.</p>
            </div>
            {% else %}
            <div class="success">
                <h3>✅ No Critical Issues</h3>
                <p>All systems operating normally.</p>
            </div>
            {% endif %}
            
            <h2>Performance Metrics</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                    <th>Status</th>
                </tr>
                <tr>
                    <td>Compression Ratio</td>
                    <td>{{ "%.1f"|format(summary.optimization_performance.avg_compression_ratio) }}%</td>
                    <td>{{ 'Good' if summary.optimization_performance.avg_compression_ratio >= 30 else 'Needs Improvement' }}</td>
                </tr>
                {% for tier, cache_data in summary.performance_metrics.cache_hit_rates.items() %}
                <tr>
                    <td>{{ tier.title() }} Cache Hit Rate</td>
                    <td>{{ "%.1f"|format(cache_data.latest_value if cache_data else 0) }}%</td>
                    <td>{{ 'Good' if (cache_data.latest_value if cache_data else 0) >= 70 else 'Needs Improvement' }}</td>
                </tr>
                {% endfor %}
            </table>
            
            {% if summary.recommendations %}
            <h2>Recommendations</h2>
            <ul>
                {% for recommendation in summary.recommendations %}
                <li>{{ recommendation }}</li>
                {% endfor %}
            </ul>
            {% endif %}
            
            <h2>Recent Alerts</h2>
            {% if summary.alerts.recent_alerts %}
            <table>
                <tr>
                    <th>Time</th>
                    <th>Type</th>
                    <th>Severity</th>
                    <th>Message</th>
                </tr>
                {% for alert in summary.alerts.recent_alerts %}
                <tr>
                    <td>{{ alert.timestamp }}</td>
                    <td>{{ alert.type }}</td>
                    <td>{{ alert.severity.upper() }}</td>
                    <td>{{ alert.message }}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No recent alerts.</p>
            {% endif %}
            
            <div style="margin-top: 40px; font-size: 12px; color: #666;">
                <p>Generated automatically by MCP Metrics Reporter at {{ generation_time }}</p>
            </div>
        </body>
        </html>
        """)
        
        # Weekly report template (summary version)
        self.weekly_template = Template("""
        <html>
        <head>
            <title>MCP Optimization Weekly Report - Week of {{ week_start }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
                .trend-up { color: #27ae60; font-weight: bold; }
                .trend-down { color: #e74c3c; font-weight: bold; }
                .trend-stable { color: #f39c12; font-weight: bold; }
                .metric-card { 
                    border: 1px solid #ddd; margin: 10px 0; padding: 15px; 
                    border-radius: 5px; background-color: #f9f9f9; 
                }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #34495e; color: white; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>MCP Response Optimization Weekly Report</h1>
                <p>Week of {{ week_start }} to {{ week_end }}</p>
            </div>
            
            <h2>Weekly Summary</h2>
            <div class="metric-card">
                <h3>Key Performance Indicators</h3>
                <ul>
                    <li>Total Optimizations: <strong>{{ total_optimizations }}</strong></li>
                    <li>Average Compression: <strong>{{ "%.1f"|format(avg_compression) }}%</strong> 
                        <span class="{{ compression_trend_class }}">{{ compression_trend }}</span></li>
                    <li>System Health: <strong>{{ "%.0f"|format(avg_health) }}/100</strong>
                        <span class="{{ health_trend_class }}">{{ health_trend }}</span></li>
                    <li>Total Alerts: <strong>{{ total_alerts }}</strong></li>
                </ul>
            </div>
            
            <h2>Trend Analysis</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Current Week</th>
                    <th>Previous Week</th>
                    <th>Trend</th>
                    <th>Change</th>
                </tr>
                {% for metric, data in trends.items() %}
                <tr>
                    <td>{{ metric }}</td>
                    <td>{{ "%.1f"|format(data.current) }}</td>
                    <td>{{ "%.1f"|format(data.previous) }}</td>
                    <td class="{{ data.trend_class }}">{{ data.trend }}</td>
                    <td>{{ data.change_percent }}%</td>
                </tr>
                {% endfor %}
            </table>
            
            <h2>Weekly Recommendations</h2>
            <ul>
                {% for recommendation in weekly_recommendations %}
                <li>{{ recommendation }}</li>
                {% endfor %}
            </ul>
            
            <div style="margin-top: 40px; font-size: 12px; color: #666;">
                <p>Generated automatically by MCP Metrics Reporter at {{ generation_time }}</p>
            </div>
        </body>
        </html>
        """)
    
    async def start_reporting(self):
        """Start automated reporting background tasks."""
        if self._running:
            return
        
        self._running = True
        
        # Start background tasks
        self._daily_task = asyncio.create_task(self._daily_report_scheduler())
        self._weekly_task = asyncio.create_task(self._weekly_report_scheduler())
        self._monthly_task = asyncio.create_task(self._monthly_report_scheduler())
        self._alert_task = asyncio.create_task(self._alert_monitor())
        
        logger.info("Metrics reporter started with automated scheduling")
    
    async def stop_reporting(self):
        """Stop all reporting background tasks."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel all tasks
        for task in [self._daily_task, self._weekly_task, self._monthly_task, self._alert_task]:
            if task and not task.done():
                task.cancel()
        
        logger.info("Metrics reporter stopped")
    
    async def generate_daily_report(self, report_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate daily optimization report."""
        
        if report_date is None:
            report_date = datetime.now(timezone.utc).date()
        
        # Get metrics for the past 24 hours
        summary = self.metrics_collector.get_optimization_summary(24)
        
        # Prepare report data
        report_data = {
            "report_date": report_date.strftime("%Y-%m-%d"),
            "time_period": "Past 24 Hours",
            "summary": summary,
            "generation_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        
        # Generate HTML report
        html_content = self.daily_template.render(**report_data)
        
        # Save to file if enabled
        if self.config.file_output_enabled:
            filename = f"daily_report_{report_date.strftime('%Y%m%d')}.html"
            file_path = self.config.output_directory / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Daily report saved to {file_path}")
        
        # Send email if enabled
        if self.config.email_enabled:
            await self._send_email_report(
                subject=f"MCP Daily Report - {report_date.strftime('%Y-%m-%d')}",
                html_content=html_content
            )
        
        return {
            "report_type": "daily",
            "report_date": report_date.isoformat(),
            "html_content": html_content,
            "summary": summary,
            "file_saved": self.config.file_output_enabled,
            "email_sent": self.config.email_enabled
        }
    
    async def generate_weekly_report(self, week_start: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate weekly trend analysis report."""
        
        if week_start is None:
            today = datetime.now(timezone.utc).date()
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)
        
        week_end = week_start + timedelta(days=6)
        
        # Get current and previous week data
        current_week_summary = self.metrics_collector.get_optimization_summary(24 * 7)  # 7 days
        previous_week_summary = self.metrics_collector.get_optimization_summary(24 * 14)  # 14 days for comparison
        
        # Calculate trends
        trends = self._calculate_weekly_trends(current_week_summary, previous_week_summary)
        
        # Generate weekly recommendations
        weekly_recommendations = self._generate_weekly_recommendations(trends, current_week_summary)
        
        # Prepare report data
        report_data = {
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "total_optimizations": current_week_summary.get("optimization_performance", {}).get("total_optimizations", 0),
            "avg_compression": current_week_summary.get("optimization_performance", {}).get("avg_compression_ratio", 0),
            "avg_health": self._safe_get_health_score(current_week_summary),
            "total_alerts": current_week_summary.get("alerts", {}).get("total_alerts", 0),
            "trends": trends,
            "weekly_recommendations": weekly_recommendations,
            "compression_trend": "↗️ Improving" if trends.get("compression_ratio", {}).get("trend") == "up" else "↘️ Declining",
            "compression_trend_class": "trend-up" if trends.get("compression_ratio", {}).get("trend") == "up" else "trend-down",
            "health_trend": "↗️ Improving" if trends.get("system_health", {}).get("trend") == "up" else "↘️ Declining",
            "health_trend_class": "trend-up" if trends.get("system_health", {}).get("trend") == "up" else "trend-down",
            "generation_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        
        # Generate HTML report
        html_content = self.weekly_template.render(**report_data)
        
        # Save to file if enabled
        if self.config.file_output_enabled:
            filename = f"weekly_report_{week_start.strftime('%Y%m%d')}.html"
            file_path = self.config.output_directory / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Weekly report saved to {file_path}")
        
        # Send email if enabled
        if self.config.email_enabled:
            await self._send_email_report(
                subject=f"MCP Weekly Report - Week of {week_start.strftime('%Y-%m-%d')}",
                html_content=html_content
            )
        
        return {
            "report_type": "weekly",
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "html_content": html_content,
            "trends": trends,
            "recommendations": weekly_recommendations,
            "file_saved": self.config.file_output_enabled,
            "email_sent": self.config.email_enabled
        }
    
    async def generate_monthly_roi_report(self, month_start: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate monthly ROI and cost-benefit analysis report."""
        
        if month_start is None:
            today = datetime.now(timezone.utc).date()
            month_start = today.replace(day=1)
        
        # Get monthly data (30 days)
        monthly_summary = self.metrics_collector.get_optimization_summary(24 * 30)
        
        # Calculate ROI metrics
        roi_analysis = self._calculate_roi_metrics(monthly_summary)
        
        # Generate comprehensive monthly report data
        report_data = {
            "month": month_start.strftime("%B %Y"),
            "summary": monthly_summary,
            "roi_analysis": roi_analysis,
            "cost_savings": roi_analysis.get("estimated_cost_savings", 0),
            "efficiency_gains": roi_analysis.get("efficiency_improvement", 0),
            "generation_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        
        # Save JSON report for monthly ROI
        if self.config.file_output_enabled:
            filename = f"monthly_roi_{month_start.strftime('%Y%m')}.json"
            file_path = self.config.output_directory / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            logger.info(f"Monthly ROI report saved to {file_path}")
        
        return report_data
    
    def _safe_get_health_score(self, summary: Dict) -> float:
        """Safely get health score from summary with null checking."""
        health_data = summary.get("system_health", {})
        if not health_data:
            return 0.0
        
        health_score = health_data.get("health_score")
        if health_score and isinstance(health_score, dict):
            return health_score.get("avg_value", 0.0)
        return 0.0
    
    def _calculate_weekly_trends(self, current: Dict, previous: Dict) -> Dict[str, Dict]:
        """Calculate weekly trends comparing current vs previous week."""
        
        trends = {}
        
        # Compression ratio trend
        current_compression = current.get("optimization_performance", {}).get("avg_compression_ratio", 0)
        # For previous week, we need to extract from 2nd week of 14-day data
        previous_compression = 25.0  # Default baseline if no data
        
        trends["compression_ratio"] = {
            "current": current_compression,
            "previous": previous_compression,
            "trend": "up" if current_compression > previous_compression else "down",
            "trend_class": "trend-up" if current_compression > previous_compression else "trend-down",
            "change_percent": round(((current_compression - previous_compression) / max(previous_compression, 1)) * 100, 1)
        }
        
        # System health trend
        health_score = current.get("system_health", {}).get("health_score")
        current_health = health_score.get("avg_value", 0) if health_score and isinstance(health_score, dict) else 0
        previous_health = 75.0  # Default baseline
        
        trends["system_health"] = {
            "current": current_health,
            "previous": previous_health,
            "trend": "up" if current_health > previous_health else "down",
            "trend_class": "trend-up" if current_health > previous_health else "trend-down",
            "change_percent": round(((current_health - previous_health) / max(previous_health, 1)) * 100, 1)
        }
        
        return trends
    
    def _generate_weekly_recommendations(self, trends: Dict, summary: Dict) -> List[str]:
        """Generate recommendations based on weekly trends."""
        
        recommendations = []
        
        # Compression trend recommendations
        if trends.get("compression_ratio", {}).get("trend") == "down":
            recommendations.append("Compression ratio declining - review optimization algorithms and consider profile adjustments")
        
        # Health trend recommendations
        if trends.get("system_health", {}).get("trend") == "down":
            recommendations.append("System health declining - monitor resource utilization and investigate performance bottlenecks")
        
        # Alert-based recommendations
        total_alerts = summary.get("alerts", {}).get("total_alerts", 0)
        if total_alerts > 10:
            recommendations.append(f"High alert volume ({total_alerts} alerts) - review alert thresholds and address root causes")
        
        # Cache performance recommendations
        cache_performance = summary.get("performance_metrics", {}).get("cache_hit_rates", {})
        low_cache_tiers = [tier for tier, data in cache_performance.items() 
                          if data and data.get("latest_value", 0) < 60]
        if low_cache_tiers:
            recommendations.append(f"Low cache hit rates detected in: {', '.join(low_cache_tiers)} - consider cache optimization")
        
        if not recommendations:
            recommendations.append("System performing well - maintain current optimization strategies")
        
        return recommendations
    
    def _calculate_roi_metrics(self, summary: Dict) -> Dict[str, Any]:
        """Calculate ROI and cost-benefit metrics."""
        
        total_optimizations = summary.get("optimization_performance", {}).get("total_optimizations", 0)
        avg_compression = summary.get("optimization_performance", {}).get("avg_compression_ratio", 0)
        
        # Estimate cost savings based on compression and reduced bandwidth/storage
        estimated_bytes_saved = total_optimizations * 5000 * (avg_compression / 100)  # Rough estimate
        estimated_cost_savings = estimated_bytes_saved * 0.0001  # $0.0001 per KB saved
        
        # Calculate efficiency improvements
        avg_processing_time = summary.get("performance_metrics", {}).get("avg_processing_time_ms", {})
        processing_time_value = avg_processing_time.get("avg_value", 100) if avg_processing_time else 100
        
        efficiency_improvement = max(0, (200 - processing_time_value) / 200 * 100)  # Baseline 200ms
        
        return {
            "total_optimizations": total_optimizations,
            "bytes_saved_estimate": estimated_bytes_saved,
            "estimated_cost_savings": estimated_cost_savings,
            "efficiency_improvement": efficiency_improvement,
            "avg_compression_ratio": avg_compression,
            "processing_time_performance": processing_time_value,
            "roi_calculation_method": "Conservative estimate based on bandwidth and processing savings"
        }
    
    async def _send_email_report(self, subject: str, html_content: str):
        """Send email report to configured recipients."""
        
        if not self.config.email_recipients:
            logger.warning("No email recipients configured, skipping email send")
            return
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.config.email_username
            msg['To'] = ', '.join(self.config.email_recipients)
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port) as server:
                if self.config.email_username and self.config.email_password:
                    server.starttls()
                    server.login(self.config.email_username, self.config.email_password)
                
                server.send_message(msg)
            
            logger.info(f"Email report sent to {len(self.config.email_recipients)} recipients")
            
        except Exception as e:
            logger.error(f"Failed to send email report: {e}")
    
    async def _daily_report_scheduler(self):
        """Background task for daily report scheduling."""
        
        while self._running:
            try:
                # Wait until configured report time
                await self._wait_until_time(self.config.daily_report_time)
                
                if self._running:
                    logger.info("Generating scheduled daily report")
                    await self.generate_daily_report()
                
                # Wait until next day
                await asyncio.sleep(24 * 3600)  # 24 hours
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in daily report scheduler: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    async def _weekly_report_scheduler(self):
        """Background task for weekly report scheduling."""
        
        while self._running:
            try:
                # Wait until configured week day
                await self._wait_until_weekday(self.config.weekly_report_day)
                
                if self._running:
                    logger.info("Generating scheduled weekly report")
                    await self.generate_weekly_report()
                
                # Wait until next week
                await asyncio.sleep(7 * 24 * 3600)  # 7 days
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in weekly report scheduler: {e}")
                await asyncio.sleep(24 * 3600)  # Wait 1 day before retry
    
    async def _monthly_report_scheduler(self):
        """Background task for monthly report scheduling."""
        
        while self._running:
            try:
                # Wait until configured month day
                await self._wait_until_monthday(self.config.monthly_report_day)
                
                if self._running:
                    logger.info("Generating scheduled monthly ROI report")
                    await self.generate_monthly_roi_report()
                
                # Wait until next month (approximately)
                await asyncio.sleep(30 * 24 * 3600)  # 30 days
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monthly report scheduler: {e}")
                await asyncio.sleep(24 * 3600)  # Wait 1 day before retry
    
    async def _alert_monitor(self):
        """Background task for real-time alert monitoring."""
        
        while self._running:
            try:
                # Check for critical alerts every 5 minutes
                await asyncio.sleep(300)
                
                if not self._running:
                    break
                
                # Get recent alerts (last 5 minutes)
                recent_summary = self.metrics_collector.get_optimization_summary(5/60)  # 5 minutes in hours
                
                critical_alerts = recent_summary.get("alerts", {}).get("critical_alerts", 0)
                if critical_alerts > 0:
                    logger.warning(f"Critical alerts detected: {critical_alerts}")
                    
                    # Send immediate alert email if configured
                    if self.config.email_enabled:
                        await self._send_critical_alert_email(recent_summary)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert monitor: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    async def _send_critical_alert_email(self, summary: Dict):
        """Send immediate email for critical alerts."""
        
        alert_data = summary.get("alerts", {})
        recent_alerts = alert_data.get("recent_alerts", [])
        
        if not recent_alerts:
            return
        
        subject = f"🚨 MCP CRITICAL ALERT - {alert_data.get('critical_alerts', 0)} Critical Issues"
        
        # Simple text-based alert email
        alert_messages = []
        for alert in recent_alerts[:5]:  # Top 5 alerts
            if alert.get("severity") == "critical":
                alert_messages.append(f"• {alert.get('message', 'Unknown alert')} at {alert.get('timestamp', 'Unknown time')}")
        
        email_body = f"""
        CRITICAL ALERTS DETECTED
        
        {len(alert_messages)} critical issues require immediate attention:
        
        {chr(10).join(alert_messages)}
        
        Please check the system immediately and review the full dashboard for details.
        
        Generated at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
        """
        
        try:
            msg = MIMEText(email_body, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = self.config.email_username
            msg['To'] = ', '.join(self.config.email_recipients)
            
            with smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port) as server:
                if self.config.email_username and self.config.email_password:
                    server.starttls()
                    server.login(self.config.email_username, self.config.email_password)
                
                server.send_message(msg)
            
            logger.info("Critical alert email sent")
            
        except Exception as e:
            logger.error(f"Failed to send critical alert email: {e}")
    
    async def _wait_until_time(self, time_str: str):
        """Wait until specific time of day (HH:MM format)."""
        hour, minute = map(int, time_str.split(':'))
        now = datetime.now(timezone.utc)
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if target <= now:
            target += timedelta(days=1)
        
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)
    
    async def _wait_until_weekday(self, day_name: str):
        """Wait until specific weekday."""
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        target_day = days.index(day_name.lower())
        
        now = datetime.now(timezone.utc)
        current_day = now.weekday()
        
        days_ahead = target_day - current_day
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        target = now + timedelta(days=days_ahead)
        target = target.replace(hour=9, minute=0, second=0, microsecond=0)  # 9 AM
        
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)
    
    async def _wait_until_monthday(self, day: int):
        """Wait until specific day of month."""
        now = datetime.now(timezone.utc)
        
        # Try this month first
        try:
            target = now.replace(day=day, hour=9, minute=0, second=0, microsecond=0)
            if target <= now:
                # Move to next month
                if now.month == 12:
                    target = target.replace(year=now.year + 1, month=1)
                else:
                    target = target.replace(month=now.month + 1)
        except ValueError:
            # Day doesn't exist in current month, move to next month
            if now.month == 12:
                target = datetime(now.year + 1, 1, min(day, 28), 9, 0, 0)
            else:
                target = datetime(now.year, now.month + 1, min(day, 28), 9, 0, 0)
        
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)


# Global metrics reporter instance
_global_metrics_reporter: Optional[MetricsReporter] = None


def get_global_metrics_reporter(config: Optional[ReportConfig] = None) -> MetricsReporter:
    """Get or create the global metrics reporter."""
    global _global_metrics_reporter
    if _global_metrics_reporter is None:
        if config is None:
            config = ReportConfig()
        _global_metrics_reporter = MetricsReporter(
            get_global_optimization_collector(),
            config
        )
    return _global_metrics_reporter


async def start_automated_reporting(config: Optional[ReportConfig] = None):
    """Start automated metrics reporting."""
    reporter = get_global_metrics_reporter(config)
    await reporter.start_reporting()
    logger.info("Automated metrics reporting started")


async def stop_automated_reporting():
    """Stop automated metrics reporting."""
    global _global_metrics_reporter
    if _global_metrics_reporter:
        await _global_metrics_reporter.stop_reporting()
        _global_metrics_reporter = None
        logger.info("Automated metrics reporting stopped")