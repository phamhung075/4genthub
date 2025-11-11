"""
Comprehensive Scalability Load Testing Suite

This test suite validates system performance at various scales after the N+1 query fix.
Tests verify that the scalability ceiling has been resolved and identify any remaining bottlenecks.

Test Objectives:
1. Validate 500 tasks load performance (<2s target)
2. Validate 1000 tasks load performance (<5s target)
3. Future-proof with 2000 tasks load test
4. Stress test with 5000 tasks scalability ceiling
5. Verify connection pool stability under concurrent load
6. Verify memory consumption remains stable

Expected Outcome: All tests should PASS after N+1 query fix implementation.
"""

import gc
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

import psutil
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
        name=f"Scalability Test Project {project_id[:8]}",
        description="Project for scalability load testing",
        user_id=user_id,
        status="active",
        metadata={},
    )
    session.add(project)

    # Create git branch
    branch = ProjectGitBranch(
        id=git_branch_id,
        project_id=project_id,
        name=f"test-branch-{git_branch_id[:8]}",
        description="Branch for scalability load testing",
        user_id=user_id,
        priority="medium",
        status="todo",
        metadata={},
        task_count=0,
        completed_task_count=0,
    )
    session.add(branch)
    session.commit()

    return project_id, git_branch_id


def create_bulk_tasks(
    session, git_branch_id: str, project_id: str, count: int
) -> list[str]:
    """
    Create multiple test tasks efficiently in bulk.

    Args:
        session: Database session
        git_branch_id: Git branch ID
        project_id: Project ID
        count: Number of tasks to create

    Returns:
        List of created task IDs
    """
    from fastmcp.task_management.infrastructure.database.models import Task as TaskModel

    task_ids = []
    user_id = str(uuid.uuid4())

    # Create tasks in batches for better performance
    batch_size = 100
    for i in range(0, count, batch_size):
        batch_count = min(batch_size, count - i)
        tasks = []

        for j in range(batch_count):
            task_num = i + j + 1
            task_id = str(uuid.uuid4())
            task_ids.append(task_id)

            now = datetime.now(UTC)
            task = TaskModel(
                id=task_id,
                title=f"Scalability Test Task {task_num}",
                description=f"Task {task_num} for load testing",
                git_branch_id=git_branch_id,
                status="todo",
                priority="medium",
                user_id=user_id,
                progress_percentage=0,
                created_at=now,
                updated_at=now,
            )
            tasks.append(task)

        # Bulk insert batch
        session.bulk_save_objects(tasks)
        session.commit()

    return task_ids


# =============================================
# TEST 1: 500 TASKS LOAD TEST
# =============================================


@pytest.mark.performance
@pytest.mark.load
def test_500_tasks_load_performance(query_counter):
    """
    Test 1: Verify system handles 500 tasks without performance degradation.

    Expected Results (after N+1 fix):
    - Response time: < 2 seconds
    - Query count: ~3 queries (constant, not N+1)
    - All tasks returned with complete data
    """
    db_config = get_db_config()

    with db_config.get_session() as session:
        # Arrange: Create test environment
        project_id, git_branch_id = create_test_project_and_branch(session)
        create_bulk_tasks(session, git_branch_id, project_id, 500)

        # Create use case
        from fastmcp.task_management.infrastructure.repositories.project_git_branch_repository import (
            ProjectGitBranchRepository,
        )
        from fastmcp.task_management.infrastructure.repositories.task_repository import (
            TaskRepository,
        )

        task_repo = TaskRepository(session)
        branch_repo = ProjectGitBranchRepository(session)
        use_case = ListTasksUseCase(task_repo, branch_repo)

        # Act: Measure performance with query counting
        request = ListTasksRequest(git_branch_id=git_branch_id)

        start_time = time.time()
        with query_counter as qc:
            response = use_case.execute(request)
        end_time = time.time()

        duration = end_time - start_time
        query_count = qc.count
        query_breakdown = qc.get_query_breakdown()

        # Assert: Performance targets
        assert duration < 2.0, (
            f"SCALABILITY ISSUE: 500 tasks took {duration:.2f}s (target: <2s). "
            f"Queries: {query_count}, Breakdown: {query_breakdown}"
        )

        assert len(response.tasks) == 500, (
            f"Expected 500 tasks, got {len(response.tasks)}"
        )

        # Verify query efficiency (should be constant ~3 queries, not 501)
        assert query_count <= 10, (
            f"QUERY EFFICIENCY ISSUE: {query_count} queries for 500 tasks. "
            f"Expected ~3 queries with batch loading. N+1 problem may still exist!"
        )

        # Verify data integrity
        for task in response.tasks:
            assert task.project_id is not None, "project_id should be populated"

        print(
            f"\n✅ Test 1 PASSED: 500 tasks in {duration:.3f}s with {query_count} queries"
        )


