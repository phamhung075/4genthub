#!/usr/bin/env python3
"""
Test Suite Verification Script - Iteration 16
=====================================================

This script verifies the current status of all test files listed in .test_cache/failed_tests.txt
and updates the cache to reflect which tests are actually passing vs failing.

Usage: python test_suite_verifier.py
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict
import time
from datetime import datetime

class TestSuiteVerifier:
    def __init__(self):
        self.project_root = Path("/home/daihungpham/__projects__/agentic-project")
        self.test_cache_dir = self.project_root / ".test_cache"
        self.failed_tests_file = self.test_cache_dir / "failed_tests.txt"
        self.passed_tests_file = self.test_cache_dir / "passed_tests.txt"
        self.working_dir = self.project_root / "dhafnck_mcp_main"

        # Results tracking
        self.newly_passing = []
        self.still_failing = []
        self.error_tests = []
        self.test_results = {}

    def load_failed_tests(self) -> List[str]:
        """Load the list of tests from failed_tests.txt"""
        if not self.failed_tests_file.exists():
            print(f"ERROR: {self.failed_tests_file} not found!")
            return []

        with open(self.failed_tests_file, 'r') as f:
            lines = f.readlines()

        # Extract test file paths, skip line numbers and empty lines
        test_files = []
        for line in lines:
            # Handle lines with various spacing and formats
            line = line.strip()
            if line and '→' in line:
                # Extract path after the arrow
                path = line.split('→', 1)[1].strip()
                if path and path.endswith('.py'):
                    test_files.append(path)
            elif line and line.endswith('.py') and 'dhafnck_mcp_main' in line:
                # Handle lines that might not have the arrow format
                if '/home/daihungpham/__projects__/agentic-project/' in line:
                    test_files.append(line)

        print(f"DEBUG: Loaded {len(test_files)} test files from failed_tests.txt")
        if test_files:
            print(f"First few tests: {test_files[:3]}")

        return test_files

    def load_existing_passed_tests(self) -> List[str]:
        """Load existing passed tests to avoid duplicates"""
        if not self.passed_tests_file.exists():
            return []

        with open(self.passed_tests_file, 'r') as f:
            lines = f.readlines()

        passed_tests = []
        for line in lines:
            line = line.strip()
            if line and '→' in line:
                path = line.split('→', 1)[1].strip()
                if path and path.endswith('.py'):
                    passed_tests.append(path)

        return passed_tests

    def run_single_test(self, test_file: str) -> Tuple[bool, str, str]:
        """
        Run a single test file and return (success, stdout, stderr)
        """
        try:
            # Convert absolute path to relative path from working directory
            if test_file.startswith('/home/daihungpham/__projects__/agentic-project/'):
                # Remove project root prefix
                test_file = test_file.replace('/home/daihungpham/__projects__/agentic-project/', '')

            if test_file.startswith('dhafnck_mcp_main/'):
                # Remove dhafnck_mcp_main prefix since we run from that directory
                test_file = test_file[len('dhafnck_mcp_main/'):]

            # Construct the full path relative to working directory
            test_path = self.working_dir / test_file

            if not test_path.exists():
                return False, "", f"Test file not found: {test_path}"

            print(f"  Testing: {test_file}...")

            # Run pytest with specific test file
            cmd = [
                sys.executable, "-m", "pytest",
                str(test_path),
                "-v",
                "--tb=short",
                "--disable-warnings",
                "--no-header"
            ]

            result = subprocess.run(
                cmd,
                cwd=str(self.working_dir),
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout per test
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", "Test timeout (>60s)"
        except Exception as e:
            return False, "", f"Error running test: {str(e)}"

    def verify_all_tests(self, test_files: List[str]) -> None:
        """Run all tests and categorize results"""
        total_tests = len(test_files)
        print(f"\n🔬 Verifying {total_tests} test files from failed_tests.txt")
        print("=" * 60)

        for i, test_file in enumerate(test_files, 1):
            print(f"\n[{i}/{total_tests}] Processing: {test_file}")

            success, stdout, stderr = self.run_single_test(test_file)

            self.test_results[test_file] = {
                'success': success,
                'stdout': stdout,
                'stderr': stderr
            }

            if success:
                print(f"  ✅ PASSED")
                self.newly_passing.append(test_file)
            else:
                print(f"  ❌ FAILED")
                if "Error running test" in stderr or "not found" in stderr:
                    self.error_tests.append(test_file)
                else:
                    self.still_failing.append(test_file)

            # Brief pause to avoid overwhelming the system
            time.sleep(0.1)

    def update_cache_files(self) -> None:
        """Update the cache files with new results"""
        print(f"\n📝 Updating cache files...")

        # Load existing passed tests
        existing_passed = self.load_existing_passed_tests()

        # Combine existing passed tests with newly passing ones
        all_passed_tests = existing_passed.copy()

        # Add newly passing tests to the passed list (avoid duplicates)
        for test in self.newly_passing:
            # Convert to absolute path for consistency
            if not test.startswith('/'):
                if not test.startswith('dhafnck_mcp_main/'):
                    test = f"dhafnck_mcp_main/src/tests/{test}"
                test = f"/home/daihungpham/__projects__/agentic-project/{test}"

            if test not in all_passed_tests:
                all_passed_tests.append(test)

        # Update passed_tests.txt
        with open(self.passed_tests_file, 'w') as f:
            for i, test in enumerate(all_passed_tests, 1):
                f.write(f"{i:5d}→{test}\n")

        # Update failed_tests.txt with only still failing tests and error tests
        remaining_failed = self.still_failing + self.error_tests

        with open(self.failed_tests_file, 'w') as f:
            for i, test in enumerate(remaining_failed, 1):
                # Convert to absolute path for consistency
                if not test.startswith('/'):
                    if not test.startswith('dhafnck_mcp_main/'):
                        test = f"dhafnck_mcp_main/src/tests/{test}"
                    test = f"/home/daihungpham/__projects__/agentic-project/{test}"
                f.write(f"{i:5d}→{test}\n")

        print(f"  ✅ Updated {self.passed_tests_file}")
        print(f"  ✅ Updated {self.failed_tests_file}")

    def generate_report(self) -> str:
        """Generate a detailed report of the verification results"""
        total_tests = len(self.test_results)
        passed_count = len(self.newly_passing)
        failed_count = len(self.still_failing)
        error_count = len(self.error_tests)

        report = f"""
