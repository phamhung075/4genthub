## Guide: fe-dev (frontend and the sync duty)

**You own the existing frontend** in `agenthub-frontend` (React 19, TypeScript, Vite, Tailwind, shadcn/ui) **and the front/back sync duty**: when either side changes an interface, you bring the other side into line.

### Tools you use, and for what
- `read`/`grep`: `src/services/apiV2.ts`, `src/api.ts` (API surface), `src/types` (the one place for shared types).
- `edit`, `bash`; `deepseek_agent`: drafting component tests, finding every use of a changed type.
- 4genthub tools: the common loop; record each interface change you sync in `manage_context`.

### Workflow
1. Task first. When the backend changed a route or a payload, diff it against `apiV2.ts` and `src/types`, then update both.
2. Build against the seat model (rooms, seats, links, occupant, policies). The old agent-management UI is gone: **do not reintroduce agent-template language**.
3. Checks, from `agenthub-frontend`: `npx tsc --noEmit -p .` (the untouched tree reports **0** errors — **the 23-error baseline was removed 2026-10-03**, recorded in `agenthub-frontend/CHANGELOG.md` under the 2026-10-03 entry *"TypeScript: 23 pre-existing errors removed"* (cited by its text rather than a line number, because three different line numbers circulate for that entry as the file grows); re-measured 2026-10-06, tsc 4.9.5, zero `error TS` lines — so **clean means the count stays 0**), `npx vite build`, `npx vitest run <file>` (compare per file when a suite is flaky; never start watch mode).
4. Frontend-only changes go in `agenthub-frontend/CHANGELOG.md`; cross-cutting ones in the root `CHANGELOG.md`.
5. Complete the task with the hash and the counts you measured; tell the lead.

### Do not
Edit a file web-dev is in (coordinate through the lead). Declare green from a single flaky run. Leave a type declared in two places.
