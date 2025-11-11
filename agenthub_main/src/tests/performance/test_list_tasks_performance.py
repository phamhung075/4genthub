"""
Performance Tests for Task List API - N+1 Query Problem Detection

This test suite is designed to FAIL initially, demonstrating the N+1 query problem.
After the batch loading implementation, these tests should pass.

TDD Methodology Phase 2: Write Failing Tests
"""

import time
import uuid
from datetime import UTC, datetime

import pytest

# SQLAlchemy imports for query counting
from sqlalchemy import event
from sqlalchemy.engine import Engine

from fastmcp.task_management.application.dtos.task import ListTasksRequest
from fastmcp.task_management.application.use_cases.list_tasks import ListTasksUseCase
from fastmcp.task_management.infrastructure.database.database_config import (
    get_db_config,
)


class QueryCounter:
    """Context manager for counting SQL queries executed during a block"""

    def __init__(self):
        self.count = 0
        self.queries = []
        self._connection = None

    def _count_query(self, conn, cursor, statement, parameters, context, executemany):
        """SQLAlchemy event handler to count queries"""
        self.count += 1
        self.queries.append(
            {"sql": statement, "params": parameters, "timestamp": time.time()}
        )

    def __enter__(self):
        """Start counting queries"""
        self.count = 0
        self.queries = []
        # Register the event listener
        event.listen(Engine, "before_cursor_execute", self._count_query)
        return self

    def __exit__(self, *args):
        """Stop counting queries"""
        # Remove the event listener
        event.remove(Engine, "before_cursor_execute", self._count_query)

    def get_query_breakdown(self) -> dict:
        """Get breakdown of query types"""
        breakdown = {"SELECT": 0, "INSERT": 0, "UPDATE": 0, "DELETE": 0, "OTHER": 0}

        for query in self.queries:
            sql = query["sql"].strip().upper()
            if sql.startswith("SELECT"):
                breakdown["SELECT"] += 1
            elif sql.startswith("INSERT"):
                breakdown["INSERT"] += 1
            elif sql.startswith("UPDATE"):
                breakdown["UPDATE"] += 1
            elif sql.startswith("DELETE"):
                breakdown["DELETE"] += 1
            else:
                breakdown["OTHER"] += 1

        return breakdown


@pytest.fixture
def query_counter():
    """Pytest fixture providing QueryCounter"""
    return QueryCounter()


def create_test_project_and_branch(session) -> tuple[str, str]:
    """
    Create test project and git branch for testing.

    Returns:
        Tuple of (project_id, git_branch_id)
    """
    from fastmcp.task_management.infrastructure.database.models import (
        Project,
        ProjectGitBranch,
    )

    project_id = str(uuid.uuid4())
    git_branch_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    # Create project
    project = Project(
        id=project_id,
        name="Test Project",
        description="Project for N+1 query testing",
        user_id=user_id,
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        metadata={},
    )
    session.add(project)

    # Create git branch
    branch = ProjectGitBranch(
        id=git_branch_id,
        project_id=project_id,
        name="main",
        description="Main branch for testing",
        user_id=user_id,
        priority="medium",
        status="todo",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        metadata={},
        task_count=0,
        completed_task_count=0,
    )
    session.add(branch)
    session.commit()

    return project_id, git_branch_id


