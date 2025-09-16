#!/bin/bash
# Test runner for ProjectMCPController tests

cd /home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${PYTHONPATH}:src"

echo "Running ProjectMCPController tests..."
python -m pytest src/tests/unit/mcp_controllers/test_project_mcp_controller.py::TestProjectMCPController::test_list_projects_empty -xvs --tb=short
echo ""
echo "Running health check test..."
python -m pytest src/tests/unit/mcp_controllers/test_project_mcp_controller.py::TestProjectMCPController::test_project_health_check_success -xvs --tb=short