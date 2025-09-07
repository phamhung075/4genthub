# Fast test commands:

# Ultra-fast unit tests only (no database)
pytest -m unit -q --tb=no

# All TaskId tests (now super fast)  
pytest src/tests/unit/task_management/domain/value_objects/test_task_id.py -q

# All SubtaskId tests (now super fast)
pytest src/tests/task_management/domain/value_objects/test_subtask_id.py -q

# Integration tests (still need database but can run in parallel)
pytest -m integration -n auto --tb=short

# All tests with minimal output
pytest -q --tb=line

# Only failed tests with details
pytest --lf -v
