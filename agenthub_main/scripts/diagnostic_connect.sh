#!/bin/bash

# =============================================================================
# MCP Server Diagnostic Script for WSL/Cursor/Claude Desktop
# =============================================================================
# This script diagnoses MCP server connection issues and provides detailed
# information about paths, configurations, and server status.
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration - repo root derived from this script's own location
# (agenthub_main/scripts/ -> repo root), never a hard-coded path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
AGENTHUB_DIR="$PROJECT_ROOT/agenthub_main"
VENV_PATH="$AGENTHUB_DIR/.venv"
PYTHON_PATH="$VENV_PATH/bin/python"
SERVER_SCRIPT="$AGENTHUB_DIR/src/fastmcp/task_management/interface/consolidated_mcp_server.py"
TASKS_JSON_PATH="$PROJECT_ROOT/.cursor/rules/tasks/tasks.json"
BACKUP_PATH="$PROJECT_ROOT/.cursor/rules/tasks/backup"

echo -e "${PURPLE}=============================================================================${NC}"
echo -e "${PURPLE}               MCP SERVER DIAGNOSTIC TOOL FOR WSL/CURSOR                     ${NC}"
echo -e "${PURPLE}                         Enhanced with Tool Diagnostics                      ${NC}"
echo -e "${PURPLE}                                Version 2.0                                   ${NC}"
echo -e "${PURPLE}=============================================================================${NC}"
echo ""

# Function to print section headers
print_section() {
    echo -e "\n${CYAN}📋 $1${NC}"
    echo -e "${CYAN}$(printf '=%.0s' {1..60})${NC}"
}

# Function to check file/directory existence
check_path() {
    local path="$1"
    local description="$2"
    local required="$3"

    if [ -e "$path" ]; then
        echo -e "  ✅ ${GREEN}$description${NC}: $path"
        if [ -f "$path" ]; then
            echo -e "     📄 File size: $(stat -c%s "$path") bytes"
            echo -e "     🕒 Modified: $(stat -c%y "$path")"
        elif [ -d "$path" ]; then
            echo -e "     📁 Directory contents: $(ls -1 "$path" 2>/dev/null | wc -l) items"
        fi
    else
        if [ "$required" = "required" ]; then
            echo -e "  ❌ ${RED}$description${NC}: $path (MISSING - REQUIRED)"
        else
            echo -e "  ⚠️  ${YELLOW}$description${NC}: $path (MISSING - OPTIONAL)"
        fi
    fi
}

# Function to test server startup
test_server_startup() {
    local test_env="$1"
    local description="$2"

    echo -e "\n${BLUE}🧪 Testing server startup: $description${NC}"

    # Create temporary test script
    local test_script="/tmp/mcp_test_$$.py"
    cat > "$test_script" << 'EOF'
import sys
import os
import asyncio
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

try:
    from fastmcp.task_management.interface.consolidated_mcp_server import mcp_instance
    print("✅ Import successful")

    async def test_tools():
        try:
            tools = await mcp_instance.get_tools()
            print(f"✅ Tools loaded: {len(tools)} tools available")
            tool_list = list(tools.values())
            for i, tool in enumerate(tool_list[:5]):  # Show first 5 tools
                print(f"   {i+1}. {tool}")
            if len(tool_list) > 5:
                print(f"   ... and {len(tool_list) - 5} more tools")
            return True
        except Exception as e:
            print(f"❌ Error loading tools: {e}")
            traceback.print_exc()
            return False

    # Test tools
    success = asyncio.run(test_tools())

    if success:
        print("✅ Server test PASSED")
        sys.exit(0)
    else:
        print("❌ Server test FAILED")
        sys.exit(1)

except ImportError as e:
    print(f"❌ Import error: {e}")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    traceback.print_exc()
    sys.exit(1)
EOF

    # Run test with specified environment
    local cmd="cd '$AGENTHUB_DIR' && source .venv/bin/activate && $test_env python '$test_script'"

    echo -e "  🔧 Command: $cmd"

    if eval "$cmd" 2>&1; then
        echo -e "  ✅ ${GREEN}Server startup test PASSED${NC}"
    else
        echo -e "  ❌ ${RED}Server startup test FAILED${NC}"
    fi

    # Cleanup
    rm -f "$test_script"
}

