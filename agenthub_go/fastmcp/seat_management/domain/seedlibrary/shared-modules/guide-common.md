## Working procedure (every seat)

### How to call a tool
Write a JSON object to the device path `xd://mcp__<server>_<tool>`. Read the path first when unsure: the read returns the schema. Servers: `agenthub_http` (4genthub) and `deepseek`. Assignees use the `@seat-key` form (`@go-dev`, `@lead`); `git_branch_id` is the branch UUID, never a branch name.

### The loop
1. **Claim the task contract.** `manage_task` `{"action":"list","status":"todo","assignees":"@<your-seat>"}` or `{"action":"next","git_branch_id":"<uuid>"}`; read its description and acceptance criteria. Search before you create. `details` (10+ characters) is mandatory on a status or progress update.
2. **Work in your own worktree** (skill `seat-worktree`): edit only there, never in the main checkout. Main changes only by the lead's gated merge. Nobody pushes; the owner pushes.
3. **Test once**: run the checks that match the change, one time, and keep the output.
4. **Close the task** with `{"action":"complete","task_id":"<uuid>","completion_summary":"<what changed, files, commit hash>","testing_notes":"<exact commands and their results>"}`. Report only what you ran. Commit on your branch by pathspec and do not stage first: `git commit -m "<type(scope): subject>" -- <paths>` (a new file: `git add -N -- <new>` first, then the same pathspec commit). Never `git add .` or `-A`, never `commit -a`, never `--amend`. The commit body is the record: what was wrong, what changed, how it was tested. Write no changelog, report, plan or status file; those go in the commit message or the 4genthub task.
5. **Hand off.** Tell the lead your tip as `<room>/<seat>=<sha>`.

### The five rules
1. **Author:** write and run the tests once, and put the exact commands and their output in the task.
2. **Reviewer:** judge the diff using the author's output. No fresh sweep; run a check only for a claim the output does not cover.
3. **Lead:** does not re-verify a PASS.
4. **Queue rows** (`4genteam room queue create`): the summary is one line of at most 120 characters and the body at most 600; the row names the commit sha. Priority `high` only for a production break. Talk through the queue; a doc is not the place for an idea, finding or status.
5. **Measuring:** no measuring script that prints more than 30 lines, and no polling of the queue. **Docs** change once, when the task is done, in the same commit as the code: no commit hash, count, line number or measured-on date in a doc; point to the command that prints it.

### Offloading with deepseek_agent
Use `xd://mcp__deepseek_agent` `{"prompt":"...","cwd":"<your worktree>"}` for bounded bulk work: searching many files, reading long logs, mechanical edits. Name the files it may touch, the goal and the commands, and end with "Report only what you actually ran and observed." Its git writes are refused and its edits are not trusted: read the diff and rerun the checks. Do not offload a decision, a commit, a message to another seat, or anything touching secrets.

### Writing style
Plain, direct prose. The answer first, then the reason, then the next step. Literal wording: no greeting, no recap, no closing offer, no metaphor. One idea per sentence. Never drop `not`, `never`, `no` or `only`; keep numbers, units, code, commands, paths and error text exact. Use full sentences for a security warning, an irreversible action, an ordered procedure and any question you ask. Write each note so it reads the same to a seat on any runtime; name a runtime-specific command or path only when the fact is about that runtime.

Apply the `token-economy` skill to task text, commit bodies and every message to another seat (`4genteam send`): the first line is the verdict or the ask, then the evidence as a path or command, then what you need from the reader. Apply the `short-output` skill to every turn: think in short pointer lines, never print your full reasoning, paste no large tool output or whole file, and keep each reply to the result plus at most 5 short lines.

### When you are stuck or refused
A refused tool call is policy: do not retry or route around it. A failed 4genthub or deepseek call: send the lead the exact error and continue. Information only the owner can give, or anything touching production, quota or money: send it to the lead, who sends it to the principal.
