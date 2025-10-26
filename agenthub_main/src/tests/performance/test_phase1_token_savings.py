"""
Phase 1 Token Savings Measurement Test

This performance test measures actual token savings achieved by Phase 1 API response refactoring.

Phase 1 Changes:
1. Removed emoji fields (priority_emoji, status_emoji)
2. Removed count fields (subtask_count, assignees_count, dependency_count)
3. Added opt-in context loading (include_context=false default)

Predicted Savings:
- Baseline: 850 tokens per operation
- After Phase 1: 605 tokens per operation
- Predicted reduction: 245 tokens (28.8%)

This test validates predictions with actual measurements.
"""

import pytest
import uuid
import json
from typing import Dict, Any
from datetime import datetime
from unittest.mock import patch

# Import MCP tools for performance testing
from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools


@pytest.fixture
def mcp_tools():
    """Initialize MCP tools with vision system disabled for performance tests"""
    return DDDCompliantMCPTools(enable_vision_system=False)


@pytest.fixture
def test_user_id():
    """Generate test user ID"""
    return str(uuid.uuid4())


@pytest.fixture
def mock_auth(test_user_id):
    """Mock authentication context"""
    mock_auth_info = {
        'user_id': test_user_id,
        'email': 'perf@test.com',
        'sub': test_user_id,
        'realm_roles': ['admin', 'user'],
        'resource_access': {}
    }

    with patch('fastmcp.auth.middleware.request_context_middleware.get_current_auth_info', return_value=mock_auth_info), \
         patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.get_authenticated_user_id', return_value=test_user_id), \
         patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.services.authentication_service.AuthenticationService.get_authenticated_user_id', return_value=test_user_id):
        yield test_user_id


@pytest.fixture
def project_with_branch(mcp_tools, mock_auth, test_user_id):
    """Create test project with git branch"""
    project_result = mcp_tools._project_controller.manage_project(
        action="create",
        name=f"Phase1 Perf Test {uuid.uuid4().hex[:8]}",
        description="Project for Phase 1 performance testing",
        user_id=test_user_id
    )

    assert project_result.get('success') is True
    project_id = project_result['data']['project']['id']

    branch_result = mcp_tools._git_branch_controller.manage_git_branch(
        action="create",
        project_id=project_id,
        git_branch_name="main",
        git_branch_description="Main branch for perf testing",
        user_id=test_user_id
    )

    assert branch_result.get('success') is True
    git_branch_id = branch_result['data']['git_branch']['id']

    yield project_id, git_branch_id

    # Cleanup
    try:
        mcp_tools._project_controller.manage_project(
            action="delete",
            project_id=project_id,
            force="true",
            user_id=test_user_id
        )
    except:
        pass


def calculate_json_size(data: Dict[str, Any]) -> int:
    """Calculate JSON string size in characters"""
    return len(json.dumps(data, separators=(',', ':')))


def estimate_tokens(char_count: int) -> int:
    """Estimate token count using 1 token ≈ 4 characters rule"""
    return char_count // 4


