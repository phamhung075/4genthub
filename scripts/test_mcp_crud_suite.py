#!/usr/bin/env python3
"""
Comprehensive MCP Server CRUD Test Suite across all layers:
- Projects: Create 2, get, list, update, health check, set context, delete 1
- Branches: Create 2, get, list, update, assign agent, set context, delete 1
- Tasks (Branch 1): Create 2, update, get, list, search, next, dependencies, assign agent
- Tasks (Branch 2): Same as Branch 1
- Subtasks (Branch 1): Create 2 per task, update, list, get, complete all for 1 task -> complete task
- Issues & Fix Prompts generation into ai_docs/
"""

import os
import sys
import time
import json
import uuid
import requests

TOKEN_HEADER = None
MCP_URL = "https://api.4genthub.com/mcp"
USER_ID = "f0de4c5d-2a97-4324-abcd-9dae3922761e"

# Load token from .mcp.json
try:
    with open("/home/daihu/__projects__/4genthub/.mcp.json", "r") as f:
        mcp_cfg = json.load(f)
        TOKEN_HEADER = mcp_cfg["mcpServers"]["agenthub_http"]["headers"]["Authorization"]
except Exception as e:
    print(f"Failed to load token from .mcp.json: {e}")
    sys.exit(1)

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Authorization": TOKEN_HEADER
}

rpc_id_counter = 100

