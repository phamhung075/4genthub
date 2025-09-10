#!/bin/bash

for agent_dir in dhafnck_mcp_main/agent-library/agents/*/; do
  agent_name=$(basename "$agent_dir")
  if [ -f "$agent_dir/capabilities.yaml" ]; then
    write_perm=$(grep -A 3 "file_operations:" "$agent_dir/capabilities.yaml" | grep -A 3 "permissions:" | grep "write:" | awk '{print $2}')
    echo "$agent_name: write=$write_perm"
  fi
done | sort