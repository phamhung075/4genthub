#!/bin/bash
# Run a single test file directly
cd dhafnck_mcp_main
python -m pytest "$1" -xvs --tb=short 2>&1 | head -200
