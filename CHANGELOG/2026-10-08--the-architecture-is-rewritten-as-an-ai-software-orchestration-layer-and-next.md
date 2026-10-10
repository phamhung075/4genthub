## The architecture is rewritten as an AI software orchestration layer, and NEXT_GEN gains group O

- **WHAT CHANGED (docs only, no code).** `ai_docs/core-architecture/agenthub-system-architecture.md`
  is written new. The file of that name was deleted in `dad51589` and described the Python backend. It
  positions 4genthub as an orchestration layer (orchestrator, brain and worker seats, MCP task/subtask/context,
  git and tests, a validation gate with accept/reject/uncertain, an observable per-task state machine,
  resume/continue, project memory), with KPI = verified software per unit of human attention. Each part is
  labelled BUILT, PARTIAL or NEW with the file it rests on.
- **THE DECISION** is `ai_docs/architecture-design/decision-orchestration-layer.md`. Of three options
  (phases as statuses; an append-only `task_events` ledger with client-collected evidence and a two-stage
  gate; server-side orchestration), the ledger option is recommended because the gate then checks facts
  the agent did not write.
- **`agenthub_go/NEXT_GEN.md`**: a new "Orchestration layer" section with a built-versus-new table, and
  checklist group O (O1 ledger, O2 seat identity on MCP calls, O3 evidence, O4 acceptance criteria and
  resume, O5 gate in shadow mode, O6 enforcement, O7 routing and wake-on-open-work, O8 timeline and KPI
  panel, O9 owner decisions), each with an acceptance check.
- **THREE STATUS LINES CORRECTED, EACH MEASURED.** G7 becomes `[~]`, superseded by group O, and its
  recorded hook point (`HandleTaskCompleted`, `event_handler_initializer.go`) is marked deleted by
  `e1970dc5`. F2 changes from "queued" to "ported, not wired": `9924b1fc` holds the package, `go test` on it
  passes, and it has no importer outside its tests. F4 is noted as half built: the `policy` module kind
  exists and no usage-samples code exists in Go.
- **NOT VERIFIED HERE:** the Jev API facts carried over from G7 (recorded 2026-10-03) are to be
  re-verified against the live docs when O5 starts.
