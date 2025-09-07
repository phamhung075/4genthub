#!/usr/bin/env python3
"""
Test Runner for Supabase Database Connection Fix Validation

This script runs comprehensive tests to validate that the Supabase connection
fix is working correctly across all components of the system.

Usage:
    python run_supabase_connection_tests.py [--unit-only] [--integration-only] [--verbose]

Features:
- Runs both unit and integration tests
- Provides detailed test reports
- Validates all aspects of the Supabase connection fix
- Generates test documentation
"""

import sys
import os
import argparse
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import test classes
from tests.unit.infrastructure.database.test_supabase_connection_unit import TestSupabaseConnectionUnit
from tests.integration.test_supabase_database_connection_comprehensive import TestSupabaseConnectionComprehensive

logger = logging.getLogger(__name__)


class SupabaseConnectionTestRunner:
    """Test runner for comprehensive Supabase connection validation"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.test_results = {
            "unit_tests": {},
            "integration_tests": {},
            "summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "start_time": None,
                "end_time": None,
                "duration": None
            }
        }
        
        # Configure logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def print_header(self, title: str, char: str = "=", width: int = 80):
        """Print a formatted header"""
        print(f"\n{char * width}")
        print(f"{title.center(width)}")
        print(f"{char * width}")
    
    def print_subheader(self, title: str, char: str = "-", width: int = 80):
        """Print a formatted subheader"""
        print(f"\n{char * width}")
        print(f"{title}")
        print(f"{char * width}")
    
    def run_test_method(self, test_instance, method_name: str) -> Tuple[bool, Optional[str]]:
        """Run a single test method and return result"""
        try:
            print(f"  📋 Running {method_name}...", end=" ")
            
            # Setup method
            if hasattr(test_instance, 'setup_method'):
                test_method = getattr(test_instance, method_name)
                test_instance.setup_method(test_method)
            
            # Run test method
            test_method = getattr(test_instance, method_name)
            test_method()
            
            # Teardown method
            if hasattr(test_instance, 'teardown_method'):
                test_instance.teardown_method(test_method)
            
            print("✅ PASSED")
            return True, None
            
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            if self.verbose:
                import traceback
                print(f"    Error details: {traceback.format_exc()}")
            return False, str(e)
    
    def run_unit_tests(self) -> Dict[str, bool]:
        """Run all unit tests for Supabase connection"""
        self.print_header("UNIT TESTS - Supabase Connection Configuration", "=")
        
        print("🎯 Testing database configuration, connection strings, and error handling...")
        
        test_instance = TestSupabaseConnectionUnit()
        
        # Get all test methods
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        test_methods.sort()  # Run tests in alphabetical order
        
        unit_results = {}
        
        for method_name in test_methods:
            success, error = self.run_test_method(test_instance, method_name)
            unit_results[method_name] = success
            
            if success:
                self.test_results["summary"]["passed_tests"] += 1
            else:
                self.test_results["summary"]["failed_tests"] += 1
                self.test_results["unit_tests"][method_name] = {
                    "status": "FAILED",
                    "error": error
                }
            
            self.test_results["summary"]["total_tests"] += 1
        
        # Print unit test summary
        passed = sum(1 for result in unit_results.values() if result)
        failed = len(unit_results) - passed
        
        print(f"\n📊 Unit Test Results:")
        print(f"  ✅ Passed: {passed}")
        print(f"  ❌ Failed: {failed}")
        print(f"  📝 Total: {len(unit_results)}")
        
        return unit_results
    
    def run_integration_tests(self) -> Dict[str, bool]:
        """Run all integration tests for Supabase connection"""
        self.print_header("INTEGRATION TESTS - Supabase Connection Comprehensive", "=")
        
        print("🎯 Testing repository connections, data persistence, and end-to-end workflows...")
        
        test_instance = TestSupabaseConnectionComprehensive()
        
        # Get all test methods (in order)
        test_methods = [
            'test_01_supabase_configuration_validation',
            'test_02_supabase_connection_establishment',
            'test_03_no_sqlite_fallback_verification',
            'test_04_global_contexts_table_operations',
            'test_05_project_repository_supabase_connection',
            'test_06_task_repository_supabase_connection',
            'test_07_git_branch_repository_supabase_connection',
            'test_08_agent_repository_supabase_connection',
            'test_09_data_persistence_validation',
            'test_10_transaction_rollback_validation',
            'test_11_end_to_end_workflow_validation',
            'test_12_database_configuration_consistency',
            'test_99_comprehensive_validation_summary'
        ]
        
        integration_results = {}
        
        for method_name in test_methods:
            if hasattr(test_instance, method_name):
                success, error = self.run_test_method(test_instance, method_name)
                integration_results[method_name] = success
                
                if success:
                    self.test_results["summary"]["passed_tests"] += 1
                else:
                    self.test_results["summary"]["failed_tests"] += 1
                    self.test_results["integration_tests"][method_name] = {
                        "status": "FAILED",
                        "error": error
                    }
                
                self.test_results["summary"]["total_tests"] += 1
        
        # Print integration test summary
        passed = sum(1 for result in integration_results.values() if result)
        failed = len(integration_results) - passed
        
        print(f"\n📊 Integration Test Results:")
        print(f"  ✅ Passed: {passed}")
        print(f"  ❌ Failed: {failed}")
        print(f"  📝 Total: {len(integration_results)}")
        
        return integration_results
    
    def run_pytest_validation(self) -> bool:
        """Run pytest validation to ensure tests can be discovered and run"""
        self.print_subheader("PYTEST VALIDATION")
        
        try:
            # Get the test directory
            test_dir = Path(__file__).parent
            
            # Run pytest discovery on our test files
            unit_test_file = test_dir / "unit" / "infrastructure" / "database" / "test_supabase_connection_unit.py"
            integration_test_file = test_dir / "integration" / "test_supabase_database_connection_comprehensive.py"
            
            print(f"🔍 Validating pytest discovery...")
            
            # Check if files exist
            if not unit_test_file.exists():
                print(f"❌ Unit test file not found: {unit_test_file}")
                return False
            
            if not integration_test_file.exists():
                print(f"❌ Integration test file not found: {integration_test_file}")
                return False
            
            print(f"✅ Test files exist and are discoverable")
            
            # Try to run pytest --collect-only to validate test discovery
            cmd = ["python", "-m", "pytest", "--collect-only", "-q", str(unit_test_file), str(integration_test_file)]
            
            result = subprocess.run(
                cmd,
                cwd=test_dir.parent,  # Run from src directory
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"✅ pytest can discover tests successfully")
                if self.verbose:
                    print(f"   pytest output: {result.stdout}")
                return True
            else:
                print(f"❌ pytest discovery failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"❌ pytest validation timed out")
            return False
        except Exception as e:
            print(f"❌ pytest validation error: {e}")
            return False
    
    def check_environment_setup(self) -> bool:
        """Check that the test environment is properly set up"""
        self.print_subheader("ENVIRONMENT VALIDATION")
        
        print("🔧 Checking environment setup...")
        
        # Check required environment variables
        required_vars = [
            "DATABASE_TYPE",
            "DATABASE_URL", 
            "SUPABASE_URL",
            "SUPABASE_ANON_KEY",
            "SUPABASE_DB_PASSWORD"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
            else:
                print(f"  ✅ {var}: SET")
        
        if missing_vars:
            print(f"\n❌ Missing environment variables: {', '.join(missing_vars)}")
            print("🔧 Please ensure your .env file is properly configured")
            return False
        
        # Check database type
        db_type = os.getenv("DATABASE_TYPE")
        if db_type != "supabase":
            print(f"❌ DATABASE_TYPE should be 'supabase', got '{db_type}'")
            return False
        
        print(f"  ✅ DATABASE_TYPE: {db_type}")
        
        # Check database URL format
        db_url = os.getenv("DATABASE_URL")
        if not db_url or not db_url.startswith("postgresql://"):
            print(f"❌ DATABASE_URL should be PostgreSQL connection string")
            return False
        
        if "supabase.com" not in db_url:
            print(f"❌ DATABASE_URL should point to Supabase")
            return False
        
        print(f"  ✅ DATABASE_URL: Valid Supabase PostgreSQL URL")
        
        print("✅ Environment setup is valid")
        return True
    
    def generate_test_report(self) -> str:
        """Generate comprehensive test report"""
        self.print_header("COMPREHENSIVE TEST REPORT", "=")
        
        duration = self.test_results["summary"]["duration"]
        total_tests = self.test_results["summary"]["total_tests"]
        passed_tests = self.test_results["summary"]["passed_tests"]
        failed_tests = self.test_results["summary"]["failed_tests"]
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = f"""
🚀 SUPABASE CONNECTION FIX VALIDATION REPORT
{'=' * 80}

