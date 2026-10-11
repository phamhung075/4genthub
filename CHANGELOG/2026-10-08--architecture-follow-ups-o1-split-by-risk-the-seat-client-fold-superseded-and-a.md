## Architecture follow-ups: O1 split by risk, the seat-client fold superseded, and a wrong "skeleton" claim corrected

- **`syncing-seats-with-the-cloud.md` carries the client fold's interim wording (architect decision `ai_docs/architecture-design/decision-seat-client-fold.md`, 2026-10-08)** — the writer's held edit is released and landed, and it landed as a NOTE rather than a rewrite: one note near the top of the doc's script section says `openrig_seat_client.py` is retiring into `agenthub-client sync`, that `status` is already ported (`agenthub-client sync status <room>` is the same check), that `sync` and `watch` stay on the script until `agenthub-client sync rig` and `sync watch` are ported, and that **the script and its test are deleted in that commit**. **The six references the doc carried before this note are untouched; the note adds one of its own**, because they are accurate while it exists — the note names the destination and the interim path, and the six citations keep naming the thing that runs today. **Why it is an interim note rather than a claim:** folding was superseded, so the doc's references go wrong only when the port lands, and the note makes that moment explicit instead of leaving six citations reading as a destination.
- **O1 IS SPLIT** in `agenthub_go/NEXT_GEN.md`, because as written it was not additive. **O1a** (assigned) adds the
  `task_events` table, repository, recorder and read route only, with a may-touch and must-not-touch file list,
  a failing-first test, three negatives and the exact command. **O1b** moves every status write into one
  transaction with its event, which changes the status path. **O1c** removes `progress_history` (19 non-test
  Go files plus the details dialog) and lands with O8. go-dev2 was removed, so O2 and O4 are go-dev's.
- **THE FOLD OF `scripts/openrig_seat_client.py` INTO `openrig_seat_sync.py` IS SUPERSEDED**
  (`ai_docs/architecture-design/decision-seat-client-fold.md`). The script retires into `agenthub-client sync`
  verb by verb: `status` is already ported (`64f8ecde`), and `sync`/`watch` map to the declared `sync rig`/`sync
  watch`. No code changes. The note gives the writer interim doc wording and the retirement's acceptance.
- **CORRECTED:** the architecture doc and the orchestration decision note called `agenthub-client` a skeleton.
  It runs `sync status`, `sync pull`, `sync connector` and `bridge` in Go (`internal/clientsync`,
  `internal/clientbridge`). Which bridge the seats run today was not checked.
