"""
Week 1 Performance Baseline Tests
Target: 3x improvement (150ms → 50ms)

This module implements comprehensive baseline performance tests for Week 1 optimization goals.
Tests measure current performance and validate the 3x improvement target across key operations.

Performance Targets:
- Task creation: 150ms → 50ms (3x faster)
- Task retrieval: 100ms → 33ms (3x faster)
- Task listing: 200ms → 67ms (3x faster)
- Task updates: 120ms → 40ms (3x faster)
- Subtask operations: 80ms → 27ms (3x faster)

Success Criteria:
- All operations must meet or exceed 3x improvement target
- Memory usage must remain stable
- Database connection pool must not be exhausted
- No degradation in data integrity
"""

import inspect
import statistics
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest

from fastmcp.task_management.application.dtos.task.create_task_request import (
    CreateTaskRequest,
)
from fastmcp.task_management.application.dtos.task.update_task_request import (
    UpdateTaskRequest,
)
from fastmcp.task_management.application.facades.task_application_facade import (
    TaskApplicationFacade,
)
from fastmcp.task_management.infrastructure.database.database_config import get_session


@dataclass
class PerformanceMetrics:
    """Container for performance measurement data."""
    operation_name: str
    baseline_target_ms: float
    optimized_target_ms: float
    measurements: list[float] = field(default_factory=list)
    success: bool = False

    @property
    def average_ms(self) -> float:
        """Calculate average execution time in milliseconds."""
        return statistics.mean(self.measurements) if self.measurements else 0.0

    @property
    def median_ms(self) -> float:
        """Calculate median execution time in milliseconds."""
        return statistics.median(self.measurements) if self.measurements else 0.0

    @property
    def p95_ms(self) -> float:
        """Calculate 95th percentile execution time in milliseconds."""
        if not self.measurements:
            return 0.0
        sorted_measurements = sorted(self.measurements)
        index = int(len(sorted_measurements) * 0.95)
        return sorted_measurements[min(index, len(sorted_measurements) - 1)]

    @property
    def improvement_factor(self) -> float:
        """Calculate actual improvement factor vs baseline."""
        if self.average_ms == 0:
            return 0.0
        return self.baseline_target_ms / self.average_ms

    @property
    def meets_target(self) -> bool:
        """Check if performance meets the 3x improvement target."""
        return self.average_ms <= self.optimized_target_ms


class Week1BaselineTester:
    """
    Comprehensive baseline performance tester for Week 1 optimization goals.

    Measures performance of key database operations and validates the 3x
    improvement target across all critical paths.
    """

    def __init__(self, iterations: int = 50):
        """
        Initialize the baseline tester.

        Args:
            iterations: Number of test iterations for statistical significance
        """
        self.iterations = iterations
        self.metrics: dict[str, PerformanceMetrics] = {}
        self.test_data = []

    def create_metric(self, operation_name: str, baseline_ms: float, target_ms: float):
        """Create a new performance metric tracker."""
        self.metrics[operation_name] = PerformanceMetrics(
            operation_name=operation_name,
            baseline_target_ms=baseline_ms,
            optimized_target_ms=target_ms
        )

    async def measure_operation(self, operation_name: str, operation_func, *args, **kwargs) -> float:
        """
        Measure the execution time of an operation.

        Args:
            operation_name: Name of the operation being measured
            operation_func: Function to execute and measure
            *args, **kwargs: Arguments to pass to the operation

        Returns:
            Execution time in milliseconds
        """
        start_time = time.perf_counter()

        if inspect.iscoroutinefunction(operation_func):
            await operation_func(*args, **kwargs)
        else:
            operation_func(*args, **kwargs)

        end_time = time.perf_counter()
        execution_time_ms = (end_time - start_time) * 1000

        if operation_name in self.metrics:
            self.metrics[operation_name].measurements.append(execution_time_ms)

        return execution_time_ms

    def cleanup_test_data(self, session):
        """Clean up test data created during benchmark runs."""
        for task_id in self.test_data:
            try:
                # Delete task and its subtasks (cascading should handle this)
                session.execute(
                    "DELETE FROM tasks WHERE id = :task_id",
                    {"task_id": task_id}
                )
            except Exception:
                pass  # Ignore cleanup errors

        session.commit()
        self.test_data.clear()

    def generate_report(self) -> dict[str, Any]:
        """
        Generate comprehensive performance report.

        Returns:
            Dictionary containing detailed performance analysis
        """
        report = {
            "test_timestamp": datetime.now(UTC).isoformat(),
            "iterations": self.iterations,
            "operations": {},
            "summary": {
                "total_operations": len(self.metrics),
                "operations_meeting_target": 0,
                "operations_failing_target": 0,
                "overall_success": False
            }
        }

        for name, metric in self.metrics.items():
            metric.success = metric.meets_target

            report["operations"][name] = {
                "baseline_target_ms": metric.baseline_target_ms,
                "optimized_target_ms": metric.optimized_target_ms,
                "average_ms": round(metric.average_ms, 2),
                "median_ms": round(metric.median_ms, 2),
                "p95_ms": round(metric.p95_ms, 2),
                "improvement_factor": round(metric.improvement_factor, 2),
                "meets_target": metric.meets_target,
                "measurements_count": len(metric.measurements)
            }

            if metric.meets_target:
                report["summary"]["operations_meeting_target"] += 1
            else:
                report["summary"]["operations_failing_target"] += 1

        # Overall success if all operations meet target
        report["summary"]["overall_success"] = (
            report["summary"]["operations_failing_target"] == 0
        )

        return report


