#!/usr/bin/env python3
"""
MCP Auto-Injection Test Runner

Comprehensive test runner for the MCP auto-injection system with various
test execution modes, reporting, and performance analysis.

Usage:
    python run_mcp_auto_injection_tests.py [options]

Features:
- Multiple test execution modes (unit, integration, e2e, performance)
- Parallel test execution
- Comprehensive reporting
- Performance analysis
- Coverage reporting
- CI/CD integration support
"""

import argparse
import sys
import subprocess
import time
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project paths
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / ".claude" / "hooks"))
sys.path.insert(0, str(project_root / "dhafnck_mcp_main" / "src"))


class MCPTestRunner:
    """Comprehensive test runner for MCP auto-injection system."""
    
    def __init__(self):
        self.test_root = Path(__file__).parent
        self.project_root = self.test_root.parent.parent.parent
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def run_tests(self, 
                  test_types: List[str] = None,
                  parallel: bool = False,
                  coverage: bool = False,
                  verbose: bool = False,
                  fast: bool = False,
                  output_format: str = "detailed") -> Dict[str, Any]:
        """Run MCP auto-injection tests with specified configuration."""
        
        self.start_time = time.time()
        
        # Default to all test types if none specified
        if not test_types:
            test_types = ["unit", "integration", "e2e"]
        
        print(f"🚀 Starting MCP Auto-Injection Test Suite")
        print(f"📅 Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Test types: {', '.join(test_types)}")
        print(f"⚡ Parallel execution: {'Enabled' if parallel else 'Disabled'}")
        print(f"📊 Coverage analysis: {'Enabled' if coverage else 'Disabled'}")
        print("-" * 60)
        
        # Set up environment
        self._setup_test_environment(fast)
        
        # Run tests for each type
        for test_type in test_types:
            print(f"\n🔍 Running {test_type.upper()} tests...")
            result = self._run_test_type(
                test_type=test_type,
                parallel=parallel,
                coverage=coverage,
                verbose=verbose,
                fast=fast
            )
            self.results[test_type] = result
            
            # Print immediate results
            self._print_test_type_results(test_type, result)
        
        self.end_time = time.time()
        
        # Generate comprehensive report
        report = self._generate_report(output_format)
        
        # Print final summary
        self._print_final_summary()
        
        return report
    
    def _setup_test_environment(self, fast: bool = False):
        """Set up test environment."""
        env_vars = {
            "TESTING_MODE": "true",
            "SESSION_CACHE_TTL": "10" if fast else "60",
            "TASK_CACHE_TTL": "5" if fast else "30", 
            "GIT_CACHE_TTL": "3" if fast else "15",
            "FAST_TESTS_ONLY": "true" if fast else "false",
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
        
        if fast:
            os.environ["SKIP_PERFORMANCE_TESTS"] = "true"
            print("⚡ Fast mode enabled - skipping slow and performance tests")
    
    def _run_test_type(self, 
                      test_type: str,
                      parallel: bool = False,
                      coverage: bool = False,
                      verbose: bool = False,
                      fast: bool = False) -> Dict[str, Any]:
        """Run tests for a specific test type."""
        
        start_time = time.time()
        
        # Build pytest command
        cmd = ["python", "-m", "pytest"]
        
        # Add test directories
        if test_type == "unit":
            cmd.extend([str(self.test_root / "unit" / "mcp_auto_injection")])
        elif test_type == "integration":
            cmd.extend([str(self.test_root / "integration" / "mcp_auto_injection")])
        elif test_type == "e2e":
            cmd.extend([str(self.test_root / "e2e" / "mcp_auto_injection")])
        elif test_type == "performance":
            cmd.extend(["-m", "performance"])
        
        # Add common options
        cmd.extend([
            f"--confcutdir={self.test_root}",
            "--tb=short",
            "--strict-markers",
        ])
        
        # Add marker filtering
        if test_type != "performance":
            cmd.extend(["-m", test_type])
        
        # Add parallel execution
        if parallel:
            cmd.extend(["-n", "auto"])
        
        # Add coverage
        if coverage:
            coverage_dir = self.test_root / "coverage" / test_type
            coverage_dir.mkdir(parents=True, exist_ok=True)
            
            cmd.extend([
                "--cov=utils",
                "--cov=session_start",
                f"--cov-report=html:{coverage_dir}/html",
                f"--cov-report=json:{coverage_dir}/coverage.json",
                "--cov-report=term-missing"
            ])
        
        # Add verbosity
        if verbose:
            cmd.extend(["-v", "-s"])
        else:
            cmd.extend(["-q"])
        
        # Add fast mode options
        if fast:
            cmd.extend([
                "--maxfail=5",  # Stop after 5 failures
                "-x"  # Stop on first failure for debugging
            ])
        
        # Add JSON output for result parsing
        json_report = self.test_root / "reports" / f"{test_type}_results.json"
        json_report.parent.mkdir(parents=True, exist_ok=True)
        cmd.extend([f"--json-report={json_report}"])
        
        # Run tests
        try:
            print(f"📋 Command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            duration = time.time() - start_time
            
            # Parse results
            test_results = self._parse_test_results(json_report, result)
            test_results.update({
                "duration": duration,
                "command": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            })
            
            return test_results
            
        except Exception as e:
            return {
                "error": str(e),
                "duration": time.time() - start_time,
                "command": " ".join(cmd),
                "returncode": 1
            }
    
    def _parse_test_results(self, json_report: Path, subprocess_result) -> Dict[str, Any]:
        """Parse test results from JSON report."""
        results = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "total": 0,
            "success_rate": 0.0,
            "test_details": []
        }
        
        try:
            if json_report.exists():
                with open(json_report, 'r') as f:
                    json_data = json.load(f)
                
                summary = json_data.get("summary", {})
                results.update({
                    "passed": summary.get("passed", 0),
                    "failed": summary.get("failed", 0),
                    "skipped": summary.get("skipped", 0),
                    "errors": summary.get("error", 0),
                    "total": summary.get("total", 0)
                })
                
                if results["total"] > 0:
                    results["success_rate"] = results["passed"] / results["total"]
                
                # Extract test details
                for test in json_data.get("tests", []):
                    results["test_details"].append({
                        "name": test.get("nodeid", "unknown"),
                        "outcome": test.get("outcome", "unknown"),
                        "duration": test.get("duration", 0),
                        "error": test.get("call", {}).get("longrepr", None) if test.get("outcome") == "failed" else None
                    })
        
        except Exception as e:
            print(f"Warning: Could not parse JSON report: {e}")
            # Fall back to parsing stdout
            stdout = subprocess_result.stdout
            if "failed" in stdout or "passed" in stdout:
                # Basic parsing from pytest output
                lines = stdout.split('\n')
                for line in lines:
                    if " passed" in line or " failed" in line:
                        # Extract basic numbers
                        import re
                        numbers = re.findall(r'(\d+) (\w+)', line)
                        for count, status in numbers:
                            if status in results:
                                results[status] = int(count)
                                results["total"] += int(count)
        
        return results
    
    def _print_test_type_results(self, test_type: str, results: Dict[str, Any]):
        """Print results for a specific test type."""
        print(f"\n📊 {test_type.upper()} Test Results:")
        
        if "error" in results:
            print(f"   ❌ Error: {results['error']}")
            return
        
        total = results.get("total", 0)
        passed = results.get("passed", 0)
        failed = results.get("failed", 0)
        skipped = results.get("skipped", 0)
        duration = results.get("duration", 0)
        
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⏭️  Skipped: {skipped}")
        print(f"   📊 Total: {total}")
        print(f"   🎯 Success Rate: {results.get('success_rate', 0):.1%}")
        print(f"   ⏱️  Duration: {duration:.2f}s")
        
        # Show failed tests
        if failed > 0:
            print(f"\n   💥 Failed Tests:")
            failed_tests = [test for test in results.get("test_details", []) if test["outcome"] == "failed"]
            for test in failed_tests[:5]:  # Show first 5 failures
                print(f"      - {test['name']}")
                if test.get('error'):
                    error_lines = str(test['error']).split('\n')[:2]  # First 2 lines
                    for line in error_lines:
                        if line.strip():
                            print(f"        {line.strip()}")
            
            if len(failed_tests) > 5:
                print(f"      ... and {len(failed_tests) - 5} more failures")
    
    def _generate_report(self, output_format: str) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        # Aggregate results
        aggregate_results = {
            "total_passed": sum(r.get("passed", 0) for r in self.results.values()),
            "total_failed": sum(r.get("failed", 0) for r in self.results.values()),
            "total_skipped": sum(r.get("skipped", 0) for r in self.results.values()),
            "total_errors": sum(r.get("errors", 0) for r in self.results.values()),
        }
        
        aggregate_results["total_tests"] = sum([
            aggregate_results["total_passed"],
            aggregate_results["total_failed"],
            aggregate_results["total_skipped"],
            aggregate_results["total_errors"]
        ])
        
        aggregate_results["overall_success_rate"] = (
            aggregate_results["total_passed"] / max(aggregate_results["total_tests"], 1)
        )
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "duration": total_duration,
            "test_types": list(self.results.keys()),
            "aggregate_results": aggregate_results,
            "detailed_results": self.results,
            "environment": {
                "python_version": sys.version,
                "platform": sys.platform,
                "testing_mode": os.environ.get("TESTING_MODE", "false"),
                "fast_mode": os.environ.get("FAST_TESTS_ONLY", "false")
            }
        }
        
        # Save report to file
        report_file = self.test_root / "reports" / f"mcp_test_report_{int(time.time())}.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📋 Detailed report saved to: {report_file}")
        
        return report
    
    def _print_final_summary(self):
        """Print final test summary."""
        if not self.results:
            print("\n❌ No test results to summarize")
            return
        
        total_duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        print("\n" + "=" * 60)
        print("🏁 FINAL TEST SUMMARY")
        print("=" * 60)
        
        # Aggregate statistics
        total_passed = sum(r.get("passed", 0) for r in self.results.values())
        total_failed = sum(r.get("failed", 0) for r in self.results.values())
        total_skipped = sum(r.get("skipped", 0) for r in self.results.values())
        total_tests = total_passed + total_failed + total_skipped
        
        print(f"📊 Overall Results:")
        print(f"   ✅ Total Passed: {total_passed}")
        print(f"   ❌ Total Failed: {total_failed}")
        print(f"   ⏭️  Total Skipped: {total_skipped}")
        print(f"   📈 Total Tests: {total_tests}")
        
        if total_tests > 0:
            success_rate = total_passed / total_tests
            print(f"   🎯 Success Rate: {success_rate:.1%}")
            
            if success_rate >= 0.95:
                print("   🎉 EXCELLENT - High success rate!")
            elif success_rate >= 0.85:
                print("   👍 GOOD - Acceptable success rate")
            elif success_rate >= 0.70:
                print("   ⚠️  WARNING - Low success rate")
            else:
                print("   💥 CRITICAL - Very low success rate")
        
        print(f"   ⏱️  Total Duration: {total_duration:.2f}s")
        
        # Per test type summary
        print(f"\n📋 By Test Type:")
        for test_type, results in self.results.items():
            duration = results.get("duration", 0)
            success_rate = results.get("success_rate", 0)
            print(f"   {test_type.upper():12} - {success_rate:.1%} success in {duration:.1f}s")
        
        # Performance insights
        if total_duration > 0:
            tests_per_second = total_tests / total_duration
            print(f"\n⚡ Performance: {tests_per_second:.1f} tests/second")
        
        # Final verdict
        if total_failed == 0:
            print(f"\n🎉 ALL TESTS PASSED! MCP auto-injection system is working correctly.")
        else:
            print(f"\n⚠️  {total_failed} test(s) failed. Check the detailed output above for failures.")
        
        print("=" * 60)


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner for MCP auto-injection system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python run_mcp_auto_injection_tests.py
  
  # Run only unit tests
  python run_mcp_auto_injection_tests.py --unit
  
  # Run tests with coverage and parallel execution
  python run_mcp_auto_injection_tests.py --coverage --parallel
  
  # Fast test run for development
  python run_mcp_auto_injection_tests.py --fast --unit
  
  # Full test suite with all options
  python run_mcp_auto_injection_tests.py --unit --integration --e2e --performance --coverage --parallel --verbose
        """
    )
    
    # Test type selection
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--all", action="store_true", help="Run all test types")
    
    # Execution options
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage reports")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fast", action="store_true", help="Fast mode - skip slow tests")
    
    # Output options
    parser.add_argument("--output-format", choices=["simple", "detailed", "json"], 
                       default="detailed", help="Output format")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    
    args = parser.parse_args()
    
    # Determine test types to run
    test_types = []
    if args.unit:
        test_types.append("unit")
    if args.integration:
        test_types.append("integration") 
    if args.e2e:
        test_types.append("e2e")
    if args.performance:
        test_types.append("performance")
    if args.all:
        test_types = ["unit", "integration", "e2e", "performance"]
    
    # Default to unit and integration if nothing specified
    if not test_types:
        test_types = ["unit", "integration"]
    
    # Create and run test runner
    runner = MCPTestRunner()
    
    try:
        report = runner.run_tests(
            test_types=test_types,
            parallel=args.parallel,
            coverage=args.coverage,
            verbose=args.verbose and not args.quiet,
            fast=args.fast,
            output_format=args.output_format
        )
        
        # Exit with appropriate code
        total_failed = report.get("aggregate_results", {}).get("total_failed", 0)
        sys.exit(1 if total_failed > 0 else 0)
        
    except KeyboardInterrupt:
        print("\n⏹️  Test run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test runner error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()