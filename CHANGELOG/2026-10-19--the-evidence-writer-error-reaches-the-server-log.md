The evidence writer's error reaches the server log

`POST /api/v2/tasks/{id}/evidence` maps every writer failure to one flat 500
("Failed to record evidence") and drops the error, so a failed completion leaves no record of why.
Measured 2026-10-18: fe-dev's two completion attempts 500'd on the live hub (routes:96) and the
writer's error was unrecoverable from outside - neither payload nor task state reproduced it against
the same server minutes later.

The adapter now logs every writer failure except the duplicate refusal the route turns into a 409
(that one is the rule working, not a fault), with the task id and the error, through the package's
existing `log` convention.

Changed files:
- `agenthub_go/fastmcp/server/httpapp/task_event_controller.go` - the four-line capture in
  `taskEvidenceWriterAdapter.RecordEvidence`; no behavior change, the same error is still returned.

Verified: the pg-backed evidence suite (`task_evidence_pg_test.go`) passes unchanged, including the
409 duplicate and the concurrent-duplicate cases.
