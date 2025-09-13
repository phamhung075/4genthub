#!/bin/bash
# Run a single test file

cd dhafnck_mcp_main
python -m pytest src/tests/unit/task_management/domain/services/test_context_derivation_service.py -xvs
