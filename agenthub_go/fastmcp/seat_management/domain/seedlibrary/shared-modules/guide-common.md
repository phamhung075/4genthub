## Working procedure (every seat)

### How to call a tool
Write a JSON object to the device path `xd://mcp__<server>_<tool>`. Read the path first when unsure: the read returns the schema. Servers: `agenthub_http` (4genthub) and `deepseek`.

### The loop, in order
1. **Find your work.** `xd://mcp__agenthub_http_manage_task` with `{"action":"list","status":"todo","assignee":"@<your-seat>"}`, or `{"action":"next","git_branch_id":"<uuid>"}`. Search before you create: `{"action":"search","query":"<words>"}`.
2. **Create a task if none exists.** `{"action":"create","git_branch_id":"<uuid>","title":"<action-oriented title>","assignees":"@<your-seat>","description":"<what, acceptance criteria>"}`. Assignees use the `@seat-key` form (`@go-dev`, `@lead`). `git_branch_id` is the branch UUID, never a branch name.
3. **Start.** `{"action":"update","task_id":"<uuid>","status":"in_progress","details":"<what you are about to do>"}`. `details` is mandatory (10+ characters) whenever status or progress changes.
4. **Split multi-step work into subtasks.** `manage_subtask`: `{"action":"create","task_id":"<uuid>","title":"..."}`; progress with `{"action":"update","task_id":"...","subtask_id":"...","progress_notes":"<10+ chars>","progress_percentage":40}`; finish with `{"action":"complete",...,"completion_summary":"...","progress_notes":"...","impact_on_parent":"..."}`.
5. **Record what the next session needs.** `manage_context`: `{"action":"add_insight","level":"task","context_id":"<task_id>","content":"<finding or decision and why>","category":"technical","importance":"high"}`, or `"action":"add_progress"`. Write down decisions, surprises, measured numbers and open questions, not a diary.
6. **Do the work** (your seat's section below), then run the checks that match the change.
7. **Finish.** `{"action":"complete","task_id":"<uuid>","completion_summary":"<what changed, files, commit hash>","testing_notes":"<exact commands and their results>"}`. Report only what you ran.
8. **Hand off.** Tell the lead the commit hash or the file you wrote. You do not push.

### Offloading with deepseek_agent
Use it for bounded bulk work: searching many files, reading long logs, drafting tests or docs, mechanical edits, a first-pass analysis. Call `xd://mcp__deepseek_agent` with `{"prompt":"...","cwd":"/home/daihu/__projects__/4genthub"}`.

A good prompt names the exact files it may touch, the goal, the commands to run, the form of the answer, and ends with: "Report only what you actually ran and observed." Its git writes are refused (the result shows a `GitWrites` line), so ask for the change and apply or commit it yourself. Its file edits are not trusted: read the diff and rerun the checks before you count them as done. Run independent jobs in parallel. Do not offload a decision, a commit, a message to another seat, or anything touching secrets.

### Commits in the shared tree
Other seats edit the same tree. Commit by pathspec and do not stage first: `git commit -m "<type(scope): subject>" -- <paths>`. A new file is the one exception: `git add -N -- <new>` (intent-to-add), then the same pathspec commit. Just before committing, read `git status --porcelain -- <paths>` and `git diff HEAD -- <paths>`, and name every line. If a file holds a line that is not yours, hold that file until its owner commits. Never `git add .`, `-A` or `--amend`. Commit types: feat, fix, refactor, test, chore, style, ai_docs. Add ONE new file `CHANGELOG/<date>--<title>.md` (and update `TEST-CHANGELOG.md` when you change tests) in the same commit, and do not read the whole `CHANGELOG/` directory (`ls CHANGELOG | tail` lists the newest).

Run the script tests with the canonical command, always with `--noconftest`, from the repository root: `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q`. The flag is not decoration: the repository conftest reaches for PostgreSQL before every test, so without it the run HANGS rather than fails. **Read the exit code WITHOUT a pipe:** a pipeline reports the LAST command's status, so `... | tail` reports 0 whatever pytest said; the run is green only when pytest itself exits 0 and prints the count.

### Work first, docs when the task is done
**The work is build, improve, fix.** A seat spends its turns on that, not on prose about it. To share an idea, a finding, a ruling or a status, talk through the queue (`4genteam room queue create`); a doc is not the place for it. `CHANGELOG/` and `TEST-CHANGELOG.md` are written once, when the task is done, in the same commit as the code, and only when the change needs them: a plan, a finding, a ruling, a status and a re-measured number are not changes. Do not open a sweep or a reconcile task on docs unless the owner asks for one. A doc line that is wrong is corrected when you next change the code it describes.

### Think and reply in short pointers
**The owner's rule of 2026-10-15, read beside the work-first rule above.** Think in short pointers: a few terse lines naming the next step, the fact you rely on, the risk — no full reasoning, no restatement of the task, no alternative you will not take. A reply and a queue row give the result first, then at most five short lines: paths and ids, not paragraphs. Do not paste large tool output or a whole file into a thought or a row; quote only the lines that matter. Keep within your thinking level.

### Writing documentation
**A doc names no commit hash, no count, no line number and no measured-on-date note; it points to the code or the command that gives the answer.** One page per topic, updated in place, with no per-change entries. `CHANGELOG/` carries only what a user or operator would notice, and an entry there must record a change. A claim that needs a number states the command that prints it. Stop commits whose only purpose is to re-measure a number in a doc: delete the number instead. This page is one of the texts `guides.lock.json` pins, so a change here is re-recorded in that lock, in the same commit, or the lock's own tests go red.

### Writing style
Write replies in plain, direct prose. Put the answer first, then the reason, then the next step. Use literal wording: no greeting, no recap, no closing offer, no metaphor or flourish. Keep each sentence to one idea. Never drop `not`, `never`, `no` or `only`; keep numbers, units, code, commands, paths and error text exact. Use full sentences for a security warning, an irreversible action, an ordered procedure, and any question you ask. Apply the `token-economy` skill to everything you write: task text, changelogs, and every message to another seat (`4genteam send`, handoffs, replies, reports). Its rule for a seat message: the first line is the verdict or the ask, then the evidence as a path or command, then what you need from the reader. Quality comes first; the reader must be able to act without a follow-up.

### Startup and the approval gate
On a seat whose policy is not `builtin:yolo` — `locked`, `standard`, `open`, or no policy at all — the launch posture is `floor` and the runtime gates **every** tool call, the startup `4genteam whoami --json` included. The prompt has no timeout (`ask.timeout: 0` disables the auto-select), so an unanswered call waits rather than failing: if your first call never returns, that is the approval gate, a human must answer it, and a floor seat is not autonomous. Mechanism with file:line, and the two-line fix this repo already has a home for: `ai_docs/operations/seat-approval-and-the-startup-call.md`.

### When you are stuck or refused
A refused tool call is policy: do not retry or route around it. A failed 4genthub or deepseek call: send the lead the exact error and continue. Information only the owner can give, or anything touching production, quota or money: send it to the lead, who sends it to the principal.
