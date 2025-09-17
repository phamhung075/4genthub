#!/usr/bin/env python3
"""
MCP Controllers Test Runner

This script provides a comprehensive test runner for all MCP controller unit tests
with detailed reporting, coverage analysis, and test result summary.

Features:
- Run individual controller tests or all tests
- Generate coverage reports (HTML and terminal)
- Detailed test result analysis
- Performance timing
- Error categorization
- Integration with CI/CD pipelines

Usage:
    # Run all MCP controller tests
    python test_runner.py

    # Run specific controller tests
    python test_runner.py --controller task
    python test_runner.py --controller project

    # Run with coverage reporting
    python test_runner.py --coverage

    # Run with detailed output
    python test_runner.py --verbose

    # Generate HTML coverage report
    python test_runner.py --coverage --html

    # Run in CI mode (minimal output)
    python test_runner.py --ci
"""

import sys
import os
import argparse
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class MCPControllerTestRunner:
    """Comprehensive test runner for MCP controller unit tests."""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.project_root = project_root
        self.results = {}
        
        # Available controller tests
        self.controller_tests = {
            'task': 'test_task_mcp_controller.py',
            'project': 'test_project_mcp_controller.py',
            'subtask': 'test_subtask_mcp_controller.py',
            'git_branch': 'test_git_branch_mcp_controller.py',
            'context': 'test_context_mcp_controller.py',
            'agent': 'test_agent_mcp_controller.py'
        }
        
        # Test categories for reporting
        self.test_categories = {
            'crud_operations': ['create', 'get', 'update', 'delete', 'list'],
            'authentication': ['auth', 'permission', 'unauthenticated'],
            'validation': ['validation', 'invalid', 'missing', 'required'],
            'error_handling': ['error', 'exception', 'failure', 'handling'],
            'edge_cases': ['edge', 'concurrent', 'large', 'special']
        }

    def run_tests(
        self, 
        controllers: Optional[List[str]] = None,
        coverage: bool = False,
        verbose: bool = False,
        html_coverage: bool = False,
        ci_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Run MCP controller tests with specified options.
        
        Args:
            controllers: List of controller names to test (None for all)
            coverage: Enable coverage reporting
            verbose: Enable verbose output
            html_coverage: Generate HTML coverage report
            ci_mode: Run in CI mode (minimal output)
        
        Returns:
            Dictionary with test results and metrics
        """
        print("🚀 MCP Controllers Test Runner Starting...")
        print("=" * 60)
        
        start_time = time.time()
        
        # Determine which tests to run
        if controllers is None:
            test_files = list(self.controller_tests.values())
            controller_names = list(self.controller_tests.keys())
        else:
            test_files = []
            controller_names = []
            for controller in controllers:
                if controller in self.controller_tests:
                    test_files.append(self.controller_tests[controller])
                    controller_names.append(controller)
                else:
                    print(f"⚠️  Warning: Unknown controller '{controller}'. Available: {list(self.controller_tests.keys())}")
        
        if not test_files:
            print("❌ No valid test files specified.")
            return {"success": False, "error": "No valid test files"}
        
        print(f"📋 Running tests for controllers: {', '.join(controller_names)}")
        print(f"📁 Test directory: {self.test_dir}")
        
        # Build pytest command
        pytest_args = self._build_pytest_command(
            test_files, coverage, verbose, html_coverage, ci_mode
        )
        
        print(f"🔧 Command: {' '.join(pytest_args)}")
        print()
        
        # Run tests
        try:
            result = subprocess.run(
                pytest_args,
                cwd=self.test_dir,
                capture_output=not verbose,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Parse results
            test_results = self._parse_test_results(result, duration)
            
            # Generate report
            self._generate_report(test_results, controller_names, coverage, html_coverage)
            
            return test_results
            
        except subprocess.TimeoutExpired:
            print("⏰ Tests timed out after 5 minutes")
            return {"success": False, "error": "Test timeout"}
        except Exception as e:
            print(f"❌ Error running tests: {e}")
            return {"success": False, "error": str(e)}

    def _build_pytest_command(
        self, 
        test_files: List[str], 
        coverage: bool, 
        verbose: bool,
        html_coverage: bool,
        ci_mode: bool
    ) -> List[str]:
        """Build pytest command with appropriate options."""
        cmd = ["python", "-m", "pytest"]
        
        # Add test files
        cmd.extend(test_files)
        
        # Add pytest options
        if verbose:
            cmd.append("-v")
        elif ci_mode:
            cmd.append("-q")
        else:
            cmd.append("--tb=short")
        
        # Add coverage options
        if coverage:
            cmd.extend([
                "--cov=fastmcp.task_management.interface.mcp_controllers",
                "--cov-report=term-missing"
            ])
            
            if html_coverage:
                cmd.append("--cov-report=html:coverage_html")
        
        # Add other useful options
        cmd.extend([
            "--asyncio-mode=auto",  # Handle async tests properly
            "--durations=10",       # Show 10 slowest tests
            "-x",                   # Stop on first failure in CI mode if requested
        ] if ci_mode else [
            "--tb=short",
            "--durations=5"
        ])
        
        return cmd

    def _parse_test_results(self, result: subprocess.CompletedProcess, duration: float) -> Dict[str, Any]:
        """Parse pytest results and extract metrics."""
        success = result.returncode == 0
        
        # Basic result structure
        test_results = {
            "success": success,
            "return_code": result.returncode,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "summary": {}
        }
        
        # Parse output for test metrics
        if result.stdout:
            stdout_lines = result.stdout.split('\n')
            test_results["summary"] = self._extract_test_metrics(stdout_lines)
        
        return test_results

    def _extract_test_metrics(self, output_lines: List[str]) -> Dict[str, Any]:
        """Extract test metrics from pytest output."""
        summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "warnings": 0,
            "coverage": None,
            "by_category": {}
        }
        
        # Look for pytest summary line
        for line in output_lines:
            line = line.strip()
            
            # Parse test results summary
            if "passed" in line and ("failed" in line or "error" in line or "warning" in line):
                # Extract numbers from summary line
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed":
                        try:
                            summary["passed"] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass
                    elif part == "failed":
                        try:
                            summary["failed"] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass
                    elif part == "skipped":
                        try:
                            summary["skipped"] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass
            
            # Parse coverage percentage
            if "coverage" in line.lower() and "%" in line:
                try:
                    # Extract percentage from coverage line
                    parts = line.split()
                    for part in parts:
                        if "%" in part:
                            summary["coverage"] = part
                            break
                except:
                    pass
        
        summary["total_tests"] = summary["passed"] + summary["failed"] + summary["skipped"]
        
        return summary

    def _generate_report(
        self, 
        results: Dict[str, Any], 
        controllers: List[str],
        coverage: bool,
        html_coverage: bool
    ):
        """Generate comprehensive test report."""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        # Basic metrics
        success_icon = "✅" if results["success"] else "❌"
        print(f"{success_icon} Overall Status: {'PASSED' if results['success'] else 'FAILED'}")
        print(f"⏱️  Duration: {results['duration']:.2f} seconds")
        print(f"🎯 Controllers Tested: {', '.join(controllers)}")
        
        # Test metrics
        summary = results.get("summary", {})
        if summary.get("total_tests", 0) > 0:
            print(f"📈 Total Tests: {summary['total_tests']}")
            print(f"✅ Passed: {summary['passed']}")
            print(f"❌ Failed: {summary['failed']}")
            print(f"⏭️  Skipped: {summary['skipped']}")
            
            if summary["total_tests"] > 0:
                pass_rate = (summary["passed"] / summary["total_tests"]) * 100
                print(f"📊 Pass Rate: {pass_rate:.1f}%")
        
        # Coverage information
        if coverage and summary.get("coverage"):
            print(f"🎯 Code Coverage: {summary['coverage']}")
            
            if html_coverage:
                html_path = self.test_dir / "coverage_html" / "index.html"
                if html_path.exists():
                    print(f"📄 HTML Coverage Report: {html_path}")
        
        # Recommendations
        print("\n📋 RECOMMENDATIONS:")
        if results["success"]:
            print("✨ All tests passed! Great job!")
            if not coverage:
                print("💡 Consider running with --coverage to check test coverage")
        else:
            print("🔧 Some tests failed. Check the output above for details.")
            print("💡 Run with --verbose for more detailed error information")
        
        # Quick commands
        print(f"\n🔧 QUICK COMMANDS:")
        print(f"   Run specific controller: python test_runner.py --controller {controllers[0] if controllers else 'task'}")
        print(f"   Run with coverage: python test_runner.py --coverage")
        print(f"   Verbose output: python test_runner.py --verbose")
        
        print("=" * 60)

    def validate_environment(self) -> bool:
        """Validate that the testing environment is properly set up."""
        print("🔍 Validating test environment...")
        
        issues = []
        
        # Check Python version
        if sys.version_info < (3, 8):
            issues.append("Python 3.8+ is required")
        
        # Check required packages
        required_packages = ["pytest", "pytest-asyncio", "pytest-cov"]
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                issues.append(f"Missing package: {package}")
        
        # Check test files exist
        missing_files = []
        for controller, filename in self.controller_tests.items():
            if not (self.test_dir / filename).exists():
                missing_files.append(filename)
        
        if missing_files:
            print(f"⚠️  Missing test files: {missing_files}")
            print("   (These tests will be skipped)")
        
        if issues:
            print("❌ Environment validation failed:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        
        print("✅ Environment validation passed")
        return True

    def list_available_tests(self):
        """List all available controller tests."""
        print("📋 Available Controller Tests:")
        print("=" * 40)
        
        for controller, filename in self.controller_tests.items():
            file_path = self.test_dir / filename
            status = "✅" if file_path.exists() else "❌"
            print(f"{status} {controller:12} - {filename}")
        
        print("\nUsage:")
        print("  python test_runner.py --controller task")
        print("  python test_runner.py --controller project,task")
        print("  python test_runner.py  # Run all tests")


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner for MCP controller unit tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_runner.py                           # Run all tests
  python test_runner.py --controller task         # Test task controller
  python test_runner.py --controller task,project # Test multiple controllers
  python test_runner.py --coverage                # Run with coverage
  python test_runner.py --verbose                 # Detailed output
  python test_runner.py --list                    # List available tests
        """
    )
    
    parser.add_argument(
        "--controller", 
        help="Comma-separated list of controllers to test (e.g., 'task,project')"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="Enable code coverage reporting"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose test output"
    )
    parser.add_argument(
        "--html", 
        action="store_true",
        help="Generate HTML coverage report (requires --coverage)"
    )
    parser.add_argument(
        "--ci", 
        action="store_true",
        help="Run in CI mode (minimal output, fail fast)"
    )
    parser.add_argument(
        "--list", 
        action="store_true",
        help="List available controller tests"
    )
    parser.add_argument(
        "--validate", 
        action="store_true",
        help="Validate testing environment only"
    )
    
    args = parser.parse_args()
    
    # Create test runner
    runner = MCPControllerTestRunner()
    
    # Handle special commands
    if args.list:
        runner.list_available_tests()
        return 0
    
    if args.validate:
        success = runner.validate_environment()
        return 0 if success else 1
    
    # Validate environment before running tests
    if not runner.validate_environment():
        print("❌ Environment validation failed. Fix issues before running tests.")
        return 1
    
    # Parse controllers
    controllers = None
    if args.controller:
        controllers = [c.strip() for c in args.controller.split(",")]
    
    # Run tests
    results = runner.run_tests(
        controllers=controllers,
        coverage=args.coverage,
        verbose=args.verbose,
        html_coverage=args.html,
        ci_mode=args.ci
    )
    
    # Return appropriate exit code
    return 0 if results.get("success", False) else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)