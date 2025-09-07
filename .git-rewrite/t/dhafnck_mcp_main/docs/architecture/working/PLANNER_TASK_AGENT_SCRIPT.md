# 📋 PLANNER TASK AGENT SCRIPT - Task Creation with Checkpoint Control

## Executive Summary for Planner Task Agent

**YOUR MISSION**: Read `workplace.md`, check for existing tasks, create new tasks if needed, and respect checkpoint flow.

## 🚦 CHECKPOINT CONTROL

The planner agent:
- **Only works** when checkpoint status is "active"
- **Skips** if tasks already exist (status = "skip")
- **Waits** when not its turn (60-second checks)
- **Activates** CODE and TEST agents when done

## 🔄 Planner Task Agent Workflow

### Phase 1: Check Checkpoint & Initialize

```python
import time
import re
from datetime import datetime

def check_my_turn():
    """Check if it's planner agent's turn to work"""
    try:
        workplace = Read(file_path="dhafnck_mcp_main/docs/architecture/workplace.md")
        
        # Check checkpoint status
        if "**PLANNER** | active" in workplace:
            return "active"
        elif "**PLANNER** | skip" in workplace:
            return "skip"
        elif "**PLANNER** | waiting" in workplace:
            return "waiting"
        elif "**PLANNER** | complete" in workplace:
            return "complete"
            
        return "waiting"  # Default to waiting
        
    except:
        return "waiting"  # No workplace.md yet

def wait_for_turn():
    """Wait until it's planner agent's turn"""
    while True:
        status = check_my_turn()
        
        if status == "active":
            print("✅ PLANNER agent's turn - checking for tasks!")
            return "active"
        elif status == "skip":
            print("⏭️ PLANNER skipping - tasks already exist")
            return "skip"
        elif status == "complete":
            print("✔️ PLANNER already complete this cycle")
            return "complete"
        else:
            print("⏱️ PLANNER agent waiting for turn...")
            print("   Current status: waiting for ANALYZE to complete")
            time.sleep(60)  # Check every minute

# Load Task Planning Agent
planner_agent = mcp__dhafnck_mcp_http__call_agent(name_agent="@task_planning_agent")

print("📋 Starting Task Planning Agent...")
print("🔍 Will check workplace.md and existing tasks")
```

### Phase 2: Check Existing Tasks

```python
def check_existing_tasks(git_branch_id):
    """Check if tasks already exist for current issues"""
    
    # Get all pending/in_progress tasks
    existing_tasks = mcp__dhafnck_mcp_http__manage_task(
        action="list",
        git_branch_id=git_branch_id,
        status="pending"
    )
    
    in_progress_tasks = mcp__dhafnck_mcp_http__manage_task(
        action="list",
        git_branch_id=git_branch_id,
        status="in_progress"
    )
    
    total_active_tasks = len(existing_tasks) + len(in_progress_tasks)
    
    if total_active_tasks > 0:
        print(f"📋 Found {total_active_tasks} active tasks")
        
        # Group by type
        code_tasks = 0
        test_tasks = 0
        review_tasks = 0
        
        for task in existing_tasks + in_progress_tasks:
            if "@coding_agent" in str(task.get("assigned_agent", "")):
                code_tasks += 1
            elif "@test" in str(task.get("assigned_agent", "")):
                test_tasks += 1
            elif "@review" in str(task.get("assigned_agent", "")):
                review_tasks += 1
        
        print(f"  - Code tasks: {code_tasks}")
        print(f"  - Test tasks: {test_tasks}")
        print(f"  - Review tasks: {review_tasks}")
        
        return {
            "has_tasks": True,
            "total": total_active_tasks,
            "code": code_tasks,
            "test": test_tasks,
            "review": review_tasks
        }
    
    return {
        "has_tasks": False,
        "total": 0
    }
```

### Phase 3: Read and Parse Workplace Report

```python
def read_workplace_report():
    """Read and parse the workplace report"""
    try:
        report_content = Read(file_path="dhafnck_mcp_main/docs/architecture/workplace.md")
        
        # Parse key metrics
        compliance_score = 0
        total_violations = 0
        
        lines = report_content.split('\n')
        for line in lines:
            if "**Compliance Score**:" in line:
                score_match = re.search(r'(\d+)/100', line)
                if score_match:
                    compliance_score = int(score_match.group(1))
            
            if "**Total Violations**:" in line:
                violation_match = re.search(r'(\d+)', line)
                if violation_match:
                    total_violations = int(violation_match.group(1))
        
        # Check what tasks are needed
        needs_controller_fixes = "Code Agent: Fix all 16 controller files" in report_content
        needs_factory_fixes = "Code Agent: Create central RepositoryFactory" in report_content
        needs_cache_fixes = "Code Agent: Create cached repository wrappers" in report_content
        needs_tests = "Test Agent: Create controller compliance tests" in report_content
        needs_review = "Review Agent: Verify fixes maintain functionality" in report_content
        
        return {
            "compliance_score": compliance_score,
            "total_violations": total_violations,
            "tasks_needed": {
                "controller": needs_controller_fixes,
                "factory": needs_factory_fixes,
                "cache": needs_cache_fixes,
                "test": needs_tests,
                "review": needs_review
            }
        }
    except:
        print("⚠️ Could not read workplace.md")
        return None
```

