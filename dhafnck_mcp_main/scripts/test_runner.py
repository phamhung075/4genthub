#!/usr/bin/env python3
"""
Enhanced Test Runner with Coverage and CI Integration
Part of subtask: 4fabc4f5-5750-4790-8055-68b443c7aafc
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import time

class TestRunner:
    """Enhanced test runner with coverage reporting and CI integration."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).parent.parent
        self.src_dir = self.base_dir / "src"
        self.tests_dir = self.src_dir / "tests"
        self.coverage_dir = self.base_dir / "htmlcov"
        self.reports_dir = self.base_dir / "test_reports"

    def setup_environment(self):
        """Setup test environment and dependencies."""
        # Ensure required directories exist
        self.reports_dir.mkdir(exist_ok=True)

        # Set PYTHONPATH
        pythonpath = str(self.src_dir)
        if "PYTHONPATH" in os.environ:
            pythonpath = f"{os.environ['PYTHONPATH']}:{pythonpath}"
        os.environ["PYTHONPATH"] = pythonpath

        # Set testing environment
        os.environ["TESTING"] = "true"
        os.environ["FASTMCP_TEST_MODE"] = "1"

        print(f"📂 Base directory: {self.base_dir}")
        print(f"🐍 PYTHONPATH: {pythonpath}")
        print(f"📊 Reports directory: {self.reports_dir}")

    def run_command(self, cmd: List[str], description: str) -> Dict[str, Any]:
        """Run a command and capture its output."""
        print(f"🔧 {description}")
        print(f"▶️  Command: {' '.join(cmd)}")

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            duration = time.time() - start_time

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration,
                "command": " ".join(cmd)
            }
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Command timed out",
                "duration": duration,
                "command": " ".join(cmd)
            }

    def run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests with coverage."""
        cmd = [
            "python", "-m", "pytest",
            "-m", "unit",
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "--cov-fail-under=80",
            "--junit-xml=test_reports/unit_tests.xml",
            "-v"
        ]
        return self.run_command(cmd, "Running unit tests with coverage")

    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        cmd = [
            "python", "-m", "pytest",
            "-m", "integration",
            "--junit-xml=test_reports/integration_tests.xml",
            "-v"
        ]
        return self.run_command(cmd, "Running integration tests")

    def run_e2e_tests(self) -> Dict[str, Any]:
        """Run end-to-end tests."""
        cmd = [
            "python", "-m", "pytest",
            "-m", "e2e",
            "--junit-xml=test_reports/e2e_tests.xml",
            "-v"
        ]
        return self.run_command(cmd, "Running end-to-end tests")

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests with comprehensive coverage."""
        cmd = [
            "python", "-m", "pytest",
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "--cov-fail-under=80",
            "--junit-xml=test_reports/all_tests.xml",
            "--durations=10",
            "-v"
        ]
        return self.run_command(cmd, "Running all tests with coverage")

    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests."""
        cmd = [
            "python", "-m", "pytest",
            "-m", "performance",
            "--junit-xml=test_reports/performance_tests.xml",
            "-v"
        ]
        return self.run_command(cmd, "Running performance tests")

    def run_parallel_tests(self) -> Dict[str, Any]:
        """Run tests in parallel for faster execution."""
        cmd = [
            "python", "-m", "pytest",
            "-n", "auto",
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "--junit-xml=test_reports/parallel_tests.xml",
            "-v"
        ]
        return self.run_command(cmd, "Running tests in parallel")

    def generate_coverage_report(self) -> Dict[str, Any]:
        """Generate detailed coverage report."""
        cmd = ["python", "-m", "coverage", "report", "--show-missing"]
        return self.run_command(cmd, "Generating coverage report")

    def generate_coverage_json(self) -> Dict[str, Any]:
        """Generate JSON coverage report for CI."""
        cmd = ["python", "-m", "coverage", "json", "-o", "test_reports/coverage.json"]
        return self.run_command(cmd, "Generating JSON coverage report")

    def check_coverage_threshold(self, threshold: float = 80.0) -> bool:
        """Check if coverage meets the threshold."""
        try:
            coverage_json_path = self.reports_dir / "coverage.json"
            if coverage_json_path.exists():
                with open(coverage_json_path) as f:
                    coverage_data = json.load(f)
                total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
                print(f"📊 Total coverage: {total_coverage:.2f}%")
                return total_coverage >= threshold
            return False
        except Exception as e:
            print(f"❌ Error checking coverage: {e}")
            return False

    def save_test_results(self, results: Dict[str, Any], output_file: str):
        """Save test results to JSON file."""
        results_file = self.reports_dir / output_file
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"💾 Test results saved to: {results_file}")

def main():
    parser = argparse.ArgumentParser(description="Enhanced Test Runner")
    parser.add_argument("--type", choices=["unit", "integration", "e2e", "all", "performance", "parallel"],
                       default="all", help="Type of tests to run")
    parser.add_argument("--coverage-threshold", type=float, default=80.0,
                       help="Coverage threshold percentage")
    parser.add_argument("--output", default="test_results.json",
                       help="Output file for test results")
    parser.add_argument("--ci", action="store_true",
                       help="CI mode - generate machine-readable reports")

    args = parser.parse_args()

    runner = TestRunner()
    runner.setup_environment()

    print("🧪 Starting Enhanced Test Runner")
    print("=" * 50)

    # Run tests based on type
    if args.type == "unit":
        result = runner.run_unit_tests()
    elif args.type == "integration":
        result = runner.run_integration_tests()
    elif args.type == "e2e":
        result = runner.run_e2e_tests()
    elif args.type == "performance":
        result = runner.run_performance_tests()
    elif args.type == "parallel":
        result = runner.run_parallel_tests()
    else:  # all
        result = runner.run_all_tests()

    # Generate additional reports
    if args.ci or args.type in ["all", "unit"]:
        print("\n📊 Generating additional reports...")
        coverage_result = runner.generate_coverage_report()
        json_result = runner.generate_coverage_json()

        # Check coverage threshold
        coverage_ok = runner.check_coverage_threshold(args.coverage_threshold)
        result["coverage_threshold_met"] = coverage_ok

        if not coverage_ok:
            print(f"❌ Coverage below threshold ({args.coverage_threshold}%)")
            result["success"] = False

    # Save results
    runner.save_test_results(result, args.output)

    # Print summary
    print("\n" + "=" * 50)
    if result["success"]:
        print("✅ Tests completed successfully!")
        exit_code = 0
    else:
        print("❌ Tests failed!")
        exit_code = 1

    print(f"⏱️  Total duration: {result['duration']:.2f} seconds")

    if args.ci:
        # Output JSON for CI tools
        print("\n📋 CI Results:")
        print(json.dumps({
            "success": result["success"],
            "duration": result["duration"],
            "coverage_threshold_met": result.get("coverage_threshold_met", True)
        }))

    sys.exit(exit_code)

if __name__ == "__main__":
    main()