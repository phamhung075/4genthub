#!/usr/bin/env python3
"""
Comprehensive test runner for MCP tool unit tests
Runs all tool tests with detailed reporting and validation
"""

import sys
import os
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@dataclass
class TestResult:
    """Test result data structure"""
    test_file: str
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    exit_code: int
    output: str
    error_output: str


@dataclass
class TestSummary:
    """Summary of all test results"""
    total_tests: int
    total_passed: int
    total_failed: int
    total_skipped: int
    total_errors: int
    total_duration: float
    success_rate: float
    results: List[TestResult]


class ToolTestRunner:
    """Comprehensive test runner for MCP tools"""
    
    def __init__(self, test_dir: Optional[Path] = None):
        self.test_dir = test_dir or Path(__file__).parent
        self.results: List[TestResult] = []
        
    def run_all_tests(self, verbose: bool = True, fail_fast: bool = False) -> TestSummary:
        """Run all tool tests and return summary"""
        print("🧪 Starting MCP Tool Test Suite")
        print(f"📁 Test directory: {self.test_dir}")
        print("=" * 60)
        
        test_files = self._discover_test_files()
        print(f"📋 Discovered {len(test_files)} test files:")
        for test_file in test_files:
            print(f"   • {test_file.name}")
        print()
        
        start_time = time.time()
        
        for test_file in test_files:
            if fail_fast and any(r.failed > 0 or r.errors > 0 for r in self.results):
                print(f"⏭️  Skipping {test_file.name} (fail-fast mode)")
                continue
                
            result = self._run_single_test(test_file, verbose)
            self.results.append(result)
            
            if verbose:
                self._print_test_result(result)
        
        total_duration = time.time() - start_time
        summary = self._generate_summary(total_duration)
        
        print("\n" + "=" * 60)
        self._print_summary(summary)
        
        return summary
    
    def run_specific_tests(self, test_names: List[str], verbose: bool = True) -> TestSummary:
        """Run specific tests by name"""
        print(f"🎯 Running specific tests: {', '.join(test_names)}")
        print("=" * 60)
        
        test_files = []
        for test_name in test_names:
            test_file = self.test_dir / f"test_{test_name}_tools.py"
            if test_file.exists():
                test_files.append(test_file)
            else:
                print(f"⚠️  Test file not found: {test_file}")
        
        start_time = time.time()
        
        for test_file in test_files:
            result = self._run_single_test(test_file, verbose)
            self.results.append(result)
            
            if verbose:
                self._print_test_result(result)
        
        total_duration = time.time() - start_time
        summary = self._generate_summary(total_duration)
        
        print("\n" + "=" * 60)
        self._print_summary(summary)
        
        return summary
    
    def validate_tool_coverage(self) -> Dict[str, Any]:
        """Validate that all tools have tests"""
        print("🔍 Validating tool test coverage...")
        
        # Expected tool test files based on our analysis
        expected_tools = [
            "task_management",
            "subtask_management", 
            "project_management",
            "agent_management",
            "template_management",
            "connection_management"
        ]
        
        coverage_report = {
            "expected_tools": expected_tools,
            "found_tests": [],
            "missing_tests": [],
            "coverage_percentage": 0
        }
        
        for tool in expected_tools:
            test_file = self.test_dir / f"test_{tool}_tools.py"
            if test_file.exists():
                coverage_report["found_tests"].append(tool)
            else:
                coverage_report["missing_tests"].append(tool)
        
        coverage_report["coverage_percentage"] = (
            len(coverage_report["found_tests"]) / len(expected_tools) * 100
        )
        
        print(f"✅ Tool test coverage: {coverage_report['coverage_percentage']:.1f}%")
        print(f"📊 Found tests for: {', '.join(coverage_report['found_tests'])}")
        
        if coverage_report["missing_tests"]:
            print(f"❌ Missing tests for: {', '.join(coverage_report['missing_tests'])}")
        
        return coverage_report
    
    def _discover_test_files(self) -> List[Path]:
        """Discover all test files in the directory"""
        return sorted(self.test_dir.glob("test_*_tools.py"))
    
    def _run_single_test(self, test_file: Path, verbose: bool) -> TestResult:
        """Run a single test file"""
        start_time = time.time()
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_file),
            "-v" if verbose else "-q",
            "--tb=short",
            "--maxfail=10",
            "--json-report",
            "--json-report-file=/tmp/pytest_report.json"
        ]
        
        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                cwd=self.test_dir
            )
            
            duration = time.time() - start_time
            
            # Parse pytest JSON report if available
            stats = self._parse_pytest_output(process.stdout, process.stderr)
            
            return TestResult(
                test_file=test_file.name,
                passed=stats.get("passed", 0),
                failed=stats.get("failed", 0),
                skipped=stats.get("skipped", 0),
                errors=stats.get("errors", 0),
                duration=duration,
                exit_code=process.returncode,
                output=process.stdout,
                error_output=process.stderr
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestResult(
                test_file=test_file.name,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=duration,
                exit_code=-1,
                output="",
                error_output="Test timed out after 5 minutes"
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_file=test_file.name,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=duration,
                exit_code=-1,
                output="",
                error_output=f"Exception running test: {str(e)}"
            )
    
    def _parse_pytest_output(self, stdout: str, stderr: str) -> Dict[str, int]:
        """Parse pytest output to extract test statistics"""
        stats = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
        
        # Try to parse JSON report first
        json_report_path = Path("/tmp/pytest_report.json")
        if json_report_path.exists():
            try:
                with open(json_report_path) as f:
                    report = json.load(f)
                    summary = report.get("summary", {})
                    stats["passed"] = summary.get("passed", 0)
                    stats["failed"] = summary.get("failed", 0)
                    stats["skipped"] = summary.get("skipped", 0)
                    stats["errors"] = summary.get("error", 0)
                json_report_path.unlink()  # Clean up
                return stats
            except Exception:
                pass
        
        # Fallback to parsing stdout
        lines = stdout.split('\n')
        for line in lines:
            if "passed" in line and ("failed" in line or "error" in line or "skipped" in line):
                # Parse summary line like "5 passed, 2 failed, 1 skipped"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit() and i + 1 < len(parts):
                        next_part = parts[i + 1]
                        if "passed" in next_part:
                            stats["passed"] = int(part)
                        elif "failed" in next_part:
                            stats["failed"] = int(part)
                        elif "skipped" in next_part:
                            stats["skipped"] = int(part)
                        elif "error" in next_part:
                            stats["errors"] = int(part)
                break
        
        return stats
    
    def _print_test_result(self, result: TestResult):
        """Print result for a single test"""
        status = "✅" if result.exit_code == 0 else "❌"
        print(f"{status} {result.test_file}")
        print(f"   📊 {result.passed} passed, {result.failed} failed, {result.skipped} skipped, {result.errors} errors")
        print(f"   ⏱️  Duration: {result.duration:.2f}s")
        
        if result.failed > 0 or result.errors > 0:
            print(f"   🚨 Errors/Failures:")
            # Print last few lines of stderr for context
            if result.error_output:
                error_lines = result.error_output.strip().split('\n')[-3:]
                for line in error_lines:
                    print(f"      {line}")
        print()
    
    def _generate_summary(self, total_duration: float) -> TestSummary:
        """Generate test summary"""
        total_tests = sum(r.passed + r.failed + r.skipped + r.errors for r in self.results)
        total_passed = sum(r.passed for r in self.results)
        total_failed = sum(r.failed for r in self.results)
        total_skipped = sum(r.skipped for r in self.results)
        total_errors = sum(r.errors for r in self.results)
        
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        return TestSummary(
            total_tests=total_tests,
            total_passed=total_passed,
            total_failed=total_failed,
            total_skipped=total_skipped,
            total_errors=total_errors,
            total_duration=total_duration,
            success_rate=success_rate,
            results=self.results
        )
    
    def _print_summary(self, summary: TestSummary):
        """Print comprehensive test summary"""
        print("📋 TEST SUMMARY")
        print(f"🎯 Total Tests: {summary.total_tests}")
        print(f"✅ Passed: {summary.total_passed}")
        print(f"❌ Failed: {summary.total_failed}")
        print(f"⏭️  Skipped: {summary.total_skipped}")
        print(f"🚨 Errors: {summary.total_errors}")
        print(f"⏱️  Total Duration: {summary.total_duration:.2f}s")
        print(f"📊 Success Rate: {summary.success_rate:.1f}%")
        
        if summary.total_failed > 0 or summary.total_errors > 0:
            print("\n❌ FAILED TESTS:")
            for result in summary.results:
                if result.failed > 0 or result.errors > 0:
                    print(f"   • {result.test_file}: {result.failed} failed, {result.errors} errors")
        
        print(f"\n🏁 Test run completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Overall status
        if summary.total_failed == 0 and summary.total_errors == 0:
            print("🎉 ALL TESTS PASSED!")
        else:
            print("⚠️  SOME TESTS FAILED - Review failures above")
    
    def save_report(self, summary: TestSummary, output_file: Path):
        """Save detailed test report to file"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": summary.total_tests,
                "total_passed": summary.total_passed,
                "total_failed": summary.total_failed,
                "total_skipped": summary.total_skipped,
                "total_errors": summary.total_errors,
                "total_duration": summary.total_duration,
                "success_rate": summary.success_rate
            },
            "results": [
                {
                    "test_file": r.test_file,
                    "passed": r.passed,
                    "failed": r.failed,
                    "skipped": r.skipped,
                    "errors": r.errors,
                    "duration": r.duration,
                    "exit_code": r.exit_code
                }
                for r in summary.results
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Detailed report saved to: {output_file}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run MCP tool unit tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fail-fast", "-x", action="store_true", help="Stop on first failure")
    parser.add_argument("--specific", nargs="+", help="Run specific tests (e.g., task_management project_management)")
    parser.add_argument("--coverage", action="store_true", help="Check test coverage")
    parser.add_argument("--report", type=Path, help="Save detailed report to file")
    
    args = parser.parse_args()
    
    runner = ToolTestRunner()
    
    # Check coverage if requested
    if args.coverage:
        coverage_report = runner.validate_tool_coverage()
        if coverage_report["missing_tests"]:
            print("❌ Missing test coverage detected!")
            return 1
    
    # Run tests
    if args.specific:
        summary = runner.run_specific_tests(args.specific, args.verbose)
    else:
        summary = runner.run_all_tests(args.verbose, args.fail_fast)
    
    # Save report if requested
    if args.report:
        runner.save_report(summary, args.report)
    
    # Exit with appropriate code
    if summary.total_failed > 0 or summary.total_errors > 0:
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())