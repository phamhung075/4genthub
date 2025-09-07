# 🔍 ANALYZE AGENT SCRIPT - Problem Analysis with Checkpoint Control

## Executive Summary for Analyze Agent

**YOUR MISSION**: Analyze architecture problems and continuously update `workplace.md` with checkpoints to control agent workflow.

## 📊 Current System Status

**Critical Status**: 
- **Compliance Score**: 20/100 (Grade F - Critical Failure)
- **Total Violations**: 90 (ALL HIGH SEVERITY)
- **Central Report**: `dhafnck_mcp_main/docs/architecture/workplace.md`
- **Workflow Control**: Via checkpoint system in workplace.md

## 🚦 CHECKPOINT SYSTEM

The analyze agent manages workflow through checkpoints in `workplace.md`:

```python
WORKFLOW_CHECKPOINTS = {
    "ANALYZE": "active|waiting|complete",
    "PLANNER": "waiting|active|complete|skip",
    "CODE": "waiting|active|complete",
    "TEST": "waiting|active|complete", 
    "REVIEW": "waiting|active|complete",
    "REANALYZE": "waiting|active|complete"
}

# Flow: ANALYZE → PLANNER → CODE+TEST → REVIEW → REANALYZE
```

## 🤖 Analyze Agent Workflow

### Phase 1: Check Checkpoint & Initialize
```python
import time
import json
from datetime import datetime
from pathlib import Path

def check_my_turn():
    """Check if it's analyze agent's turn to work"""
    try:
        workplace = Read(file_path="dhafnck_mcp_main/docs/architecture/workplace.md")
        
        # Extract checkpoint status
        for line in workplace.split('\n'):
            if "## 🚦 WORKFLOW CHECKPOINTS" in line:
                # Find the checkpoint section
                checkpoint_section = workplace[workplace.index(line):]
                
                if "**ANALYZE**: active" in checkpoint_section:
                    return True
                elif "**ANALYZE**: waiting" in checkpoint_section:
                    return False
                    
        # First run - no checkpoints yet
        return True
        
    except:
        # No workplace.md yet - analyze should start
        return True

def wait_for_turn():
    """Wait until it's analyze agent's turn"""
    while not check_my_turn():
        print("⏱️ ANALYZE agent waiting for turn...")
        print("   Current workflow position: Not my turn")
        time.sleep(60)  # Check every minute
    
    print("✅ ANALYZE agent's turn - starting analysis!")

# Load Analyze Agent
analyze_agent = mcp__dhafnck_mcp_http__call_agent(name_agent="@architecture_compliance_agent")

# Wait for turn
wait_for_turn()

print("🔍 Starting Architecture Analysis...")
print("📝 Will update workplace.md with checkpoints")
```

### Phase 2: Create/Update Issues Report with Checkpoints

```python
def create_workplace_with_checkpoints(analysis_results):
    """Create workplace.md with checkpoint control system"""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    workplace_template = '''# 📋 ARCHITECTURE COMPLIANCE WORKPLACE
## Central Coordination & Checkpoint Control

**Report Status**: ACTIVE ANALYSIS
**Last Updated**: {timestamp}
**Compliance Score**: {compliance_score}/100
**Total Violations**: {total_violations}

## 🚦 WORKFLOW CHECKPOINTS
**Control the agent workflow through these checkpoints:**

| Agent | Status | Can Work? | Notes |
|-------|--------|-----------|-------|
| **ANALYZE** | active | ✅ | Currently analyzing architecture |
| **PLANNER** | waiting | ⏸️ | Waiting for analyze to complete |
| **CODE** | waiting | ⏸️ | Waiting for tasks from planner |
| **TEST** | waiting | ⏸️ | Waiting for code implementation |
| **REVIEW** | waiting | ⏸️ | Waiting for test completion |
| **REANALYZE** | waiting | ⏸️ | Waiting for review completion |

### Workflow Rules:
1. Only ONE agent can be "active" at a time
2. Agents check their checkpoint before working
3. If status is "waiting", agent sleeps for 60 seconds
4. Planner can be "skip" if tasks already exist
5. Code and Test can be "active" simultaneously

---

## 🚨 CRITICAL ISSUES IDENTIFIED

### 1. Controller Layer Violations (HIGH PRIORITY)
**Status**: IDENTIFIED - NEEDS CODE FIXES
**Count**: 16 files
**Impact**: Breaks DDD architecture
**Description**: Controllers directly access database/repositories instead of using facades

#### Affected Files:
{controller_violations}

#### Required Fix:
```python
# REMOVE:
from infrastructure.repositories.orm import GitBranchRepository
self.repository = GitBranchRepository()