# =============================================
# TEST 2: 1000 TASKS LOAD TEST
# =============================================


@pytest.mark.performance
@pytest.mark.load
def test_1000_tasks_load_performance(query_counter):
    """
    Test 2: Verify system can scale to 1000 tasks under acceptable threshold.

    Expected Results (after N+1 fix):
    - Response time: < 5 seconds
    - Query count: ~3 queries (constant, not N+1)
    - All tasks returned with complete data integrity
    """
    db_config = get_db_config()

    with db_config.get_session() as session:
        # Arrange
        project_id, git_branch_id = create_test_project_and_branch(session)
        create_bulk_tasks(session, git_branch_id, project_id, 1000)

        from fastmcp.task_management.infrastructure.repositories.project_git_branch_repository import (
            ProjectGitBranchRepository,
        )
        from fastmcp.task_management.infrastructure.repositories.task_repository import (
            TaskRepository,
        )

        task_repo = TaskRepository(session)
        branch_repo = ProjectGitBranchRepository(session)
        use_case = ListTasksUseCase(task_repo, branch_repo)

        # Act
        request = ListTasksRequest(git_branch_id=git_branch_id)

        start_time = time.time()
        with query_counter as qc:
            response = use_case.execute(request)
        end_time = time.time()

        duration = end_time - start_time
        query_count = qc.count

        # Assert
        assert duration < 5.0, (
            f"UNACCEPTABLE RESPONSE TIME: 1000 tasks took {duration:.2f}s (target: <5s)"
        )

        assert len(response.tasks) == 1000, (
            f"Expected 1000 tasks, got {len(response.tasks)}"
        )

        assert query_count <= 10, (
            f"QUERY EFFICIENCY ISSUE: {query_count} queries for 1000 tasks. "
            f"Expected ~3 queries. N+1 problem still exists!"
        )

        # Verify data integrity at scale
        project_ids = [task.project_id for task in response.tasks]
        assert None not in project_ids, "Data integrity compromised at 1000 task scale"

        print(
            f"\n✅ Test 2 PASSED: 1000 tasks in {duration:.3f}s with {query_count} queries"
        )


# =============================================
# TEST 3: 2000 TASKS FUTURE-PROOFING
# =============================================


@pytest.mark.performance
@pytest.mark.stress
def test_2000_tasks_future_proofing(query_counter):
    """
    Test 3: Future-proofing test to verify system can handle 2000 tasks.

    Expected Results:
    - Response time: < 10 seconds (reasonable for large dataset)
    - Query count: ~3 queries (constant batch loading)
    - System remains stable without crashes
    """
    db_config = get_db_config()

    with db_config.get_session() as session:
        # Arrange
        project_id, git_branch_id = create_test_project_and_branch(session)
        create_bulk_tasks(session, git_branch_id, project_id, 2000)

        from fastmcp.task_management.infrastructure.repositories.project_git_branch_repository import (
            ProjectGitBranchRepository,
        )
        from fastmcp.task_management.infrastructure.repositories.task_repository import (
            TaskRepository,
        )

        task_repo = TaskRepository(session)
        branch_repo = ProjectGitBranchRepository(session)
        use_case = ListTasksUseCase(task_repo, branch_repo)

        # Act
        request = ListTasksRequest(git_branch_id=git_branch_id)

        start_time = time.time()
        with query_counter as qc:
            response = use_case.execute(request)
        end_time = time.time()

        duration = end_time - start_time
        query_count = qc.count

        # Assert
        assert duration < 10.0, (
            f"FUTURE-PROOFING CONCERN: 2000 tasks took {duration:.2f}s (target: <10s)"
        )

        assert len(response.tasks) == 2000, (
            f"Expected 2000 tasks, got {len(response.tasks)}"
        )

        assert query_count <= 10, (
            f"SCALABILITY ISSUE: {query_count} queries for 2000 tasks. "
            f"Batch loading not scaling properly!"
        )

        print(
            f"\n✅ Test 3 PASSED: 2000 tasks in {duration:.3f}s with {query_count} queries"
        )


# =============================================
# TEST 4: 5000 TASKS SCALABILITY CEILING
# =============================================


