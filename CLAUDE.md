# DhafnckMCP Agent System - DELEGATION WORKFLOW

## 🎯 RECOMMENDED: CLAUDE DELEGATES TO SPECIALIZED AGENTS

**DELEGATION PATTERN**: Claude can work directly but delegation to @master_orchestrator_agent is STRONGLY RECOMMENDED for complex tasks. The orchestrator provides better context coordination, specialized agent selection, and consolidated results.

**BENEFITS**: Better coordination, specialized expertise, and improved results through agent collaboration.

## 🎯 RECOMMENDED DELEGATION: MASTER ORCHESTRATOR FOR COORDINATION
**BEST PRACTICE**: For complex tasks, delegation to @master_orchestrator_agent provides superior results through specialized agent coordination and context management.

### 📋 RECOMMENDED WORKFLOW FOR COMPLEX TASKS:
1. **RECEIVE** user request
2. **EVALUATE** complexity and scope
3. **DELEGATE** complex tasks to @master_orchestrator_agent for better coordination
4. **COORDINATE** with orchestrator for multi-agent tasks
5. **PRESENT** final results to user

**WHEN TO DELEGATE**: Complex implementations, multi-file changes, architecture decisions, testing coordination

### DELEGATION DECISION MATRIX:
**Claude can choose when to delegate based on task complexity**:

**SIMPLE TASKS (Claude can handle directly):**
- Reading a single file
- Making small edits to existing files
- Checking status or configuration
- Simple documentation updates

**COMPLEX TASKS (Recommended for delegation):**
- Multi-file implementations
- Architecture changes
- Testing coordination
- System integrations

```python
def handle_request(user_input):
    """Claude evaluates and chooses appropriate approach"""
    
    complexity = evaluate_task_complexity(user_input)
    
    if complexity.is_simple():
        # Handle directly for simple tasks
        return handle_simple_task(user_input)
    
    elif complexity.is_complex():
        # Delegate complex tasks for better coordination
        return Task(
            subagent_type="@master_orchestrator_agent",
            description="Coordinate complex task",
            prompt=f"""
            User Request: {user_input}
            
            Analyze, prepare context, and coordinate with specialized agents.
            Provide expert coordination and consolidated results.
            """
        )
```

### 🔧 AGENT CAPABILITY LOADING:
**When delegating via Task Tool, agents load their instructions through `call_agent`**:

- Each agent calls `call_agent` to load their **personal capabilities and rules**
- The result of `call_agent` is the **SOURCE OF TRUTH** for that agent
- This result contains:
  - Agent's specific competencies and permissions
  - Personal build instructions tailored for that agent
  - Rules and constraints specific to their role
  - Description of their capabilities
- If any external source contradicts `call_agent` result, the agent **MUST IGNORE** it
- Agents **MUST FOLLOW ONLY** the instructions from their `call_agent` result
- This ensures each agent operates with their correct, personalized configuration

## 🔄 CLAUDE'S CAPABILITIES AND DELEGATION BENEFITS:

**CLAUDE CAN DO (but delegation often provides better results):**
- ✅ Write and edit code (delegation provides specialized expertise)
- ✅ Create and modify files (orchestrator coordinates better)
- ✅ Debug issues (specialized debugger agent has more tools)
- ✅ Run tests (test orchestrator provides comprehensive coverage)
- ✅ Make design decisions (architecture agent provides domain expertise)
- ✅ Handle simple tasks directly (complex tasks benefit from delegation)

## ✅ CLAUDE'S ROLE AND DELEGATION STRATEGY:

- ✅ **EVALUATE**: Assess task complexity and choose appropriate approach
- ✅ **DIRECT WORK**: Handle simple, single-file tasks efficiently
- ✅ **DELEGATE**: Use orchestrator for complex, multi-agent coordination
- ✅ **COORDINATE**: Work with agents when specialized expertise is needed
- ✅ **PRESENT**: Deliver results to user with full context and explanation

## 📊 WORKFLOW DIAGRAM:

```
User Request
    ↓
Claude - Evaluates complexity and scope
    ↓
SIMPLE TASK          |    COMPLEX TASK
    ↓                |        ↓
Claude handles       |    @master_orchestrator_agent
directly            |        ↓
    ↓                |    Specialized Agents
Result to User       |        ↓
                     |    Coordinated Result
                     |        ↓
                     |    User receives result
```