# REPLACE WITH:
from application.facades import GitBranchApplicationFacade
self.facade = GitBranchApplicationFacade()
```

#### Tasks Needed:
- [ ] Code Agent: Fix all 16 controller files
- [ ] Test Agent: Create controller compliance tests
- [ ] Review Agent: Verify fixes maintain functionality

---

### 2. Repository Factory Pattern Broken (HIGH PRIORITY)
**Status**: IDENTIFIED - NEEDS CODE IMPLEMENTATION  
**Count**: 27 factory files
**Impact**: No environment switching (SQLite/Supabase), no Redis caching
**Description**: Factory files exist but don't check environment variables

#### Problem Analysis:
{factory_analysis}

#### Required Implementation:
```python
class RepositoryFactory:
    @staticmethod
    def get_task_repository():
        env = os.getenv('ENVIRONMENT', 'production')
        db_type = os.getenv('DATABASE_TYPE', 'supabase')
        redis_enabled = os.getenv('REDIS_ENABLED', 'true').lower() == 'true'
        
        if env == 'test':
            base_repo = SQLiteTaskRepository()
        elif db_type == 'supabase':
            base_repo = SupabaseTaskRepository()
        
        if redis_enabled and env != 'test':
            return CachedTaskRepository(base_repo)
        return base_repo
```

#### Tasks Needed:
- [ ] Code Agent: Create central RepositoryFactory
- [ ] Code Agent: Update all 27 factory files
- [ ] Test Agent: Create factory environment tests
- [ ] Review Agent: Verify environment switching works

---

### 3. Cache Invalidation Missing (HIGH PRIORITY)
**Status**: IDENTIFIED - NEEDS IMPLEMENTATION
**Count**: 32 mutation methods  
**Impact**: Stale data when Redis enabled
**Description**: 0/32 code paths have cache invalidation

#### Missing Cache Invalidation:
{cache_violations}

#### Tasks Needed:
- [ ] Code Agent: Create cached repository wrappers
- [ ] Code Agent: Add invalidation to all 32 methods
- [ ] Test Agent: Create cache invalidation tests
- [ ] Review Agent: Verify cache behavior

---

## 📋 NEXT AGENT ACTION

**ANALYZE COMPLETE** → **ACTIVATE PLANNER**

To activate the next agent, the analyze agent will update checkpoints:
- Set ANALYZE to "complete"
- Set PLANNER to "active"
- Planner will then read this file and create tasks

---

## 📊 ANALYSIS METRICS

- **Total Files Analyzed**: {files_analyzed}
- **Violations Found**: {total_violations}
- **Estimated Fix Time**: 2-3 days
- **Blocking Production**: YES
- **Next Analysis**: After all fixes applied

---

**Report Generated By**: @architecture_compliance_agent
**Next Agent**: @task_planning_agent (when PLANNER = active)
'''
    
    # Fill in the template with actual analysis
    filled_report = workplace_template.format(
        timestamp=timestamp,
        compliance_score=analysis_results["compliance_score"],
        total_violations=analysis_results["total_violations"],
        controller_violations=analysis_results["controller_violations"],
        factory_analysis=analysis_results["factory_analysis"],
        cache_violations=analysis_results["cache_violations"],
        files_analyzed=analysis_results["files_analyzed"]
    )
    
    Write(
        file_path="dhafnck_mcp_main/docs/architecture/workplace.md",
        content=filled_report
    )
    
    print(f"📝 Created workplace.md with checkpoints at {timestamp}")
```

### Phase 3: Continuous Analysis with Checkpoint Updates

