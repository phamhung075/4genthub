## The counts audit retunes four rows for the one-credential removal

### Changed
- `scripts/COUNTS-AUDIT.py`: four `EXPECTED` rows move, each re-derived rather than copied from the numbers the audit printed, and each attributed to the commit and the file that moved it.

| row | was | is | what moved it, named |
|---|---|---|---|
| `httpapp route registrations` | 126 | **124** | `e5ecff63` deleted `machine_token_mount.go`, which carried `POST /api/v2/openrig/machines` and `DELETE /api/v2/openrig/machines/{machine}/token` |
| `seat tables` | 16 | **15** | the same commit removed the `machine_tokens` depth-1 entry from `seat_tables.go` (the table, its ORM, its repository and its service went with the credential change) |
| `registered tables total` | 41 | **40** | follows seat tables — 20 + 3 + 15 + 2, counted once and not twice |
| `SQL CREATE TABLE statements` | 18 | **17** | the same commit deleted the `machine_tokens` statement, 16 lines out of `seat_management_postgresql.sql` |

- **The other httpapp edits in that commit move a wrapper, not a count.** `seat_mount.go`, `seat_status_mount.go`, `seat_feedback_mount.go` and `routes_mount.go` swap `machineAuthed` for `authed` on registrations that STAY, which is why the count falls by exactly the two deletions rather than by seven.
- **`CITATION-AUDIT.py` is not beside this file.** The docstring said it was and the output named it bare; the tool lives in the seat area (`~/.openrig/agenthub-seats/<seat>/CITATION-AUDIT.py`). Both now say so — a tool named at a path a reader cannot follow is the class this audit exists to catch.

### Verified
- **Re-derived at both ends of the move, not adjusted:** the audit's own patterns return `httpapp` **126** at `6cfd56ab` and **124** at `a7990665`; the depth-1 `{Name: ...}` parse **16** at `6cfd56ab` and **15** at `a7990665`; `grep -cE '^CREATE TABLE IF NOT EXISTS'` **18** at `6cfd56ab` and **17** now — while the unanchored `grep -c` reads **18** because it also counts the file's line-6 header comment, which is why the pair is quoted as 15/17/18 and not as 15/17/17.
- **The removal witness, read from the commit:** `git show --stat e5ecff63` -> 37 files, 144 insertions, 1731 deletions, and its own message says it: "Machine token routes, service, repository, table and the client's register command are removed."
- **Not one of the four rows is the tree's fault.** Each is exactly one deliberate removal by one commit — 126-2=124, 16-1=15, 41-1=40, 18-1=17 — so nothing in the tree lost a route or a table the source still registers; the stale side was this file's memory, which is the failure the file's own header describes.
- **The instrument is still falsifiable:** `python3 scripts/COUNTS-AUDIT.py --self-test` -> `perturbed 'httpapp route registrations' by +1 -> tree exit 1, document exit 1 (PASS)`. A check that cannot be shown to fail is not a check.

### Split, said plainly rather than implied
- **This commit moves the instrument's four rows and nothing else.** At this commit the TREE side matches on all eleven rows; three rows still differ in the DOCUMENT column, and that half is not this commit's to take: the `e5ecff63` gate is held by go-dev on row `2609e098`, and its working-tree edit to `surface-inventory.md` — uncommitted, 60/60 — already states 144 / 124 `httpapp`, 15 entries, 17 tables and 17 statements, and records the same split in its own paragraph. Taking that file here would sweep another seat's in-flight work, which is the incident class this lane has already reported once. **The audit reaches exit 0 when both halves are committed; it exits 1 on the document column until then, and that is the honest reading rather than a suppressed one.**

### Found by
- Lead row `0a94db94`, which measured the four rows red at `a7990665`. The reviewer measured the mismatch; this seat measured the cause and named the file behind each row.