# Function to test comprehensive tool diagnostics
test_tool_diagnostics() {
    echo -e "\n${BLUE}🔧 COMPREHENSIVE TOOL DIAGNOSTICS${NC}"

    # Create detailed tool test script
    local tool_test_script="/tmp/tool_diagnostic_$$.py"
    cat > "$tool_test_script" << 'EOF'
import sys
import os
import asyncio
import traceback
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

async def comprehensive_tool_test():
    """Comprehensive tool testing and diagnostics"""

    try:
        print("🔄 Importing server module...")
        from fastmcp.task_management.interface.consolidated_mcp_server import mcp_instance
        print("✅ Server module imported successfully")
        print(f"📊 Server name: {mcp_instance.name}")
        print(f"📊 Server type: {type(mcp_instance)}")

        # Test 1: Check tool manager
        print("\n🔧 Testing tool manager...")
        tm = mcp_instance._tool_manager
        print(f"✅ Tool manager type: {type(tm)}")

        # Access tools directly from tool manager
        if hasattr(tm, '_tools'):
            tools_dict = tm._tools
            print(f"✅ Tool manager has {len(tools_dict)} tools:")
            for i, name in enumerate(tools_dict.keys(), 1):
                print(f"   {i}. {name}")
        else:
            print("❌ No _tools attribute found in tool manager")

        # Test 2: Async get_tools method
        print("\n🔧 Testing async get_tools() method...")
        try:
            tools = await mcp_instance.get_tools()
            print(f"✅ get_tools() returned {len(tools)} tools")
            for i, (name, tool) in enumerate(tools.items(), 1):
                print(f"   {i}. {name}: {type(tool)}")
                if hasattr(tool, 'description'):
                    desc = tool.description[:100] + "..." if len(tool.description) > 100 else tool.description
                    print(f"      Description: {desc}")
        except Exception as e:
            print(f"❌ Error with get_tools(): {e}")
            traceback.print_exc()

        # Test 3: MCP protocol methods
        print("\n🔧 Testing MCP protocol methods...")
        try:
            # Test _mcp_list_tools
            mcp_tools = await mcp_instance._mcp_list_tools()
            print(f"✅ _mcp_list_tools() returned: {type(mcp_tools)}")
            print(f"✅ MCP tools count: {len(mcp_tools)}")

            # Show first few tools with details
            for i, tool in enumerate(mcp_tools[:3], 1):
                print(f"   {i}. Tool type: {type(tool)}")
                if hasattr(tool, 'name'):
                    print(f"      Name: {tool.name}")
                if hasattr(tool, 'description'):
                    desc = tool.description[:80] + "..." if len(tool.description) > 80 else tool.description
                    print(f"      Description: {desc}")
                if hasattr(tool, 'inputSchema'):
                    print(f"      Input schema: {type(tool.inputSchema)}")

        except Exception as e:
            print(f"❌ Error with MCP protocol methods: {e}")
            traceback.print_exc()

        # Test 4: Tool functionality test
        print("\n🔧 Testing individual tool functionality...")
        try:
            tools = await mcp_instance.get_tools()
            if tools:
                # Test a simple tool (like manage_project with list action)
                test_tool_name = list(tools.keys())[0]
                print(f"🧪 Testing tool: {test_tool_name}")

                tool = tools[test_tool_name]
                print(f"   Tool type: {type(tool)}")
                print(f"   Tool enabled: {getattr(tool, 'enabled', 'Unknown')}")

                # Try to call the tool with safe parameters
                if test_tool_name == 'manage_project':
                    print("   🧪 Testing manage_project with list action...")
                    try:
                        result = await mcp_instance._call_tool('manage_project', {'action': 'list'})
                        print(f"   ✅ Tool call successful: {type(result)}")
                        print(f"   📊 Result length: {len(result) if hasattr(result, '__len__') else 'N/A'}")
                    except Exception as e:
                        print(f"   ⚠️  Tool call failed (expected for missing data): {e}")
                else:
                    print(f"   ℹ️  Skipping functionality test for {test_tool_name}")

        except Exception as e:
            print(f"❌ Error testing tool functionality: {e}")
            traceback.print_exc()

        # Test 5: Tool registration verification
        print("\n🔧 Verifying tool registration...")
        try:
            expected_tools = [
                'manage_project', 'manage_task', 'manage_subtask', 'manage_agent',
                'update_auto_rule', 'validate_rules', 'manage_rule',
                'regenerate_auto_rule', 'validate_tasks_json', 'call_agent'
            ]

            tools = await mcp_instance.get_tools()
            found_tools = set(tools.keys())
            expected_set = set(expected_tools)

            print(f"✅ Expected tools: {len(expected_set)}")
            print(f"✅ Found tools: {len(found_tools)}")

            missing = expected_set - found_tools
            extra = found_tools - expected_set

            if missing:
                print(f"⚠️  Missing expected tools: {', '.join(missing)}")
            else:
                print("✅ All expected tools found")

            if extra:
                print(f"ℹ️  Additional tools found: {', '.join(extra)}")

        except Exception as e:
            print(f"❌ Error verifying tool registration: {e}")
            traceback.print_exc()

        # Test 6: Server state verification
        print("\n🔧 Verifying server state...")
        try:
            print(f"✅ Server name: {mcp_instance.name}")
            print(f"✅ Server instructions: {mcp_instance.instructions or 'None'}")

            # Check if server has required managers
            managers = ['_tool_manager', '_resource_manager', '_prompt_manager']
            for manager_name in managers:
                if hasattr(mcp_instance, manager_name):
                    manager = getattr(mcp_instance, manager_name)
                    print(f"✅ {manager_name}: {type(manager)}")
                else:
                    print(f"❌ Missing {manager_name}")

        except Exception as e:
            print(f"❌ Error verifying server state: {e}")
            traceback.print_exc()

        print("\n🎯 TOOL DIAGNOSTIC SUMMARY:")
        print("=" * 50)

        try:
            tools = await mcp_instance.get_tools()
            mcp_tools = await mcp_instance._mcp_list_tools()

            print(f"✅ Server import: SUCCESS")
            print(f"✅ Tool manager: {len(tm._tools) if hasattr(tm, '_tools') else 'UNKNOWN'} tools")
            print(f"✅ Async tools: {len(tools)} tools")
            print(f"✅ MCP protocol: {len(mcp_tools)} tools")
            print(f"✅ Tool registration: {'COMPLETE' if len(tools) >= 10 else 'INCOMPLETE'}")

            return True

        except Exception as e:
            print(f"❌ DIAGNOSTIC FAILED: {e}")
            return False

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Set environment variables
    os.environ['PYTHONPATH'] = os.path.join(os.getcwd(), 'src')
    os.environ['TASKS_JSON_PATH'] = os.path.join(os.path.dirname(os.getcwd()), '.cursor', 'rules', 'tasks', 'tasks.json')
    os.environ['TASK_JSON_BACKUP_PATH'] = os.path.join(os.path.dirname(os.getcwd()), '.cursor', 'rules', 'tasks', 'backup')

    success = asyncio.run(comprehensive_tool_test())
    sys.exit(0 if success else 1)
EOF

    # Run comprehensive tool diagnostic
    local cmd="cd '$AGENTHUB_DIR' && source .venv/bin/activate && python '$tool_test_script'"

    echo -e "  🔧 Running comprehensive tool diagnostics..."

    if eval "$cmd" 2>&1; then
        echo -e "  ✅ ${GREEN}Tool diagnostics COMPLETED${NC}"
    else
        echo -e "  ❌ ${RED}Tool diagnostics FAILED${NC}"
    fi

    # Cleanup
    rm -f "$tool_test_script"
}

