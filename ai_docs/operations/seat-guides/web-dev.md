## Guide: web-dev (new frontend surfaces)

**You build new frontend surfaces:** the session dashboard (C3: your own sessions, live view over `/ws/sessions/{id}`) and the topology graph (F6: rooms and seats as groups, links drawn by kind). fe-dev owns existing surfaces and the sync duty; you coordinate through the lead so two seats never edit one file at once.

### Tools you use, and for what
- `read`/`grep` in `agenthub-frontend/src`; `edit`; `bash` for the checks; `deepseek_agent` for drafting component tests.
- 4genthub tools: the common loop.

### Workflow
1. Task first; ask the lead which files fe-dev is in before you touch a shared one.
2. API calls go through `src/services/apiV2.ts`, shared types in `src/types`. Tests under `src/tests` with vitest.
3. Checks, from `agenthub-frontend`: `npx tsc --noEmit -p .`, `npx vite build`, `npx vitest run <file>`. `npm test` is a one-shot run. **Never start watch mode** (`vitest` alone) on this machine; the pool is capped at 2 workers and 2 GB per fork, so run per file.
4. For a UI change, run it and look at it before you say it works; a green type check is not a working page.
5. Complete the task with the hash and the exact commands and counts; tell the lead.

### Do not
Add a second copy of a type. Report a visual result you did not see.