### Phase 4: Decision Logic - Skip or Create Tasks

```python
def should_create_tasks(report_analysis, existing_tasks):
    """Decide if we should create tasks or skip"""
    
    if not report_analysis:
        print("❌ No report to analyze")
        return False
    
    if report_analysis["compliance_score"] >= 100:
        print("✅ System already compliant (100/100)")
        return False
    
    if existing_tasks["has_tasks"]:
        # Check if existing tasks cover the issues
        has_coverage = (
            existing_tasks["code"] > 0 and
            existing_tasks["test"] > 0
        )
        
        if has_coverage:
            print("⏭️ Existing tasks cover current issues")
            return False
        else:
            print("⚠️ Existing tasks incomplete - creating additional tasks")
            return True
    
    print("📋 No existing tasks - will create new ones")
    return True
```

### Phase 5: Create Tasks Based on Report

```python
def create_tasks_from_report(report_analysis, git_branch_id):
    """Create tasks based on workplace report"""
    
    tasks_created = []
    
    # Create master compliance task
    if report_analysis["compliance_score"] < 100:
        master_task = mcp__dhafnck_mcp_http__manage_task(
            action="create",
            git_branch_id=git_branch_id,
            title=f"Fix {report_analysis['total_violations']} Architecture Violations",
            description=f"Compliance: {report_analysis['compliance_score']}/100",
            priority="critical",
            metadata={
                "source": "workplace.md",
                "violations": report_analysis["total_violations"]
            }
        )
        tasks_created.append(master_task)
        master_id = master_task["task"]["id"]
        
        # Create subtasks for each issue type
        if report_analysis["tasks_needed"]["controller"]:
            controller_task = mcp__dhafnck_mcp_http__manage_subtask(
                action="create",
                task_id=master_id,
                title="Fix Controller Violations",
                description="Remove direct DB access from controllers",
                assignees="@coding_agent",
                priority="P1"
            )
            tasks_created.append(controller_task)
        
        if report_analysis["tasks_needed"]["factory"]:
            factory_task = mcp__dhafnck_mcp_http__manage_subtask(
                action="create",
                task_id=master_id,
                title="Implement Repository Factory",
                description="Add environment checking to factories",
                assignees="@coding_agent",
                priority="P1"
            )
            tasks_created.append(factory_task)
        
        if report_analysis["tasks_needed"]["cache"]:
            cache_task = mcp__dhafnck_mcp_http__manage_subtask(
                action="create",
                task_id=master_id,
                title="Add Cache Invalidation",
                description="Implement cache invalidation for mutations",
                assignees="@coding_agent",
                priority="P2"
            )
            tasks_created.append(cache_task)
        
        if report_analysis["tasks_needed"]["test"]:
            test_task = mcp__dhafnck_mcp_http__manage_subtask(
                action="create",
                task_id=master_id,
                title="Create Compliance Tests",
                description="Test architecture compliance",
                assignees="@test_orchestrator_agent",
                priority="P2"
            )
            tasks_created.append(test_task)
        
        if report_analysis["tasks_needed"]["review"]:
            review_task = mcp__dhafnck_mcp_http__manage_subtask(
                action="create",
                task_id=master_id,
                title="Review Implementation",
                description="Verify all fixes work correctly",
                assignees="@review_agent",
                priority="P3"
            )
            tasks_created.append(review_task)
    
    return tasks_created
```

### Phase 6: Update Checkpoints

```python
def update_checkpoint(agent_name, new_status):
    """Update checkpoint status in workplace.md"""
    
    workplace = Read(file_path="dhafnck_mcp_main/docs/architecture/workplace.md")
    
    lines = workplace.split('\n')
    for i, line in enumerate(lines):
        if f"**{agent_name.upper()}**" in line and "|" in line:
            parts = line.split('|')
            
            # Update status and icon
            if new_status == "active":
                parts[2] = " active "
                parts[3] = " ✅ "
            elif new_status == "complete":
                parts[2] = " complete "
                parts[3] = " ✔️ "
            elif new_status == "skip":
                parts[2] = " skip "
                parts[3] = " ⏭️ "
            elif new_status == "waiting":
                parts[2] = " waiting "
                parts[3] = " ⏸️ "
            
            lines[i] = '|'.join(parts)
            break
    
    updated_content = '\n'.join(lines)
    
    Write(
        file_path="dhafnck_mcp_main/docs/architecture/workplace.md",
        content=updated_content
    )
    
    print(f"✅ Updated {agent_name} checkpoint to: {new_status}")
```