def create_tasks_bulk(
    git_branch_id: str, count: int, user_id: str = None
) -> tuple[list[str], str]:
    """
    Create multiple tasks in bulk for testing using repository.

    Args:
        git_branch_id: Git branch ID to associate tasks with
        count: Number of tasks to create
        user_id: User ID for task isolation (defaults to test user)

    Returns:
        Tuple of (list of created task IDs, user_id used)
    """
    from fastmcp.task_management.application.services.repository_provider_service import (
        RepositoryProviderService,
    )
    from fastmcp.task_management.domain.entities.task import Task as TaskEntity
    from fastmcp.task_management.domain.value_objects.priority import Priority
    from fastmcp.task_management.domain.value_objects.task_id import TaskId
    from fastmcp.task_management.domain.value_objects.task_status import TaskStatus

    if user_id is None:
        user_id = str(uuid.uuid4())

    # Get task repository and scope it to the user
    provider = RepositoryProviderService.get_instance()
    task_repo = provider.get_task_repository().with_user(user_id)

    task_ids = []

    for i in range(count):
        # Create task entity - use string values for enums
        task = TaskEntity(
            id=TaskId(str(uuid.uuid4())),
            title=f"Test Task {i + 1}",
            description=f"Description for task {i + 1}",
            status=TaskStatus("todo"),  # Use string value, not method
            priority=Priority("medium"),  # Use string value, not method
            git_branch_id=git_branch_id,
            assignees=["@coding-agent"],
            labels=[],
            dependencies=[],
            subtasks=[],
        )

        # Save task
        saved_task = task_repo.save(task)
        task_ids.append(str(saved_task.id.value))

    return task_ids, user_id


