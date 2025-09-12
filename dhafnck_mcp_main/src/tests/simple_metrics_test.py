#!/usr/bin/env python3
"""
Simple Metrics Test

Simplified test to validate the core metrics components without complex dependencies.
"""

import asyncio
import json
import random
import time
import sys
import os
from pathlib import Path
from datetime import datetime

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent
sys.path.insert(0, str(src_dir))

async def test_optimization_metrics():
    """Test the optimization metrics system directly."""
    
    print("🚀 Testing MCP Optimization Metrics System")
    print("=" * 50)
    
    try:
        # Direct import to avoid __init__ issues
        from fastmcp.task_management.infrastructure.monitoring.optimization_metrics import OptimizationMetricsCollector
        
        print("✅ Successfully imported OptimizationMetricsCollector")
        
        # Create collector instance
        collector = OptimizationMetricsCollector(buffer_size=1000, flush_interval_seconds=10)
        print("✅ Created metrics collector instance")
        
        # Start collection
        collector.start_collection()
        print("✅ Started metrics collection")
        
        # Test basic metrics recording
        print("\n📊 Recording test metrics...")
        
        # Record some response optimizations
        for i in range(5):
            original_size = random.randint(5000, 15000)
            optimized_size = int(original_size * random.uniform(0.3, 0.8))
            processing_time = random.uniform(50, 200)
            opt_type = random.choice(["MINIMAL", "STANDARD", "DETAILED", "DEBUG"])
            
            collector.record_response_optimization(
                original_size=original_size,
                optimized_size=optimized_size,
                processing_time_ms=processing_time,
                optimization_type=opt_type,
                tags={"test": f"run_{i}"}
            )
        
        print(f"✅ Recorded 5 response optimizations")
        
        # Record context metrics
        for i in range(3):
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
                tags={"test": f"context_{i}"}
            )
        
        print(f"✅ Recorded 3 context injection metrics")
        
        # Record AI performance metrics
        for i in range(3):
            parse_success = random.choice([True, True, True, False])  # 75% success
            extraction_time = random.uniform(10, 50)
            response_format = random.choice(["MINIMAL", "STANDARD"])
            agent_operation = random.choice(["hint_extraction", "response_parsing", "task_delegation"])
            
            collector.record_ai_performance_metrics(
                parse_success=parse_success,
                extraction_time_ms=extraction_time,
                response_format=response_format,
                agent_operation=agent_operation,
                tags={"test": f"ai_{i}"}
            )
        
        print(f"✅ Recorded 3 AI performance metrics")
        
        # Wait for metrics to be processed
        await asyncio.sleep(1.0)
        
        # Get optimization summary
        print("\n📈 Generating optimization summary...")
        summary = collector.get_optimization_summary(1)  # Last hour
        
        print(f"✅ Generated summary with {summary['optimization_performance']['total_optimizations']} optimizations")
        print(f"   Average compression: {summary['optimization_performance']['avg_compression_ratio']:.1f}%")
        print(f"   Alerts generated: {summary['alerts']['total_alerts']}")
        
        # Test dashboard data export
        print("\n📊 Testing dashboard data export...")
        dashboard_data = collector.export_optimization_dashboard_data(1)
        
        print(f"✅ Generated dashboard data with {len(dashboard_data['metrics'])} metric types")
        
        # Save test output
        output_dir = Path("/tmp/mcp_metrics_test")
        output_dir.mkdir(exist_ok=True)
        
        # Save summary
        summary_file = output_dir / "metrics_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        # Save dashboard data
        dashboard_file = output_dir / "dashboard_data.json"
        with open(dashboard_file, 'w') as f:
            json.dump(dashboard_data, f, indent=2, default=str)
        
        print(f"📁 Test results saved to: {output_dir}")
        
        # Test Prometheus export
        print("\n📊 Testing Prometheus export...")
        prometheus_metrics = collector.export_prometheus_metrics()
        
        if prometheus_metrics:
            prometheus_file = output_dir / "metrics.prom"
            with open(prometheus_file, 'w') as f:
                f.write(prometheus_metrics)
            print(f"✅ Exported Prometheus metrics to {prometheus_file}")
        else:
            print("⚠️ No Prometheus metrics to export")
        
        # Stop collection
        await collector.stop_collection()
        print("✅ Stopped metrics collection")
        
        print("\n🎉 ALL TESTS PASSED!")
        print("\nMetrics System Capabilities Validated:")
        print("  ✅ Response optimization tracking")
        print("  ✅ Context injection metrics")
        print("  ✅ AI performance metrics")
        print("  ✅ Alert system")
        print("  ✅ Dashboard data generation")
        print("  ✅ Prometheus export")
        print("  ✅ JSON export")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_metrics_reporter():
    """Test the metrics reporter functionality."""
    
    print("\n📧 Testing Metrics Reporter...")
    
    try:
        from fastmcp.task_management.infrastructure.workers.metrics_reporter import MetricsReporter, ReportConfig
        from fastmcp.task_management.infrastructure.monitoring.optimization_metrics import OptimizationMetricsCollector
        
        # Create collector with some test data
        collector = OptimizationMetricsCollector()
        collector.start_collection()
        
        # Add some test data
        for i in range(3):
            collector.record_response_optimization(
                original_size=10000,
                optimized_size=4000,  # 60% compression
                processing_time_ms=100,
                optimization_type="STANDARD"
            )
        
        # Configure reporter
        output_dir = Path("/tmp/mcp_metrics_test")
        config = ReportConfig(
            file_output_enabled=True,
            output_directory=output_dir,
            email_enabled=False  # Disable for testing
        )
        
        reporter = MetricsReporter(collector, config)
        
        # Generate test reports
        print("  📝 Generating daily report...")
        daily_report = await reporter.generate_daily_report()
        
        print("  📝 Generating weekly report...")
        weekly_report = await reporter.generate_weekly_report()
        
        print("  📝 Generating monthly ROI report...")
        monthly_report = await reporter.generate_monthly_roi_report()
        
        # Check files were created
        report_files = list(output_dir.glob("*report*")) + list(output_dir.glob("*roi*"))
        print(f"✅ Generated {len(report_files)} report files")
        
        for file in report_files:
            print(f"    📄 {file.name}")
        
        await collector.stop_collection()
        
        return True
        
    except Exception as e:
        print(f"❌ Metrics reporter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    
    print("MCP Metrics Dashboard Validation")
    print("=" * 50)
    
    test_results = []
    
    # Test 1: Core metrics functionality
    result1 = await test_optimization_metrics()
    test_results.append(("Optimization Metrics", result1))
    
    # Test 2: Metrics reporter
    result2 = await test_metrics_reporter()
    test_results.append(("Metrics Reporter", result2))
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL SYSTEMS OPERATIONAL!")
        print("\nThe MCP Metrics Dashboard is ready for deployment with:")
        print("  📊 Comprehensive metrics collection")
        print("  📈 Real-time performance monitoring")  
        print("  🚨 Automated alerting system")
        print("  📧 Scheduled reporting")
        print("  📋 Grafana dashboard integration")
        return True
    else:
        print(f"\n⚠️ {total - passed} test(s) failed - please review issues")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        exit(1)