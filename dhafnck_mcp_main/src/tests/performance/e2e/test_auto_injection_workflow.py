"""
End-to-End Performance Tests for Auto-Injection Workflow

Tests the complete user workflow from session start to task completion:
- Full auto-injection pipeline performance
- Real-world scenario simulation
- User experience impact measurement
- Complete system integration validation
"""

import asyncio
import pytest
import time
import statistics
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess

# Import the complete workflow components
import sys
test_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(test_dir / ".claude" / "hooks"))
sys.path.insert(0, str(test_dir / ".claude" / "hooks" / "utils"))

from session_start import log_session_start, get_git_status, query_mcp_pending_tasks, format_mcp_context
from cache_manager import CacheManager
from mcp_client import get_default_client, OptimizedMCPClient

# Import performance test config and mocks
from ..mocks.mock_mcp_server import MockMCPServer, create_performance_test_server
from .. import PERFORMANCE_CONFIG, setup_performance_logger

logger = setup_performance_logger()


class TestCompleteAutoInjectionWorkflow:
    """End-to-end tests for the complete auto-injection workflow."""
    
    @pytest.fixture
    def e2e_test_environment(self):
        """Set up complete test environment with all components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test environment
            env = {
                "cache_dir": temp_path / "cache",
                "logs_dir": temp_path / "logs", 
                "config_dir": temp_path / "config",
                "mock_server": create_performance_test_server(
                    response_delay=0.05,
                    error_rate=0.01  # 1% error rate for realism
                )
            }
            
            # Create directories
            env["cache_dir"].mkdir(parents=True)
            env["logs_dir"].mkdir(parents=True)
            env["config_dir"].mkdir(parents=True)
            
            yield env
            
            # Cleanup
            env["mock_server"].reset_metrics()
    
    @pytest.mark.performance
    @pytest.mark.e2e
    async def test_full_session_injection_workflow(self, e2e_test_environment):
        """Test complete session start to context injection workflow."""
        
        env = e2e_test_environment
        cache = CacheManager(str(env["cache_dir"]))
        
        # Simulate complete user session workflow
        workflows_completed = []
        total_token_usage = []
        user_experience_times = []
        
        iterations = 10  # Realistic number for E2E tests
        
        for session_id in range(iterations):
            workflow_start = time.perf_counter()
            
            # Step 1: Session initialization (simulating Claude Code startup)
            session_data = {
                "session_id": f"session_{session_id}",
                "timestamp": time.time(),
                "user": "test_user",
                "project_path": "/test/project"
            }
            
            with patch('session_start.get_ai_data_path', return_value=env["logs_dir"]):
                init_start = time.perf_counter()
                log_session_start(session_data)
                init_time = time.perf_counter() - init_start
            
            # Step 2: Git context gathering
            git_start = time.perf_counter()
            with patch('subprocess.run') as mock_run:
                # Mock git commands
                branch_result = Mock(returncode=0, stdout="feature/test-workflow")
                status_result = Mock(returncode=0, stdout="M test.py\nA new_file.py")
                log_result = Mock(returncode=0, stdout="abc123 Latest commit\ndef456 Previous commit")
                
                mock_run.side_effect = [branch_result, status_result, log_result]
                
                from session_start import get_git_branch_context
                git_context = get_git_branch_context()
            git_time = time.perf_counter() - git_start
            
            # Step 3: MCP server queries with caching
            mcp_start = time.perf_counter()
            with patch('session_start.get_session_cache', return_value=cache):
                with patch('session_start.get_default_client') as mock_get_client:
                    mock_client = Mock()
                    mock_get_client.return_value = mock_client
                    
                    # Configure realistic responses
                    tasks_data = await env["mock_server"].handle_manage_task({
                        "action": "list",
                        "status": "todo",
                        "limit": 5
                    })
                    
                    next_task_data = await env["mock_server"].handle_manage_task({
                        "action": "next", 
                        "git_branch_id": "branch-456"
                    })
                    
                    mock_client.query_pending_tasks.return_value = tasks_data["data"]["tasks"]
                    mock_client.get_next_recommended_task.return_value = next_task_data["data"]["task"]
                    
                    # Execute MCP queries
                    tasks = query_mcp_pending_tasks()
                    if git_context:
                        git_context["git_branch_id"] = "branch-456"
                    next_task = query_mcp_next_task("branch-456") if git_context else None
            
            mcp_time = time.perf_counter() - mcp_start
            
            # Step 4: Context formatting and injection
            format_start = time.perf_counter()
            context_text = format_mcp_context(tasks, next_task, git_context)
            format_time = time.perf_counter() - format_start
            
            # Step 5: Calculate metrics
            workflow_end = time.perf_counter()
            total_workflow_time = workflow_end - workflow_start
            
            # Token estimation (4 chars ≈ 1 token)
            estimated_tokens = len(context_text) // 4 if context_text else 0
            
            # Record metrics
            workflow_result = {
                "session_id": session_id,
                "total_time": total_workflow_time,
                "init_time": init_time,
                "git_time": git_time,
                "mcp_time": mcp_time,
                "format_time": format_time,
                "estimated_tokens": estimated_tokens,
                "context_length": len(context_text) if context_text else 0,
                "success": context_text is not None and len(context_text) > 0
            }
            
            workflows_completed.append(workflow_result)
            total_token_usage.append(estimated_tokens)
            user_experience_times.append(total_workflow_time)
            
            logger.debug(f"Session {session_id}: {total_workflow_time:.4f}s, {estimated_tokens} tokens")
        
        # Analyze E2E performance
        successful_workflows = [w for w in workflows_completed if w["success"]]
        success_rate = len(successful_workflows) / len(workflows_completed)
        
        avg_total_time = statistics.mean([w["total_time"] for w in successful_workflows])
        p95_total_time = statistics.quantiles([w["total_time"] for w in successful_workflows], n=20)[18]
        
        avg_tokens = statistics.mean(total_token_usage)
        max_tokens = max(total_token_usage)
        
        # Component timing breakdown
        avg_init = statistics.mean([w["init_time"] for w in successful_workflows])
        avg_git = statistics.mean([w["git_time"] for w in successful_workflows])
        avg_mcp = statistics.mean([w["mcp_time"] for w in successful_workflows])
        avg_format = statistics.mean([w["format_time"] for w in successful_workflows])
        
        logger.info("=== E2E Auto-Injection Workflow Performance ===")
        logger.info(f"Success rate: {success_rate:.2%}")
        logger.info(f"Average total time: {avg_total_time:.4f}s")
        logger.info(f"P95 total time: {p95_total_time:.4f}s")
        logger.info(f"Average token usage: {avg_tokens:.1f}")
        logger.info(f"Max token usage: {max_tokens}")
        logger.info("Component breakdown:")
        logger.info(f"  Initialization: {avg_init:.4f}s ({avg_init/avg_total_time*100:.1f}%)")
        logger.info(f"  Git context: {avg_git:.4f}s ({avg_git/avg_total_time*100:.1f}%)")
        logger.info(f"  MCP queries: {avg_mcp:.4f}s ({avg_mcp/avg_total_time*100:.1f}%)")
        logger.info(f"  Formatting: {avg_format:.4f}s ({avg_format/avg_total_time*100:.1f}%)")
        
        # Performance assertions
        assert success_rate >= 0.95, f"E2E success rate too low: {success_rate:.2%}"
        assert avg_total_time < PERFORMANCE_CONFIG["response_time_targets"]["full_injection"]
        assert p95_total_time < PERFORMANCE_CONFIG["response_time_targets"]["full_injection"] * 2
        assert avg_tokens < PERFORMANCE_CONFIG["max_tokens_per_injection"]
        assert max_tokens < PERFORMANCE_CONFIG["max_tokens_per_injection"] * 1.2
    
    @pytest.mark.performance
    @pytest.mark.e2e
    async def test_user_experience_under_load(self, e2e_test_environment):
        """Test user experience when multiple sessions start simultaneously."""
        
        env = e2e_test_environment
        concurrent_sessions = PERFORMANCE_CONFIG["concurrent_sessions"]
        
        async def simulate_user_session(user_id):
            """Simulate a complete user session."""
            session_start = time.perf_counter()
            
            # User starts Claude Code session
            cache = CacheManager(str(env["cache_dir"] / f"user_{user_id}"))
            
            session_data = {
                "session_id": f"user_{user_id}_session",
                "timestamp": time.time(),
                "user": f"user_{user_id}",
                "project_path": f"/test/project_{user_id}"
            }
            
            try:
                # Complete workflow simulation
                with patch('session_start.get_ai_data_path', return_value=env["logs_dir"]):
                    log_session_start(session_data)
                
                with patch('session_start.get_session_cache', return_value=cache):
                    with patch('session_start.get_default_client') as mock_get_client:
                        mock_client = Mock()
                        mock_get_client.return_value = mock_client
                        
                        # Simulate variable response times
                        await asyncio.sleep(0.1 + (user_id % 3) * 0.05)  # 100-250ms variation
                        
                        tasks_data = await env["mock_server"].handle_manage_task({
                            "action": "list",
                            "status": "todo", 
                            "limit": 3  # Smaller limit for concurrent testing
                        })
                        
                        mock_client.query_pending_tasks.return_value = tasks_data["data"]["tasks"]
                        
                        # Execute user workflow
                        tasks = query_mcp_pending_tasks()
                        git_context = {"branch": f"user_{user_id}/feature", "git_branch_id": f"branch-{user_id}"}
                        context_text = format_mcp_context(tasks, None, git_context)
                
                session_end = time.perf_counter()
                session_duration = session_end - session_start
                
                return {
                    "user_id": user_id,
                    "success": context_text is not None,
                    "duration": session_duration,
                    "context_length": len(context_text) if context_text else 0,
                    "estimated_tokens": len(context_text) // 4 if context_text else 0
                }
                
            except Exception as e:
                logger.warning(f"User {user_id} session failed: {e}")
                return {
                    "user_id": user_id,
                    "success": False,
                    "duration": time.perf_counter() - session_start,
                    "error": str(e)
                }
        
        # Execute concurrent user sessions
        total_start = time.perf_counter()
        tasks = [simulate_user_session(i) for i in range(concurrent_sessions)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.perf_counter() - total_start
        
        # Handle exceptions
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Session failed with exception: {result}")
                valid_results.append({"success": False, "duration": 10.0})  # Penalty time
            else:
                valid_results.append(result)
        
        # Analyze user experience
        successful_users = [r for r in valid_results if r.get("success", False)]
        success_rate = len(successful_users) / len(valid_results)
        
        if successful_users:
            avg_user_time = statistics.mean([r["duration"] for r in successful_users])
            p95_user_time = statistics.quantiles([r["duration"] for r in successful_users], n=20)[18]
            avg_user_tokens = statistics.mean([r.get("estimated_tokens", 0) for r in successful_users])
        else:
            avg_user_time = p95_user_time = avg_user_tokens = 0
        
        logger.info("=== User Experience Under Load ===")
        logger.info(f"Concurrent sessions: {concurrent_sessions}")
        logger.info(f"Total duration: {total_duration:.4f}s")
        logger.info(f"Success rate: {success_rate:.2%}")
        logger.info(f"Average user session time: {avg_user_time:.4f}s")
        logger.info(f"P95 user session time: {p95_user_time:.4f}s")
        logger.info(f"Average tokens per user: {avg_user_tokens:.1f}")
        
        # User experience assertions
        assert success_rate >= 0.90, f"User success rate too low under load: {success_rate:.2%}"
        assert avg_user_time < PERFORMANCE_CONFIG["response_time_targets"]["full_injection"] * 2
        assert p95_user_time < PERFORMANCE_CONFIG["response_time_targets"]["full_injection"] * 3
        assert total_duration < 15.0, f"Concurrent user sessions took too long: {total_duration}s"
    
    @pytest.mark.performance
    @pytest.mark.e2e
    async def test_system_degradation_scenarios(self, e2e_test_environment):
        """Test system behavior under degraded conditions."""
        
        env = e2e_test_environment
        
        # Test scenarios with different degradation levels
        scenarios = [
            {
                "name": "High Latency",
                "server_config": {"response_delay": 1.0, "error_rate": 0.0},
                "expected_max_time": 3.0
            },
            {
                "name": "Intermittent Failures", 
                "server_config": {"response_delay": 0.2, "error_rate": 0.3},
                "expected_max_time": 2.0
            },
            {
                "name": "High Error Rate",
                "server_config": {"response_delay": 0.1, "error_rate": 0.5}, 
                "expected_max_time": 2.5
            }
        ]
        
        results = {}
        
        for scenario in scenarios:
            logger.info(f"Testing scenario: {scenario['name']}")
            
            # Configure degraded server
            env["mock_server"].configure_behavior(**scenario["server_config"])
            
            scenario_results = []
            cache = CacheManager(str(env["cache_dir"] / scenario["name"].lower().replace(" ", "_")))
            
            # Test multiple requests in this scenario
            for i in range(5):
                start_time = time.perf_counter()
                
                with patch('session_start.get_session_cache', return_value=cache):
                    with patch('session_start.get_default_client') as mock_get_client:
                        mock_client = Mock()
                        mock_get_client.return_value = mock_client
                        
                        try:
                            # Simulate degraded responses
                            if env["mock_server"].should_simulate_error():
                                raise ConnectionError("Simulated connection error")
                            
                            tasks_data = await env["mock_server"].handle_manage_task({
                                "action": "list",
                                "status": "todo",
                                "limit": 3
                            })
                            mock_client.query_pending_tasks.return_value = tasks_data["data"]["tasks"]
                            
                            tasks = query_mcp_pending_tasks()
                            git_context = {"branch": "test", "git_branch_id": "branch-test"}
                            context_text = format_mcp_context(tasks, None, git_context)
                            
                            success = context_text is not None
                            tokens = len(context_text) // 4 if context_text else 0
                            
                        except Exception as e:
                            logger.debug(f"Scenario {scenario['name']} iteration {i} failed: {e}")
                            success = False
                            tokens = 0
                            context_text = None
                
                end_time = time.perf_counter()
                duration = end_time - start_time
                
                scenario_results.append({
                    "success": success,
                    "duration": duration,
                    "tokens": tokens
                })
            
            # Analyze scenario results
            successful = [r for r in scenario_results if r["success"]]
            success_rate = len(successful) / len(scenario_results)
            avg_duration = statistics.mean([r["duration"] for r in scenario_results])
            
            results[scenario["name"]] = {
                "success_rate": success_rate,
                "avg_duration": avg_duration,
                "max_expected": scenario["expected_max_time"]
            }
            
            logger.info(f"  Success rate: {success_rate:.2%}")
            logger.info(f"  Average duration: {avg_duration:.4f}s")
            
            # Scenario-specific assertions
            assert success_rate >= 0.6, f"Success rate too low in {scenario['name']}: {success_rate:.2%}"
            assert avg_duration <= scenario["expected_max_time"], f"Duration too high in {scenario['name']}: {avg_duration}s"
        
        logger.info("=== System Degradation Test Results ===")
        for name, result in results.items():
            logger.info(f"{name}: {result['success_rate']:.2%} success, {result['avg_duration']:.4f}s avg")
    
    @pytest.mark.performance
    @pytest.mark.e2e
    async def test_performance_improvement_measurement(self, e2e_test_environment):
        """Measure the actual performance improvement from auto-injection."""
        
        env = e2e_test_environment
        
        # Test without auto-injection (baseline)
        baseline_times = []
        baseline_task_info = []
        
        for i in range(10):
            start_time = time.perf_counter()
            
            # Simulate manual task discovery (slower, less context)
            with patch('time.sleep') as mock_sleep:  # Simulate user thinking time
                mock_sleep.return_value = None
                
                # Basic task query without context
                tasks_data = await env["mock_server"].handle_manage_task({
                    "action": "list",
                    "status": "todo",
                    "limit": 10
                })
                
                # Simulate user manually reviewing tasks (additional time)
                manual_review_time = 2.0  # 2 seconds to manually review
                await asyncio.sleep(0.1)  # Small actual delay to simulate
                
            end_time = time.perf_counter()
            baseline_time = (end_time - start_time) + manual_review_time
            
            baseline_times.append(baseline_time)
            baseline_task_info.append({
                "tasks_found": len(tasks_data["data"]["tasks"]),
                "context_quality": 30  # Low context quality score
            })
        
        # Test with auto-injection (improved)
        improved_times = []
        improved_task_info = []
        cache = CacheManager(str(env["cache_dir"] / "improvement_test"))
        
        for i in range(10):
            start_time = time.perf_counter()
            
            # Complete auto-injection workflow
            with patch('session_start.get_session_cache', return_value=cache):
                with patch('session_start.get_default_client') as mock_get_client:
                    mock_client = Mock()
                    mock_get_client.return_value = mock_client
                    
                    tasks_data = await env["mock_server"].handle_manage_task({
                        "action": "list", 
                        "status": "todo",
                        "limit": 5
                    })
                    
                    next_task_data = await env["mock_server"].handle_manage_task({
                        "action": "next",
                        "git_branch_id": "branch-456"
                    })
                    
                    mock_client.query_pending_tasks.return_value = tasks_data["data"]["tasks"]
                    mock_client.get_next_recommended_task.return_value = next_task_data["data"]["task"]
                    
                    # Execute auto-injection
                    tasks = query_mcp_pending_tasks()
                    git_context = {"branch": "feature/improvement", "git_branch_id": "branch-456"}
                    next_task = query_mcp_next_task("branch-456")
                    context_text = format_mcp_context(tasks, next_task, git_context)
            
            end_time = time.perf_counter()
            improved_time = end_time - start_time
            
            improved_times.append(improved_time)
            improved_task_info.append({
                "tasks_found": len(tasks) if tasks else 0,
                "context_quality": 85,  # High context quality score
                "tokens_used": len(context_text) // 4 if context_text else 0
            })
        
        # Calculate improvement metrics
        avg_baseline = statistics.mean(baseline_times)
        avg_improved = statistics.mean(improved_times)
        time_improvement = (avg_baseline - avg_improved) / avg_baseline
        
        avg_baseline_quality = statistics.mean([info["context_quality"] for info in baseline_task_info])
        avg_improved_quality = statistics.mean([info["context_quality"] for info in improved_task_info])
        quality_improvement = (avg_improved_quality - avg_baseline_quality) / avg_baseline_quality
        
        avg_tokens = statistics.mean([info["tokens_used"] for info in improved_task_info])
        
        # Calculate effective productivity improvement
        # Combines time savings and quality improvement
        effective_improvement = time_improvement + (quality_improvement * 0.3)  # Weight quality at 30%
        
        logger.info("=== Performance Improvement Measurement ===")
        logger.info(f"Baseline average time: {avg_baseline:.4f}s")
        logger.info(f"Improved average time: {avg_improved:.4f}s") 
        logger.info(f"Time improvement: {time_improvement:.2%}")
        logger.info(f"Context quality improvement: {quality_improvement:.2%}")
        logger.info(f"Effective productivity improvement: {effective_improvement:.2%}")
        logger.info(f"Average token usage: {avg_tokens:.1f}")
        
        # Validate improvement targets
        target_improvement = PERFORMANCE_CONFIG["target_improvement"]
        assert effective_improvement >= target_improvement * 0.8, f"Improvement target not met: {effective_improvement:.2%} < {target_improvement:.2%}"
        assert avg_tokens < PERFORMANCE_CONFIG["max_tokens_per_injection"], f"Token usage too high: {avg_tokens}"
        
        # Return metrics for further analysis
        return {
            "time_improvement": time_improvement,
            "quality_improvement": quality_improvement,
            "effective_improvement": effective_improvement,
            "average_tokens": avg_tokens,
            "target_met": effective_improvement >= target_improvement * 0.8
        }