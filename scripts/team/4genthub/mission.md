Standing mission: keep developing and maintaining 4genthub until the codebase is clean and complete. The owner's words: fix and continue the app to make it clean and perfect.

Architecture you work inside: the brain is 4genthub in the cloud, the office is OpenRig. 4genthub holds the seat definitions, modules, overlays, pins, tasks, subtasks and contexts. OpenRig holds the running room: your seat, its terminal, rig send and the queue. Keep it that way. Record every task, progress note and result in 4genthub through the MCP server in your settings, not only in chat or files, and read your instructions from the pulled seat files instead of copying them elsewhere. Do not store brain state in OpenRig, or run seat logic in the cloud.

What clean means here, as checks anyone can run:
- Go: gofmt reports nothing for the files you touched, go vet passes, go test passes for the affected packages.
- Frontend: no new TypeScript errors (23 old ones removed 2026-10-03; count now zero), vitest passes, vite build passes.
- Scripts: the script tests pass with --noconftest.
- No compatibility code, no dead code, no duplicated definitions, one source of truth per concept.
- Every change has a test and a changelog entry.

Backlog: agenthub_go/NEXT_GEN.md is the single backlog and decision record. Take items in this order unless the owner says otherwise:
1. Defects found by running the real stack (server on Postgres, a real OpenRig rig, the bridge). Reproduce first, then fix the cause.
2. The seat model: authoring screens for modules and seat types in the frontend, link deletion, room deletion, changing a seat's runtime or model, connecting the local send guard (seatcheck) to seats, per-machine tokens for the bridge, recording the pinned hash in the bridge status.
3. ~~Retire the old agenthub_main/agent-library and the call_agent path~~ **DONE** — the `agent-library`, the `call_agent` tool and its routes are removed on both the Go and Python sides; the seat model (`manage_seat` / `call_seat`) replaced them (`call_agent` survives only as a field of `manage_agent`).
4. Remaining Go port items in NEXT_GEN.md, and the known cleanups: the 23 TypeScript errors, the gofmt finding in the subtask controller.
Do not work on the GitHub pipeline test job; the owner decided against it.

Working loop for the lead: pick one backlog item, write its acceptance criteria, delegate to the right seat, require the evidence format of that seat, send the change to the review seat, then to the tester, then report. Keep several independent items in flight when seats are idle. Record each decision and finished item in NEXT_GEN.md.

Approval boundary: commit locally when the work is verified. Never push, tag or deploy on your own: a push to main deploys to production automatically. When one or more verified commits are ready, send the owner one message listing them with the evidence and ask for the push. The health version in agenthub_go/fastmcp/server/httpapp/http.go must be bumped in the same commit set so the deploy can be confirmed.

Report to the owner in plain language: what changed, what was verified, what is still open, and what needs a decision.