# Function to test MCP protocol communication
test_mcp_protocol() {
    echo -e "\n${BLUE}🔌 MCP PROTOCOL COMMUNICATION TEST${NC}"

    # Create MCP protocol test script
    local protocol_test_script="/tmp/mcp_protocol_test_$$.py"
    cat > "$protocol_test_script" << 'EOF'
import sys
import os
import asyncio
import json
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

async def test_mcp_protocol():
    """Test MCP protocol communication"""
    try:
        print("🔄 Testing MCP protocol communication...")
        from fastmcp.task_management.interface.consolidated_mcp_server import mcp_instance
        # Test MCP initialize simulation
        print("\n🔧 Simulating MCP initialize...")
        try:
            # This simulates what happens when Cursor connects
            print("✅ Server ready for MCP communication")
            print(f"✅ Server name: {mcp_instance.name}")
            # Test tools/list endpoint
            print("\n🔧 Testing tools/list endpoint...")
            mcp_tools = await mcp_instance._mcp_list_tools()
            print(f"✅ tools/list returned {len(mcp_tools)} tools")
            # Validate tool format
            if mcp_tools:
                first_tool = mcp_tools[0]
                print(f"✅ First tool type: {type(first_tool)}")
                # Check required MCP tool attributes
                required_attrs = ['name', 'description']
                for attr in required_attrs:
                    if hasattr(first_tool, attr):
                        value = getattr(first_tool, attr)
                        if isinstance(value, str) and len(value) > 50:
                            print(f"   ✅ {attr}: {value[:50]}...")
                        else:
                            print(f"   ✅ {attr}: {value}")
                    else:
                        print(f"   ❌ Missing required attribute: {attr}")
                # Check input schema
                if hasattr(first_tool, 'inputSchema'):
                    schema = first_tool.inputSchema
                    print(f"   ✅ inputSchema: {type(schema)}")
                    if hasattr(schema, 'type'):
                        print(f"      Schema type: {schema.type}")
                    if hasattr(schema, 'properties'):
                        props = schema.properties
                        print(f"      Properties: {len(props) if props else 0} fields")
                else:
                    print("   ❌ Missing inputSchema")
            # Test tool call simulation
            print("\n🔧 Testing tool call simulation...")
            try:
                # Try to call a safe tool
                result = await mcp_instance._mcp_call_tool('manage_project', {'action': 'list'})
                print(f"✅ Tool call successful: {type(result)}")
                print(f"✅ Result format: {len(result) if hasattr(result, '__len__') else 'N/A'} items")
            except Exception as e:
                print(f"⚠️  Tool call failed (may be expected): {e}")
            print("\n🎯 MCP PROTOCOL TEST SUMMARY:")
            print("=" * 40)
            print("✅ MCP server ready: YES")
            print(f"✅ Tools endpoint: {len(mcp_tools)} tools")
            print(f"✅ Tool format: '{'VALID' if mcp_tools and hasattr(mcp_tools[0], 'name') else 'INVALID'}'")
            print(f"✅ Protocol compliance: '{'GOOD' if len(mcp_tools) > 0 else 'ISSUES'}'")
            return True
        except Exception as e:
            print(f"❌ MCP protocol test failed: {e}")
            traceback.print_exc()
            return False
    except Exception as e:
        print(f"❌ Critical MCP protocol error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Set environment variables
    os.environ['PYTHONPATH'] = os.path.join(os.getcwd(), 'src')
    os.environ['TASKS_JSON_PATH'] = os.path.join(os.path.dirname(os.getcwd()), '.cursor', 'rules', 'tasks', 'tasks.json')
    os.environ['TASK_JSON_BACKUP_PATH'] = os.path.join(os.path.dirname(os.getcwd()), '.cursor', 'rules', 'tasks', 'backup')
    success = asyncio.run(test_mcp_protocol())
    sys.exit(0 if success else 1)
EOF

    # Run MCP protocol test
    local cmd="cd '$AGENTHUB_DIR' && source .venv/bin/activate && python '$protocol_test_script'"

    echo -e "  🔧 Testing MCP protocol communication..."

    if eval "$cmd" 2>&1; then
        echo -e "  ✅ ${GREEN}MCP protocol test PASSED${NC}"
    else
        echo -e "  ❌ ${RED}MCP protocol test FAILED${NC}"
    fi

    # Cleanup
    rm -f "$protocol_test_script"
}

# Function to test Cursor-specific connectivity
test_cursor_connectivity() {
    echo -e "\n${BLUE}🎯 CURSOR CONNECTIVITY DIAGNOSTICS${NC}"

    # Check if Cursor is running
    echo -e "\n🔧 Checking Cursor processes..."
    local cursor_procs=$(pgrep -f "cursor|code" | wc -l)
    if [ $cursor_procs -gt 0 ]; then
        echo -e "  ✅ ${GREEN}Cursor processes found: $cursor_procs${NC}"
    else
        echo -e "  ⚠️  ${YELLOW}No Cursor processes detected${NC}"
    fi

    # Check MCP configuration accessibility
    echo -e "\n🔧 Testing MCP configuration accessibility..."
    local configs=(
        "$HOME/.cursor/mcp.json:Global MCP Config"
        "$PROJECT_ROOT/.cursor/mcp.json:Project MCP Config"
    )

    for config_info in "${configs[@]}"; do
        local config_path="${config_info%%:*}"
        local config_desc="${config_info##*:}"

        if [ -f "$config_path" ]; then
            echo -e "  ✅ ${GREEN}$config_desc accessible${NC}: $config_path"

            # Check if agenthub is configured
            if grep -q '"agenthub"' "$config_path" 2>/dev/null; then
                echo -e "     ✅ agenthub server configured"

                # Extract command path and test it
                local cmd_path=$(python3 -c "
import json
try:
    with open('$config_path', 'r') as f:
        config = json.load(f)
    tm_config = config.get('mcpServers', {}).get('agenthub', {})
    print(f'     Command: {tm_config.get("command", "NOT SET")}')
except:
    pass
" 2>/dev/null)

                if [ -n "$cmd_path" ] && [ -x "$cmd_path" ]; then
                    echo -e "     ✅ Command path executable: $cmd_path"
                elif [ -n "$cmd_path" ]; then
                    echo -e "     ❌ Command path not executable: $cmd_path"
                else
                    echo -e "     ❌ Could not extract command path"
                fi
            else
                echo -e "     ❌ agenthub server not configured"
            fi
        else
            echo -e "  ❌ ${RED}$config_desc missing${NC}: $config_path"
        fi
    done

    # Test server response time
    echo -e "\n🔧 Testing server response time..."
    local response_test_script="/tmp/response_test_$$.py"
    cat > "$response_test_script" << 'EOF'
import sys
import os
import asyncio
import time
import traceback

sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

async def test_response_time():
    try:
        os.environ['PYTHONPATH'] = os.path.join(os.getcwd(), 'src')
        os.environ['TASKS_JSON_PATH'] = os.path.join(os.path.dirname(os.getcwd()), '.cursor', 'rules', 'tasks', 'tasks.json')
        os.environ['TASK_JSON_BACKUP_PATH'] = os.path.join(os.path.dirname(os.getcwd()), '.cursor', 'rules', 'tasks', 'backup')
        start_time = time.time()
        from fastmcp.task_management.interface.consolidated_mcp_server import mcp_instance
        import_time = time.time() - start_time
        start_time = time.time()
        tools = await mcp_instance._mcp_list_tools()
        list_time = time.time() - start_time
        print(f"✅ Import time: {import_time:.3f} s")
        print(f"✅ Tool list time: {list_time:.3f} s")
        print(f"✅ Total response time: {import_time + list_time:.3f} s")
        print(f"✅ Tools available: {len(tools)}")
        if import_time + list_time < 2:
            print("✅ Response time: EXCELLENT (< 2s)")
        elif import_time + list_time < 5:
            print("⚠️  Response time: ACCEPTABLE (< 5s)")
        else:
            print("❌ Response time: SLOW (> 5s)")
        return True
    except Exception as e:
        print(f"❌ Response test failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_response_time())
    sys.exit(0 if success else 1)
EOF

    local cmd="cd '$AGENTHUB_DIR' && source .venv/bin/activate && python '$response_test_script'"

    if eval "$cmd" 2>&1; then
        echo -e "  ✅ ${GREEN}Response time test PASSED${NC}"
    else
        echo -e "  ❌ ${RED}Response time test FAILED${NC}"
    fi

    rm -f "$response_test_script"

    # Check for common Cursor issues
    echo -e "\n🔧 Checking for common Cursor MCP issues..."

    # Check WSL path mapping
    echo -e "  🔍 WSL path mapping check:"
    if echo "$PYTHON_PATH" | grep -q "/mnt/c"; then
        echo -e "     ⚠️  Python path uses Windows mount - may cause issues"
    else:
        echo -e "     ✅ Python path uses native WSL paths"
    fi

    # Check for port conflicts
    echo -e "  🔍 Port conflict check:"
    local used_ports=$(netstat -tlnp 2>/dev/null | grep -E ":3000|:8000|:9000" | wc -l)
    if [ $used_ports -gt 0 ]; then
        echo -e "     ⚠️  Common MCP ports in use: $used_ports"
    else
        echo -e "     ✅ No port conflicts detected"
    fi

    # Check environment variables
    echo -e "  🔍 Environment variables:"
    local env_vars=("PYTHONPATH" "PATH" "HOME" "USER")
    for var in "${env_vars[@]}"; do
        local value=$(printenv "$var" 2>/dev/null)
        if [ -n "$value" ]; then
            if [ ${#value} -gt 50 ]; then
                echo -e "     ✅ $var: ${value:0:50}..."
            else
                echo -e "     ✅ $var: $value"
            fi
        else
            echo -e "     ❌ $var: Not set"
        fi
    done
}

# Function to generate tool summary report
generate_tool_summary() {
    echo -e "\n${PURPLE}📊 TOOL SUMMARY REPORT${NC}"
    echo -e "${PURPLE}$(printf '=%.0s' {1..60})${NC}"

    # Create summary script
    local summary_script="/tmp/tool_summary_$$.py"
    cat > "$summary_script" << 'EOF'
import sys
import os
import asyncio
import json
from pathlib import Path

sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

async def generate_summary():
    try:
        os.environ['PYTHONPATH'] = os.path.join(os.getcwd(), 'src')
        os.environ['TASKS_JSON_PATH'] = os.path.join(os.path.dirname(os.getcwd()), '.cursor', 'rules', 'tasks', 'tasks.json')
        os.environ['TASK_JSON_BACKUP_PATH'] = os.path.join(os.path.dirname(os.getcwd()), '.cursor', 'rules', 'tasks', 'backup')

        from fastmcp.task_management.interface.consolidated_mcp_server import mcp_instance

        # Get all tools
        tools = await mcp_instance.get_tools()
        mcp_tools = await mcp_instance._mcp_list_tools()

        print("🎯 FINAL TOOL SUMMARY:")
        print("=" * 50)
        print(f"📊 Server Status: {'OPERATIONAL' if tools else 'FAILED'}")
        print(f" Total Tools: {len(tools)}")
        print(f"📊 MCP Tools: {len(mcp_tools)}")
        print(f"📊 Server Name: {mcp_instance.name}")

        print("\n📋 Available Tools:")
        for i, (name, tool) in enumerate(tools.items(), 1):
            desc = ""
            if hasattr(tool, 'description'):
                desc = tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
            print(f"  {i}. {name} - {desc}")

        # Tool categories
        categories = {
            'Project Management': ['manage_project'],
            'Task Management': ['manage_task', 'manage_subtask'],
            'Agent Management': ['manage_agent', 'call_agent'],
            'Rule Management': ['update_auto_rule', 'validate_rules', 'manage_rule', 'regenerate_auto_rule'],
            'Validation': ['validate_tasks_json']
        }

        print("\n📂 Tool Categories:")
        for category, tool_names in categories.items():
            found = [name for name in tool_names if name in tools]
            missing = [name for name in tool_names if name not in tools]
            status = "✅" if len(found) == len(tool_names) else "⚠️" if found else "❌"
            print(f"  {status} {category}: {len(found)}/{len(tool_names)} tools")
            if missing:
                print(f"     Missing: {', '.join(missing)}")

        print("\n🎯 Overall Status: '${READY FOR CURSOR if len(tools) >= 10 else 'NEEDS ATTENTION'}'")

        return len(tools) >= 10

    except Exception as e:
        print(f"❌ Summary generation failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(generate_summary())
    sys.exit(0 if success else 1)
EOF

    local cmd="cd '$AGENTHUB_DIR' && source .venv/bin/activate && python '$summary_script'"

    eval "$cmd" 2>&1

    rm -f "$summary_script"
}

# Function to check process status
check_processes() {
    echo -e "\n${BLUE}🔍 Checking running processes${NC}"

    local mcp_processes=$(ps aux | grep -E "(consolidated_mcp_server|fastmcp)" | grep -v grep || true)
    if [ -n "$mcp_processes" ]; then
        echo -e "  ✅ ${GREEN}MCP server processes found:${NC}"
        echo "$mcp_processes" | while read line; do
            echo -e "     📊 $line"
        done
    else
        echo -e "  ⚠️  ${YELLOW}No MCP server processes running${NC}"
    fi

    local cursor_processes=$(ps aux | grep -E "(cursor|code)" | grep -v grep || true)
    if [ -n "$cursor_processes" ]; then
        echo -e "  ✅ ${GREEN}Cursor processes found:${NC}"
        echo "$cursor_processes" | while read line; do
            echo -e "     📊 $line"
        done
    else
        echo -e "  ⚠️  ${YELLOW}No Cursor processes running${NC}"
    fi
}

# Function to check Claude Desktop logs
check_claude_logs() {
    echo -e "\n${BLUE}📜 Checking Claude Desktop logs${NC}"

    # Common Claude Desktop log locations
    local log_locations=(
        "$HOME/.claude/logs"
        "$HOME/.config/claude/logs"
        "$HOME/.local/share/claude/logs"
        "$HOME/AppData/Roaming/Claude/logs"  # Windows path (might be accessible via WSL)
    )

    for log_dir in "${log_locations[@]}"; do
        if [ -d "$log_dir" ]; then
            echo -e "  ✅ ${GREEN}Claude logs found at:${NC} $log_dir"
            local recent_logs=$(find "$log_dir" -name "*.log" -type f -mtime -1 2>/dev/null | head -5)
            if [ -n "$recent_logs" ]; then
                echo -e "     📄 Recent log files:"
                echo "$recent_logs" | while read log_file; do
                    echo -e "        - $(basename "$log_file") ($(stat -c%s "$log_file") bytes, modified: $(stat -c%y "$log_file" | cut -d' ' -f1-2))"
                done

                # Show last few lines of most recent log
                local latest_log=$(find "$log_dir" -name "*.log" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
                if [ -n "$latest_log" ]; then
                    echo -e "     📖 Last 10 lines of latest log ($latest_log):"
                    tail -10 "$latest_log" 2>/dev/null | while read line; do
                        echo -e "        $line"
                    done
                fi
            else
                echo -e "     ⚠️  No recent log files found"
            fi
        else
            echo -e "  ❌ ${RED}Claude logs not found at:${NC} $log_dir"
        fi
    done
}

# Function to validate MCP configuration
validate_mcp_config() {
    local config_file="$1"
    local description="$2"

    echo -e "\n${BLUE}🔧 Validating MCP configuration: $description${NC}"
    echo -e "  📁 Config file: $config_file"

    if [ ! -f "$config_file" ]; then
        echo -e "  ❌ ${RED}Configuration file not found${NC}"
        return 1
    fi

    echo -e "  ✅ ${GREEN}Configuration file exists${NC}"
    echo -e "  📄 File size: $(stat -c%s "$config_file") bytes"
    echo -e "  🕒 Modified: $(stat -c%y "$config_file")"

    # Validate JSON syntax
    if python3 -m json.tool "$config_file" > /dev/null 2>&1; then
        echo -e "  ✅ ${GREEN}JSON syntax is valid${NC}"
    else
        echo -e "  ❌ ${RED}JSON syntax is invalid${NC}"
        echo -e "  🔍 JSON validation error:"
        python3 -m json.tool "$config_file" 2>&1 | head -5 | while read line; do
            echo -e "     $line"
        done
        return 1
    fi

    # Check for agenthub server
    if grep -q '"agenthub"' "$config_file"; then
        echo -e "  ✅ ${GREEN}agenthub server found in config${NC}"

        # Extract and validate agenthub configuration
        echo -e "  🔍 agenthub configuration:"
        python3 -c "
import json
import os
import sys

try:
    with open('$config_file', 'r') as f:
        config = json.load(f)

    if 'mcpServers' in config and 'agenthub' in config['mcpServers']:
        tm_config = config['mcpServers']['agenthub']
        print(f'     Command: {tm_config.get(\"command\", \"NOT SET\")}')
        print(f'     Args: {tm_config.get(\"args\", \"NOT SET\")}')
        print(f'     CWD: {tm_config.get(\"cwd\", \"NOT SET\")}')
        print(f'     Env vars: {len(tm_config.get(\"env\", {}))} variables')

        # Validate paths
        command = tm_config.get('command', '')
        if command and os.path.exists(command):
            print(f'     ✅ Command path exists: {command}')
        elif command:
            print(f'     ❌ Command path missing: {command}')
        else:
            print(f'     ❌ Command not set')

        cwd = tm_config.get('cwd', '')
        if cwd and os.path.exists(cwd):
            print(f'     ✅ Working directory exists: {cwd}')
        elif cwd:
            print(f'     ❌ Working directory missing: {cwd}')
        else:
            print(f'     ❌ Working directory not set')

        # Check environment variables
        env = tm_config.get('env', {})
        for key, value in env.items():
            print(f'     🌍 {key}={value}')
            if key.endswith('_PATH') and value:
                # Handle relative paths by joining with cwd
                if not os.path.isabs(value) and cwd:
                    full_path = os.path.join(cwd, value)
                else:
                    full_path = value

                if os.path.exists(full_path):
                    print(f'        ✅ Path exists: {full_path}')
                else:
                    print(f'        ❌ Path missing: {full_path}')

        # Check if using correct server script
        args = tm_config.get('args', [])
        if args and isinstance(args, list):
            server_script = args[0] if args else ''
            if 'consolidated_mcp_server' in server_script:
                print(f'     ✅ Using consolidated MCP server')
            elif 'simple_test_server' in server_script:
                print(f'     ⚠️  Using test server instead of consolidated server')
            else:
                print(f'     ❌ Unknown server script: {server_script}')
    else:
        print('     ❌ agenthub not found in mcpServers')

except json.JSONDecodeError as e:
    print(f'     ❌ JSON parsing error: {e}')
except FileNotFoundError:
    print(f'     ❌ Configuration file not found: $config_file')
except Exception as e:
    print(f'     ❌ Error reading configuration: {e}')
" 2>/dev/null || echo -e "     ❌ ${RED}Error parsing configuration${NC}"
    else
        echo -e "  ❌ ${RED}agenthub server not found in config${NC}"
    fi
}

# Function to compare expected vs actual paths
compare_paths() {
    echo -e "\n${BLUE}🔍 Path Comparison Analysis${NC}"

    echo -e "\n  ${YELLOW}Expected vs Actual Paths:${NC}"

    # Project structure paths
    local paths=(
        "Project Root:$PROJECT_ROOT"
        "agenthub_main:$AGENTHUB_DIR"
        "Virtual Environment:$VENV_PATH"
        "Python Executable:$PYTHON_PATH"
        "Server Script:$SERVER_SCRIPT"
        "Tasks JSON:$TASKS_JSON_PATH"
        "Backup Directory:$BACKUP_PATH"
    )

    for path_info in "${paths[@]}"; do
        local label="${path_info%%:*}"
        local path="${path_info##*:}"

        echo -e "\n  📁 ${CYAN}$label${NC}:"
        echo -e "     Expected: $path"
        if [ -e "$path" ]; then
            echo -e "     Status: ✅ ${GREEN}EXISTS${NC}"
            if [ -f "$path" ] && [ -x "$path" ]; then
                echo -e "     Permissions: ✅ ${GREEN}EXECUTABLE${NC}"
            elif [ -f "$path" ]; then
                echo -e "     Permissions: ✅ ${GREEN}READABLE${NC}"
            elif [ -d "$path" ]; then
                echo -e "     Permissions: ✅ ${GREEN}DIRECTORY${NC}"
            fi
        else
            echo -e "     Status: ❌ ${RED}MISSING${NC}"
        fi
    done

    # Configuration file paths
    echo -e "\n  ${YELLOW}Configuration Files:${NC}"
    local config_files=(
        "Global MCP Config:$HOME/.cursor/mcp.json"
        "Project MCP Config:$PROJECT_ROOT/.cursor/mcp.json"
        "Cursor Settings:$PROJECT_ROOT/.cursor/settings.json"
    )

    for config_info in "${config_files[@]}"; do
        local label="${config_info%%:*}"
        local path="${config_info##*:}"

        echo -e "\n  ⚙️  ${CYAN}$label${NC}:"
        echo -e "     Path: $path"
        if [ -f "$path" ]; then
            echo -e "     Status: ✅ ${GREEN}EXISTS${NC}"
            echo -e "     Size: $(stat -c%s "$path") bytes"
            echo -e "     Modified: $(stat -c%y "$path" | cut -d' ' -f1-2)"
        else
            echo -e "     Status: ❌ ${RED}MISSING${NC}"
        fi
    done
}

# Function to test manual server startup
test_manual_startup() {
    echo -e "\n${BLUE}🚀 Testing manual server startup${NC}"

    local startup_cmd="cd '$AGENTHUB_DIR' && source .venv/bin/activate && PYTHONPATH='$AGENTHUB_DIR/src' TASKS_JSON_PATH='$TASKS_JSON_PATH' TASK_JSON_BACKUP_PATH='$BACKUP_PATH' python -m fastmcp.task_management.interface.consolidated_mcp_server"

    echo -e "  🔧 Startup command:"
    echo -e "     $startup_cmd"

    echo -e "\n  🧪 Testing server startup (5 second test)..."

    # Start server in background and capture output
    local log_file="/tmp/mcp_server_test_$$.log"
    eval "$startup_cmd" > "$log_file" 2>&1 &
    local server_pid=$!

    # Wait a few seconds
    sleep 5

    # Check if process is still running
    if kill -0 "$server_pid" 2>/dev/null; then
        echo -e "  ✅ ${GREEN}Server started successfully (PID: $server_pid)${NC}"

        # Show server output
        echo -e "  📜 Server output:"
        head -20 "$log_file" | while read line; do
            echo -e "     $line"
        done

        # Kill the test server
        kill "$server_pid" 2>/dev/null || true
        wait "$server_pid" 2>/dev/null || true
        echo -e "  🛑 Test server stopped"
    else
        echo -e "  ❌ ${RED}Server failed to start or crashed${NC}"
        echo -e "  📜 Error output:"
        cat "$log_file" | while read line; do
            echo -e "     $line"
        done
    fi

    # Cleanup
    rm -f "$log_file"
}

# Function to provide recommendations
provide_recommendations() {
    echo -e "\n${PURPLE}💡 DIAGNOSTIC RECOMMENDATIONS${NC}"
    echo -e "${PURPLE}$(printf '=%.0s' {1..60})${NC}"

    # Check critical issues
    local issues=()

    if [ ! -f "$PYTHON_PATH" ]; then
        issues+=("Virtual environment Python not found at $PYTHON_PATH")
    fi

    if [ ! -f "$SERVER_SCRIPT" ]; then
        issues+=("Server script not found at $SERVER_SCRIPT")
    fi

    if [ ! -f "$TASKS_JSON_PATH" ]; then
        issues+=("Tasks JSON file not found at $TASKS_JSON_PATH")
    fi

    if [ ! -f "$PROJECT_ROOT/.cursor/mcp.json" ] && [ ! -f "$HOME/.cursor/mcp.json" ]; then
        issues+=("No MCP configuration file found")
    fi

    if [ ${#issues[@]} -eq 0 ]; then
        echo -e "✅ ${GREEN}No critical issues detected!${NC}"
        echo -e "\n${YELLOW}If Cursor still shows 0 tools, try these solutions:${NC}"
        echo -e "  1. 🔄 Restart Cursor completely (close all windows)"
        echo -e "  2. 🧹 Clear Cursor cache: rm -rf ~/.cursor/User/workspaceStorage"
        echo -e "  3. 🔍 Check Cursor developer console (F12) for MCP errors"
        echo -e "  4. 📁 Verify you're in the correct project directory"
        echo -e "  5. ⏱️  Wait 30 seconds after Cursor startup for MCP initialization"
        echo -e "  6. 🔧 Try manual server test: run the diagnostic tool tests above"
        echo -e "  7. 🔌 Check MCP server status in Cursor: Ctrl+Shift+P > 'MCP'"
        echo -e "  8. 📋 Verify MCP configuration is loaded: check Cursor settings"
        echo -e "\n${CYAN}Advanced troubleshooting:${NC}"
        echo -e "  • Check if server starts manually: cd $AGENTHUB_DIR && source .venv/bin/activate && python -m fastmcp.task_management.interface.consolidated_mcp_server"
        echo -e "  • Test with minimal config: temporarily disable other MCP servers"
        echo -e "  • Verify WSL integration: ensure Cursor can access WSL paths"
        echo -e "  • Check permissions: ls -la $PYTHON_PATH"
    else
        echo -e "❌ ${RED}Critical issues found:${NC}"
        for issue in "${issues[@]}"; do
            echo -e "  • $issue"
        done

        echo -e "\n${YELLOW}Recommended fixes:${NC}"
        echo -e "  1. Ensure you're in the correct directory: cd $PROJECT_ROOT"
        echo -e "  2. Activate virtual environment: cd $AGENTHUB_DIR && source .venv/bin/activate"
        echo -e "  3. Install dependencies: uv sync"
        echo -e "  4. Create missing directories: mkdir -p $(dirname "$TASKS_JSON_PATH")"
        echo -e "  5. Initialize tasks file: echo '[]' > $TASKS_JSON_PATH"
    fi

    echo -e "\n${YELLOW}For further debugging:${NC}"
    echo -e "  • Check this diagnostic script output"
    echo -e "  • Run manual server test above"
    echo -e "  • Check Cursor developer console (F12)"
    echo -e "  • Verify WSL and Windows path mappings"
    echo -e "  • Run quick tool test: $0 --quick-test"
}

# Main execution
main() {
    print_section "SYSTEM INFORMATION"
    echo -e "  🖥️  Operating System: $(uname -a)"
    echo -e "  🐧 WSL Version: $(cat /proc/version | grep -o 'Microsoft.*' || echo 'Not WSL or version unknown')"
    echo -e "  🏠 Home Directory: $HOME"
    echo -e "  📁 Current Directory: $(pwd)"
    echo -e "  🕒 Current Time: $(date)"
    echo -e "  👤 Current User: $(whoami)"

    print_section "PYTHON/ENVIRONMENT SESSION DIAGNOSTICS"
    echo -e "${YELLOW}Running Python environment diagnostics...${NC}"

    $PYTHON_PATH << 'EOF'
import sys
import os
print("\n===== PYTHON SESSION DIAGNOSTICS =====")
print(f"sys.executable: {sys.executable}")
print(f"os.getcwd(): {os.getcwd()}")
print("sys.path:")
for p in sys.path:
    print(f"  - {p}")
print("\nEnvironment variables:")
for var in ["PYTHONPATH", "VIRTUAL_ENV", "PATH", "HOME", "USER", "SHELL"]:
    print(f"{var}: {os.environ.get(var, '<not set>')}")
print("===== END PYTHON SESSION DIAGNOSTICS =====\n")
EOF

    print_section "PROJECT STRUCTURE VALIDATION"
    check_path "$PROJECT_ROOT" "Project Root" "required"
    check_path "$AGENTHUB_DIR" "agenthub_main Directory" "required"
    check_path "$VENV_PATH" "Virtual Environment" "required"
    check_path "$PYTHON_PATH" "Python Executable" "required"
    check_path "$SERVER_SCRIPT" "Server Script" "required"
    check_path "$AGENTHUB_DIR/src/fastmcp" "FastMCP Package" "required"
    check_path "$AGENTHUB_DIR/src/fastmcp/task_management" "Task Management Package" "required"

    print_section "TASK MANAGEMENT FILES"
    check_path "$TASKS_JSON_PATH" "Tasks JSON File" "required"
    check_path "$BACKUP_PATH" "Backup Directory" "optional"
    check_path "$(dirname "$TASKS_JSON_PATH")" "Tasks Directory" "required"

    print_section "CONFIGURATION FILES"
    validate_mcp_config "$PROJECT_ROOT/.cursor/mcp.json" "Project MCP Config"
    validate_mcp_config "$HOME/.cursor/mcp.json" "Global MCP Config"
    check_path "$PROJECT_ROOT/.cursor/settings.json" "Cursor Settings" "optional"

    compare_paths
    check_processes

    print_section "SERVER FUNCTIONALITY TESTS"
    test_server_startup "PYTHONPATH='$AGENTHUB_DIR/src'" "Default Environment"
    test_server_startup "PYTHONPATH='$AGENTHUB_DIR/src' TASKS_JSON_PATH='$TASKS_JSON_PATH' TASK_JSON_BACKUP_PATH='$BACKUP_PATH'" "Full Environment"

    test_manual_startup

    print_section "COMPREHENSIVE TOOL DIAGNOSTICS"
    test_tool_diagnostics
    test_mcp_protocol
    test_cursor_connectivity

    print_section "CLAUDE DESKTOP LOGS"
    check_claude_logs

    generate_tool_summary

    provide_recommendations

    echo -e "\n${PURPLE}=============================================================================${NC}"
    echo -e "${PURPLE}                            DIAGNOSTIC COMPLETE                             ${NC}"
    echo -e "${PURPLE}=============================================================================${NC}"
    echo -e "\nDiagnostic completed at $(date)"
    echo -e "Save this output for debugging: ${CYAN}./diagnostic_connect.sh > diagnostic_output.txt 2>&1${NC}"
}

# Function for quick tool test
quick_tool_test() {
    echo -e "${CYAN}🚀 QUICK TOOL TEST${NC}"
    echo -e "${CYAN}$(printf '=%.0s' {1..40})${NC}"

    local quick_test_script="/tmp/quick_test_$$.py"
    cat > "$quick_test_script" << 'EOF'
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

async def quick_test():
    try:
        os.environ['PYTHONPATH'] = os.path.join(os.getcwd(), 'src')
        os.environ['TASKS_JSON_PATH'] = os.path.join(os.path.dirname(os.getcwd()), '.cursor', 'rules', 'tasks', 'tasks.json')
        os.environ['TASK_JSON_BACKUP_PATH'] = os.path.join(os.path.dirname(os.getcwd()), '.cursor', 'rules', 'tasks', 'backup')

        print("🔄 Loading server...")
        from fastmcp.task_management.interface.consolidated_mcp_server import mcp_instance

        print("🔧 Testing tools...")
        tools = await mcp_instance._mcp_list_tools()

        print(f"✅ SUCCESS: {len(tools)} tools available")
        print(f"📋 Tools: {', '.join([t.name for t in tools[:5]]) + ('...' if len(tools) > 5 else '')}")

        return len(tools) > 0

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    print(f"\n{'🎉 TOOLS WORKING!' if success else '❌ TOOLS NOT WORKING'}")
    sys.exit(0 if success else 1)
EOF

    local cmd="cd '$AGENTHUB_DIR' && source .venv/bin/activate && python '$quick_test_script'"

    if eval "$cmd" 2>&1; then
        echo -e "\n✅ ${GREEN}Quick test PASSED - Tools are working!${NC}"
    else
        echo -e "\n❌ ${RED}Quick test FAILED - Run full diagnostic${NC}"
    fi

    rm -f "$quick_test_script"
}

# Handle command line arguments
if [ "$1" = "--quick-test" ] || [ "$1" = "-q" ]; then
    quick_tool_test
    exit $?
elif [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "MCP Server Diagnostic Tool"
    echo ""
    echo "Usage:"
    echo "  $0                 Run full diagnostic"
    echo "  $0 --quick-test    Run quick tool test only"
    echo "  $0 --help         Show this help"
    echo ""
    exit 0
fi

# Run main function
main "$@"
