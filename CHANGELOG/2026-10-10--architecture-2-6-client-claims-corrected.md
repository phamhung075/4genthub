## §2.6 of the architecture doc claimed a client that does not exist

### Changed
- `ai_docs/core-architecture/agenthub-system-architecture.md` — **§2.6's client paragraph is corrected in place, beside the text it overtakes.** Four claims were
  false of this tree: the binary is **`4genteam`** (`cmd/4genteam`), not `cmd/agenthubclient`; the command surface is the registry of nine Go packages plus the
  deliberate `seatcheck` refusal (`agenthub_client/cmd/4genteam/main.go:98-108`); **`sync rig` / `sync bundle` / `sync switch` are built** (each answers with its own
  usage) and nothing points at the retired `openrig_seat_sync.py`; and **`4genteam evidence` does not exist** (`unknown command evidence`, no `clientevidence`
  package), so the command and JSON payload that paragraph carried describe an unbuilt design. `feedback` is built (`internal/clientfeedback/feedback.go`).
- The §2.14 status cell "the client binary is partial (2.6); the remaining sync verbs and `feedback` are still Python scripts" is corrected the same way.

### Verified
- Built and ran the client at the pin `80cc766`: `go build -o /tmp/4genteam ./cmd/4genteam` rc 0, then `--help`, `sync rig|bundle|switch --help`, `sync watch`,
  `feedback --help`, `seatcheck --help`. **The server half of the section is real** and was checked rather than assumed: `evidence_submitted` is in the kind
  vocabulary (`task_event_ensurer.go:59`), the domain entity (`task_event.go:45`) and the TableDef (`task_event_tables.go:40`, which also declares `subtask_id`).
- Not changed here, and named as unverified: the D1-D5 gate text and the Jev API shape are server-side claims this seat did not re-measure in this pass.
