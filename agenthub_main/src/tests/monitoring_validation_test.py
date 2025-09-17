#!/usr/bin/env python3
"""
Monitoring Validation Test

Test script to validate the complete metrics dashboard and monitoring system.
Tests all components including metrics collection, dashboard data generation,
and automated reporting functionality.
"""

import asyncio
import json
import random
import time
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastmcp.task_management.infrastructure.monitoring.optimization_metrics import (
    OptimizationMetricsCollector,
    get_global_optimization_collector
)
from fastmcp.task_management.infrastructure.monitoring.metrics_integration import (
    MetricsCollectionService,
    initialize_metrics_system,
    optimization_context,
    response_optimization_tracker,
    track_optimization
)
from fastmcp.task_management.infrastructure.workers.metrics_reporter import (
    MetricsReporter,
    ReportConfig
)


class MetricsValidationTest:
    """Comprehensive test suite for metrics system validation."""
    
    def __init__(self):
        """Initialize test suite."""
        self.test_results = []
        self.output_dir = Path("/tmp/mcp_metrics_test")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def run_all_tests(self):
        """Run complete test suite."""
        print("🚀 Starting MCP Metrics Dashboard Validation Tests")
        print("=" * 60)
        
        try:
            # Initialize metrics system
            await self.test_metrics_initialization()
            
            # Test basic metrics collection
            await self.test_basic_metrics_collection()
            
            # Test optimization tracking
            await self.test_optimization_tracking()
            
            # Test context and AI metrics
            await self.test_context_ai_metrics()
            
            # Test alert system
            await self.test_alert_system()
            
            # Test dashboard data generation
            await self.test_dashboard_data_generation()
            
            # Test automated reporting
            await self.test_automated_reporting()
            
            # Test integration components
            await self.test_integration_components()
            
            # Generate test summary
            await self.generate_test_summary()
            
        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
            raise
        
        finally:
            # Cleanup
            await self.cleanup_test_environment()
    
    async def test_metrics_initialization(self):
        """Test metrics system initialization."""
        print("\n📊 Testing Metrics System Initialization...")
        
        try:
            # Test metrics service initialization
            service = await initialize_metrics_system(
                enable_reporting=True,
                output_directory=str(self.output_dir)
            )
            
            assert service is not None, "Metrics service should be initialized"
            
            # Test collector is available
            collector = get_global_optimization_collector()
            assert collector is not None, "Global collector should be available"
            
            self.test_results.append({
                "test": "metrics_initialization",
                "status": "PASSED",
                "details": "Metrics system initialized successfully"
            })
            print("  ✅ Metrics system initialization: PASSED")
            
        except Exception as e:
            self.test_results.append({
                "test": "metrics_initialization", 
                "status": "FAILED",
                "error": str(e)
            })
            print(f"  ❌ Metrics system initialization: FAILED - {e}")
            raise
    
    async def test_basic_metrics_collection(self):
        """Test basic metrics collection functionality."""
        print("\n📈 Testing Basic Metrics Collection...")
        
        collector = get_global_optimization_collector()
        
        try:
            # Record various metric types
            collector.record_timing_metric("test_operation", time.time())
            collector.record_size_metric("test_size", 1024, {"test": "basic"})
            collector.record_percentage_metric("test_percentage", 85.5, {"test": "basic"})
            collector.record_rate_metric("test_rate", 150.0, {"test": "basic"})
            
            # Wait a moment for collection
            await asyncio.sleep(0.1)
            
            # Test metric retrieval
            summary = collector.get_metric_summary("test_operation", 1)
            assert summary is not None, "Should be able to retrieve metrics"
            
            self.test_results.append({
                "test": "basic_metrics_collection",
                "status": "PASSED",
                "details": f"Collected {len(collector.get_all_metric_names())} different metrics"
            })
            print("  ✅ Basic metrics collection: PASSED")
            
        except Exception as e:
            self.test_results.append({
                "test": "basic_metrics_collection",
                "status": "FAILED", 
                "error": str(e)
            })
            print(f"  ❌ Basic metrics collection: FAILED - {e}")
            raise
    
    async def test_optimization_tracking(self):
        """Test optimization metrics tracking."""
        print("\n🔧 Testing Optimization Tracking...")
        
        collector = get_global_optimization_collector()
        
        try:
            # Test response optimization tracking
            original_sizes = [5000, 8000, 12000, 3000, 15000]
            optimization_types = ["MINIMAL", "STANDARD", "DETAILED", "DEBUG"]
            
            for i in range(10):
                original_size = random.choice(original_sizes)
                optimized_size = int(original_size * random.uniform(0.3, 0.8))  # 20-70% compression
                processing_time = random.uniform(50, 200)  # 50-200ms
                opt_type = random.choice(optimization_types)
                
                collector.record_response_optimization(
                    original_size=original_size,
                    optimized_size=optimized_size,
                    processing_time_ms=processing_time,
                    optimization_type=opt_type,
                    tags={"test": "optimization"}
                )
            
            # Test optimization context manager
            async with optimization_context("MINIMAL", "test_context") as ctx:
                ctx["original_size"] = 10000
                ctx["optimized_size"] = 3000
                ctx["parse_success"] = True
            
            # Get optimization summary
            summary = collector.get_optimization_summary(1)
            assert summary["optimization_performance"]["total_optimizations"] > 0
            
            self.test_results.append({
                "test": "optimization_tracking",
                "status": "PASSED",
                "details": f"Tracked {summary['optimization_performance']['total_optimizations']} optimizations"
            })
            print("  ✅ Optimization tracking: PASSED")
            
        except Exception as e:
            self.test_results.append({
                "test": "optimization_tracking",
                "status": "FAILED",
                "error": str(e)
            })
            print(f"  ❌ Optimization tracking: FAILED - {e}")
            raise
    
    async def test_context_ai_metrics(self):
        """Test context and AI performance metrics."""
        print("\n🤖 Testing Context and AI Metrics...")
        
        collector = get_global_optimization_collector()
        
        try:
            # Test context injection metrics
            for i in range(5):
                fields_requested = random.randint(50, 200)
                fields_returned = int(fields_requested * random.uniform(0.3, 0.9))
                query_time = random.uniform(20, 100)
                cache_hit = random.choice([True, False])
                tier = random.choice(["global", "project", "branch", "task"])
                
                collector.record_context_injection_metrics(
                    fields_requested=fields_requested,
                    fields_returned=fields_returned,
                    query_time_ms=query_time,
                    cache_hit=cache_hit,
                    tier=tier,
                    tags={"test": "context"}
                )
            
            # Test AI performance metrics
            for i in range(5):
                parse_success = random.choice([True, True, True, False])  # 75% success rate
                extraction_time = random.uniform(10, 50)
                response_format = random.choice(["MINIMAL", "STANDARD"])
                agent_operation = random.choice(["hint_extraction", "response_parsing", "task_delegation"])
                
                collector.record_ai_performance_metrics(
                    parse_success=parse_success,
                    extraction_time_ms=extraction_time,
                    response_format=response_format,
                    agent_operation=agent_operation,
                    tags={"test": "ai"}
                )
            
            # Verify metrics were recorded
            summary = collector.get_optimization_summary(1)
            assert summary["performance_metrics"], "Performance metrics should be recorded"
            
            self.test_results.append({
                "test": "context_ai_metrics",
                "status": "PASSED",
                "details": "Context and AI metrics recorded successfully"
            })
            print("  ✅ Context and AI metrics: PASSED")
            
        except Exception as e:
            self.test_results.append({
                "test": "context_ai_metrics",
                "status": "FAILED",
                "error": str(e)
            })
            print(f"  ❌ Context and AI metrics: FAILED - {e}")
            raise
    
    async def test_alert_system(self):
        """Test alert threshold and notification system."""
        print("\n🚨 Testing Alert System...")
        
        collector = get_global_optimization_collector()
        
        try:
            # Trigger alerts by recording metrics that exceed thresholds
            
            # Low compression ratio alert
            collector.record_response_optimization(
                original_size=10000,
                optimized_size=9500,  # Only 5% compression (below 30% threshold)
                processing_time_ms=50,
                optimization_type="DEBUG",
                tags={"test": "alert_low_compression"}
            )
            
            # High processing time alert
            collector.record_response_optimization(
                original_size=5000,
                optimized_size=2000,
                processing_time_ms=400,  # Above 300ms threshold
                optimization_type="DETAILED",
                tags={"test": "alert_high_processing"}
            )
            
            # Low cache hit rate
            for _ in range(10):
                collector.record_context_injection_metrics(
                    fields_requested=100,
                    fields_returned=50,
                    query_time_ms=30,
                    cache_hit=False,  # Force low hit rate
                    tier="test",
                    tags={"test": "alert_cache"}
                )
            
            # Wait for alerts to be processed
            await asyncio.sleep(0.5)
            
            # Check if alerts were triggered
            summary = collector.get_optimization_summary(1)
            total_alerts = summary.get("alerts", {}).get("total_alerts", 0)
            
            assert total_alerts > 0, "Alerts should be triggered"
            
            self.test_results.append({
                "test": "alert_system",
                "status": "PASSED",
                "details": f"Generated {total_alerts} alerts successfully"
            })
            print(f"  ✅ Alert system: PASSED ({total_alerts} alerts generated)")
            
        except Exception as e:
            self.test_results.append({
                "test": "alert_system",
                "status": "FAILED",
                "error": str(e)
            })
            print(f"  ❌ Alert system: FAILED - {e}")
            raise
    
    async def test_dashboard_data_generation(self):
        """Test dashboard data generation and export."""
        print("\n📊 Testing Dashboard Data Generation...")
        
        collector = get_global_optimization_collector()
        
        try:
            # Generate dashboard data
            dashboard_data = collector.export_optimization_dashboard_data(1)
            
            # Validate dashboard structure
            assert "dashboard" in dashboard_data, "Dashboard config should be present"
            assert "metrics" in dashboard_data, "Metrics data should be present"
            assert "summary" in dashboard_data, "Summary should be present"
            
            # Validate dashboard panels
            dashboard_config = dashboard_data["dashboard"]
            assert "title" in dashboard_config, "Dashboard should have title"
            assert "panels" in dashboard_config, "Dashboard should have panels"
            
            # Save dashboard data to file
            dashboard_file = self.output_dir / "test_dashboard_data.json"
            with open(dashboard_file, 'w') as f:
                json.dump(dashboard_data, f, indent=2, default=str)
            
            # Test Prometheus export
            prometheus_metrics = collector.export_prometheus_metrics()
            assert prometheus_metrics, "Prometheus metrics should be generated"
            
            prometheus_file = self.output_dir / "test_metrics.prom"
            with open(prometheus_file, 'w') as f:
                f.write(prometheus_metrics)
            
            self.test_results.append({
                "test": "dashboard_data_generation",
                "status": "PASSED",
                "details": f"Generated dashboard with {len(dashboard_data['metrics'])} metric types"
            })
            print("  ✅ Dashboard data generation: PASSED")
            
        except Exception as e:
            self.test_results.append({
                "test": "dashboard_data_generation",
                "status": "FAILED",
                "error": str(e)
            })
            print(f"  ❌ Dashboard data generation: FAILED - {e}")
            raise
    
    async def test_automated_reporting(self):
        """Test automated reporting functionality."""
        print("\n📧 Testing Automated Reporting...")
        
        try:
            # Configure test reporter
            config = ReportConfig(
                file_output_enabled=True,
                output_directory=self.output_dir,
                email_enabled=False  # Disable email for testing
            )
            
            collector = get_global_optimization_collector()
            reporter = MetricsReporter(collector, config)
            
            # Generate test reports
            daily_report = await reporter.generate_daily_report()
            assert daily_report["report_type"] == "daily", "Daily report should be generated"
            
            weekly_report = await reporter.generate_weekly_report()
            assert weekly_report["report_type"] == "weekly", "Weekly report should be generated"
            
            monthly_report = await reporter.generate_monthly_roi_report()
            assert "roi_analysis" in monthly_report, "Monthly ROI report should contain ROI analysis"
            
            # Verify files were created
            report_files = list(self.output_dir.glob("*_report_*.html")) + list(self.output_dir.glob("*_roi_*.json"))
            assert len(report_files) >= 2, "Report files should be created"
            
            self.test_results.append({
                "test": "automated_reporting",
                "status": "PASSED",
                "details": f"Generated {len(report_files)} report files successfully"
            })
            print(f"  ✅ Automated reporting: PASSED ({len(report_files)} reports generated)")
            
        except Exception as e:
            self.test_results.append({
                "test": "automated_reporting",
                "status": "FAILED",
                "error": str(e)
            })
            print(f"  ❌ Automated reporting: FAILED - {e}")
            raise
    
    async def test_integration_components(self):
        """Test integration decorators and context managers."""
        print("\n🔗 Testing Integration Components...")
        
        try:
            # Test optimization decorator
            @track_optimization("MINIMAL", "test_decorator")
            async def test_optimization_function():
                await asyncio.sleep(0.1)
                return {"result": "success"}
            
            result = await test_optimization_function()
            assert result["result"] == "success", "Decorated function should work"
            
            # Test response optimization tracker
            with response_optimization_tracker("STANDARD", 5000, "test_tracker") as tracker:
                tracker["optimized_size"] = 2000
                tracker["cache_hit"] = True
            
            # Test async optimization context
            async with optimization_context("DETAILED", "test_async_context") as ctx:
                ctx["original_size"] = 8000
                ctx["optimized_size"] = 3000
                ctx["fields_requested"] = 100
                ctx["fields_returned"] = 40
                ctx["cache_hit"] = True
            
            self.test_results.append({
                "test": "integration_components",
                "status": "PASSED",
                "details": "All integration components working correctly"
            })
            print("  ✅ Integration components: PASSED")
            
        except Exception as e:
            self.test_results.append({
                "test": "integration_components",
                "status": "FAILED",
                "error": str(e)
            })
            print(f"  ❌ Integration components: FAILED - {e}")
            raise
    
    async def generate_test_summary(self):
        """Generate comprehensive test summary."""
        print("\n📋 Generating Test Summary...")
        
        passed_tests = [t for t in self.test_results if t["status"] == "PASSED"]
        failed_tests = [t for t in self.test_results if t["status"] == "FAILED"]
        
        summary = {
            "test_run_timestamp": datetime.now().isoformat(),
            "total_tests": len(self.test_results),
            "passed_tests": len(passed_tests),
            "failed_tests": len(failed_tests),
            "success_rate": (len(passed_tests) / len(self.test_results)) * 100,
            "test_details": self.test_results,
            "system_validation": {
                "metrics_collection": "operational",
                "dashboard_generation": "operational", 
                "alert_system": "operational",
                "automated_reporting": "operational",
                "integration_components": "operational"
            }
        }
        
        # Save summary to file
        summary_file = self.output_dir / "test_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        # Generate human-readable summary
        print("\n" + "=" * 60)
        print("🎯 METRICS DASHBOARD VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Total Tests Run: {summary['total_tests']}")
        print(f"Tests Passed: {summary['passed_tests']}")
        print(f"Tests Failed: {summary['failed_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        
        if failed_tests:
            print("\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test.get('error', 'Unknown error')}")
        
        print(f"\n📁 Test artifacts saved to: {self.output_dir}")
        print(f"📊 Dashboard data: {self.output_dir}/test_dashboard_data.json")
        print(f"📈 Prometheus metrics: {self.output_dir}/test_metrics.prom")
        print(f"📧 Reports generated: {len(list(self.output_dir.glob('*report*')))} files")
        
        if summary['success_rate'] == 100:
            print("\n🎉 ALL TESTS PASSED! Metrics dashboard is ready for deployment.")
        else:
            print(f"\n⚠️  {len(failed_tests)} tests failed. Please review and fix issues before deployment.")
        
        return summary
    
    async def cleanup_test_environment(self):
        """Clean up test environment."""
        print("\n🧹 Cleaning up test environment...")
        
        try:
            # Stop metrics collection if running
            from fastmcp.task_management.infrastructure.monitoring.metrics_integration import get_metrics_service
            service = get_metrics_service()
            await service.stop_metrics_collection()
            
            print("  ✅ Test cleanup completed")
            
        except Exception as e:
            print(f"  ⚠️  Cleanup warning: {e}")


# Helper function to run the test
async def run_validation():
    """Run the complete validation test suite."""
    test_suite = MetricsValidationTest()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    print("MCP Metrics Dashboard Validation Test")
    print("=====================================")
    print("This test validates the complete metrics dashboard implementation.")
    print("It will test metrics collection, optimization tracking, alerts,")
    print("dashboard data generation, and automated reporting.\n")
    
    try:
        asyncio.run(run_validation())
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        exit(1)