```python
def update_checkpoint(agent_name, new_status):
    """Update a specific agent's checkpoint status"""
    
    workplace = Read(file_path="dhafnck_mcp_main/docs/architecture/workplace.md")
    
    # Update the checkpoint for the specified agent
    lines = workplace.split('\n')
    for i, line in enumerate(lines):
        if f"**{agent_name.upper()}**" in line and "|" in line:
            parts = line.split('|')
            if new_status == "active":
                parts[2] = " active "
                parts[3] = " ✅ "
            elif new_status == "complete":
                parts[2] = " complete "
                parts[3] = " ✔️ "
            elif new_status == "waiting":
                parts[2] = " waiting "
                parts[3] = " ⏸️ "
            elif new_status == "skip":
                parts[2] = " skip "
                parts[3] = " ⏭️ "
            
            lines[i] = '|'.join(parts)
            break
    
    updated_content = '\n'.join(lines)
    
    Write(
        file_path="dhafnck_mcp_main/docs/architecture/workplace.md",
        content=updated_content
    )
    
    print(f"✅ Updated {agent_name} checkpoint to: {new_status}")

def analyze_and_update():
    """Run analysis and update workplace with results"""
    
    print("🔄 Running architecture analysis...")
    
    # Perform actual analysis
    controller_analysis = analyze_controllers()
    factory_analysis = analyze_factories() 
    cache_analysis = analyze_cache_invalidation()
    
    # Calculate metrics
    total_violations = (
        controller_analysis["violations"] + 
        factory_analysis["violations"] + 
        cache_analysis["violations"]
    )
    
    compliance_score = max(0, 100 - (total_violations * 1.1))
    
    analysis_results = {
        "compliance_score": compliance_score,
        "total_violations": total_violations,
        "controller_violations": controller_analysis["details"],
        "factory_analysis": factory_analysis["details"],
        "cache_violations": cache_analysis["details"],
        "files_analyzed": controller_analysis["files_scanned"] + factory_analysis["files_scanned"]
    }
    
    # Create/update workplace with results
    create_workplace_with_checkpoints(analysis_results)
    
    return compliance_score, total_violations

def analyze_controllers():
    """Analyze controller layer compliance"""
    violations = []
    files_scanned = 0
    violation_details = []
    
    controller_path = Path('src/fastmcp/task_management/interface/controllers')
    
    for controller_file in controller_path.glob('*.py'):
        files_scanned += 1
        content = controller_file.read_text()
        
        # Check for violations
        if 'from infrastructure.database import' in content:
            violations.append(f"{controller_file.name}: Direct DB import")
            violation_details.append(f"- {controller_file.name} (Direct database access)")
        if 'from infrastructure.repositories import' in content:
            violations.append(f"{controller_file.name}: Direct repo import")
            violation_details.append(f"- {controller_file.name} (Direct repository import)")
        if 'SessionLocal()' in content:
            violations.append(f"{controller_file.name}: Creates DB session")
            violation_details.append(f"- {controller_file.name} (Creates database session)")
    
    return {
        "files_scanned": files_scanned,
        "violations": len(violations),
        "details": '\n'.join(violation_details) if violation_details else "- None found"
    }

def analyze_factories():
    """Analyze factory pattern implementation"""
    factory_path = Path('src/fastmcp/task_management/infrastructure/repositories')
    factory_files = list(factory_path.glob('*factory.py'))
    
    working_factories = 0
    broken_details = []
    files_scanned = len(factory_files)
    
    for factory_file in factory_files:
        content = factory_file.read_text()
        
        # Check if factory checks environment
        has_env_check = "os.getenv('ENVIRONMENT'" in content
        has_db_check = "os.getenv('DATABASE_TYPE'" in content
        has_redis_check = "os.getenv('REDIS_ENABLED'" in content
        
        if not (has_env_check and has_db_check and has_redis_check):
            broken_details.append(f"- {factory_file.name} (Missing environment checks)")
        else:
            working_factories += 1
    
    return {
        "files_scanned": files_scanned,
        "violations": len(factory_files) - working_factories,
        "details": f"- {len(factory_files)} total factories\n- {working_factories} working correctly\n- {len(factory_files) - working_factories} need fixes"
    }

def analyze_cache_invalidation():
    """Analyze cache invalidation implementation"""
    repo_path = Path('src/fastmcp/task_management/infrastructure/repositories')
    
    total_methods = 32  # Known mutation methods
    methods_with_invalidation = 0
    missing_details = []
    
    mutations_needing_cache = [
        "create_task", "update_task", "delete_task",
        "create_project", "update_project", "delete_project",
        "create_context", "update_context", "delete_context"
    ]
    
    for repo_file in repo_path.rglob('*repository.py'):
        content = repo_file.read_text()
        
        for mutation in mutations_needing_cache:
            if f"def {mutation}" in content:
                if 'invalidate' not in content[content.index(f"def {mutation}"):content.index(f"def {mutation}") + 500]:
                    missing_details.append(f"- {mutation} in {repo_file.name}")
                else:
                    methods_with_invalidation += 1
    
    return {
        "files_scanned": len(list(repo_path.rglob('*repository.py'))),
        "violations": total_methods - methods_with_invalidation,
        "details": '\n'.join(missing_details[:10]) if missing_details else "- None (all have invalidation)"
    }
```

