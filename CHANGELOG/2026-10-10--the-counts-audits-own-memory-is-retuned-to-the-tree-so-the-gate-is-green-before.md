## The counts audit's own memory is retuned to the tree, so the gate is green before the seal

### Changed
- `scripts/COUNTS-AUDIT.py`, the `EXPECTED` block: **four numbers moved to what the TREE reads** — `httpapp` route registrations **123 -> 126**, seat tables **14 -> 16**, registered tables total **39 -> 41**, `SQL CREATE TABLE` statements **16 -> 18** — each with a comment in the form that block already uses, naming the cause and the commits rather than the delta alone.
- **The cause, named per number.** `a56e58a7` added ONE registration (the room-scoped seat-message POST, which is why the path carries the room) and `7c81981b` added TWO (the machine-authenticated GET pull and the POST ack) — so the route row was red from `a56e58a7`. The table rows moved with `7c81981b` (`seat_messages`) and `02bfd416` (`machine_edges`), each of which added its own DDL statement, which is why `seat tables`, `registered tables total` and `SQL CREATE TABLE statements` move together and neither alone can be retuned.
- **Why this file and not the document.** The audit reads THREE things: the tree, the document, and its own expectations. Pass 6 (`f6bcb56d`) made the document agree with the tree on all eleven rows and the gate still exited 1, because the third memory still held the pre-pass figures. A green document is not a green gate, and no edit to the document could have changed that.

### Verified
- **The four numbers are re-derived from the TREE, never from the document**, with the audit's own commands: `grep -rn 'mux.HandleFunc(' --include='*.go' fastmcp/server/httpapp | grep -v _test.go | wc -l` -> **126**; the depth-1 `{Name: ...}` count of `seatDatabaseTables` -> **16** (and **14** at `e6829b32`, the reading this retunes away from); the total follows as **20 + 3 + 16 + 2 = 41**; `grep -cE '^CREATE TABLE IF NOT EXISTS' seat_management_postgresql.sql` -> **18**.
- `python3 scripts/COUNTS-AUDIT.py` -> **exit 0**, and its report is `matches` on all eleven rows including the four retuned, with the fenced check still reporting no contradiction.
- **Control, because a retuned memory that can no longer go red would be worse than a red one:** `python3 scripts/COUNTS-AUDIT.py --self-test` -> `self-test: perturbed 'httpapp route registrations' by +1 -> tree exit 1, document exit 1 (PASS)`. It still fails when the world is perturbed.
- **Scope:** this file and this entry. `ai_docs/api-integration/surface-inventory.md` was NOT touched here — it was corrected by pass 6, which is what put the document column and the tree in agreement before this retune moved the third memory.

### Found by
- Pass 6, which could not make the gate green by editing the document; ordered by the lead with four conditions — measure the tree, do not touch the document, quote the output and the exit code (which must be 0), and stop and report if any number disagrees with the tree. None disagreed.