@pytest.mark.performance
class TestTaskListNPlusOneQuery:
    """
    Test suite for detecting N+1 query problem in task list operations.

    These tests will FAIL initially, demonstrating the N+1 query problem.
    After implementing batch loading, they should pass.
    """

    def test_list_tasks_should_not_have_n_plus_1_queries(self, query_counter):
        """
        TEST 1: Query Count Test - Verify no N+1 query problem when listing tasks

        EXPECTED TO FAIL INITIALLY:
        - Current implementation: 1 query for tasks + N queries for project_id lookups
        - Expected after fix: 3 queries max (1 for tasks + 1 for batch git_branches + 1 for connection health check)

        This test demonstrates the core N+1 query problem.
        """
        db_config = get_db_config()

        with db_config.get_session() as session:
            # Arrange: Create test data
            project_id, git_branch_id = create_test_project_and_branch(session)
            task_count = 100
            task_ids, user_id = create_tasks_bulk(git_branch_id, task_count)

            # Get repository
            from fastmcp.task_management.application.services.repository_provider_service import (
                RepositoryProviderService,
            )

            provider = RepositoryProviderService.get_instance()
            task_repo = provider.get_task_repository().with_user(user_id)

            # Create use case
            use_case = ListTasksUseCase(task_repo)
            request = ListTasksRequest(git_branch_id=git_branch_id)

            # Act: Count queries during list operation
            with query_counter as counter:
                response = use_case.execute(request)

            # Assert: Should be 3 queries max (tasks + git_branches batch + connection health)
            # EXPECTED TO FAIL: Currently will be 101 queries (1 + 100)
            query_breakdown = counter.get_query_breakdown()

            print("\n=== N+1 Query Test Results ===")
            print(f"Total queries executed: {counter.count}")
            print(f"Query breakdown: {query_breakdown}")
            print(f"Tasks returned: {len(response.tasks)}")
            print(
                "Expected queries: 3 (1 for tasks + 1 for batch branches + 1 for connection health)"
            )
            print(f"Actual queries: {counter.count}")
            print(f"N+1 problem detected: {counter.count > 3}")

            assert len(response.tasks) == task_count, (
                f"Should return all {task_count} tasks"
            )

            # CRITICAL ASSERTION - WILL FAIL INITIALLY
            assert counter.count <= 3, (
                f"N+1 query problem detected! "
                f"Expected ≤3 queries but got {counter.count} queries for {task_count} tasks. "
                f"Query breakdown: {query_breakdown}. "
                f"This indicates each task is fetching project_id individually instead of batch loading."
            )

    def test_list_1000_tasks_should_complete_under_1_second(self):
        """
        TEST 2: Performance Benchmark Test - Ensure scalability to 1000 tasks

        EXPECTED TO FAIL INITIALLY:
        - Current implementation: ~20 seconds for 1000 tasks (1001 queries)
        - Expected after fix: < 1 second (2 queries with batch loading)

        This test verifies performance improvement after batch loading implementation.
        """
        db_config = get_db_config()

        with db_config.get_session() as session:
            # Arrange: Create 1000 tasks
            project_id, git_branch_id = create_test_project_and_branch(session)
            task_count = 1000
            task_ids, user_id = create_tasks_bulk(git_branch_id, task_count)

            # Get repository
            from fastmcp.task_management.application.services.repository_provider_service import (
                RepositoryProviderService,
            )

            provider = RepositoryProviderService.get_instance()
            task_repo = provider.get_task_repository().with_user(user_id)

            # Create use case
            use_case = ListTasksUseCase(task_repo)
            request = ListTasksRequest(git_branch_id=git_branch_id)

            # Act: Measure execution time
            start_time = time.time()
            response = use_case.execute(request)
            duration = time.time() - start_time

            # Assert: Should complete in under 1 second
            # EXPECTED TO FAIL: Currently takes ~20 seconds
            print("\n=== Performance Benchmark Results ===")
            print(f"Task count: {task_count}")
            print(f"Execution time: {duration:.3f} seconds")
            print(f"Tasks per second: {task_count / duration:.1f}")
            print("Performance target: < 1.0 second")
            print(f"Performance issue: {duration > 1.0}")

            assert len(response.tasks) == task_count, (
                f"Should return all {task_count} tasks"
            )

            # CRITICAL ASSERTION - WILL FAIL INITIALLY
            assert duration < 1.0, (
                f"Performance regression detected! "
                f"Expected < 1.0 second but took {duration:.3f} seconds for {task_count} tasks. "
                f"This indicates N+1 query problem causing excessive database round trips."
            )

    def test_batch_loading_returns_correct_project_ids(self):
        """
        TEST 3: Correctness Test - Verify project_id is correctly populated via batch loading

        EXPECTED TO PASS (but may fail if batch loading has bugs):
        - All tasks should have correct project_id
        - No null project_ids
        - Project IDs should match the branch's project

        This test ensures batch loading maintains data integrity.
        """
        db_config = get_db_config()

        with db_config.get_session() as session:
            # Arrange: Create test data
            project_id, git_branch_id = create_test_project_and_branch(session)
            task_count = 10
            task_ids, user_id = create_tasks_bulk(git_branch_id, task_count)

            # Get repository
            from fastmcp.task_management.application.services.repository_provider_service import (
                RepositoryProviderService,
            )

            provider = RepositoryProviderService.get_instance()
            task_repo = provider.get_task_repository().with_user(user_id)

            # Create use case
            use_case = ListTasksUseCase(task_repo)
            request = ListTasksRequest(git_branch_id=git_branch_id)

            # Act: Execute list operation
            response = use_case.execute(request)

            # Assert: All tasks should have correct project_id
            print("\n=== Correctness Test Results ===")
            print(f"Expected project_id: {project_id}")
            print(f"Tasks returned: {len(response.tasks)}")

            mismatches = []
            null_count = 0

            for i, task in enumerate(response.tasks):
                if task.project_id is None:
                    null_count += 1
                    print(f"Task {i + 1}: project_id is NULL (ERROR)")
                elif task.project_id != project_id:
                    mismatches.append((i + 1, task.project_id))
                    print(
                        f"Task {i + 1}: project_id mismatch - expected {project_id}, got {task.project_id}"
                    )

            assert len(response.tasks) == task_count, (
                f"Should return all {task_count} tasks"
            )

            # CRITICAL ASSERTIONS - Verify data integrity
            assert null_count == 0, (
                f"Found {null_count} tasks with NULL project_id. "
                f"Batch loading failed to populate project_id for some tasks."
            )

            assert len(mismatches) == 0, (
                f"Found {len(mismatches)} tasks with incorrect project_id: {mismatches}. "
                f"Expected all tasks to have project_id={project_id}"
            )

            print(f"✅ All {task_count} tasks have correct project_id: {project_id}")

    def test_query_count_scales_linearly_not_exponentially(self, query_counter):
        """
        TEST 4: Scalability Test - Query count should not increase with task count

        EXPECTED TO FAIL INITIALLY:
        - Current: Query count = N+1 (increases with task count)
        - Expected: Query count = 2 (constant regardless of task count)

        This test verifies that batch loading eliminates query growth.
        """
        db_config = get_db_config()
        results = []

        for task_count in [10, 50, 100, 200]:
            with db_config.get_session() as session:
                # Arrange: Create varying numbers of tasks
                project_id, git_branch_id = create_test_project_and_branch(session)
                task_ids, user_id = create_tasks_bulk(git_branch_id, task_count)

                # Get repository
                from fastmcp.task_management.application.services.repository_provider_service import (
                    RepositoryProviderService,
                )

                provider = RepositoryProviderService.get_instance()
                task_repo = provider.get_task_repository()

                # Create use case
                use_case = ListTasksUseCase(task_repo)
                request = ListTasksRequest(git_branch_id=git_branch_id)

                # Act: Count queries
                with query_counter as counter:
                    use_case.execute(request)

                results.append(
                    {
                        "task_count": task_count,
                        "query_count": counter.count,
                        "ratio": counter.count / task_count if task_count > 0 else 0,
                    }
                )

                # Cleanup for next iteration
                session.rollback()

        # Assert: Query count should be constant (2), not linear with tasks
        print("\n=== Scalability Test Results ===")
        print(f"{'Tasks':<10} {'Queries':<10} {'Ratio':<10} {'Expected':<10}")
        print("-" * 50)

        for result in results:
            expected = 2  # Should always be 2 with batch loading
            print(
                f"{result['task_count']:<10} {result['query_count']:<10} {result['ratio']:<10.2f} {expected:<10}"
            )

        # CRITICAL ASSERTION - Query count should be constant
        query_counts = [r["query_count"] for r in results]
        max_queries = max(query_counts)
        min(query_counts)

        # With batch loading, query count variance should be minimal (±1 for transaction overhead)
        assert max_queries <= 3, (
            f"Query count is growing with task count! "
            f"Maximum queries: {max_queries} (expected ≤3). "
            f"Results: {results}. "
            f"This indicates N+1 query problem is not fixed."
        )

        # Additional check: query count should not scale linearly with task count
        # If ratio stays close to 1.0, it means N+1 problem exists
        high_task_ratio = results[-1]["ratio"]  # Ratio for highest task count
        assert high_task_ratio < 0.1, (
            f"Query-to-task ratio too high: {high_task_ratio:.3f} (expected < 0.1). "
            f"This indicates queries are scaling with task count (N+1 problem). "
            f"Results: {results}"
        )

    def test_compare_with_and_without_batch_loading(self, query_counter):
        """
        TEST 5: Comparison Test - Direct comparison of old vs new implementation

        This test will help visualize the improvement after batch loading is implemented.
        Initially, this test documents the current poor performance.
        """
        db_config = get_db_config()
        task_count = 50

        with db_config.get_session() as session:
            # Arrange: Create test data
            project_id, git_branch_id = create_test_project_and_branch(session)
            task_ids, user_id = create_tasks_bulk(git_branch_id, task_count)

            # Get repository
            from fastmcp.task_management.application.services.repository_provider_service import (
                RepositoryProviderService,
            )

            provider = RepositoryProviderService.get_instance()
            task_repo = provider.get_task_repository().with_user(user_id)

            # Create use case
            use_case = ListTasksUseCase(task_repo)
            request = ListTasksRequest(git_branch_id=git_branch_id)

            # Measure current implementation
            with query_counter as counter:
                start_time = time.time()
                response = use_case.execute(request)
                duration = time.time() - start_time

            current_queries = counter.count
            current_duration = duration

            # Calculate expected improvement with batch loading
            expected_queries = 2  # 1 for tasks + 1 for batch branches
            expected_improvement_ratio = current_queries / expected_queries
            expected_time_improvement = current_duration * (
                expected_queries / current_queries
            )

            print("\n=== Performance Comparison ===")
            print(f"Task count: {task_count}")
            print("\nCurrent Implementation (N+1):")
            print(f"  Queries: {current_queries}")
            print(f"  Duration: {current_duration:.3f}s")
            print(f"  Queries per task: {current_queries / task_count:.2f}")
            print("\nExpected with Batch Loading:")
            print(f"  Queries: {expected_queries}")
            print(f"  Duration: ~{expected_time_improvement:.3f}s (estimated)")
            print(f"  Queries per task: {expected_queries / task_count:.2f}")
            print("\nExpected Improvement:")
            print(f"  Query reduction: {expected_improvement_ratio:.1f}x fewer queries")
            print(
                f"  Speed improvement: {current_duration / expected_time_improvement:.1f}x faster"
            )

            # Document baseline for future comparison
            assert len(response.tasks) == task_count

            # This assertion will fail initially, documenting the problem
            improvement_threshold = 10  # We expect at least 10x improvement
            assert current_queries / expected_queries < improvement_threshold, (
                f"Current implementation shows severe N+1 problem: "
                f"{current_queries} queries vs expected {expected_queries}. "
                f"Improvement potential: {expected_improvement_ratio:.1f}x"
            )