### Phase 4: Main Loop with Checkpoint Control

```python
def main_analyze_loop():
    """Main analysis loop with checkpoint control"""
    
    analysis_run = 1
    max_runs = 50
    
    while analysis_run <= max_runs:
        print(f"\n{'='*60}")
        print(f"🔍 Analysis Run #{analysis_run}")
        print(f"{'='*60}")
        
        # Check if it's our turn
        if not check_my_turn():
            print("⏸️ Not analyze agent's turn. Waiting 60 seconds...")
            time.sleep(60)
            continue
        
        # Set our status to active
        print("✅ Analyze agent active - running analysis")
        
        # Run analysis
        compliance_score, total_violations = analyze_and_update()
        
        print(f"📊 Analysis Results:")
        print(f"   - Compliance Score: {compliance_score}/100")
        print(f"   - Total Violations: {total_violations}")
        
        # Check if we're done
        if compliance_score >= 100:
            print("🎉 TARGET ACHIEVED: 100/100 Compliance!")
            
            # Update final report
            update_checkpoint("ANALYZE", "complete")
            
            print("✅ Analysis complete - system is compliant!")
            break
        
        # Hand off to planner
        print("\n🔄 Analysis complete - activating PLANNER agent")
        update_checkpoint("ANALYZE", "complete")
        update_checkpoint("PLANNER", "active")
        
        print("⏸️ Analyze agent going to sleep...")
        print("   Will reactivate after REVIEW completes")
        
        # Wait for our next turn (after review)
        while True:
            time.sleep(60)  # Check every minute
            
            workplace = Read(file_path="dhafnck_mcp_main/docs/architecture/workplace.md")
            
            # Check if review is done and we should reanalyze
            if "**REANALYZE** | active" in workplace or "**ANALYZE** | active" in workplace:
                print("\n✅ Reanalysis requested - starting new analysis run")
                analysis_run += 1
                
                # Reset checkpoints for new cycle
                update_checkpoint("ANALYZE", "active")
                update_checkpoint("PLANNER", "waiting")
                update_checkpoint("CODE", "waiting")
                update_checkpoint("TEST", "waiting")
                update_checkpoint("REVIEW", "waiting")
                update_checkpoint("REANALYZE", "waiting")
                break
            
            # Check if review marked us complete
            if "**ANALYZE** | complete" in workplace and compliance_score >= 100:
                print("✅ System fully compliant - analyze agent done!")
                return
    
    print("⚠️ Maximum analysis runs reached. Manual intervention needed.")

# Execute the main loop
main_analyze_loop()

print("🏁 Analyze agent workflow complete")
```

## 📊 Checkpoint Management

The analyze agent:

1. **Checks Checkpoint** - Only works when status is "active"
2. **Updates Workplace** - Writes analysis results and issues
3. **Controls Flow** - Updates checkpoints to activate next agent
4. **Waits for Turn** - Sleeps when not active
5. **Reanalyzes** - Reactivates after review completes

## 🎯 Success Criteria

- ✅ Checkpoint system implemented in workplace.md
- ✅ Agent only works when checkpoint is "active"
- ✅ Updates checkpoint to pass control to next agent
- ✅ Waits patiently when not its turn (60-second checks)
- ✅ Reanalyzes after review cycle completes
- ✅ Clear workflow: ANALYZE → PLANNER → CODE+TEST → REVIEW → REANALYZE

**⚠️ CRITICAL**: The analyze agent respects workflow order through checkpoints, ensuring coordinated multi-agent operation.