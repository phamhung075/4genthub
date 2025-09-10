# DhafnckMCP Maximum Performance Parallel Execution

## 🎯 MASTER ORCHESTRATOR AGENT - PRIMARY ENTRY POINT
**CRITICAL**: ALL user requests MUST FIRST go through @master_orchestrator_agent

### 📋 PRIMARY DELEGATION RULE
**ALWAYS** call @master_orchestrator_agent FIRST for ANY user request:

```python
def handle_any_user_request(user_input):
    """ALL requests must go through master orchestrator first"""
    
    # STEP 1: ALWAYS call master_orchestrator_agent FIRST
    Task(
        subagent_type="master-orchestrator-agent",
        description="Process and delegate user request",
        prompt=f"""
        User Request: {user_input}
        
        As the Master Orchestrator, you must:
        1. Analyze and understand the user's request
        2. Reformat the request for optimal delegation
        3. Identify the workflow phase needed
        4. Determine which agents are required
        5. Create a delegation plan
        6. For complex requests: Call @task_planning_agent FIRST
        7. For specialized needs: Delegate to appropriate specialist agents
        8. Provide document paths to economize tokens
        9. Monitor and coordinate all agent activities
        
        You are the CHEF of all agents - orchestrate them efficiently!
        """
    )
```

### 🔄 Master Orchestrator Workflow
```python
def master_orchestrator_process(user_request):
    """Master Orchestrator is the chef - manages all agents"""
    
    # Step 1: Master Orchestrator analyzes request
    analysis = analyze_request(user_request)
    
    # Step 2: Priority - Task Planning for complex requests
    if is_complex_request(analysis):
        # PRIORITY: Call task_planning_agent first
        Task(
            subagent_type="task-planning-agent",
            description="Create detailed task breakdown",
            prompt=f"Break down this complex request into tasks: {analysis}"
        )
    
    # Step 3: Delegate with file context (economize tokens)
    if existing_files_relevant(analysis):
        # Send file paths with specific line numbers
        context = {
            "task": analysis.task,
            "existing_files": [
                "/src/auth.py:45-89",      # Just the auth function
                "/tests/test_auth.py:12-34" # Just the relevant test
            ],
            "output_path": "/src/auth_enhanced.py"
        }
        return delegate_with_context(specialist_agent, context)
    
    # Step 4: Delegate to specialists for documentation
    if needs_documentation(analysis):
        # Call specialist to create document
        specialist_agent = identify_specialist(analysis)
        document_path = Task(
            subagent_type=specialist_agent,
            description="Create specialized document",
            prompt=f"Create document for: {analysis.topic}"
        )
        
        # Then delegate document path (economize tokens)
        return delegate_document_path(document_path)
    
    # Step 5: Orchestrate workflow phases
    workflow_phase = identify_phase(analysis)
    return orchestrate_phase(workflow_phase)
```

### 📁 TOKEN ECONOMY: File Path + Line References
**CRITICAL**: Master Orchestrator MUST use file:line references to save tokens

```python
# BAD - Sending full content (10,000+ tokens)
delegate_task(agent, {
    "code": entire_file_content,
    "tests": entire_test_content
})

# GOOD - Sending references (130 tokens - 98.7% reduction!)
delegate_task(agent, {
    "code": "/src/auth.py:45-89",        # Specific function
    "tests": "/tests/test_auth.py:12-34", # Specific test
    "docs": "/docs/auth.md"               # Full path for docs
})
```

#### File Reference Patterns:
1. **Full file**: `"/path/to/file.py"`
2. **Specific lines**: `"/path/to/file.py:45-67"`
3. **Multiple sections**: `["/src/auth.py:23-45", "/src/jwt.py:12-34"]`
4. **With purpose**: `{"path": "/src/auth.py:45-67", "purpose": "Fix login bug"}`

#### Context Sharing by Task Type:
```yaml
for_bug_fixes:
  provide:
    - error_file: "/src/app.py:234"           # Exact error line
    - stack_trace: "first_5_lines_only"       # Minimal trace
    - test_file: "/tests/test_app.py:45-67"   # Failing test only

for_feature_implementation:
  provide:
    - interface: "/src/types.ts:12-34"        # Interface definition
    - example: "/src/similar.py:56-78"        # Reference implementation
    - test_template: "/tests/template.py"     # Full path only

for_code_review:
  provide:
    - changed_files: 
        - "/src/auth.py:45-89"                # Changed function
        - "/src/user.py:123-145"              # Modified class
    - pr_summary: "Authentication refactor"   # Brief description

for_documentation:
  provide:
    - code_files: ["/src/auth.py", "/src/user.py"]  # Paths only
    - existing_docs: "/docs/auth.md:15-45"          # Section to update
    - examples: "/examples/auth_demo.py:10-25"      # Code example
```