### Phase 7: Main Planner Loop

```python
def main_planner_loop():
    """Main planner loop with checkpoint control"""
    
    git_branch_id = "current-branch-id"  # Get from context
    
    while True:
        print(f"\n{'='*60}")
        print("📋 PLANNER Agent Check")
        print(f"{'='*60}")
        
        # Wait for our turn
        status = wait_for_turn()
        
        if status == "skip":
            print("⏭️ Skipping - tasks already exist")
            # Activate next agents
            update_checkpoint("PLANNER", "skip")
            update_checkpoint("CODE", "active")
            update_checkpoint("TEST", "active")
            break
        
        if status == "complete":
            print("✔️ Planner already ran this cycle")
            time.sleep(60)
            continue
        
        if status != "active":
            continue
        
        # Check existing tasks
        print("\n📊 Checking existing tasks...")
        existing_tasks = check_existing_tasks(git_branch_id)
        
        # Read workplace report
        print("\n📖 Reading workplace report...")
        report_analysis = read_workplace_report()
        
        if not report_analysis:
            print("⚠️ No report found - waiting...")
            time.sleep(60)
            continue
        
        print(f"📊 Compliance Score: {report_analysis['compliance_score']}/100")
        print(f"🚨 Total Violations: {report_analysis['total_violations']}")
        
        # Decide whether to create tasks
        if should_create_tasks(report_analysis, existing_tasks):
            print("\n✅ Creating tasks from report...")
            
            # Create tasks
            tasks_created = create_tasks_from_report(report_analysis, git_branch_id)
            
            print(f"📋 Created {len(tasks_created)} tasks")
            
            for task in tasks_created:
                if "subtask" in task:
                    print(f"  - {task['subtask']['title']}")
                else:
                    print(f"  - {task['task']['title']}")
            
            # Update context
            mcp__dhafnck_mcp_http__manage_context(
                action="update",
                level="branch",
                context_id=git_branch_id,
                data={
                    "planner_run": datetime.now().isoformat(),
                    "tasks_created": len(tasks_created),
                    "compliance_score": report_analysis["compliance_score"]
                }
            )
            
            # Mark planner complete and activate next agents
            update_checkpoint("PLANNER", "complete")
            update_checkpoint("CODE", "active")
            update_checkpoint("TEST", "active")
            
            print("\n✅ Tasks created - activating CODE and TEST agents")
            break
            
        else:
            print("\n⏭️ No new tasks needed")
            
            if existing_tasks["has_tasks"]:
                # Skip and let existing tasks continue
                update_checkpoint("PLANNER", "skip")
                update_checkpoint("CODE", "active")
                update_checkpoint("TEST", "active")
                print("✅ Activating CODE and TEST for existing tasks")
            else:
                # System might be complete
                if report_analysis["compliance_score"] >= 100:
                    update_checkpoint("PLANNER", "complete")
                    print("🎉 System compliant - planner complete")
                else:
                    print("⚠️ No tasks but not compliant - check manually")
            
            break

# Execute the main loop
main_planner_loop()

print("🏁 Planner agent workflow complete")
```

## 📊 Decision Tree

```
START
  ↓
Check Checkpoint Status
  ↓
┌─────────────┐
│   active?   │──Yes──→ Continue
└─────────────┘
       │
       No
       ↓
┌─────────────┐
│    skip?    │──Yes──→ Skip (tasks exist)
└─────────────┘
       │
       No
       ↓
┌─────────────┐
│  waiting?   │──Yes──→ Sleep 60s
└─────────────┘
       │
       No
       ↓
┌─────────────┐
│  complete?  │──Yes──→ Already done
└─────────────┘

CONTINUE
  ↓
Check Existing Tasks
  ↓
┌─────────────────┐
│ Tasks exist?    │──Yes──→ Mark "skip"
└─────────────────┘         Activate CODE+TEST
       │
       No
       ↓
Read Workplace Report
  ↓
┌──────────────────┐
│ Violations > 0?  │──No──→ Mark "complete"
└──────────────────┘
       │
       Yes
       ↓
Create Tasks
  ↓
Mark "complete"
  ↓
Activate CODE+TEST
```

## 🎯 Success Criteria

- ✅ Respects checkpoint system - only works when "active"
- ✅ Checks for existing tasks before creating new ones
- ✅ Can skip if tasks already exist (prevents duplicates)
- ✅ Activates CODE and TEST agents when done
- ✅ Updates checkpoints to control workflow
- ✅ Waits patiently when not its turn

**⚠️ CRITICAL**: The planner agent intelligently decides whether to create tasks or skip, preventing task duplication while ensuring all issues are addressed.