📊 SUMMARY:
  • Total Tests: {total_tests}
  • Passed: {passed_tests} ✅
  • Failed: {failed_tests} ❌
  • Success Rate: {success_rate:.1f}%
  • Duration: {duration:.2f} seconds

🎯 TEST CATEGORIES:
  • Unit Tests: Configuration and connection string validation
  • Integration Tests: Repository connections and data persistence
  • End-to-End Tests: Complete workflow validation

"""
        
        if failed_tests == 0:
            report += """
✅ RESULT: ALL TESTS PASSED!

🎉 The Supabase database connection fix has been successfully validated.
🔗 All components are correctly connecting to Supabase PostgreSQL.
🚫 No SQLite fallback is occurring.
💾 Data persistence is working correctly.
🔄 Repository operations are functioning properly.

✨ The system is ready for production use with Supabase!
"""
        else:
            report += f"""
❌ RESULT: {failed_tests} TEST(S) FAILED

🔍 FAILED TESTS:
"""
            
            for test_name, test_info in self.test_results.get("unit_tests", {}).items():
                if test_info.get("status") == "FAILED":
                    report += f"  • Unit Test - {test_name}: {test_info.get('error', 'Unknown error')}\n"
            
            for test_name, test_info in self.test_results.get("integration_tests", {}).items():
                if test_info.get("status") == "FAILED":
                    report += f"  • Integration Test - {test_name}: {test_info.get('error', 'Unknown error')}\n"
            
            report += """
