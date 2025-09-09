Task(description: string, prompt: string, subagent_type: string): void
// Launch specialized AI agents for complex multi-step tasks


Bash(command: string, description?: string, run_in_background?:
boolean, timeout?: number): void
// Execute bash commands in a persistent shell session


Glob(pattern: string, path?: string): void
// Fast file pattern matching for finding files by name patterns


Grep(pattern: string, path?: string, output_mode?: string, glob?:
string, type?: string, ...options): void
// Powerful search tool using ripgrep for finding content in files


ExitPlanMode(plan: string): void
// Exit plan mode after presenting implementation plan for coding tasks


Read(file_path: string, limit?: number, offset?: number): void
// Read files from the filesystem including images, PDFs, and notebooks


Edit(file_path: string, old_string: string, new_string: string,
replace_all?: boolean): void
// Perform exact string replacements in files


MultiEdit(file_path: string, edits: Array<{old_string: string,
new_string: string, replace_all?: boolean}>): void
// Make multiple edits to a single file in one operation


Write(file_path: string, content: string): void
// Write a file to the filesystem (overwrites existing files)


NotebookEdit(notebook_path: string, new_source: string, cell_id?:
string, cell_type?: string, edit_mode?: string): void
// Edit specific cells in Jupyter notebooks


WebFetch(url: string, prompt: string): void
// Fetch web content and process it with an AI model


TodoWrite(todos: Array<{content: string, status: string, activeForm:
string}>): void
// Create and manage structured task lists for coding sessions


WebSearch(query: string, allowed_domains?: string[], blocked_domains?:
string[]): void
// Search the web for up-to-date information


BashOutput(bash_id: string, filter?: string): void
// Retrieve output from running or completed background bash shells


KillBash(shell_id: string): void
// Terminate a running background bash shell


mcp__sequential-thinking__sequentialthinking(thought: string,
nextThoughtNeeded: boolean, thoughtNumber: number, totalThoughts:
number, ...options): void
// Dynamic problem-solving through flexible chain of thought analysis


mcp__dhafnck_mcp_http__manage_task(action: string, git_branch_id?:
string, task_id?: string, title?: string, ...options): void
// Complete task lifecycle operations with vision system integration


mcp__dhafnck_mcp_http__manage_subtask(action: string, task_id?: string,
subtask_id?: string, title?: string, ...options): void
// Hierarchical task decomposition with automatic context updates


mcp__dhafnck_mcp_http__manage_context(action: string, level?: string,
context_id?: string, data?: string, ...options): void
// 4-tier hierarchical context management (Global → Project → Branch → 
Task)


mcp__dhafnck_mcp_http__manage_project(action: string, project_id?:
string, name?: string, description?: string, ...options): void
// Complete project lifecycle and multi-project orchestration


mcp__dhafnck_mcp_http__manage_git_branch(action: string, project_id?:
string, git_branch_id?: string, git_branch_name?: string, ...options):
void
// Git branch operations and task tree organization


mcp__dhafnck_mcp_http__manage_agent(action: string, project_id?:
string, agent_id?: string, name?: string, ...options): void
// Agent registration, assignment, and lifecycle management


mcp__dhafnck_mcp_http__validate_token(token: string): void
// Validate an authentication token


mcp__dhafnck_mcp_http__get_rate_limit_status(token: string): void
// Get rate limit status for a token


mcp__dhafnck_mcp_http__revoke_token(token: string): void
// Revoke an authentication token


mcp__dhafnck_mcp_http__get_auth_status(): void
// Get authentication system status


mcp__dhafnck_mcp_http__generate_token(): void
// Generate authentication token (deprecated - use API endpoint)


mcp__dhafnck_mcp_http__manage_connection(include_details?: boolean,
user_id?: string): void
// Basic health check for system monitoring


ListMcpResourcesTool(server?: string): void
// List available resources from configured MCP servers


ReadMcpResourceTool(server: string, uri: string): void
// Read specific resource from an MCP server


mcp__shadcn-ui-server__list-components(): void
// List available shadcn/ui components


mcp__shadcn-ui-server__get-component-docs(component: string): void
// Get documentation for a specific shadcn/ui component


mcp__shadcn-ui-server__install-component(component: string, runtime?:
string): void
// Install a shadcn/ui component


mcp__shadcn-ui-server__list-blocks(): void
// List available shadcn/ui blocks


mcp__shadcn-ui-server__get-block-docs(block: string): void
// Get documentation for a specific shadcn/ui block


mcp__shadcn-ui-server__install-blocks(block: string, runtime?: string):
void
// Install shadcn/ui blocks


mcp__ide__getDiagnostics(uri?: string): void
// Get language diagnostics from VS Code


mcp__ide__executeCode(code: string): void
// Execute Python code in Jupyter kernel


mcp__browsermcp__browser_navigate(url: string): void
// Navigate browser to a URL


mcp__browsermcp__browser_go_back(): void
// Navigate back in browser history


mcp__browsermcp__browser_go_forward(): void
// Navigate forward in browser history


mcp__browsermcp__browser_snapshot(): void
// Capture accessibility snapshot of current page


mcp__browsermcp__browser_click(element: string, ref: string): void
// Click on a web page element


mcp__browsermcp__browser_hover(element: string, ref: string): void
// Hover over a web page element


mcp__browsermcp__browser_type(element: string, ref: string, text:
string, submit: boolean): void
// Type text into an editable element


mcp__browsermcp__browser_select_option(element: string, ref: string,
values: string[]): void
// Select option(s) in a dropdown


mcp__browsermcp__browser_press_key(key: string): void
// Press a keyboard key


mcp__browsermcp__browser_wait(time: number): void
// Wait for specified time in seconds


mcp__browsermcp__browser_get_console_logs(): void
// Get browser console logs


mcp__browsermcp__browser_screenshot(): void
// Take a screenshot of the current browser page