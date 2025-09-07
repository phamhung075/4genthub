#!/usr/bin/env python3
"""
Test Runner for Comprehensive MCP Tools Test Suite
=================================================

This script runs the comprehensive test suite for dhafnck_mcp_http tools
with proper configuration and reporting.

Usage:
    python run_comprehensive_tests.py [--verbose] [--coverage]

Options:
    --verbose    Show detailed test output
    --coverage   Generate coverage report
    --help       Show this help message

Author: DhafnckMCP Test Orchestrator Agent
Date: 2025-08-24
"""

import sys
import subprocess
import argparse
import os
from pathlib import Path

def run_comprehensive_tests(verbose=False, coverage=False):
    """Run the comprehensive MCP tools test suite."""
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    test_file = Path(__file__).parent / "integration" / "test_mcp_tools_comprehensive.py"
    
    # Check if test file exists
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return 1
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.extend(["-v", "--tb=short"])
    else:
        cmd.extend(["--tb=line"])
    
    if coverage:
        cmd.extend([
            "--cov=dhafnck_mcp_main.src.fastmcp",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    
    # Add specific test markers
    cmd.extend([
        "-m", "not slow",  # Skip slow tests by default
        "--durations=10",  # Show 10 slowest tests
    ])
    
    # Add the test file
    cmd.append(str(test_file))
    
    print("🚀 Running Comprehensive MCP Tools Test Suite")
    print("=" * 60)
    print(f"Test file: {test_file}")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        # Change to project root directory
        os.chdir(project_root)
        
        # Run the tests
        result = subprocess.run(cmd, capture_output=False, text=True)
        
        if result.returncode == 0:
            print("\n✅ All tests passed successfully!")
            if coverage:
                print("📊 Coverage report generated in htmlcov/index.html")
        else:
            print(f"\n❌ Tests failed with return code: {result.returncode}")
        
        return result.returncode
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

def run_specific_test_class(test_class, verbose=False):
    """Run a specific test class."""
    
    test_file = Path(__file__).parent / "integration" / "test_mcp_tools_comprehensive.py"
    
    cmd = [
        "python", "-m", "pytest",
        f"{test_file}::{test_class}",
        "-v" if verbose else "-q"
    ]
    
    print(f"🎯 Running test class: {test_class}")
    print("=" * 40)
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode
    except Exception as e:
        print(f"❌ Error running test class: {e}")
        return 1

def list_test_classes():
    """List all available test classes in the comprehensive suite."""
    
    test_classes = [
        "TestTaskPersistence",
        "TestContextManagement", 
        "TestSubtaskManagement",
        "TestProjectAndBranchManagement",
        "TestErrorHandling",
        "TestDataIntegrity",
        "TestPerformance"
    ]
    
    print("📋 Available Test Classes:")
    print("=" * 30)
    for i, test_class in enumerate(test_classes, 1):
        print(f"{i}. {test_class}")
    
    return test_classes

def main():
    """Main entry point for the test runner."""
    
    parser = argparse.ArgumentParser(
        description="Run comprehensive MCP tools test suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_comprehensive_tests.py                    # Run all tests
    python run_comprehensive_tests.py --verbose          # Verbose output
    python run_comprehensive_tests.py --coverage         # With coverage
    python run_comprehensive_tests.py --list-classes     # List test classes
    python run_comprehensive_tests.py --class TestTaskPersistence  # Run specific class
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed test output"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--list-classes", "-l",
        action="store_true",
        help="List all available test classes"
    )
    
    parser.add_argument(
        "--class",
        dest="test_class",
        help="Run specific test class"
    )
    
    args = parser.parse_args()
    
    # Handle list classes
    if args.list_classes:
        list_test_classes()
        return 0
    
    # Handle specific test class
    if args.test_class:
        return run_specific_test_class(args.test_class, args.verbose)
    
    # Run all tests
    return run_comprehensive_tests(args.verbose, args.coverage)

if __name__ == "__main__":
    sys.exit(main())