@pytest.mark.performance
@pytest.mark.stress
@pytest.mark.slow
def test_5000_tasks_scalability_ceiling(query_counter):
    """
    Test 4: Stress test to identify true scalability ceiling at 5000 tasks.

    This test validates that the N+1 fix enables scaling beyond the previous 500-1000 task limit.

    Expected Results:
    - Response time: < 30 seconds (stress test threshold)
    - Query count: ~3 queries (validates batch loading at extreme scale)
    - System completes without timeout or crash
    """
    db_config = get_db_config()

    with db_config.get_session() as session:
        # Arrange
        project_id, git_branch_id = create_test_project_and_branch(session)

        print("\n📊 Creating 5000 tasks for scalability ceiling test...")
        task_ids = create_bulk_tasks(session, git_branch_id, project_id, 5000)
        print(f"✅ Created {len(task_ids)} tasks")

        from fastmcp.task_management.infrastructure.repositories.project_git_branch_repository import (
            ProjectGitBranchRepository,
        )
        from fastmcp.task_management.infrastructure.repositories.task_repository import (
            TaskRepository,
        )

        task_repo = TaskRepository(session)
        branch_repo = ProjectGitBranchRepository(session)
        use_case = ListTasksUseCase(task_repo, branch_repo)

        # Act
        request = ListTasksRequest(git_branch_id=git_branch_id)

        print("🚀 Running 5000 task query...")
        start_time = time.time()
        with query_counter as qc:
            response = use_case.execute(request)
        end_time = time.time()

        duration = end_time - start_time
        query_count = qc.count

        # Assert
        assert duration < 30.0, (
            f"SCALABILITY CEILING HIT: 5000 tasks took {duration:.2f}s (max threshold: 30s). "
            f"Consider implementing pagination for datasets this large."
        )

        assert len(response.tasks) == 5000, (
            f"Expected 5000 tasks, got {len(response.tasks)}"
        )

        assert query_count <= 10, (
            f"BATCH LOADING FAILURE: {query_count} queries for 5000 tasks. "
            f"Batch loading should be constant ~3 queries regardless of task count!"
        )

        print(
            f"\n✅ Test 4 PASSED: 5000 tasks in {duration:.3f}s with {query_count} queries"
        )
        print(
            "   Scalability ceiling validated - system can handle enterprise-scale workloads"
        )


# =============================================
# TEST 5: CONNECTION POOL STABILITY
# =============================================


@pytest.mark.performance
@pytest.mark.stress
def test_connection_pool_stability_concurrent_load():
    """
    Test 5: Verify database connection pool handles concurrent large queries without exhaustion.

    Simulates 5 concurrent users each querying 200 tasks (1000 total tasks).

    Expected Results:
    - All 5 concurrent requests complete successfully
    - No connection pool exhaustion errors
    - Each request completes in < 10 seconds
    """
    db_config = get_db_config()

    def query_tasks(git_branch_id: str) -> tuple[float, int]:
        """Execute task query and return (duration, task_count)"""
        with db_config.get_session() as session:
            from fastmcp.task_management.infrastructure.repositories.project_git_branch_repository import (
                ProjectGitBranchRepository,
            )
            from fastmcp.task_management.infrastructure.repositories.task_repository import (
                TaskRepository,
            )

            task_repo = TaskRepository(session)
            branch_repo = ProjectGitBranchRepository(session)
            use_case = ListTasksUseCase(task_repo, branch_repo)

            request = ListTasksRequest(git_branch_id=git_branch_id)

            start = time.time()
            response = use_case.execute(request)
            duration = time.time() - start

            return duration, len(response.tasks)

    # Arrange: Create 5 branches with 200 tasks each
    with db_config.get_session() as session:
        branch_configs = []
        for i in range(5):
            project_id, git_branch_id = create_test_project_and_branch(session)
            create_bulk_tasks(session, git_branch_id, project_id, 200)
            branch_configs.append(git_branch_id)

    # Act: Execute concurrent requests
    results = []
    errors = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(query_tasks, branch_id): branch_id
            for branch_id in branch_configs
        }

        for future in as_completed(futures, timeout=30):
            branch_id = futures[future]
            try:
                duration, task_count = future.result(timeout=10)
                results.append((branch_id, duration, task_count))
                print(
                    f"  ✅ Branch {branch_id[:8]}: {task_count} tasks in {duration:.3f}s"
                )
            except Exception as e:
                errors.append((branch_id, str(e)))
                print(f"  ❌ Branch {branch_id[:8]} failed: {e}")

    # Assert
    assert len(errors) == 0, (
        f"CONNECTION POOL EXHAUSTION: {len(errors)}/{5} requests failed. "
        f"Errors: {errors}"
    )

    assert len(results) == 5, (
        f"Expected 5 successful concurrent requests, got {len(results)}"
    )

    for branch_id, duration, task_count in results:
        assert task_count == 200, (
            f"Branch {branch_id} returned {task_count} tasks, expected 200"
        )
        assert duration < 10.0, f"Branch {branch_id} took {duration:.2f}s (max: 10s)"

    print("\n✅ Test 5 PASSED: Connection pool stable under 5 concurrent requests")


# =============================================
# TEST 6: MEMORY CONSUMPTION STABILITY
# =============================================