📊 TEST SUITE VERIFICATION REPORT - ITERATION 16
==================================================
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 SUMMARY STATISTICS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Total tests verified: {total_tests}
• Tests now passing: {passed_count} ({passed_count/total_tests*100:.1f}%)
• Tests still failing: {failed_count} ({failed_count/total_tests*100:.1f}%)
• Tests with errors: {error_count} ({error_count/total_tests*100:.1f}%)

🎯 CACHE UPDATE STATUS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Added to passed_tests.txt: {passed_count} tests
• Remaining in failed_tests.txt: {failed_count + error_count} tests

📊 DETAILED BREAKDOWN:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        if self.newly_passing:
            report += f"""
✅ NEWLY PASSING TESTS ({len(self.newly_passing)}):
"""
            for i, test in enumerate(self.newly_passing, 1):
                short_name = test.split('/')[-1] if '/' in test else test
                report += f"  {i:2d}. {short_name}\n"

        if self.still_failing:
            report += f"""
❌ STILL FAILING TESTS ({len(self.still_failing)}):
"""
            for i, test in enumerate(self.still_failing, 1):
                short_name = test.split('/')[-1] if '/' in test else test
                report += f"  {i:2d}. {short_name}\n"

        if self.error_tests:
            report += f"""
🔥 TESTS WITH ERRORS ({len(self.error_tests)}):
"""
            for i, test in enumerate(self.error_tests, 1):
                short_name = test.split('/')[-1] if '/' in test else test
                report += f"  {i:2d}. {short_name}\n"

        report += f"""
🏆 OVERALL PROGRESS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Previously passing tests: {len(self.load_existing_passed_tests())}
• Tests moved to passing: {passed_count}
• Total passing tests: {len(self.load_existing_passed_tests()) + passed_count}
• Tests still needing fixes: {failed_count + error_count}

✨ SUCCESS RATE: {passed_count/(total_tests)*100:.1f}% of failed tests are now passing!
"""

        return report

    def run_verification(self) -> None:
        """Main verification process"""
        print("🚀 Starting Test Suite Verification - Iteration 16")
        print(f"Working directory: {self.working_dir}")

        # Load tests to verify
        test_files = self.load_failed_tests()
        if not test_files:
            print("❌ No test files found in failed_tests.txt")
            return

        print(f"📋 Loaded {len(test_files)} test files to verify")

        # Verify all tests
        self.verify_all_tests(test_files)

        # Update cache files
        self.update_cache_files()

        # Generate and display report
        report = self.generate_report()
        print(report)

        # Save report to file
        report_file = self.project_root / "test_verification_report_iteration16.txt"
        with open(report_file, 'w') as f:
            f.write(report)

        print(f"\n📄 Full report saved to: {report_file}")

        print(f"\n🎉 Verification complete!")
        print(f"🎯 Next steps: Review the {len(self.still_failing + self.error_tests)} remaining failing tests")

def main():
    """Main entry point"""
    verifier = TestSuiteVerifier()
    verifier.run_verification()

if __name__ == "__main__":
    main()