#### Advanced Token-Saving Patterns:
```python
# Pattern 1: Conditional File References
if bug_fix_needed:
    context = {
        "error": "/src/auth.py:234",          # Just the error line
        "context": "/src/auth.py:230-240",    # Surrounding context
        "test": "/tests/test_auth.py:45-67"   # Related test
    }
elif new_feature:
    context = {
        "similar": "/src/existing_feature.py:100-200",  # Reference
        "output": "/src/new_feature.py"                 # Target path
    }

# Pattern 2: Multi-File Context with Line Ranges
complex_task_context = {
    "files": [
        {"path": "/src/api/auth.ts", "lines": "45-89", "purpose": "API endpoint"},
        {"path": "/src/components/Login.tsx", "lines": "15-45", "purpose": "UI component"},
        {"path": "/src/utils/jwt.ts", "lines": "10-30", "purpose": "Token handler"}
    ],
    "output_dir": "/src/enhanced/"
}

# Pattern 3: Incremental Context Loading
initial_context = {
    "overview": "/docs/architecture.md",      # Full doc for understanding
    "specific": "/src/core/engine.py:500-600" # Specific area to modify
}
# Agent can request more context if needed
additional_context = {
    "related": "/src/core/utils.py:200-250"   # Loaded only if required
}
```

#### Token Savings Calculator:
```
Full file content:     ~5,000 tokens per file
File path only:        ~20 tokens
Path with line range:  ~30 tokens
Savings:              99.4% reduction!

Example for 10 files:
- Full content:       50,000 tokens
- Path references:    300 tokens
- Savings:           49,700 tokens (99.4%)
```

### 💬 INTER-AGENT COMMUNICATION PATTERNS
**CRITICAL**: Agents communicate through Master Orchestrator using structured messages and file references

#### Communication Flow:
```
Agent A → Master Orchestrator → Agent B
        ↓                     ↓
   File Reference        File Reference
   + Message            + Context
```

#### Communication Message Structure:
```python
inter_agent_message = {
    "from_agent": "@coding_agent",
    "to_agent": "@test_orchestrator_agent",
    "message_type": "handoff",  # handoff, request, response, alert
    "priority": "high",
    "payload": {
        "task_completed": "Authentication implementation",
        "files_created": [
            "/src/auth/login.py:1-150",
            "/src/auth/jwt.py:1-89"
        ],
        "files_modified": [
            "/src/models/user.py:45-67"
        ],
        "next_action": "Create unit tests for authentication",
        "context": {
            "test_requirements": "/docs/test_spec.md:12-45",
            "api_contract": "/docs/api.yaml:100-150"
        }
    }
}
```

#### Communication Patterns:

##### Pattern 1: Handoff Communication
```python
# Agent A completes work and hands off to Agent B
handoff_message = {
    "from": "@system_architect_agent",
    "to": "@coding_agent",
    "type": "handoff",
    "completed_work": {
        "architecture_design": "/docs/architecture.md",
        "api_spec": "/docs/api_spec.yaml",
        "database_schema": "/docs/db_schema.sql"
    },
    "instructions": "Implement based on architecture design",
    "priority_files": [
        "/docs/architecture.md:45-89",  # Core components section
        "/docs/api_spec.yaml:12-67"     # Endpoint definitions
    ]
}
```

##### Pattern 2: Request Communication
```python
# Agent requests assistance from another agent
request_message = {
    "from": "@debugger_agent",
    "to": "@root_cause_analysis_agent",
    "type": "request",
    "issue": "Authentication fails intermittently",
    "relevant_files": [
        "/src/auth.py:234",              # Error location
        "/logs/error.log:last_100_lines", # Recent errors
        "/tests/test_auth.py:45-67"      # Failing test
    ],
    "urgency": "high",
    "expected_response": "root_cause_analysis"
}
```