@pytest.mark.performance
@pytest.mark.memory
def test_memory_consumption_stability():
    """
    Test 6: Verify memory usage remains stable during repeated large queries.

    Executes 10 sequential requests for 1000 tasks and measures memory growth.

    Expected Results:
    - Memory growth < 50MB over 10 requests
    - No memory leaks detected
    - Stable memory profile at scale
    """
    db_config = get_db_config()

    # Arrange
    with db_config.get_session() as session:
        project_id, git_branch_id = create_test_project_and_branch(session)
        create_bulk_tasks(session, git_branch_id, project_id, 1000)

    # Force garbage collection before measurement
    gc.collect()
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024  # MB

    # Act: Execute 10 requests
    for i in range(10):
        with db_config.get_session() as session:
            from fastmcp.task_management.infrastructure.repositories.project_git_branch_repository import (
                ProjectGitBranchRepository,
            )
            from fastmcp.task_management.infrastructure.repositories.task_repository import (
                TaskRepository,
            )

            task_repo = TaskRepository(session)
            branch_repo = ProjectGitBranchRepository(session)
            use_case = ListTasksUseCase(task_repo, branch_repo)

            request = ListTasksRequest(git_branch_id=git_branch_id)
            response = use_case.execute(request)

            # Explicitly delete response to test cleanup
            del response

        # Force garbage collection after each request
        gc.collect()

    # Measure memory after
    mem_after = process.memory_info().rss / 1024 / 1024  # MB
    mem_growth = mem_after - mem_before

    # Assert
    assert mem_growth < 50, (
        f"MEMORY LEAK DETECTED: {mem_growth:.2f}MB growth over 10 requests (threshold: 50MB). "
        f"Memory before: {mem_before:.2f}MB, after: {mem_after:.2f}MB"
    )

    print(
        f"\n✅ Test 6 PASSED: Memory stable - {mem_growth:.2f}MB growth over 10 requests"
    )
    print(f"   (Before: {mem_before:.1f}MB, After: {mem_after:.1f}MB)")


# =============================================
# PERFORMANCE REPORT SUMMARY
# =============================================


@pytest.mark.performance
def test_generate_performance_summary(query_counter):
    """
    Generate comprehensive performance report for all scalability tests.

    This test runs a representative workload and generates metrics for documentation.
    """
    db_config = get_db_config()
    metrics = {}

    # Test scales: 100, 500, 1000
    test_scales = [100, 500, 1000]

    for scale in test_scales:
        with db_config.get_session() as session:
            project_id, git_branch_id = create_test_project_and_branch(session)
            create_bulk_tasks(session, git_branch_id, project_id, scale)

            from fastmcp.task_management.infrastructure.repositories.project_git_branch_repository import (
                ProjectGitBranchRepository,
            )
            from fastmcp.task_management.infrastructure.repositories.task_repository import (
                TaskRepository,
            )

            task_repo = TaskRepository(session)
            branch_repo = ProjectGitBranchRepository(session)
            use_case = ListTasksUseCase(task_repo, branch_repo)

            request = ListTasksRequest(git_branch_id=git_branch_id)

            start = time.time()
            with query_counter as qc:
                response = use_case.execute(request)
            duration = time.time() - start

            metrics[scale] = {
                "duration": duration,
                "queries": qc.count,
                "task_count": len(response.tasks),
                "queries_per_task": qc.count / scale if scale > 0 else 0,
            }

    # Print performance report
    print("\n" + "=" * 70)
    print("SCALABILITY PERFORMANCE REPORT")
    print("=" * 70)
    print(f"{'Tasks':<10} {'Duration':<12} {'Queries':<10} {'Q/Task':<10} {'Status'}")
    print("-" * 70)

    for scale in test_scales:
        m = metrics[scale]
        status = (
            "✅ PASS"
            if m["duration"] < (2.0 if scale == 500 else 5.0 if scale == 1000 else 1.0)
            else "❌ SLOW"
        )
        print(
            f"{scale:<10} {m['duration']:.3f}s {'':<6} {m['queries']:<10} {m['queries_per_task']:.4f} {'':<5} {status}"
        )

    print("=" * 70)
    print("\nSCALABILITY VALIDATION:")
    print(
        f"✅ Query efficiency: Constant ~{metrics[1000]['queries']} queries regardless of task count"
    )
    print(
        f"✅ Linear time scaling: {metrics[1000]['duration'] / metrics[100]['duration']:.1f}x time for 10x tasks"
    )
    print(
        f"✅ N+1 problem resolved: {metrics[1000]['queries_per_task']:.4f} queries per task"
    )
    print("=" * 70 + "\n")

    # Assert summary metrics
    assert metrics[1000]["queries"] <= 10, (
        "Query count should be constant with batch loading"
    )
    assert metrics[1000]["duration"] < 5.0, "1000 tasks should complete in <5s"
