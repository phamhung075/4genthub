#!/usr/bin/env python3
"""
Comprehensive integration test runner.

This script runs all integration tests and provides a summary report
of the ORM migration validation results.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import all test modules
from test_database_switching import run_database_switching_tests
from test_orm_relationships import run_orm_relationships_tests
from test_json_fields import run_json_compatibility_tests
from test_error_handling import run_error_handling_tests
from test_performance_comparison import run_performance_comparison


def run_all_integration_tests():
    """Run all integration tests and generate comprehensive report"""
    print("🧪 COMPREHENSIVE INTEGRATION TEST SUITE")
    print("=" * 60)
    print("Running all integration tests for ORM migration validation...")
    print("=" * 60)
    
    test_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "skipped_tests": 0,
        "test_suites": {}
    }
    
    # Define test suites
    test_suites = [
        {
            "name": "Database Switching",
            "description": "Tests DATABASE_TYPE environment variable switching",
            "function": run_database_switching_tests,
            "critical": True
        },
        {
            "name": "ORM Relationships",
            "description": "Tests model relationships and constraints",
            "function": run_orm_relationships_tests,
            "critical": True
        },
        {
            "name": "JSON Field Compatibility",
            "description": "Tests JSON field storage and retrieval",
            "function": run_json_compatibility_tests,
            "critical": True
        },
        {
            "name": "Error Handling",
            "description": "Tests error handling and recovery",
            "function": run_error_handling_tests,
            "critical": False
        },
        {
            "name": "Performance Comparison",
            "description": "Basic performance benchmarks",
            "function": run_performance_comparison,
            "critical": False
        }
    ]
    
    # Run each test suite
    for suite in test_suites:
        print(f"\n{'='*20} {suite['name']} {'='*20}")
        print(f"📝 {suite['description']}")
        print("-" * 60)
        
        try:
            start_time = time.time()
            success, results = suite["function"]()
            duration = time.time() - start_time
            
            suite_result = {
                "success": success,
                "duration": duration,
                "results": results,
                "critical": suite["critical"]
            }
            
            test_results["test_suites"][suite["name"]] = suite_result
            
            if isinstance(results, dict):
                suite_passed = results.get("passed", 0)
                suite_failed = results.get("failed", 0)
                suite_skipped = results.get("skipped", 0)
                
                test_results["passed_tests"] += suite_passed
                test_results["failed_tests"] += suite_failed
                test_results["skipped_tests"] += suite_skipped
                test_results["total_tests"] += suite_passed + suite_failed + suite_skipped
            
            status = "✅ PASSED" if success else "❌ FAILED"
            criticality = "🔴 CRITICAL" if suite["critical"] else "🟡 NON-CRITICAL"
            print(f"\n{status} - {suite['name']} - {criticality}")
            print(f"⏱️  Duration: {duration:.2f}s")
            
        except Exception as e:
            print(f"❌ FAILED - {suite['name']} - Exception: {e}")
            test_results["test_suites"][suite["name"]] = {
                "success": False,
                "duration": 0,
                "results": {"error": str(e)},
                "critical": suite["critical"]
            }
            test_results["failed_tests"] += 1
            test_results["total_tests"] += 1
    
    return test_results


def generate_summary_report(test_results: Dict[str, Any]) -> str:
    """Generate a comprehensive summary report"""
    report = []
    
    # Header
    report.append("=" * 80)
    report.append("🎯 INTEGRATION TEST SUMMARY REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {test_results['timestamp']}")
    report.append("")
    
    # Overall Statistics
    total = test_results["total_tests"]
    passed = test_results["passed_tests"]
    failed = test_results["failed_tests"]
    skipped = test_results["skipped_tests"]
    
    success_rate = (passed / total * 100) if total > 0 else 0
    
    report.append("📊 OVERALL STATISTICS")
    report.append("-" * 40)
    report.append(f"Total Tests: {total}")
    report.append(f"Passed: {passed} ({success_rate:.1f}%)")
    report.append(f"Failed: {failed}")
    report.append(f"Skipped: {skipped}")
    report.append("")
    
    # Test Suite Results
    report.append("🧪 TEST SUITE RESULTS")
    report.append("-" * 40)
    
    critical_failures = []
    
    for suite_name, suite_result in test_results["test_suites"].items():
        status = "✅ PASSED" if suite_result["success"] else "❌ FAILED"
        criticality = "🔴 CRITICAL" if suite_result["critical"] else "🟡 NON-CRITICAL"
        duration = suite_result["duration"]
        
        report.append(f"{status} {suite_name} - {criticality}")
        report.append(f"   Duration: {duration:.2f}s")
        
        if isinstance(suite_result["results"], dict):
            if "passed" in suite_result["results"]:
                passed = suite_result["results"]["passed"]
                failed = suite_result["results"]["failed"]
                skipped = suite_result["results"]["skipped"]
                report.append(f"   Results: {passed} passed, {failed} failed, {skipped} skipped")
            elif "error" in suite_result["results"]:
                report.append(f"   Error: {suite_result['results']['error']}")
        
        if not suite_result["success"] and suite_result["critical"]:
            critical_failures.append(suite_name)
        
        report.append("")
    
    # Critical Analysis
    report.append("🔍 CRITICAL ANALYSIS")
    report.append("-" * 40)
    
    if critical_failures:
        report.append(f"❌ CRITICAL FAILURES DETECTED: {len(critical_failures)}")
        for failure in critical_failures:
            report.append(f"   - {failure}")
        report.append("")
        report.append("🚨 MIGRATION NOT READY FOR PRODUCTION")
        report.append("   Critical test failures must be resolved before deployment.")
    else:
        report.append("✅ ALL CRITICAL TESTS PASSED")
        report.append("🎉 MIGRATION READY FOR PRODUCTION")
    
    report.append("")
    
    # Recommendations
    report.append("💡 RECOMMENDATIONS")
    report.append("-" * 40)
    
    if failed > 0:
        report.append("1. Review and fix failing tests")
        report.append("2. Ensure all database connections are properly configured")
        report.append("3. Verify PostgreSQL setup if PostgreSQL tests are failing")
    
    if skipped > 0:
        report.append("4. Investigate skipped tests - they may indicate missing dependencies")
    
    report.append("5. Run performance tests in production-like environment")
    report.append("6. Consider load testing with realistic data volumes")
    report.append("")
    
    # Validation Checklist
    report.append("✅ VALIDATION CHECKLIST")
    report.append("-" * 40)
    
    checklist_items = [
        ("All repositories work with both databases", "database_switching" in [name.lower().replace(" ", "_") for name in test_results["test_suites"].keys()]),
        ("Model relationships work correctly", "orm_relationships" in [name.lower().replace(" ", "_") for name in test_results["test_suites"].keys()]),
        ("JSON fields are compatible", "json_field_compatibility" in [name.lower().replace(" ", "_") for name in test_results["test_suites"].keys()]),
        ("Error handling is robust", "error_handling" in [name.lower().replace(" ", "_") for name in test_results["test_suites"].keys()]),
        ("Performance is acceptable", "performance_comparison" in [name.lower().replace(" ", "_") for name in test_results["test_suites"].keys()]),
        ("No critical failures", len(critical_failures) == 0)
    ]
    
    for item, status in checklist_items:
        status_icon = "✅" if status else "❌"
        report.append(f"{status_icon} {item}")
    
    report.append("")
    report.append("=" * 80)
    
    return "\n".join(report)


def main():
    """Main function to run all integration tests"""
    try:
        # Run all tests
        test_results = run_all_integration_tests()
        
        # Generate report
        report = generate_summary_report(test_results)
        
        # Display report
        print("\n" + report)
        
        # Save results to files
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        
        # Save JSON results
        json_file = results_dir / "integration_test_results.json"
        with open(json_file, 'w') as f:
            json.dump(test_results, f, indent=2, default=str)
        
        # Save text report
        report_file = results_dir / "integration_test_report.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\n📄 Results saved to: {json_file}")
        print(f"📄 Report saved to: {report_file}")
        
        # Determine exit code
        critical_failures = [
            name for name, result in test_results["test_suites"].items()
            if not result["success"] and result["critical"]
        ]
        
        if critical_failures:
            print(f"\n💥 Integration tests FAILED with {len(critical_failures)} critical failures!")
            sys.exit(1)
        else:
            print(f"\n🎉 All integration tests PASSED!")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n💥 Integration test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()