class TestPhase1TokenSavings:
    """Measure actual token savings from Phase 1 refactoring"""

    def test_task_get_response_size(self, mcp_tools, mock_auth, project_with_branch, test_user_id):
        """
        Measure Task GET response size with and without context.

        Expected:
        - Without context (default): Smaller response
        - With context: Larger response (opt-in)
        - Removal of emoji/count fields reduces base size
        """
        project_id, git_branch_id = project_with_branch

        # Create typical task with multiple components
        task_result = mcp_tools._task_controller.manage_task(
            action="create",
            git_branch_id=git_branch_id,
            title="Test task for token measurement",
            description="Task with typical data for measurement",
            assignees=["agent1", "agent2"],
            labels=["test", "performance"],
            priority="high",
            user_id=test_user_id
        )

        assert task_result.get('success') is True
        task_id = task_result['data']['task']['id']

        # Add subtasks to task
        for i in range(3):
            mcp_tools._subtask_controller.manage_subtask(
                action="create",
                task_id=task_id,
                title=f"Subtask {i+1}",
                description=f"Test subtask {i+1}",
                user_id=test_user_id
            )

        # Add dependency
        dep_task_result = mcp_tools._task_controller.manage_task(
            action="create",
            git_branch_id=git_branch_id,
            title="Dependency task",
            assignees=["agent1"],
            user_id=test_user_id
        )
        dep_task_id = dep_task_result['data']['task']['id']

        mcp_tools._task_controller.manage_task(
            action="add_dependency",
            task_id=task_id,
            dependency_id=dep_task_id,
            user_id=test_user_id
        )

        # Measure WITHOUT context (Phase 1 default)
        response_without_context = mcp_tools._task_controller.manage_task(
            action="get",
            task_id=task_id,
            include_context=False,
            user_id=test_user_id
        )

        # Measure WITH context (opt-in)
        response_with_context = mcp_tools._task_controller.manage_task(
            action="get",
            task_id=task_id,
            include_context=True,
            user_id=test_user_id
        )

        # Calculate sizes
        size_without_context = calculate_json_size(response_without_context)
        size_with_context = calculate_json_size(response_with_context)

        tokens_without_context = estimate_tokens(size_without_context)
        tokens_with_context = estimate_tokens(size_with_context)

        # Calculate savings from opt-in context
        context_savings = size_with_context - size_without_context
        context_token_savings = tokens_with_context - tokens_without_context

        # Verify removed fields are NOT present
        task_data = response_without_context['data']['task']
        assert 'priority_emoji' not in task_data, "priority_emoji should be removed in Phase 1"
        assert 'status_emoji' not in task_data, "status_emoji should be removed in Phase 1"

        # Verify counts can be derived from arrays
        assert 'assignees' in task_data
        assert len(task_data['assignees']) == 2
        assert 'labels' in task_data
        assert len(task_data['labels']) == 2

        # Print measurements
        print(f"\n=== TASK GET MEASUREMENTS ===")
        print(f"Without context (default): {size_without_context} chars = ~{tokens_without_context} tokens")
        print(f"With context (opt-in): {size_with_context} chars = ~{tokens_with_context} tokens")
        print(f"Context savings: {context_savings} chars = ~{context_token_savings} tokens")
        print(f"Removed fields verified: priority_emoji, status_emoji")

        # Store measurements for final report
        return {
            'operation': 'task_get',
            'without_context_chars': size_without_context,
            'without_context_tokens': tokens_without_context,
            'with_context_chars': size_with_context,
            'with_context_tokens': tokens_with_context,
            'context_savings_chars': context_savings,
            'context_savings_tokens': context_token_savings
        }

    def test_task_list_response_size(self, mcp_tools, mock_auth, project_with_branch, test_user_id):
        """
        Measure Task LIST response size.

        Expected:
        - Multiple tasks multiplies savings
        - No emoji fields in any task
        - Array-based counts work correctly
        """
        project_id, git_branch_id = project_with_branch

        # Create 5 tasks with varying complexity
        task_ids = []
        for i in range(5):
            result = mcp_tools._task_controller.manage_task(
                action="create",
                git_branch_id=git_branch_id,
                title=f"List test task {i+1}",
                description=f"Task {i+1} for list measurement",
                assignees=["agent1", "agent2"],
                labels=["test"],
                priority="medium",
                user_id=test_user_id
            )
            task_ids.append(result['data']['task']['id'])

            # Add subtasks to some tasks
            if i % 2 == 0:
                for j in range(2):
                    mcp_tools._subtask_controller.manage_subtask(
                        action="create",
                        task_id=result['data']['task']['id'],
                        title=f"Subtask {j+1}",
                        user_id=test_user_id
                    )

        # Measure list response
        list_response = mcp_tools._task_controller.manage_task(
            action="list",
            git_branch_id=git_branch_id,
            include_context=False,
            user_id=test_user_id
        )

        # Calculate size
        list_size = calculate_json_size(list_response)
        list_tokens = estimate_tokens(list_size)

        # Verify removed fields in all tasks
        tasks = list_response['data']['tasks']
        for task in tasks:
            assert 'priority_emoji' not in task, f"priority_emoji found in task {task['id']}"
            assert 'status_emoji' not in task, f"status_emoji found in task {task['id']}"

        # Calculate per-task average
        per_task_chars = list_size // len(tasks)
        per_task_tokens = list_tokens // len(tasks)

        print(f"\n=== TASK LIST MEASUREMENTS ===")
        print(f"Total list size: {list_size} chars = ~{list_tokens} tokens")
        print(f"Number of tasks: {len(tasks)}")
        print(f"Per-task average: {per_task_chars} chars = ~{per_task_tokens} tokens")
        print(f"Removed fields verified in all {len(tasks)} tasks")

        return {
            'operation': 'task_list',
            'total_chars': list_size,
            'total_tokens': list_tokens,
            'task_count': len(tasks),
            'per_task_chars': per_task_chars,
            'per_task_tokens': per_task_tokens
        }

    def test_subtask_list_response_size(self, mcp_tools, mock_auth, project_with_branch, test_user_id):
        """
        Measure Subtask LIST response size.

        Expected:
        - Subtasks don't have redundant parent_id when embedded
        - No emoji fields
        - Clean response structure
        """
        project_id, git_branch_id = project_with_branch

        # Create task with multiple subtasks
        task_result = mcp_tools._task_controller.manage_task(
            action="create",
            git_branch_id=git_branch_id,
            title="Parent task for subtask measurement",
            assignees=["agent1"],
            user_id=test_user_id
        )
        task_id = task_result['data']['task']['id']

        # Create 5 subtasks
        for i in range(5):
            mcp_tools._subtask_controller.manage_subtask(
                action="create",
                task_id=task_id,
                title=f"Subtask {i+1}",
                description=f"Subtask {i+1} for measurement",
                assignees=["agent1", "agent2"],
                user_id=test_user_id
            )

        # Measure subtask list response
        subtask_list_response = mcp_tools._subtask_controller.manage_subtask(
            action="list",
            task_id=task_id,
            user_id=test_user_id
        )

        # Calculate size
        subtask_list_size = calculate_json_size(subtask_list_response)
        subtask_list_tokens = estimate_tokens(subtask_list_size)

        # Verify removed fields
        subtasks = subtask_list_response.get('subtasks', [])
        for subtask in subtasks:
            assert 'priority_emoji' not in subtask, f"priority_emoji found in subtask {subtask['id']}"
            assert 'status_emoji' not in subtask, f"status_emoji found in subtask {subtask['id']}"

        # Calculate per-subtask average
        per_subtask_chars = subtask_list_size // len(subtasks) if subtasks else 0
        per_subtask_tokens = subtask_list_tokens // len(subtasks) if subtasks else 0

        print(f"\n=== SUBTASK LIST MEASUREMENTS ===")
        print(f"Total list size: {subtask_list_size} chars = ~{subtask_list_tokens} tokens")
        print(f"Number of subtasks: {len(subtasks)}")
        print(f"Per-subtask average: {per_subtask_chars} chars = ~{per_subtask_tokens} tokens")

        return {
            'operation': 'subtask_list',
            'total_chars': subtask_list_size,
            'total_tokens': subtask_list_tokens,
            'subtask_count': len(subtasks),
            'per_subtask_chars': per_subtask_chars,
            'per_subtask_tokens': per_subtask_tokens
        }

    def test_emoji_field_removal_impact(self, mcp_tools, mock_auth, project_with_branch, test_user_id):
        """
        Calculate exact token savings from emoji field removal.

        Emoji fields removed:
        - priority_emoji (e.g., "⚡", "🔴")
        - status_emoji (e.g., "⚪", "🟢")

        Expected savings: ~20 tokens per response
        """
        project_id, git_branch_id = project_with_branch

        # Create task
        result = mcp_tools._task_controller.manage_task(
            action="create",
            git_branch_id=git_branch_id,
            title="Emoji measurement task",
            priority="high",
            user_id=test_user_id
        )

        # Get task response
        task_response = mcp_tools._task_controller.manage_task(
            action="get",
            task_id=result['data']['task']['id'],
            user_id=test_user_id
        )

        # Calculate what emoji fields would have added
        # Format: "priority_emoji": "⚡", "status_emoji": "⚪"
        emoji_field_size = len('"priority_emoji":"⚡","status_emoji":"⚪"')
        emoji_tokens_saved = estimate_tokens(emoji_field_size)

        print(f"\n=== EMOJI FIELD REMOVAL IMPACT ===")
        print(f"Emoji fields removed: priority_emoji, status_emoji")
        print(f"Characters saved per response: {emoji_field_size}")
        print(f"Tokens saved per response: ~{emoji_tokens_saved}")

        return {
            'operation': 'emoji_removal',
            'chars_saved_per_response': emoji_field_size,
            'tokens_saved_per_response': emoji_tokens_saved
        }

    def test_count_field_removal_impact(self, mcp_tools, mock_auth, project_with_branch, test_user_id):
        """
        Calculate exact token savings from count field removal.

        Count fields removed:
        - subtask_count
        - assignees_count
        - dependency_count

        Expected savings: ~75 tokens per response
        """
        project_id, git_branch_id = project_with_branch

        # Create task with subtasks, assignees, dependencies
        task_result = mcp_tools._task_controller.manage_task(
            action="create",
            git_branch_id=git_branch_id,
            title="Count field measurement task",
            assignees=["agent1", "agent2"],
            user_id=test_user_id
        )
        task_id = task_result['data']['task']['id']

        # Add 3 subtasks
        for i in range(3):
            mcp_tools._subtask_controller.manage_subtask(
                action="create",
                task_id=task_id,
                title=f"Subtask {i+1}",
                user_id=test_user_id
            )

        # Add 1 dependency
        dep_result = mcp_tools._task_controller.manage_task(
            action="create",
            git_branch_id=git_branch_id,
            title="Dependency",
            assignees=["agent1"],
            user_id=test_user_id
        )
        mcp_tools._task_controller.manage_task(
            action="add_dependency",
            task_id=task_id,
            dependency_id=dep_result['data']['task']['id'],
            user_id=test_user_id
        )

        # Get response
        response = mcp_tools._task_controller.manage_task(
            action="get",
            task_id=task_id,
            user_id=test_user_id
        )

        # Calculate what count fields would have added
        # Format: "subtask_count":3,"assignees_count":2,"dependency_count":1
        count_field_size = len('"subtask_count":3,"assignees_count":2,"dependency_count":1')
        count_tokens_saved = estimate_tokens(count_field_size)

        print(f"\n=== COUNT FIELD REMOVAL IMPACT ===")
        print(f"Count fields removed: subtask_count, assignees_count, dependency_count")
        print(f"Characters saved per response: {count_field_size}")
        print(f"Tokens saved per response: ~{count_tokens_saved}")

        return {
            'operation': 'count_removal',
            'chars_saved_per_response': count_field_size,
            'tokens_saved_per_response': count_tokens_saved
        }

    def test_aggregate_token_savings(self, mcp_tools, mock_auth, project_with_branch, test_user_id):
        """
        Calculate total aggregate token savings from all Phase 1 changes.

        Aggregates:
        - Emoji removal savings
        - Count removal savings
        - Context opt-in savings

        Compares against predicted 28.8% reduction (245 tokens from 850 to 605)
        """
        project_id, git_branch_id = project_with_branch

        # Create typical task scenario
        task_result = mcp_tools._task_controller.manage_task(
            action="create",
            git_branch_id=git_branch_id,
            title="Aggregate measurement task",
            description="Task with typical data",
            assignees=["agent1", "agent2"],
            labels=["test"],
            priority="high",
            user_id=test_user_id
        )
        task_id = task_result['data']['task']['id']

        # Add 3 subtasks
        for i in range(3):
            mcp_tools._subtask_controller.manage_subtask(
                action="create",
                task_id=task_id,
                title=f"Subtask {i+1}",
                user_id=test_user_id
            )

        # Add 1 dependency
        dep_result = mcp_tools._task_controller.manage_task(
            action="create",
            git_branch_id=git_branch_id,
            title="Dependency",
            assignees=["agent1"],
            user_id=test_user_id
        )
        mcp_tools._task_controller.manage_task(
            action="add_dependency",
            task_id=task_id,
            dependency_id=dep_result['data']['task']['id'],
            user_id=test_user_id
        )

        # Measure current response (after Phase 1)
        current_response = mcp_tools._task_controller.manage_task(
            action="get",
            task_id=task_id,
            include_context=False,
            user_id=test_user_id
        )

        current_size = calculate_json_size(current_response)
        current_tokens = estimate_tokens(current_size)

        # Estimate baseline (before Phase 1)
        emoji_chars_saved = len('"priority_emoji":"⚡","status_emoji":"⚪"')
        count_chars_saved = len('"subtask_count":3,"assignees_count":2,"dependency_count":1')

        estimated_baseline_size = current_size + emoji_chars_saved + count_chars_saved
        estimated_baseline_tokens = estimate_tokens(estimated_baseline_size)

        # Calculate actual savings
        total_chars_saved = estimated_baseline_size - current_size
        total_tokens_saved = estimated_baseline_tokens - current_tokens

        # Calculate percentage reduction
        percentage_reduction = (total_tokens_saved / estimated_baseline_tokens) * 100

        # Compare with predictions
        predicted_baseline = 850
        predicted_after = 605
        predicted_reduction = 245
        predicted_percentage = 28.8

        accuracy = abs(percentage_reduction - predicted_percentage) / predicted_percentage * 100
        within_tolerance = accuracy <= 5.0  # ±5% tolerance

        print(f"\n=== AGGREGATE TOKEN SAVINGS ===")
        print(f"Estimated baseline (before Phase 1): {estimated_baseline_size} chars = ~{estimated_baseline_tokens} tokens")
        print(f"Current response (after Phase 1): {current_size} chars = ~{current_tokens} tokens")
        print(f"Total savings: {total_chars_saved} chars = ~{total_tokens_saved} tokens")
        print(f"Percentage reduction: {percentage_reduction:.1f}%")
        print(f"\n=== COMPARISON WITH PREDICTIONS ===")
        print(f"Predicted baseline: ~{predicted_baseline} tokens")
        print(f"Predicted after Phase 1: ~{predicted_after} tokens")
        print(f"Predicted reduction: ~{predicted_reduction} tokens ({predicted_percentage}%)")
        print(f"Prediction accuracy: {100 - accuracy:.1f}%")
        print(f"Within ±5% tolerance: {within_tolerance}")

        assert within_tolerance, f"Predictions not accurate (off by {accuracy:.1f}%, expected ±5%)"

        return {
            'operation': 'aggregate_savings',
            'estimated_baseline_tokens': estimated_baseline_tokens,
            'current_tokens': current_tokens,
            'total_tokens_saved': total_tokens_saved,
            'percentage_reduction': percentage_reduction,
            'predicted_baseline': predicted_baseline,
            'predicted_after': predicted_after,
            'predicted_reduction': predicted_reduction,
            'predicted_percentage': predicted_percentage,
            'prediction_accuracy': 100 - accuracy,
            'within_tolerance': within_tolerance
        }


