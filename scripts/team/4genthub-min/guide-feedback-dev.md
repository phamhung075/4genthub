## Guide: feedback-dev (seat feedback channel)

**You own NEXT_GEN directive H, end to end:** the channel where seats report the constraints and improvements they hit while using 4genthub and OpenRig, so the friction stops dying in a transcript. Read `agenthub_go/NEXT_GEN.md`, section (H), first.

### Tools you use, and for what
- `read` `NEXT_GEN.md` (H); `edit`/`bash` across `agenthub_go` and `agenthub-frontend`; `deepseek_agent` for drafting handler and page tests.
- 4genthub tools: the common loop; record the design decisions of the channel in `manage_context`.

### Workflow
1. Task first. Build in this order: the `seat_feedback` table (per user and per machine; ORM struct, DDL in the project SQL, the DDL-versus-struct test in the same commit, no CASCADE), then `POST /api/v2/openrig/feedback` (machine token) and `GET /api/v2/openrig/feedback` (user token, scoped by the caller's user id), then the MCP tool, then the page.
2. A failure the page cannot load must be shown as a failure, not as an empty list.
3. Checks: Go as go-dev; frontend as fe-dev; the schema upgrade test for the new table.
4. Complete the task with the hash and the measured counts; tell the lead.

### Do not
Let one user read another's feedback. Show an empty state when the request failed.
