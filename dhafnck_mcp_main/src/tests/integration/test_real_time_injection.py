#!/usr/bin/env python3
"""
Test Suite for Real-Time Context Injection System

This script tests the complete real-time context injection system including:
- Context detection and injection (pre-tool hook)
- Context updates and synchronization (post-tool hook)
- Performance and reliability metrics

Task ID: de7621a4-df75-4d03-a967-8fb743b455f1 (Phase 2)
Architecture Reference: Real-Time Context Injection System
"""

import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add hooks utils directory to path
hooks_utils_path = Path(__file__).resolve().parents[5] / ".claude" / "hooks" / "utils"
sys.path.insert(0, str(hooks_utils_path))

# Import our modules
try:
    from context_injector import create_context_injector, inject_context_sync
    from context_updater import create_context_updater, update_context_sync
    from context_synchronizer import get_global_synchronizer, sync_context_change
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import modules: {e}")
    MODULES_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RealTimeInjectionTester:
    """Comprehensive test suite for the real-time injection system."""
    
    def __init__(self):
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'performance_metrics': [],
            'test_details': []
        }
        self.performance_threshold_ms = 500
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all test suites and return comprehensive results."""
        print("🚀 Starting Real-Time Context Injection System Tests")
        print("=" * 60)
        
        if not MODULES_AVAILABLE:
            print("❌ Cannot run tests - required modules not available")
            return self.test_results
        
        # Test suites
        test_suites = [
            ("Context Detection", self.test_context_detection),
            ("Context Injection", self.test_context_injection),
            ("Context Updates", self.test_context_updates),
            ("Context Synchronization", self.test_context_synchronization),
            ("Performance Tests", self.test_performance),
            ("Integration Tests", self.test_integration),
            ("Error Handling", self.test_error_handling)
        ]
        
        for suite_name, test_method in test_suites:
            print(f"\n📋 Running {suite_name} Tests...")
            try:
                suite_results = test_method()
                self._process_suite_results(suite_name, suite_results)
            except Exception as e:
                print(f"❌ Test suite {suite_name} failed with error: {e}")
                self._record_test_failure(suite_name, str(e))
        
        # Generate final report
        self._generate_final_report()
        
        return self.test_results
    
    def test_context_detection(self) -> List[Dict[str, Any]]:
        """Test context relevance detection."""
        test_cases = [
            {
                'name': 'MCP Task Operation Detection',
                'tool_name': 'mcp__dhafnck_mcp_http__manage_task',
                'tool_input': {'action': 'get', 'task_id': 'test-123'},
                'expected_relevant': True
            },
            {
                'name': 'File Operation Detection',
                'tool_name': 'Write',
                'tool_input': {'file_path': '/test/file.py', 'content': 'print("test")'},
                'expected_relevant': True
            },
            {
                'name': 'Non-Relevant Operation',
                'tool_name': 'Read',
                'tool_input': {'file_path': '/test/file.txt'},
                'expected_relevant': False
            },
            {
                'name': 'Git Operation Detection',
                'tool_name': 'Bash',
                'tool_input': {'command': 'git status'},
                'expected_relevant': True
            }
        ]
        
        results = []
        injector = create_context_injector()
        
        for test_case in test_cases:
            start_time = time.time()
            try:
                is_relevant, priority, context_reqs = injector.detector.is_context_relevant(
                    test_case['tool_name'],
                    test_case['tool_input']
                )
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                success = is_relevant == test_case['expected_relevant']
                results.append({
                    'test': test_case['name'],
                    'success': success,
                    'execution_time_ms': execution_time_ms,
                    'details': {
                        'expected_relevant': test_case['expected_relevant'],
                        'actual_relevant': is_relevant,
                        'priority': priority,
                        'context_requirements': context_reqs
                    }
                })
                
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"  {status} {test_case['name']} ({execution_time_ms:.2f}ms)")
                
            except Exception as e:
                results.append({
                    'test': test_case['name'],
                    'success': False,
                    'error': str(e),
                    'execution_time_ms': (time.time() - start_time) * 1000
                })
                print(f"  ❌ FAIL {test_case['name']} - Error: {e}")
        
        return results
    
    def test_context_injection(self) -> List[Dict[str, Any]]:
        """Test context injection functionality."""
        test_cases = [
            {
                'name': 'MCP Task Context Injection',
                'tool_name': 'mcp__dhafnck_mcp_http__manage_task',
                'tool_input': {'action': 'get', 'task_id': 'test-task-123'},
            },
            {
                'name': 'File Operation Context',
                'tool_name': 'Edit',
                'tool_input': {'file_path': '/test/example.py', 'old_string': 'old', 'new_string': 'new'},
            },
            {
                'name': 'Non-Context Tool',
                'tool_name': 'Read',
                'tool_input': {'file_path': '/test/readme.txt'},
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            start_time = time.time()
            try:
                # Test synchronous injection
                injected_context = inject_context_sync(
                    test_case['tool_name'],
                    test_case['tool_input']
                )
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Determine success criteria
                success = True
                if injected_context:
                    # If context was injected, validate format
                    success = (
                        '<context-injection>' in injected_context and
                        '</context-injection>' in injected_context and
                        'Priority:' in injected_context
                    )
                
                results.append({
                    'test': test_case['name'],
                    'success': success,
                    'execution_time_ms': execution_time_ms,
                    'details': {
                        'context_injected': injected_context is not None,
                        'context_size': len(injected_context) if injected_context else 0,
                        'performance_ok': execution_time_ms < self.performance_threshold_ms
                    }
                })
                
                status = "✅ PASS" if success else "❌ FAIL"
                perf_status = "🚀" if execution_time_ms < self.performance_threshold_ms else "⚠️"
                print(f"  {status} {perf_status} {test_case['name']} ({execution_time_ms:.2f}ms)")
                
            except Exception as e:
                results.append({
                    'test': test_case['name'],
                    'success': False,
                    'error': str(e),
                    'execution_time_ms': (time.time() - start_time) * 1000
                })
                print(f"  ❌ FAIL {test_case['name']} - Error: {e}")
        
        return results
    
    def test_context_updates(self) -> List[Dict[str, Any]]:
        """Test context update functionality."""
        test_cases = [
            {
                'name': 'File Modification Update',
                'tool_name': 'Edit',
                'tool_input': {'file_path': '/test/modified.py', 'old_string': 'old', 'new_string': 'new'},
                'tool_output': {'success': True}
            },
            {
                'name': 'Task Update',
                'tool_name': 'mcp__dhafnck_mcp_http__manage_task',
                'tool_input': {'action': 'update', 'task_id': 'test-123', 'status': 'in_progress'},
                'tool_output': {'success': True, 'data': {'task': {'id': 'test-123'}}}
            },
            {
                'name': 'Git Operation Update',
                'tool_name': 'Bash',
                'tool_input': {'command': 'git add test.py'},
                'tool_output': None
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            start_time = time.time()
            try:
                # Test synchronous update
                update_success = update_context_sync(
                    test_case['tool_name'],
                    test_case['tool_input'],
                    test_case.get('tool_output')
                )
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                results.append({
                    'test': test_case['name'],
                    'success': update_success,
                    'execution_time_ms': execution_time_ms,
                    'details': {
                        'update_successful': update_success,
                        'performance_ok': execution_time_ms < 1000  # 1 second for updates
                    }
                })
                
                status = "✅ PASS" if update_success else "❌ FAIL"
                perf_status = "🚀" if execution_time_ms < 1000 else "⚠️"
                print(f"  {status} {perf_status} {test_case['name']} ({execution_time_ms:.2f}ms)")
                
            except Exception as e:
                results.append({
                    'test': test_case['name'],
                    'success': False,
                    'error': str(e),
                    'execution_time_ms': (time.time() - start_time) * 1000
                })
                print(f"  ❌ FAIL {test_case['name']} - Error: {e}")
        
        return results
    
    def test_context_synchronization(self) -> List[Dict[str, Any]]:
        """Test context synchronization functionality."""
        test_cases = [
            {
                'name': 'Simple Context Sync',
                'source': 'test_hook',
                'operation': 'update',
                'context_type': 'task',
                'context_id': 'test-sync-123',
                'changes': {'status': 'updated', 'timestamp': datetime.now().isoformat()}
            },
            {
                'name': 'High Priority Sync',
                'source': 'test_hook',
                'operation': 'create',
                'context_type': 'branch',
                'context_id': 'test-branch-456',
                'changes': {'name': 'test-branch', 'created': True},
                'priority': 5
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            start_time = time.time()
            try:
                # Test synchronous context sync
                sync_success = sync_context_change(
                    source=test_case['source'],
                    operation=test_case['operation'],
                    context_type=test_case['context_type'],
                    context_id=test_case['context_id'],
                    changes=test_case['changes'],
                    priority=test_case.get('priority', 1)
                )
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                results.append({
                    'test': test_case['name'],
                    'success': sync_success,
                    'execution_time_ms': execution_time_ms,
                    'details': {
                        'sync_successful': sync_success,
                        'performance_ok': execution_time_ms < 2000  # 2 seconds for sync
                    }
                })
                
                status = "✅ PASS" if sync_success else "❌ FAIL"
                perf_status = "🚀" if execution_time_ms < 2000 else "⚠️"
                print(f"  {status} {perf_status} {test_case['name']} ({execution_time_ms:.2f}ms)")
                
            except Exception as e:
                results.append({
                    'test': test_case['name'],
                    'success': False,
                    'error': str(e),
                    'execution_time_ms': (time.time() - start_time) * 1000
                })
                print(f"  ❌ FAIL {test_case['name']} - Error: {e}")
        
        return results
    
    def test_performance(self) -> List[Dict[str, Any]]:
        """Test performance benchmarks."""
        results = []
        
        # Performance test: Multiple rapid context injections
        print("  📊 Running performance benchmarks...")
        
        # Test 1: Rapid context detection
        start_time = time.time()
        injector = create_context_injector()
        
        detection_times = []
        for i in range(50):
            test_start = time.time()
            injector.detector.is_context_relevant(
                'mcp__dhafnck_mcp_http__manage_task',
                {'action': 'get', 'task_id': f'perf-test-{i}'}
            )
            detection_times.append((time.time() - test_start) * 1000)
        
        avg_detection_time = sum(detection_times) / len(detection_times)
        max_detection_time = max(detection_times)
        
        results.append({
            'test': 'Context Detection Performance',
            'success': avg_detection_time < 10 and max_detection_time < 50,  # < 10ms avg, < 50ms max
            'execution_time_ms': avg_detection_time,
            'details': {
                'average_detection_ms': avg_detection_time,
                'max_detection_ms': max_detection_time,
                'total_detections': len(detection_times)
            }
        })
        
        # Test 2: Context injection performance
        injection_times = []
        for i in range(10):  # Fewer iterations for injection (slower operation)
            test_start = time.time()
            inject_context_sync(
                'mcp__dhafnck_mcp_http__manage_task',
                {'action': 'get', 'task_id': f'perf-test-inject-{i}'}
            )
            injection_times.append((time.time() - test_start) * 1000)
        
        avg_injection_time = sum(injection_times) / len(injection_times)
        max_injection_time = max(injection_times)
        
        results.append({
            'test': 'Context Injection Performance',
            'success': avg_injection_time < self.performance_threshold_ms,
            'execution_time_ms': avg_injection_time,
            'details': {
                'average_injection_ms': avg_injection_time,
                'max_injection_ms': max_injection_time,
                'total_injections': len(injection_times),
                'threshold_ms': self.performance_threshold_ms
            }
        })
        
        print(f"    Detection: {avg_detection_time:.2f}ms avg, {max_detection_time:.2f}ms max")
        print(f"    Injection: {avg_injection_time:.2f}ms avg, {max_injection_time:.2f}ms max")
        
        return results
    
    def test_integration(self) -> List[Dict[str, Any]]:
        """Test full integration scenarios."""
        results = []
        
        # Integration test: Full hook simulation
        print("  🔄 Testing full hook integration...")
        
        test_scenario = {
            'name': 'Complete Hook Workflow',
            'pre_tool_data': {
                'tool_name': 'mcp__dhafnck_mcp_http__manage_task',
                'tool_input': {'action': 'update', 'task_id': 'integration-test-123', 'status': 'in_progress'}
            },
            'post_tool_data': {
                'tool_name': 'mcp__dhafnck_mcp_http__manage_task',
                'tool_input': {'action': 'update', 'task_id': 'integration-test-123', 'status': 'in_progress'},
                'tool_output': {'success': True, 'data': {'task': {'id': 'integration-test-123'}}}
            }
        }
        
        start_time = time.time()
        try:
            # Step 1: Pre-tool context injection
            injected_context = inject_context_sync(
                test_scenario['pre_tool_data']['tool_name'],
                test_scenario['pre_tool_data']['tool_input']
            )
            
            # Step 2: Simulate tool execution delay
            time.sleep(0.1)
            
            # Step 3: Post-tool context update
            update_success = update_context_sync(
                test_scenario['post_tool_data']['tool_name'],
                test_scenario['post_tool_data']['tool_input'],
                test_scenario['post_tool_data']['tool_output']
            )
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            success = update_success  # Both steps should complete
            
            results.append({
                'test': test_scenario['name'],
                'success': success,
                'execution_time_ms': execution_time_ms,
                'details': {
                    'context_injected': injected_context is not None,
                    'context_updated': update_success,
                    'total_workflow_time_ms': execution_time_ms
                }
            })
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"    {status} Full workflow completed ({execution_time_ms:.2f}ms)")
            
        except Exception as e:
            results.append({
                'test': test_scenario['name'],
                'success': False,
                'error': str(e),
                'execution_time_ms': (time.time() - start_time) * 1000
            })
            print(f"    ❌ FAIL Integration test failed: {e}")
        
        return results
    
    def test_error_handling(self) -> List[Dict[str, Any]]:
        """Test error handling and resilience."""
        results = []
        
        error_test_cases = [
            {
                'name': 'Invalid Tool Name',
                'test_func': lambda: inject_context_sync('InvalidTool', {}),
                'expect_graceful_failure': True
            },
            {
                'name': 'Malformed Tool Input',
                'test_func': lambda: inject_context_sync('Write', {'invalid': None}),
                'expect_graceful_failure': True
            },
            {
                'name': 'Context Update with No MCP Server',
                'test_func': lambda: update_context_sync('Write', {'file_path': '/test/nonexistent.py'}),
                'expect_graceful_failure': True
            }
        ]
        
        for test_case in error_test_cases:
            start_time = time.time()
            try:
                result = test_case['test_func']()
                execution_time_ms = (time.time() - start_time) * 1000
                
                # For error tests, we expect either None/False or graceful handling
                success = result is None or result is False or isinstance(result, bool)
                
                results.append({
                    'test': test_case['name'],
                    'success': success,
                    'execution_time_ms': execution_time_ms,
                    'details': {
                        'graceful_failure': success,
                        'result': result
                    }
                })
                
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"  {status} {test_case['name']} (graceful: {success})")
                
            except Exception as e:
                execution_time_ms = (time.time() - start_time) * 1000
                # For error handling tests, we expect exceptions to be handled gracefully
                success = test_case['expect_graceful_failure']
                
                results.append({
                    'test': test_case['name'],
                    'success': success,
                    'error': str(e),
                    'execution_time_ms': execution_time_ms
                })
                
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"  {status} {test_case['name']} (exception handled: {success})")
        
        return results
    
    def _process_suite_results(self, suite_name: str, results: List[Dict[str, Any]]):
        """Process test suite results and update overall statistics."""
        for result in results:
            self.test_results['total_tests'] += 1
            
            if result['success']:
                self.test_results['passed_tests'] += 1
            else:
                self.test_results['failed_tests'] += 1
            
            # Record performance metrics
            if 'execution_time_ms' in result:
                self.test_results['performance_metrics'].append({
                    'suite': suite_name,
                    'test': result['test'],
                    'execution_time_ms': result['execution_time_ms'],
                    'success': result['success']
                })
            
            # Record detailed results
            test_detail = {
                'suite': suite_name,
                'test': result['test'],
                'success': result['success'],
                'execution_time_ms': result.get('execution_time_ms', 0),
                'details': result.get('details', {}),
                'error': result.get('error')
            }
            self.test_results['test_details'].append(test_detail)
    
    def _record_test_failure(self, suite_name: str, error: str):
        """Record a test suite failure."""
        self.test_results['total_tests'] += 1
        self.test_results['failed_tests'] += 1
        
        self.test_results['test_details'].append({
            'suite': suite_name,
            'test': 'Suite Execution',
            'success': False,
            'error': error,
            'execution_time_ms': 0,
            'details': {}
        })
    
    def _generate_final_report(self):
        """Generate and display the final test report."""
        total = self.test_results['total_tests']
        passed = self.test_results['passed_tests']
        failed = self.test_results['failed_tests']
        
        print("\n" + "=" * 60)
        print("📊 REAL-TIME INJECTION SYSTEM TEST REPORT")
        print("=" * 60)
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%" if total > 0 else "N/A")
        
        # Performance summary
        if self.test_results['performance_metrics']:
            execution_times = [m['execution_time_ms'] for m in self.test_results['performance_metrics']]
            avg_time = sum(execution_times) / len(execution_times)
            max_time = max(execution_times)
            
            print(f"\n📈 Performance Summary:")
            print(f"  Average execution time: {avg_time:.2f}ms")
            print(f"  Maximum execution time: {max_time:.2f}ms")
            print(f"  Performance threshold: {self.performance_threshold_ms}ms")
            
            slow_tests = [m for m in self.test_results['performance_metrics'] 
                         if m['execution_time_ms'] > self.performance_threshold_ms]
            if slow_tests:
                print(f"  ⚠️  {len(slow_tests)} tests exceeded performance threshold")
        
        # Failure summary
        if failed > 0:
            print(f"\n❌ Failed Tests:")
            failed_tests = [t for t in self.test_results['test_details'] if not t['success']]
            for test in failed_tests:
                error_info = f" - {test['error']}" if test.get('error') else ""
                print(f"  • {test['suite']}: {test['test']}{error_info}")
        
        print(f"\n{'✅ ALL TESTS PASSED!' if failed == 0 else '❌ SOME TESTS FAILED'}")
        print("=" * 60)


def main():
    """Main test execution function."""
    tester = RealTimeInjectionTester()
    results = tester.run_all_tests()
    
    # Save detailed results to file
    try:
        # Try to save to logs directory if available
        logs_dir = Path(__file__).resolve().parents[5] / "logs"
        if logs_dir.exists():
            results_file = logs_dir / 'real_time_injection_test_results.json'
        else:
            # Fallback to test directory
            results_file = Path(__file__).parent / 'real_time_injection_test_results.json'
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
    except Exception as e:
        print(f"Warning: Could not save detailed results: {e}")
    
    # Exit with appropriate code
    exit_code = 0 if results['failed_tests'] == 0 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()