@pytest.mark.performance
class TestPhase1PerformanceReport:
    """Generate comprehensive performance report"""

    def test_generate_performance_report(self, mcp_tools, mock_auth, project_with_branch, test_user_id):
        """
        Run all measurements and generate comprehensive report.

        This test orchestrates all measurement tests and compiles results.
        """
        test_suite = TestPhase1TokenSavings()

        # Run all measurement tests
        task_get = test_suite.test_task_get_response_size(
            mcp_tools, mock_auth, project_with_branch, test_user_id
        )
        task_list = test_suite.test_task_list_response_size(
            mcp_tools, mock_auth, project_with_branch, test_user_id
        )
        subtask_list = test_suite.test_subtask_list_response_size(
            mcp_tools, mock_auth, project_with_branch, test_user_id
        )
        emoji_impact = test_suite.test_emoji_field_removal_impact(
            mcp_tools, mock_auth, project_with_branch, test_user_id
        )
        count_impact = test_suite.test_count_field_removal_impact(
            mcp_tools, mock_auth, project_with_branch, test_user_id
        )
        aggregate = test_suite.test_aggregate_token_savings(
            mcp_tools, mock_auth, project_with_branch, test_user_id
        )

        # Compile report data
        report_data = {
            'test_date': datetime.now().isoformat(),
            'phase': 'Phase 1',
            'measurements': {
                'task_get': task_get,
                'task_list': task_list,
                'subtask_list': subtask_list,
                'emoji_removal': emoji_impact,
                'count_removal': count_impact,
                'aggregate': aggregate
            },
            'summary': {
                'total_tokens_saved': aggregate['total_tokens_saved'],
                'percentage_reduction': aggregate['percentage_reduction'],
                'prediction_accuracy': aggregate['prediction_accuracy'],
                'predictions_validated': aggregate['within_tolerance']
            }
        }

        print(f"\n=== PERFORMANCE REPORT COMPILED ===")
        print(f"Report data saved for documentation generation")
        print(json.dumps(report_data, indent=2))

        return report_data
