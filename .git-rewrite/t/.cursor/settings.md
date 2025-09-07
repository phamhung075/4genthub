---
protect: true
alwaysApply: true
description: GLOBAL CONTEXT VARIABLES
tags: [RUNTIME-CONSTANTS, RUNTIME-VARIABLES, init, continue, P00-MT00, P00-MT01, P00-MT02, P00-MT03, P00-MT04, P00-MT05, P00-MT06, MASTER-TASK, GLOBAL-RULE, TASK-MANAGEMENT, AGENT-MANAGEMENT, tag1, tag2]
---

  

## Runtime Constants (Fixed Values)
#RUNTIME-CONSTANTS

CONTINUE_AUTOMATIC: ON              # Auto-continue tasks after completion
FORCE_CONTINUE_AUTOMATIC: ON       # Force automatic continuation without asking
USE_ABSOLUTE_PATH_FROM_ROOT_PROJECT: ON  # Always use absolute paths from project root
project_id: dhafnck_mcp_main
PROJECT_ROOT: /home/<username>/agentic-project
AI_DOCS_PATH: /home/<username>/agentic-project/dhafnck_mcp_main/docs
UI_DOCS_PATH: /home/<username>/agentic-project/dhafnck_mcp_main/docs/ui

  

## Runtime Variables (Dynamic Values)
#RUNTIME-VARIABLES

tools_count: 0                     # Current tool usage count (reset >20)
current_branch / git_branch_name: "$(git rev-parse --abbrev-ref HEAD)"
username: "$(whoami)"
project_path: "$(pwd)"


#init 
Initialize
1. demande project-id: 
	- actual root folder
	- other folder
2. git init
3. git add .
4. git commit -m "Initial : project-id"

Load: use manage_rule() load `rules/core/master-tasks.md` #MASTER-TASK 

#continue
1. Load: use manage_rule() load `rules/core/global_rule.md`  #GLOBAL-RULE 
2. Load: use manage_rule() load `rules/core/master-tasks.md` #TASK-MANAGEMENT  #AGENT-MANAGEMENT 
3. #P00-MT00 
4. #P00-MT01 
5. #P00-MT02 
6. #P00-MT03 
7. #P00-MT04 
8. #P00-MT05 
9. #P00-MT06
10. `call_agent` assigned to perform this task  
11. Update the context to complete the task  
12. Write documentation in the `docs` folder after completing the task

---

example document: [document.md](document.md)