🔧 RECOMMENDED ACTIONS:
  1. Review failed test details above
  2. Verify Supabase configuration in .env file
  3. Check DATABASE_URL is correctly set
  4. Ensure all required environment variables are present
  5. Retry tests after fixing configuration issues
"""
        
        print(report)
        return report
    
    def run_all_tests(self, unit_only: bool = False, integration_only: bool = False) -> bool:
        """Run all tests and return overall success status"""
        self.test_results["summary"]["start_time"] = time.time()
        
        self.print_header("SUPABASE CONNECTION FIX VALIDATION", "=")
        print("🎯 Validating that the Supabase database connection fix is working correctly")
        print("📋 This will test configuration, connections, repositories, and data persistence")
        
        # Check environment setup first
        if not self.check_environment_setup():
            print("\n❌ Environment validation failed. Please fix configuration issues.")
            return False
        
        # Run pytest validation
        if not self.run_pytest_validation():
            print("\n⚠️ pytest validation failed, but continuing with direct test execution...")
        
        success = True
        
        # Run unit tests
        if not integration_only:
            unit_results = self.run_unit_tests()
            if not all(unit_results.values()):
                success = False
        
        # Run integration tests  
        if not unit_only:
            integration_results = self.run_integration_tests()
            if not all(integration_results.values()):
                success = False
        
        # Record end time and calculate duration
        self.test_results["summary"]["end_time"] = time.time()
        self.test_results["summary"]["duration"] = (
            self.test_results["summary"]["end_time"] - 
            self.test_results["summary"]["start_time"]
        )
        
        # Generate and display report
        self.generate_test_report()
        
        return success


def main():
    """Main entry point for the test runner"""
    parser = argparse.ArgumentParser(
        description="Run comprehensive Supabase connection fix validation tests"
    )
    parser.add_argument(
        "--unit-only", 
        action="store_true",
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration-only",
        action="store_true", 
        help="Run only integration tests"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Validate argument combination
    if args.unit_only and args.integration_only:
        print("❌ Error: Cannot specify both --unit-only and --integration-only")
        return 1
    
    # Create and run test runner
    runner = SupabaseConnectionTestRunner(verbose=args.verbose)
    
    try:
        success = runner.run_all_tests(
            unit_only=args.unit_only,
            integration_only=args.integration_only
        )
        
        if success:
            print(f"\n🎉 ALL TESTS PASSED! Supabase connection fix validated successfully.")
            return 0
        else:
            print(f"\n❌ Some tests failed. Review the results above.")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n⚠️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)