@pytest.mark.performance
@pytest.mark.integration
class TestTaskListPerformanceRegression:
    """
    Performance regression tests to ensure batch loading doesn't break over time.

    These tests should pass after batch loading implementation and continue to pass.
    """

    def test_small_task_list_performance_baseline(self, query_counter):
        """Baseline test for 10 tasks - should always be fast"""
        db_config = get_db_config()

        with db_config.get_session() as session:
            project_id, git_branch_id = create_test_project_and_branch(session)
            task_ids, user_id = create_tasks_bulk(git_branch_id, 10)

            from fastmcp.task_management.application.services.repository_provider_service import (
                RepositoryProviderService,
            )

            provider = RepositoryProviderService.get_instance()
            task_repo = provider.get_task_repository().with_user(user_id)

            use_case = ListTasksUseCase(task_repo)
            request = ListTasksRequest(git_branch_id=git_branch_id)

            with query_counter:
                start_time = time.time()
                response = use_case.execute(request)
                duration = time.time() - start_time

            # Even with N+1 problem, 10 tasks should be reasonably fast
            assert duration < 0.5, f"Small list too slow: {duration:.3f}s"
            assert len(response.tasks) == 10

    def test_verify_all_required_fields_populated(self):
        """Ensure batch loading doesn't break any response fields"""
        db_config = get_db_config()

        with db_config.get_session() as session:
            project_id, git_branch_id = create_test_project_and_branch(session)
            task_ids, user_id = create_tasks_bulk(git_branch_id, 5)

            from fastmcp.task_management.application.services.repository_provider_service import (
                RepositoryProviderService,
            )

            provider = RepositoryProviderService.get_instance()
            task_repo = provider.get_task_repository().with_user(user_id)

            use_case = ListTasksUseCase(task_repo)
            request = ListTasksRequest(git_branch_id=git_branch_id)
            response = use_case.execute(request)

            # Verify all tasks have required fields
            for task in response.tasks:
                assert task.id is not None, "Task missing id"
                assert task.title is not None, "Task missing title"
                assert task.status is not None, "Task missing status"
                assert task.priority is not None, "Task missing priority"
                assert task.git_branch_id is not None, "Task missing git_branch_id"
                # project_id should be populated via batch loading
                assert task.project_id is not None, (
                    "Task missing project_id (batch loading failed)"
                )


if __name__ == "__main__":
    """
    Run these tests directly to see N+1 query problem demonstration.

    Expected results BEFORE batch loading implementation:
    - test_list_tasks_should_not_have_n_plus_1_queries: FAIL (101 queries instead of 2)
    - test_list_1000_tasks_should_complete_under_1_second: FAIL (~20s instead of <1s)
    - test_batch_loading_returns_correct_project_ids: PASS (data is correct, just slow)
    - test_query_count_scales_linearly_not_exponentially: FAIL (queries scale with tasks)
    - test_compare_with_and_without_batch_loading: FAIL (documents 50x improvement potential)

    After batch loading implementation, ALL tests should PASS.
    """
    pytest.main([__file__, "-v", "-s"])
