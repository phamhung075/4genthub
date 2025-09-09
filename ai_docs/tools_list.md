Task(description: string, prompt: string, subagent_type: string): void
Purpose: Launch specialized AI agents for complex, multi-step tasks
autonomously

Bash(command: string, description?: string, run_in_background?:
boolean, timeout?: number): void
Purpose: Execute bash commands in a persistent shell session with
optional timeout

Glob(pattern: string, path?: string): void
Purpose: Fast file pattern matching that works with any codebase size

Grep(pattern: string, path?: string, glob?: string, type?: string,
output_mode?: string, -A?: number, -B?: number, -C?: number, -i?:
boolean, -n?: boolean, multiline?: boolean, head_limit?: number): void
Purpose: Powerful search tool built on ripgrep for searching file
contents

ExitPlanMode(plan: string): void
Purpose: Exit plan mode and prompt user for approval when ready to code

Read(file_path: string, limit?: number, offset?: number): void
Purpose: Read files from the local filesystem including images, PDFs,
and notebooks

Edit(file_path: string, old_string: string, new_string: string,
replace_all?: boolean): void
Purpose: Perform exact string replacements in files

MultiEdit(file_path: string, edits: Array<{old_string: string,
new_string: string, replace_all?: boolean}>): void
Purpose: Make multiple edits to a single file in one operation

Write(file_path: string, content: string): void
Purpose: Write a file to the local filesystem

NotebookEdit(notebook_path: string, new_source: string, cell_id?:
string, cell_type?: string, edit_mode?: string): void
Purpose: Replace contents of specific cells in Jupyter notebooks

WebFetch(url: string, prompt: string): void
Purpose: Fetch content from URLs and process with AI model

TodoWrite(todos: Array<{content: string, status: string, activeForm:
string}>): void
Purpose: Create and manage structured task lists for coding sessions

WebSearch(query: string, allowed_domains?: string[], blocked_domains?:
string[]): void
Purpose: Search the web and use results to inform responses

BashOutput(bash_id: string, filter?: string): void
Purpose: Retrieve output from running or completed background bash
shells

KillBash(shell_id: string): void
Purpose: Terminate a running background bash shell by its ID

ListMcpResourcesTool(server?: string): void
Purpose: List available resources from configured MCP servers

ReadMcpResourceTool(server: string, uri: string): void
Purpose: Read specific resources from MCP servers

mcp__dhafnck_mcp_http__validate_token(token: string): void
Purpose: Validate an authentication token

mcp__dhafnck_mcp_http__get_rate_limit_status(token: string): void
Purpose: Get rate limit status for a token

mcp__dhafnck_mcp_http__revoke_token(token: string): void
Purpose: Revoke an authentication token

mcp__dhafnck_mcp_http__get_auth_status(): void
Purpose: Get authentication system status

mcp__dhafnck_mcp_http__generate_token(): void
Purpose: Generate new secure authentication token (deprecated)

mcp__dhafnck_mcp_http__manage_connection(include_details?: boolean,
user_id?: string): void
Purpose: Basic health check endpoint for system monitoring

mcp__sequential-thinking__sequentialthinking(thought: string,
nextThoughtNeeded: boolean, thoughtNumber: number, totalThoughts:
number, isRevision?: boolean, revisesThought?: number,
branchFromThought?: number, branchId?: string, needsMoreThoughts?:
boolean): void
Purpose: Dynamic problem-solving through flexible chain of thought
reasoning

mcp__shadcn-ui-server__list-components(): void
Purpose: List available shadcn/ui components

mcp__shadcn-ui-server__get-component-docs(component: string): void
Purpose: Get documentation for specific shadcn/ui components

mcp__shadcn-ui-server__install-component(component: string, runtime?:
string): void
Purpose: Install shadcn/ui components

mcp__shadcn-ui-server__list-blocks(): void
Purpose: List available shadcn/ui blocks

mcp__shadcn-ui-server__get-block-docs(block: string): void
Purpose: Get documentation for specific shadcn/ui blocks

mcp__shadcn-ui-server__install-blocks(block: string, runtime?: string):
void
Purpose: Install shadcn/ui blocks

mcp__ide__getDiagnostics(uri?: string): void
Purpose: Get language diagnostics from VS Code

mcp__ide__executeCode(code: string): void
Purpose: Execute Python code in Jupyter kernel

mcp__browsermcp__browser_navigate(url: string): void
Purpose: Navigate browser to a URL

mcp__browsermcp__browser_go_back(): void
Purpose: Navigate browser to previous page

mcp__browsermcp__browser_go_forward(): void
Purpose: Navigate browser to next page

mcp__browsermcp__browser_snapshot(): void
Purpose: Capture accessibility snapshot of current browser page

mcp__browsermcp__browser_click(element: string, ref: string): void
Purpose: Click on web page elements

mcp__browsermcp__browser_hover(element: string, ref: string): void
Purpose: Hover over web page elements

mcp__browsermcp__browser_type(element: string, ref: string, text:
string, submit: boolean): void
Purpose: Type text into editable web elements

mcp__browsermcp__browser_select_option(element: string, ref: string,
values: string[]): void
Purpose: Select options in dropdowns

mcp__browsermcp__browser_press_key(key: string): void
Purpose: Press keyboard keys in browser

mcp__browsermcp__browser_wait(time: number): void
Purpose: Wait for specified time in seconds

mcp__browsermcp__browser_get_console_logs(): void
Purpose: Get console logs from browser

mcp__browsermcp__browser_screenshot(): void
Purpose: Take screenshot of current browser page