def call_mcp(tool_name: str, arguments: dict) -> dict:
    global rpc_id_counter
    rpc_id_counter += 1
    payload = {
        "jsonrpc": "2.0",
        "id": rpc_id_counter,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    t0 = time.time()
    try:
        resp = requests.post(MCP_URL, json=payload, headers=HEADERS, timeout=30)
        duration = round(time.time() - t0, 3)
        if resp.status_code != 200:
            return {
                "ok": False,
                "http_status": resp.status_code,
                "duration": duration,
                "error": f"HTTP {resp.status_code}: {resp.text}"
            }

        rpc_resp = resp.json()
        if "error" in rpc_resp:
            return {
                "ok": False,
                "http_status": 200,
                "duration": duration,
                "error": rpc_resp["error"]
            }

        result = rpc_resp.get("result", {})
        is_error = result.get("isError", False)
        content = result.get("content", [])
        if not content:
            return {
                "ok": not is_error,
                "http_status": 200,
                "duration": duration,
                "data": None,
                "is_error": is_error
            }

        text = content[0].get("text", "")
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = text

        # Check tool-level success
        tool_success = True
        err_msg = None
        if isinstance(parsed, dict):
            if parsed.get("success") is False:
                tool_success = False
                err_msg = parsed.get("error") or parsed.get("message")

        return {
            "ok": tool_success and not is_error,
            "http_status": 200,
            "duration": duration,
            "data": parsed,
            "is_error": is_error,
            "error_detail": err_msg
        }
    except Exception as exc:
        return {
            "ok": False,
            "http_status": None,
            "duration": round(time.time() - t0, 3),
            "error": str(exc)
        }

results = []

def record_test(layer: str, action: str, description: str, res: dict, extra: dict = None):
    status = "PASS" if res.get("ok") else "FAIL"
    item = {
        "layer": layer,
        "action": action,
        "description": description,
        "status": status,
        "duration": res.get("duration", 0),
        "response": res,
        "extra": extra or {}
    }
    results.append(item)
    symbol = "✅" if status == "PASS" else "❌"
    print(f"[{symbol} {status}] {layer} :: {action} - {description} ({res.get('duration')}s)")
    if status == "FAIL":
        err = res.get("error") or res.get("error_detail") or res.get("data")
        print(f"   -> Error: {json.dumps(err, default=str)[:200]}")
    return item

def run_suite():
    run_id = uuid.uuid4().hex[:6]
    print(f"=== Starting MCP CRUD Test Suite (Run ID: {run_id}) ===")

    # ---------------------------------------------------------
    # LAYER 1: PROJECTS
    # Checklist: Create 2, get, list, update, health check, set context, delete 1
    # ---------------------------------------------------------
    print("\n--- Layer 1: Projects ---")
    p1_name = f"crud-p1-{run_id}"
    p2_name = f"crud-p2-{run_id}"

    # 1. Create Project 1
    r_cp1 = call_mcp("manage_project", {"action": "create", "name": p1_name, "description": "Project 1 description", "user_id": USER_ID})
    p1_id = None
    if r_cp1.get("ok") and isinstance(r_cp1.get("data"), dict):
        p_data = r_cp1["data"].get("data", {}).get("project", {}) or r_cp1["data"].get("project", {})
        p1_id = p_data.get("id")
    record_test("Projects", "create", f"Create Project 1 ({p1_name})", r_cp1, {"project_id": p1_id})

    # 2. Create Project 2
    r_cp2 = call_mcp("manage_project", {"action": "create", "name": p2_name, "description": "Project 2 description", "user_id": USER_ID})
    p2_id = None
    if r_cp2.get("ok") and isinstance(r_cp2.get("data"), dict):
        p_data = r_cp2["data"].get("data", {}).get("project", {}) or r_cp2["data"].get("project", {})
        p2_id = p_data.get("id")
    record_test("Projects", "create", f"Create Project 2 ({p2_name})", r_cp2, {"project_id": p2_id})

    if not p1_id:
        print("Project 1 creation failed, aborting dependent tests.")
        return

    # 3. Get Project 1
    r_gp1 = call_mcp("manage_project", {"action": "get", "project_id": p1_id, "user_id": USER_ID})
    record_test("Projects", "get", f"Get Project 1 ({p1_id})", r_gp1)

    # 4. List Projects
    r_lp = call_mcp("manage_project", {"action": "list", "user_id": USER_ID})
    record_test("Projects", "list", "List all projects", r_lp)

    # 5. Update Project 1
    r_up1 = call_mcp("manage_project", {"action": "update", "project_id": p1_id, "name": f"{p1_name}-updated", "description": "Updated description for P1", "user_id": USER_ID})
    record_test("Projects", "update", f"Update Project 1 ({p1_id})", r_up1)

    # 6. Health Check Project 1
    r_hp1 = call_mcp("manage_project", {"action": "project_health_check", "project_id": p1_id, "user_id": USER_ID})
    record_test("Projects", "health_check", f"Health Check Project 1 ({p1_id})", r_hp1)

    # 7. Set Context on Project 1
    r_scp1 = call_mcp("manage_context", {
        "action": "create",
        "level": "project",
        "context_id": p1_id,
        "project_id": p1_id,
        "data": json.dumps({"architecture": "microservices", "env": "testing", "run_id": run_id}),
        "user_id": USER_ID
    })
    # If create context says already exists or needs update, try update
    if not r_scp1.get("ok"):
        r_scp1 = call_mcp("manage_context", {
            "action": "update",
            "level": "project",
            "context_id": p1_id,
            "project_id": p1_id,
            "data": json.dumps({"architecture": "microservices", "env": "testing", "run_id": run_id}),
            "user_id": USER_ID
        })
    record_test("Projects", "set_context", f"Set Context for Project 1 ({p1_id})", r_scp1)

    # 8. Delete Project 2
    if p2_id:
        r_dp2 = call_mcp("manage_project", {"action": "delete", "project_id": p2_id, "user_id": USER_ID})
        record_test("Projects", "delete", f"Delete Project 2 ({p2_id})", r_dp2)

    # ---------------------------------------------------------
    # LAYER 2: BRANCHES
    # Checklist: Create 2, get, list, update, assign agent, set context, delete 1
    # ---------------------------------------------------------
    print("\n--- Layer 2: Branches ---")
    b1_name = f"branch-1-{run_id}"
    b2_name = f"branch-2-{run_id}"

    # 1. Create Branch 1
    r_cb1 = call_mcp("manage_git_branch", {
        "action": "create",
        "project_id": p1_id,
        "git_branch_name": b1_name,
        "git_branch_description": "Branch 1 for testing",
        "user_id": USER_ID
    })
    b1_id = None
    if r_cb1.get("ok") and isinstance(r_cb1.get("data"), dict):
        b_data = r_cb1["data"].get("data", {}).get("git_branch", {}) or r_cb1["data"].get("git_branch", {})
        b1_id = b_data.get("id")
    record_test("Branches", "create", f"Create Branch 1 ({b1_name})", r_cb1, {"branch_id": b1_id})

    # 2. Create Branch 2
    r_cb2 = call_mcp("manage_git_branch", {
        "action": "create",
        "project_id": p1_id,
        "git_branch_name": b2_name,
        "git_branch_description": "Branch 2 for testing",
        "user_id": USER_ID
    })
    b2_id = None
    if r_cb2.get("ok") and isinstance(r_cb2.get("data"), dict):
        b_data = r_cb2["data"].get("data", {}).get("git_branch", {}) or r_cb2["data"].get("git_branch", {})
        b2_id = b_data.get("id")
    record_test("Branches", "create", f"Create Branch 2 ({b2_name})", r_cb2, {"branch_id": b2_id})

    if not b1_id:
        print("Branch 1 creation failed, aborting dependent tests.")
        return

    # 3. Get Branch 1
    r_gb1 = call_mcp("manage_git_branch", {
        "action": "get",
        "project_id": p1_id,
        "git_branch_id": b1_id,
        "user_id": USER_ID
    })
    record_test("Branches", "get", f"Get Branch 1 ({b1_id})", r_gb1)

    # 4. List Branches
    r_lb = call_mcp("manage_git_branch", {
        "action": "list",
        "project_id": p1_id,
        "user_id": USER_ID
    })
    record_test("Branches", "list", f"List Branches for Project 1 ({p1_id})", r_lb)

    # 5. Update Branch 1
    r_ub1 = call_mcp("manage_git_branch", {
        "action": "update",
        "project_id": p1_id,
        "git_branch_id": b1_id,
        "git_branch_name": f"{b1_name}-updated",
        "git_branch_description": "Updated branch 1 description",
        "user_id": USER_ID
    })
    record_test("Branches", "update", f"Update Branch 1 ({b1_id})", r_ub1)

    # 6. Assign Agent to Branch 1
    # First register an agent if needed, or use an existing agent
    agent_name = f"tester-agent-{run_id}"
    r_reg_agent = call_mcp("manage_agent", {
        "action": "register",
        "project_id": p1_id,
        "name": agent_name,
        "call_agent": "coding-agent",
        "user_id": USER_ID
    })
    record_test("Agents", "register", f"Register Agent ({agent_name})", r_reg_agent)
    agent_id = None
    if r_reg_agent.get("ok") and isinstance(r_reg_agent.get("data"), dict):
        ag_data = r_reg_agent["data"].get("data", {}).get("agent", {}) or r_reg_agent["data"].get("agent", {})
        agent_id = ag_data.get("id")

    if agent_id:
        r_assign_agent = call_mcp("manage_git_branch", {
            "action": "assign_agent",
            "project_id": p1_id,
            "git_branch_id": b1_id,
            "agent_id": agent_id,
            "user_id": USER_ID
        })
        record_test("Branches", "assign_agent", f"Assign Agent {agent_name} to Branch 1", r_assign_agent)
    else:
        # Fallback test with existing agent 'coding-agent' if register failed
        r_assign_agent = call_mcp("manage_git_branch", {
            "action": "assign_agent",
            "project_id": p1_id,
            "git_branch_id": b1_id,
            "agent_id": "coding-agent",
            "user_id": USER_ID
        })
        record_test("Branches", "assign_agent", f"Assign Agent coding-agent to Branch 1", r_assign_agent)

    # 7. Set Context on Branch 1
    r_scb1 = call_mcp("manage_context", {
        "action": "create",
        "level": "branch",
        "context_id": b1_id,
        "project_id": p1_id,
        "git_branch_id": b1_id,
        "data": json.dumps({"branch_goal": "feature testing", "run_id": run_id}),
        "user_id": USER_ID
    })
    if not r_scb1.get("ok"):
        r_scb1 = call_mcp("manage_context", {
            "action": "update",
            "level": "branch",
            "context_id": b1_id,
            "project_id": p1_id,
            "git_branch_id": b1_id,
            "data": json.dumps({"branch_goal": "feature testing", "run_id": run_id}),
            "user_id": USER_ID
        })
    record_test("Branches", "set_context", f"Set Context for Branch 1 ({b1_id})", r_scb1)

    # Note: We will delete Branch 2 AFTER testing Tasks on Branch 2!

    # ---------------------------------------------------------
    # LAYER 3: TASKS (BRANCH 1)
    # Checklist: Create 2, update, get, list, search, next, dependencies, assign agent
    # ---------------------------------------------------------
    print("\n--- Layer 3: Tasks (Branch 1) ---")

    # 1. Create Task 1A
    r_ct1a = call_mcp("manage_task", {
        "action": "create",
        "project_id": p1_id,
        "git_branch_id": b1_id,
        "title": f"Task 1A: Core Implementation {run_id}",
        "description": "Implement the core engine functionality",
        "priority": "high",
        "assignees": "coding-agent",
        "user_id": USER_ID
    })
    t1a_id = None
    if r_ct1a.get("ok") and isinstance(r_ct1a.get("data"), dict):
        t_data = r_ct1a["data"].get("data", {}).get("task", {}) or r_ct1a["data"].get("task", {})
        t1a_id = t_data.get("id")
    record_test("Tasks (B1)", "create", f"Create Task 1A", r_ct1a, {"task_id": t1a_id})

    # 2. Create Task 1B
    r_ct1b = call_mcp("manage_task", {
        "action": "create",
        "project_id": p1_id,
        "git_branch_id": b1_id,
        "title": f"Task 1B: Integration Testing {run_id}",
        "description": "Write and run comprehensive test suite",
        "priority": "medium",
        "assignees": "coding-agent",
        "user_id": USER_ID
    })
    t1b_id = None
    if r_ct1b.get("ok") and isinstance(r_ct1b.get("data"), dict):
        t_data = r_ct1b["data"].get("data", {}).get("task", {}) or r_ct1b["data"].get("task", {})
        t1b_id = t_data.get("id")
    record_test("Tasks (B1)", "create", f"Create Task 1B", r_ct1b, {"task_id": t1b_id})

    if t1a_id:
        # 3. Update Task 1A
        r_ut1a = call_mcp("manage_task", {
            "action": "update",
            "task_id": t1a_id,
            "status": "in_progress",
            "details": "Started working on core implementation",
            "user_id": USER_ID
        })
        record_test("Tasks (B1)", "update", f"Update Task 1A to in_progress", r_ut1a)

        # 4. Get Task 1A
        r_gt1a = call_mcp("manage_task", {
            "action": "get",
            "task_id": t1a_id,
            "user_id": USER_ID
        })
        record_test("Tasks (B1)", "get", f"Get Task 1A ({t1a_id})", r_gt1a)

        # 5. List Tasks on Branch 1
        r_lt1 = call_mcp("manage_task", {
            "action": "list",
            "project_id": p1_id,
            "git_branch_id": b1_id,
            "user_id": USER_ID
        })
        record_test("Tasks (B1)", "list", f"List Tasks on Branch 1", r_lt1)

        # 6. Search Tasks
        r_st = call_mcp("manage_task", {
            "action": "search",
            "project_id": p1_id,
            "git_branch_id": b1_id,
            "query": "Core Implementation",
            "user_id": USER_ID
        })
        record_test("Tasks (B1)", "search", "Search Tasks for 'Core Implementation'", r_st)

        # 7. Next Task
        r_nt = call_mcp("manage_task", {
            "action": "next",
            "project_id": p1_id,
            "git_branch_id": b1_id,
            "user_id": USER_ID
        })
        record_test("Tasks (B1)", "next", "Get Next Task on Branch 1", r_nt)

        # 8. Dependencies: add dependency from Task 1B -> Task 1A
        if t1b_id:
            r_dep = call_mcp("manage_task", {
                "action": "add_dependency",
                "task_id": t1b_id,
                "dependency_id": t1a_id,
                "user_id": USER_ID
            })
            record_test("Tasks (B1)", "add_dependency", f"Add Dependency (1B depends on 1A)", r_dep)

        # 9. Assign Agent to Task 1A
        r_at1 = call_mcp("manage_task", {
            "action": "update",
            "task_id": t1a_id,
            "assignees": "coding-agent",
            "details": "Assigned coding-agent to task 1A",
            "user_id": USER_ID
        })
        record_test("Tasks (B1)", "assign_agent", "Assign coding-agent to Task 1A", r_at1)

    # ---------------------------------------------------------
    # LAYER 4: TASKS (BRANCH 2) & DELETE BRANCH 2
    # Checklist: Same as Branch 1
    # ---------------------------------------------------------
    print("\n--- Layer 4: Tasks (Branch 2) ---")
    if b2_id:
        # 1. Create Task 2A
        r_ct2a = call_mcp("manage_task", {
            "action": "create",
            "project_id": p1_id,
            "git_branch_id": b2_id,
            "title": f"Task 2A: Branch 2 Feature {run_id}",
            "description": "Feature implementation on Branch 2",
            "priority": "low",
            "assignees": "coding-agent",
            "user_id": USER_ID
        })
        t2a_id = None
        if r_ct2a.get("ok") and isinstance(r_ct2a.get("data"), dict):
            t_data = r_ct2a["data"].get("data", {}).get("task", {}) or r_ct2a["data"].get("task", {})
            t2a_id = t_data.get("id")
        record_test("Tasks (B2)", "create", f"Create Task 2A", r_ct2a, {"task_id": t2a_id})

        # 2. Create Task 2B
        r_ct2b = call_mcp("manage_task", {
            "action": "create",
            "project_id": p1_id,
            "git_branch_id": b2_id,
            "title": f"Task 2B: Branch 2 Docs {run_id}",
            "description": "Documentation for Branch 2",
            "priority": "low",
            "assignees": "coding-agent",
            "user_id": USER_ID
        })
        t2b_id = None
        if r_ct2b.get("ok") and isinstance(r_ct2b.get("data"), dict):
            t_data = r_ct2b["data"].get("data", {}).get("task", {}) or r_ct2b["data"].get("task", {})
            t2b_id = t_data.get("id")
        record_test("Tasks (B2)", "create", f"Create Task 2B", r_ct2b, {"task_id": t2b_id})

        if t2a_id:
            # 3. Update Task 2A
            r_ut2a = call_mcp("manage_task", {
                "action": "update",
                "task_id": t2a_id,
                "status": "in_progress",
                "details": "Working on branch 2 feature documentation",
                "user_id": USER_ID
            })
            record_test("Tasks (B2)", "update", f"Update Task 2A", r_ut2a)

            # 4. Get Task 2A
            r_gt2a = call_mcp("manage_task", {
                "action": "get",
                "task_id": t2a_id,
                "user_id": USER_ID
            })
            record_test("Tasks (B2)", "get", f"Get Task 2A", r_gt2a)

            # 5. List Tasks on Branch 2
            r_lt2 = call_mcp("manage_task", {
                "action": "list",
                "project_id": p1_id,
                "git_branch_id": b2_id,
                "user_id": USER_ID
            })
            record_test("Tasks (B2)", "list", f"List Tasks on Branch 2", r_lt2)

            # 6. Search Tasks on Branch 2
            r_st2 = call_mcp("manage_task", {
                "action": "search",
                "project_id": p1_id,
                "git_branch_id": b2_id,
                "query": "Branch 2 Feature",
                "user_id": USER_ID
            })
            record_test("Tasks (B2)", "search", "Search Tasks on Branch 2", r_st2)

            # 7. Next Task on Branch 2
            r_nt2 = call_mcp("manage_task", {
                "action": "next",
                "project_id": p1_id,
                "git_branch_id": b2_id,
                "user_id": USER_ID
            })
            record_test("Tasks (B2)", "next", "Get Next Task on Branch 2", r_nt2)

            # 8. Dependencies on Branch 2
            if t2b_id:
                r_dep2 = call_mcp("manage_task", {
                    "action": "add_dependency",
                    "task_id": t2b_id,
                    "dependency_id": t2a_id,
                    "user_id": USER_ID
                })
                record_test("Tasks (B2)", "add_dependency", "Add Dependency on Branch 2", r_dep2)

            # 9. Assign Agent to Task 2A
            r_at2 = call_mcp("manage_task", {
                "action": "update",
                "task_id": t2a_id,
                "assignees": "coding-agent",
                "details": "Assigned coding-agent to task 2A",
                "user_id": USER_ID
            })
            record_test("Tasks (B2)", "assign_agent", "Assign agent to Task 2A", r_at2)

        # Now delete Branch 2 (Branch checklist item: delete 1)
        r_db2 = call_mcp("manage_git_branch", {
            "action": "delete",
            "project_id": p1_id,
            "git_branch_id": b2_id,
            "user_id": USER_ID
        })
        record_test("Branches", "delete", f"Delete Branch 2 ({b2_id})", r_db2)

    # ---------------------------------------------------------
    # LAYER 5: SUBTASKS (BRANCH 1)
    # Checklist: Create 2 per task, update, list, get, complete all for 1 task -> complete task
    # ---------------------------------------------------------
    print("\n--- Layer 5: Subtasks (Branch 1) ---")
    st1_id = None
    st2_id = None
    if t1a_id:
        # 1. Create Subtask 1
        r_cst1 = call_mcp("manage_subtask", {
            "action": "create",
            "task_id": t1a_id,
            "title": f"Subtask 1A-1: DB Schema Setup {run_id}",
            "description": "Configure database schemas and migration scripts",
            "user_id": USER_ID
        })
        if r_cst1.get("ok") and isinstance(r_cst1.get("data"), dict):
            st_data = r_cst1["data"].get("data", {}).get("subtask", {}) or r_cst1["data"].get("subtask", {})
            st1_id = st_data.get("id")
        record_test("Subtasks", "create", "Create Subtask 1A-1", r_cst1, {"subtask_id": st1_id})

        # 2. Create Subtask 2
        r_cst2 = call_mcp("manage_subtask", {
            "action": "create",
            "task_id": t1a_id,
            "title": f"Subtask 1A-2: API Endpoints Wiring {run_id}",
            "description": "Wire REST and JSON-RPC endpoints",
            "user_id": USER_ID
        })
        if r_cst2.get("ok") and isinstance(r_cst2.get("data"), dict):
            st_data = r_cst2["data"].get("data", {}).get("subtask", {}) or r_cst2["data"].get("subtask", {})
            st2_id = st_data.get("id")
        record_test("Subtasks", "create", "Create Subtask 1A-2", r_cst2, {"subtask_id": st2_id})

        # 3. List Subtasks for Task 1A
        r_lst = call_mcp("manage_subtask", {
            "action": "list",
            "task_id": t1a_id,
            "user_id": USER_ID
        })
        record_test("Subtasks", "list", f"List Subtasks for Task 1A", r_lst)

        if st1_id:
            # 4. Get Subtask 1A-1
            r_gst1 = call_mcp("manage_subtask", {
                "action": "get",
                "task_id": t1a_id,
                "subtask_id": st1_id,
                "user_id": USER_ID
            })
            record_test("Subtasks", "get", f"Get Subtask 1A-1", r_gst1)

            # 5. Update Subtask 1A-1
            r_ust1 = call_mcp("manage_subtask", {
                "action": "update",
                "task_id": t1a_id,
                "subtask_id": st1_id,
                "progress_percentage": 50,
                "progress_notes": "Completed initial schema design and migration drafts",
                "user_id": USER_ID
            })
            record_test("Subtasks", "update", "Update Subtask 1A-1", r_ust1)

            # 6. Complete Subtask 1A-1
            r_cp_st1 = call_mcp("manage_subtask", {
                "action": "complete",
                "task_id": t1a_id,
                "subtask_id": st1_id,
                "completion_summary": "Database schemas created, migrated and tested successfully",
                "impact_on_parent": "Enables API endpoint integration",
                "progress_notes": "All database requirements met",
                "user_id": USER_ID
            })
            record_test("Subtasks", "complete", "Complete Subtask 1A-1", r_cp_st1)

        if st2_id:
            # 7. Complete Subtask 1A-2
            r_cp_st2 = call_mcp("manage_subtask", {
                "action": "complete",
                "task_id": t1a_id,
                "subtask_id": st2_id,
                "completion_summary": "Endpoints wired and verified with integration tests",
                "impact_on_parent": "Completes all subtasks for Task 1A",
                "progress_notes": "All endpoint requirements satisfied",
                "user_id": USER_ID
            })
            record_test("Subtasks", "complete", "Complete Subtask 1A-2", r_cp_st2)

        # 8. Complete Task 1A
        r_cpt1a = call_mcp("manage_task", {
            "action": "complete",
            "task_id": t1a_id,
            "completion_summary": "All work and subtasks completed, verified end to end implementation",
            "testing_notes": "All integration tests passed",
            "user_id": USER_ID
        })
        record_test("Tasks (B1)", "complete", "Complete Task 1A", r_cpt1a)

    # ---------------------------------------------------------
    # LAYER 6: CONTEXT MANAGEMENT
    # Checklist: get project context, update project context, list contexts
    # ---------------------------------------------------------
    print("\n--- Layer 6: Context Management ---")
    # 1. Get Project Context
    r_gcp1 = call_mcp("manage_context", {
        "action": "get",
        "level": "project",
        "context_id": p1_id,
        "project_id": p1_id,
        "user_id": USER_ID
    })
    record_test("Context", "get", f"Get Context for Project 1 ({p1_id})", r_gcp1)

    # 2. Update Project Context
    r_ucp1 = call_mcp("manage_context", {
        "action": "update",
        "level": "project",
        "context_id": p1_id,
        "project_id": p1_id,
        "data": json.dumps({"architecture": "microservices", "env": "staging-verified", "run_id": run_id}),
        "user_id": USER_ID
    })
    record_test("Context", "update", f"Update Context for Project 1 ({p1_id})", r_ucp1)

    # 3. List Contexts
    r_lcp = call_mcp("manage_context", {
        "action": "list",
        "level": "project",
        "user_id": USER_ID
    })
    record_test("Context", "list", "List Project Contexts", r_lcp)

    # ---------------------------------------------------------
    # LAYER 7: AGENT MANAGEMENT
    # Checklist: get agent, list agents, unregister agent
    # ---------------------------------------------------------
    print("\n--- Layer 7: Agent Management ---")
    if agent_id:
        # 1. Get Agent
        r_gag = call_mcp("manage_agent", {
            "action": "get",
            "project_id": p1_id,
            "agent_id": agent_id,
            "user_id": USER_ID
        })
        record_test("Agents", "get", f"Get Agent ({agent_id})", r_gag)

        # 2. List Agents
        r_lag = call_mcp("manage_agent", {
            "action": "list",
            "project_id": p1_id,
            "user_id": USER_ID
        })
        record_test("Agents", "list", f"List Agents for Project 1 ({p1_id})", r_lag)

        # 3. Unregister Agent
        r_uag = call_mcp("manage_agent", {
            "action": "unregister",
            "project_id": p1_id,
            "agent_id": agent_id,
            "user_id": USER_ID
        })
        record_test("Agents", "unregister", f"Unregister Agent ({agent_id})", r_uag)

    # ---------------------------------------------------------
    # CLEANUP TEST PROJECT 1
    # ---------------------------------------------------------
    print("\n--- Cleaning up Test Project 1 ---")
    r_dp1 = call_mcp("manage_project", {"action": "delete", "project_id": p1_id, "force": True, "user_id": USER_ID})
    record_test("Cleanup", "delete", f"Clean up Project 1 ({p1_id})", r_dp1)

    # ---------------------------------------------------------
    # GENERATE DETAILED REPORT
    # ---------------------------------------------------------
    print("\n--- Generating Report ---")
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    total = len(results)

    report_lines = [
        "# MCP CRUD All Layers Test Report",
        "",
        f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}  ",
        f"**Target**: `https://api.4genthub.com/mcp` (Go FastMCP Production)  ",
        f"**Run ID**: `{run_id}`  ",
        f"**User ID**: `{USER_ID}`  ",
        "",
        "## Summary",
        "",
        f"- **Total Tests**: {total}",
        f"- **Passed**: {passed} ({(passed/total*100):.1f}%)",
        f"- **Failed**: {failed} ({(failed/total*100):.1f}%)",
        "",
        "## Detailed Results by Layer",
        "",
        "| Layer | Action | Description | Status | Latency | Details |",
        "| :--- | :--- | :--- | :---: | :---: | :--- |"
    ]

    issues = []

    for r in results:
        status_badge = "✅ PASS" if r["status"] == "PASS" else "❌ FAIL"
        err_brief = ""
        if r["status"] == "FAIL":
            err_detail = r["response"].get("error") or r["response"].get("error_detail") or r["response"].get("data")
            err_str = json.dumps(err_detail, default=str) if isinstance(err_detail, (dict, list)) else str(err_detail)
            err_brief = f"`{err_str[:60]}...`" if len(err_str) > 60 else f"`{err_str}`"
            issues.append(r)
        report_lines.append(f"| {r['layer']} | `{r['action']}` | {r['description']} | {status_badge} | {r['duration']}s | {err_brief} |")

    report_lines.extend([
        "",
        "## Issues & Fix Prompts",
        ""
    ])

    if not issues:
        report_lines.append("🎉 **No issues found! All CRUD operations across all layers succeeded.**")
    else:
        for idx, iss in enumerate(issues, 1):
            err_detail = iss["response"].get("error") or iss["response"].get("error_detail") or iss["response"].get("data")
            report_lines.extend([
                f"### Issue {idx}: {iss['layer']} - `{iss['action']}` failed",
                "",
                f"- **Action**: `{iss['action']}`",
                f"- **Layer**: {iss['layer']}",
                f"- **Description**: {iss['description']}",
                f"- **Error Output**: ```json\n{json.dumps(err_detail, indent=2, default=str)}\n```",
                "",
                "#### Fix Prompt:",
                "```text",
                f"Fix the {iss['layer']} `{iss['action']}` handler in the Go FastMCP server.",
                f"Operation '{iss['action']}' failed with error:",
                f"{json.dumps(err_detail, indent=2, default=str)}",
                "Ensure that parameters and interface implementations match the expected domain contract.",
                "```",
                ""
            ])

    os.makedirs("/home/daihu/__projects__/4genthub/ai_docs", exist_ok=True)
    report_path = "/home/daihu/__projects__/4genthub/ai_docs/mcp-crud-all-layers-report.md"
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines) + "\n")
    print(f"\nReport written to: {report_path}")
    print(f"Summary: {passed}/{total} passed, {failed}/{total} failed.")

if __name__ == "__main__":
    run_suite()