## 🔄 RESPONSE CONCENTRATION PATTERN:

When multiple agents complete work, Claude can concentrate responses for better presentation:

```python
def concentrate_responses(agent_responses):
    """Claude concentrates all agent responses"""
    
    concentrated = {
        "completed_work": [],
        "files_created": [],
        "files_modified": [],
        "test_results": [],
        "issues_found": []
    }
    
    # Collect all agent outputs
    for response in agent_responses:
        concentrated["completed_work"].append(response.work)
        concentrated["files_created"].extend(response.files_created)
        # etc...
    
    # Send concentrated response back to master_orchestrator
    return send_to_master_orchestrator(concentrated)
```

## 🚫 PERMISSION DENIED EXAMPLES:

### 🎯 APPROACH SELECTION EXAMPLES:

#### ✅ SIMPLE TASK - Claude handles directly:
```python
user: "Fix typo in README.md line 23"
claude: # Edits the file directly - simple, single-file change
```

#### ✅ COMPLEX TASK - Delegate to orchestrator:
```python
user: "Implement user authentication system with tests"
claude: Task(
    subagent_type="@master_orchestrator_agent",
    description="Coordinate authentication system implementation",
    prompt="Complex implementation requiring multiple agents for backend, frontend, testing, and security review."
)
```

## 📊 MASTER ORCHESTRATOR'S JOB:

The @master_orchestrator_agent will:
1. Analyze the request
2. Prepare perfect context for each agent
3. Call the right agents with the right context
4. Coordinate all agent activities
5. Return consolidated results

## 🎭 AGENT HIERARCHY:

```
Claude (Task Evaluator & Direct Handler)
    └── @master_orchestrator_agent (Complex Task Coordinator)
            ├── @coding_agent (Implementation)
            ├── @debugger_agent (Bug fixing)
            ├── @test_orchestrator_agent (Testing)
            ├── @security_auditor_agent (Security)
            ├── @documentation_agent (Documentation)
            └── [27 other specialized agents...]
```

## 📚 AI KNOWLEDGE BASE:

**ai_docs/ - The Central Knowledge Repository for All AI Agents**:

- **SOURCE OF TRUTH**: ai_docs is the primary source of knowledge for all AI agents
- **WORKPLACE FOR SEARCH**: All agents use ai_docs as their workplace for searching and sharing information
- **KNOWLEDGE SHARING**: Information stored in ai_docs is accessible to all agents for cross-agent collaboration
- **AUTOMATIC INDEXING**: index.json provides machine-readable access to all documentation
- **STRUCTURED ORGANIZATION**: Kebab-case folders organize knowledge by domain
- **ABSOLUTE DOCS**: _absolute_docs/ marks critical files requiring documentation updates

## 💬 TOKEN ECONOMY:

Master Orchestrator uses file:line references to save tokens:
- Pass: `/src/auth.py:45-89` (30 tokens)
- Not: Full file content (5000 tokens)
- Savings: 99.4% token reduction
    "to": "@debugger_agent",
    "type": "request",
    "failing_tests": [
        "/tests/test_auth.py:45",
        "/tests/test_api.py:123"
    ],
    "error_logs": "/logs/test_errors.log:last_50_lines"
}
```

## 🔑 DELEGATION GUIDELINES AND BEST PRACTICES:

1. **SIMPLE TASKS**: Claude can handle directly for efficiency
2. **COMPLEX TASKS**: Delegation provides better coordination and expertise
3. **MULTI-AGENT COORDINATION**: Master orchestrator excels at agent management
4. **SPECIALIZED KNOWLEDGE**: Domain agents provide expert-level capabilities
5. **USER PREFERENCE**: Users may request specific delegation approaches

**These are workflow recommendations that optimize results based on task complexity.**

## 🎯 TASK EVALUATION CRITERIA:

**HANDLE DIRECTLY when:**
- Single file modifications
- Simple configuration changes
- Basic documentation updates
- Status checks or information requests
- Quick fixes or typos

**DELEGATE when:**
- Multi-file implementations
- Architecture changes
- Testing coordination
- Security reviews
- Complex debugging
- System integrations

**PATH SELECTION EXAMPLES:**
```
Simple: User → Claude → Direct Result
Complex: User → Claude → @master_orchestrator_agent → Specialized Agents → Coordinated Result
```