##### Pattern 3: Broadcast Communication
```python
# Master Orchestrator broadcasts to multiple agents
broadcast_message = {
    "from": "@master_orchestrator_agent",
    "to": ["@coding_agent", "@test_orchestrator_agent", "@documentation_agent"],
    "type": "broadcast",
    "event": "feature_complete",
    "feature": "User Authentication",
    "files": {
        "implementation": "/src/auth/",
        "tests": "/tests/auth/",
        "docs": "/docs/auth.md"
    },
    "next_phase": "integration_testing"
}
```

##### Pattern 4: Alert Communication
```python
# Agent alerts about critical issue
alert_message = {
    "from": "@security_auditor_agent",
    "to": "@master_orchestrator_agent",
    "type": "alert",
    "severity": "critical",
    "issue": "SQL injection vulnerability detected",
    "location": "/src/database/queries.py:156",
    "requires_immediate_action": True,
    "suggested_agents": ["@debugger_agent", "@coding_agent"]
}
```

#### Asynchronous Communication Queue:
```python
class AgentCommunicationQueue:
    """Managed by Master Orchestrator"""
    
    def send_message(self, message):
        """Send message through orchestrator"""
        # Validate message structure
        validate_message(message)
        
        # Add metadata
        message["timestamp"] = now()
        message["message_id"] = generate_id()
        
        # Route through Master Orchestrator
        master_orchestrator.route_message(message)
        
    def batch_communicate(self, messages):
        """Send multiple messages efficiently"""
        batch = {
            "type": "batch",
            "messages": messages,
            "optimize_routing": True
        }
        master_orchestrator.process_batch(batch)
```

#### Communication Efficiency Rules:

1. **Always Use File References**:
```python
# BAD - Sending code content
{"code": full_file_content}  # 5000 tokens

# GOOD - Sending reference
{"code": "/src/file.py:45-89"}  # 30 tokens
```

2. **Structured Messages Only**:
```python
# BAD - Unstructured text
"Hey, I finished the auth code, please test it"

# GOOD - Structured message
{
    "type": "handoff",
    "completed": "authentication",
    "files": ["/src/auth.py"],
    "next": "testing"
}
```

3. **Batch Related Communications**:
```python
# BAD - Multiple individual messages
send_message(msg1)
send_message(msg2)
send_message(msg3)

# GOOD - Batched communication
batch_communicate([msg1, msg2, msg3])
```

4. **Use Message Types for Routing**:
```yaml
message_types:
  handoff: Direct transfer of work
  request: Asking for assistance
  response: Answering a request
  broadcast: Multi-agent notification
  alert: Critical issue notification
  status: Progress update
  complete: Task completion notice
```

#### Communication Examples by Phase:

##### Planning → Implementation:
```python
{
    "from": "@task_planning_agent",
    "to": "@coding_agent",
    "type": "handoff",
    "tasks": "/docs/task_breakdown.md",
    "priorities": ["auth", "database", "api"],
    "dependencies": "/docs/dependencies.json"
}
```

##### Implementation → Testing:
```python
{
    "from": "@coding_agent",
    "to": "@test_orchestrator_agent",
    "type": "handoff",
    "implemented_features": [
        "/src/auth/login.py",
        "/src/auth/logout.py"
    ],
    "test_requirements": "/docs/test_requirements.md:45-89",
    "coverage_target": "80%"
}
```

##### Testing → Debugging:
```python
{
    "from": "@test_orchestrator_agent",
    "to": "@debugger_agent",
    "type": "request",
    "failing_tests": [
        "/tests/test_auth.py:45",
        "/tests/test_api.py:123"
    ],
    "error_logs": "/logs/test_errors.log:last_50_lines"
}
```

### 🎯 MASTER ORCHESTRATOR - SINGLE ENTRY POINT
**CRITICAL**: ALL work MUST go through @master_orchestrator_agent FIRST

```python
# SIMPLE RULE: Always call Master Orchestrator first
Task(
    subagent_type="master-orchestrator-agent",
    description="Handle user request",
    prompt=user_request
)
# Master Orchestrator will handle ALL delegation internally
```

**That's it! The Master Orchestrator handles everything else.**

For detailed delegation patterns, see:
`dhafnck_mcp_main/agent-library/agents/master_orchestrator_agent/contexts/master_orchestrator_instructions.yaml`

## 🚨 IMPORTANT NOTE
All parallel execution patterns, delegation strategies, and agent cloning examples have been moved to the Master Orchestrator's instructions for better organization.

See: `dhafnck_mcp_main/agent-library/agents/master_orchestrator_agent/contexts/master_orchestrator_instructions.yaml`