@pytest.fixture(scope="module")
def baseline_tester():
    """Create a baseline tester instance."""
    return Week1BaselineTester(iterations=50)


@pytest.fixture(scope="function")
def db_session():
    """Create a database session for testing."""
    session = get_session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def git_branch_id(db_session):
    """Create and provide a git branch ID for testing."""
    import uuid
    from datetime import UTC, datetime

    from fastmcp.task_management.infrastructure.database.models import (
        Project,
        ProjectGitBranch,
    )

    # Create a test project first
    project = Project(
        id=str(uuid.uuid4()),
        name="Performance Test Project",
        description="Project for performance testing",
        user_id="test-user-perf",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    db_session.add(project)

    # Create a test git branch
    branch = ProjectGitBranch(
        id=str(uuid.uuid4()),
        name="performance-test-branch",
        description="Branch for performance testing",
        project_id=project.id,
        user_id="test-user-perf",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    db_session.add(branch)
    db_session.commit()

    yield branch.id

    # Cleanup after test
    try:
        db_session.delete(branch)
        db_session.delete(project)
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest.fixture(scope="function")
def task_facade(db_session):
    """Create a task application facade for testing."""
    from fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository import (
        ORMGitBranchRepository,
    )
    from fastmcp.task_management.infrastructure.repositories.orm.subtask_repository import (
        ORMSubtaskRepository,
    )
    from fastmcp.task_management.infrastructure.repositories.orm.task_repository import (
        ORMTaskRepository,
    )

    task_repo = ORMTaskRepository(performance_mode=True)
    subtask_repo = ORMSubtaskRepository()
    branch_repo = ORMGitBranchRepository(performance_mode=False)

    return TaskApplicationFacade(
        task_repository=task_repo,
        subtask_repository=subtask_repo,
        git_branch_repository=branch_repo
    )


class TestWeek1BaselinePerformance:
    """Test suite for Week 1 baseline performance measurements."""

    @pytest.mark.performance
    def test_task_creation_performance(self, baseline_tester, db_session, task_facade, git_branch_id):
        """
        Test task creation performance.
        Target: 150ms → 50ms (3x improvement)
        """
        baseline_tester.create_metric("task_creation", baseline_ms=150.0, target_ms=50.0)

        for i in range(baseline_tester.iterations):
            # Measure task creation
            start_time = time.perf_counter()

            request = CreateTaskRequest(
                title=f"Performance Test Task {i}",
                description=f"Test task for baseline performance measurement iteration {i}",
                git_branch_id=git_branch_id,
                status="pending",
                assignees=["@test-agent"],
                user_id="test-user-perf"
            )
            result = task_facade.create_task(request)

            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            baseline_tester.metrics["task_creation"].measurements.append(execution_time_ms)
            if result.get("success") and result.get("task"):
                baseline_tester.test_data.append(result["task"]["id"])

        # Cleanup
        baseline_tester.cleanup_test_data(db_session)

        # Validate performance
        metric = baseline_tester.metrics["task_creation"]
        assert metric.meets_target, (
            f"Task creation failed to meet 3x improvement target. "
            f"Average: {metric.average_ms:.2f}ms, Target: {metric.optimized_target_ms}ms"
        )

    @pytest.mark.performance
    def test_task_retrieval_performance(self, baseline_tester, db_session, task_facade, git_branch_id):
        """
        Test task retrieval performance.
        Target: 100ms → 33ms (3x improvement)
        """
        baseline_tester.create_metric("task_retrieval", baseline_ms=100.0, target_ms=33.0)

        # Create test task
        request = CreateTaskRequest(
            title="Test Task for Retrieval",
            description="Task used for retrieval performance testing",
            git_branch_id=git_branch_id,
            status="in_progress",
            assignees=["@test-agent"],
            user_id="test-user-perf"
        )
        create_result = task_facade.create_task(request)
        assert create_result.get("success"), f"Failed to create test task: {create_result.get('error')}"
        task_id = create_result["task"]["id"]
        baseline_tester.test_data.append(task_id)

        # Measure retrieval performance
        for _ in range(baseline_tester.iterations):
            start_time = time.perf_counter()

            retrieved_result = task_facade.get_task(task_id)

            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            baseline_tester.metrics["task_retrieval"].measurements.append(execution_time_ms)
            assert retrieved_result.get("success"), "Task retrieval failed"
            assert retrieved_result["task"]["id"] == task_id

        # Cleanup
        baseline_tester.cleanup_test_data(db_session)

        # Validate performance
        metric = baseline_tester.metrics["task_retrieval"]
        assert metric.meets_target, (
            f"Task retrieval failed to meet 3x improvement target. "
            f"Average: {metric.average_ms:.2f}ms, Target: {metric.optimized_target_ms}ms"
        )

    @pytest.mark.performance
    def test_task_listing_performance(self, baseline_tester, db_session, task_facade, git_branch_id):
        """
        Test task listing performance.
        Target: 200ms → 67ms (3x improvement)
        """
        baseline_tester.create_metric("task_listing", baseline_ms=200.0, target_ms=67.0)

        # Create multiple test tasks
        from fastmcp.task_management.application.dtos.task.list_tasks_request import (
            ListTasksRequest,
        )

        for i in range(10):
            request = CreateTaskRequest(
                title=f"List Test Task {i}",
                description=f"Task {i} for listing performance testing",
                git_branch_id=git_branch_id,
                status="todo" if i % 2 == 0 else "in_progress",
                assignees=["@test-agent"],
                user_id="test-user-perf"
            )
            result = task_facade.create_task(request)
            if result.get("success") and result.get("task"):
                baseline_tester.test_data.append(result["task"]["id"])

        # Measure listing performance
        for _ in range(baseline_tester.iterations):
            start_time = time.perf_counter()

            list_request = ListTasksRequest(
                git_branch_id=git_branch_id,
                limit=20  # Increased limit to ensure we get all test tasks
            )
            result = task_facade.list_tasks(list_request, minimal=True)

            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            baseline_tester.metrics["task_listing"].measurements.append(execution_time_ms)
            assert result.get("success"), "Task listing failed"
            assert len(result.get("tasks", [])) >= 10, f"Expected at least 10 tasks, got {len(result.get('tasks', []))}"

        # Cleanup
        baseline_tester.cleanup_test_data(db_session)

        # Validate performance
        metric = baseline_tester.metrics["task_listing"]
        assert metric.meets_target, (
            f"Task listing failed to meet 3x improvement target. "
            f"Average: {metric.average_ms:.2f}ms, Target: {metric.optimized_target_ms}ms"
        )

    @pytest.mark.performance
    def test_task_update_performance(self, baseline_tester, db_session, task_facade, git_branch_id):
        """
        Test task update performance.
        Target: 120ms → 40ms (3x improvement)
        """
        baseline_tester.create_metric("task_update", baseline_ms=120.0, target_ms=40.0)

        # Create test task
        request = CreateTaskRequest(
            title="Test Task for Updates",
            description="Task used for update performance testing",
            git_branch_id=git_branch_id,
            status="todo",
            assignees=["@test-agent"],
            user_id="test-user-perf"
        )
        create_result = task_facade.create_task(request)
        assert create_result.get("success"), f"Failed to create test task: {create_result.get('error')}"
        task_id = create_result["task"]["id"]
        baseline_tester.test_data.append(task_id)

        # Measure update performance
        for i in range(baseline_tester.iterations):
            start_time = time.perf_counter()

            update_request = UpdateTaskRequest(
                task_id=task_id,
                title=f"Updated Task {i}",
                status="in_progress" if i % 2 == 0 else "completed"
            )
            task_facade.update_task(task_id, update_request)

            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            baseline_tester.metrics["task_update"].measurements.append(execution_time_ms)

        # Cleanup
        baseline_tester.cleanup_test_data(db_session)

        # Validate performance
        metric = baseline_tester.metrics["task_update"]
        assert metric.meets_target, (
            f"Task update failed to meet 3x improvement target. "
            f"Average: {metric.average_ms:.2f}ms, Target: {metric.optimized_target_ms}ms"
        )

    @pytest.mark.performance
    def test_subtask_operations_performance(self, baseline_tester, db_session, task_facade, git_branch_id):
        """
        Test subtask operations performance.
        Target: 80ms → 27ms (3x improvement)
        """
        baseline_tester.create_metric("subtask_operations", baseline_ms=80.0, target_ms=27.0)

        # Create parent task
        request = CreateTaskRequest(
            title="Parent Task for Subtasks",
            description="Parent task for subtask performance testing",
            git_branch_id=git_branch_id,
            status="in_progress",
            assignees=["@test-agent"],
            user_id="test-user-perf"
        )
        create_result = task_facade.create_task(request)
        assert create_result.get("success"), f"Failed to create parent task: {create_result.get('error')}"
        parent_task_id = create_result["task"]["id"]
        baseline_tester.test_data.append(parent_task_id)

        # Create subtask facade for operations
        from fastmcp.task_management.application.facades.subtask_application_facade import (
            SubtaskApplicationFacade,
        )
        from fastmcp.task_management.infrastructure.repositories.orm.subtask_repository import (
            ORMSubtaskRepository,
        )
        from fastmcp.task_management.infrastructure.repositories.orm.task_repository import (
            ORMTaskRepository,
        )

        task_repo = ORMTaskRepository(git_branch_id=git_branch_id, performance_mode=True)
        subtask_repo = ORMSubtaskRepository()
        subtask_facade = SubtaskApplicationFacade(
            task_repository=task_repo,
            subtask_repository=subtask_repo,
            user_id="test-user-perf"
        )

        # Measure subtask creation performance
        for i in range(baseline_tester.iterations):
            start_time = time.perf_counter()

            # Create subtask using the facade with proper data structure
            result = subtask_facade.handle_manage_subtask(
                action="create",
                task_id=parent_task_id,
                subtask_data={
                    "title": f"Subtask {i}",
                    "description": f"Test subtask {i} for performance measurement"
                }
            )

            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            baseline_tester.metrics["subtask_operations"].measurements.append(execution_time_ms)
            assert result.get("success"), f"Failed to create subtask: {result.get('error')}"

        # Cleanup
        baseline_tester.cleanup_test_data(db_session)

        # Validate performance
        metric = baseline_tester.metrics["subtask_operations"]
        assert metric.meets_target, (
            f"Subtask operations failed to meet 3x improvement target. "
            f"Average: {metric.average_ms:.2f}ms, Target: {metric.optimized_target_ms}ms"
        )

    @pytest.mark.performance
    def test_generate_baseline_report(self, baseline_tester):
        """Generate and display comprehensive baseline performance report."""
        report = baseline_tester.generate_report()

        print("\n" + "="*80)
        print("WEEK 1 BASELINE PERFORMANCE REPORT")
        print("="*80)
        print(f"Test Timestamp: {report['test_timestamp']}")
        print(f"Iterations: {report['iterations']}")
        print()

        print("OPERATION PERFORMANCE:")
        print("-"*80)
        for op_name, op_data in report["operations"].items():
            status = "✅ PASS" if op_data["meets_target"] else "❌ FAIL"
            print(f"\n{op_name.upper().replace('_', ' ')}:")
            print(f"  Status: {status}")
            print(f"  Baseline Target: {op_data['baseline_target_ms']}ms")
            print(f"  Optimized Target: {op_data['optimized_target_ms']}ms")
            print(f"  Average: {op_data['average_ms']}ms")
            print(f"  Median: {op_data['median_ms']}ms")
            print(f"  P95: {op_data['p95_ms']}ms")
            print(f"  Improvement Factor: {op_data['improvement_factor']}x")

        print("\n" + "-"*80)
        print("SUMMARY:")
        print(f"  Total Operations: {report['summary']['total_operations']}")
        print(f"  Operations Meeting Target: {report['summary']['operations_meeting_target']}")
        print(f"  Operations Failing Target: {report['summary']['operations_failing_target']}")
        print(f"  Overall Success: {'✅ YES' if report['summary']['overall_success'] else '❌ NO'}")
        print("="*80)

        # Assert overall success
        assert report["summary"]["overall_success"], (
            "Week 1 baseline performance targets not met. "
            f"{report['summary']['operations_failing_target']} operations failed."
        )


if __name__ == "__main__":
    """Run baseline tests directly."""
    pytest.main([__file__, "-v", "-s", "--tb=short"])
