Decision: the 4genthub-min room definition follows the live roster. Remove go-dev2 everywhere it is declared, declare the architect seat, and leave history alone. Neither `apply` runs before this lands.

Context: the lead routed this at 18:21Z after the architect found it. Measured 2026-10-08:
- The live rig has ten seats (`rig ps --json` gives `nodeCount` 10 for `4genthub-min`; the names come from the rig's exported spec, `rig export`, read the same day): lead, architect, go-dev, fe-dev, web-dev, reviewer, writer, skills-dev, context-dev, feedback-dev. go-dev2 was removed today. The architect runs on `claude-code` (`agent_ref: local:agents/architect`, `model: opus` in the exported spec), and every other seat runs on `omp`.
- `scripts/team/4genthub-min/team.json` also declares ten seats, but a different ten. It has go-dev2 (the seat at line 150, its overlay at 217-219, and the modules `guide-go-dev2` at 26-29 and `policy-go-dev2` at 86-89) and no architect.
- `scripts/openrig_seat_policy.py:73` lists `"go-dev2": "dev"` in `SEAT_ROLES["4genthub-min"]`.
- The seed library ships a per-seat guide for go-dev2: `seedlibrary/blocks/guide-go-dev2.md`, its entry in `seedlibrary/guides.lock.json` (slug at line 41), the seat list in `seedlibrary/guides_test.go:20`, and its source `ai_docs/operations/seat-guides/go-dev2.md`.
- `scripts/team/4genthub-min/NOTES.md:25` and `:28` count go-dev2 among the ten.
- The seat type exists: `seedlibrary/seat-types/architect.yaml` (`default_runtime: claude-code`). The type carries the role, including "you do not implement".
- A stale state directory exists: `~/.openrig/state/omp/4genthub-min-go-dev2@4genthub-min` (found by the reviewer). It is the owner's state, outside the repository.

What each "apply" would do today. This corrects "drop the architect" to what the code does:
- `scripts/openrig_team_setup.py apply` only creates. Seats are `POST .../rooms/{room}/seats` with 409 accepted, and overlays are `PUT` (`build_plan`, lines 536-570). It deletes nothing and writes to the 4genthub API room, not to the live OpenRig rig. So it does not remove a live seat. The first apply for this room (never run, per NOTES.md "Not settled here") would build go-dev2 with its guide and policy, and never create the architect. The cloud room would describe a team that does not exist.
- `scripts/openrig_seat_policy.py apply` walks `SEAT_ROLES` and stops with `EXIT_USAGE` at the first seat whose state directory is missing (`cmd_apply`, lines 216-238). Today the stale go-dev2 directory exists, so the run passes and writes a `config.yml` into a dead seat's directory. **The order matters.** If the stale directory is removed before `SEAT_ROLES` is fixed, the run stops at go-dev2, and the seats after it in the dict (fe-dev, web-dev, skills-dev, context-dev, feedback-dev, reviewer, writer) are never checked. So the code fix lands first and the directory goes second.
- Even after both files are fixed, any scan that reads the state root (attribution, declared area, watch tooling) still returns a go-dev2 seat until the directory is moved away.

Options:
- A. Align the definition with the live roster now. Remove go-dev2 from the room definition, the policy table and the guide shelf. Declare the architect in `team.json`. Cost: about ten files in one commit, plus one lock re-record. The wrong apply stops being possible.
- B. Hold until an apply is scheduled. Cost: nothing today, but the wrong first apply stays armed until someone remembers this note, and the policy run keeps writing into a dead seat's directory. The fix needs the same work later, from someone with less context.
- C. Remove go-dev2 only and do not declare the architect. Cost: smaller, but the room definition would still not be the live team. A first apply would build nine seats without the one that holds design decisions, so the mismatch would be shrunk, not fixed.

Recommendation: A. The definition exists to rebuild the live team, so it should list the live team. B pays the same cost later and keeps the trap armed. C fixes half of it.

Shape (if A):
- Behaviour-changing for the room definition and the omp policy table. Additive for the architect. No Go or Python logic changes, no ORM, no database.
- `team.json`:
  - Remove the go-dev2 seat, the `go-dev2` key in `seat_overlays`, and the `guide-go-dev2` and `policy-go-dev2` module entries.
  - Add the seat `{"seat_key": "architect", "seat_type": "architect", "runtime": "claude-code", "model": "opus"}`. `model` is the live spec's value. Leave `pinned_version` out: the column is nullable, and the others' `1.3.0` does not trace to any version field in `seedlibrary/seat-types/*.yaml`, so copying it would invent a pin.
  - Give the architect no `seat_overlays` entry. Its seat type already carries the role. A `policy-*.json` is an omp bash-pattern document, which does not fit a claude-code seat.
- Delete `scripts/team/4genthub-min/guide-go-dev2.md` and `policy-go-dev2.json`.
- `scripts/openrig_seat_policy.py`: remove the go-dev2 line. Do **not** add the architect. The script writes omp `config.yml` under `~/.openrig/state/omp`, the architect has no directory there, and adding it would make `apply` exit at the architect.
- Seed library: delete `blocks/guide-go-dev2.md`, its `guides.lock.json` entry, and `"go-dev2"` from `guideSeats` in `guides_test.go`. Delete the source `ai_docs/operations/seat-guides/go-dev2.md`, and regenerate `ai_docs/index.json` in the same commit so the index never points at a missing file.
- `NOTES.md`: rewrite the seat-type table and its 7 + 3 sentence for the new ten. The architect matches its seeded type by name, so it is 7 clean + 3 flagged = 10 seats, with go-dev2 replaced by the architect. Re-measure the 7 + 3 from the OpenRig ledger, the way the existing footnote says, and not from `team.json`.
- History stays as written: CHANGELOG.md, TEST-CHANGELOG.md, `agenthub-frontend/CHANGELOG.md`, NEXT_GEN.md, `ai_docs/reports-status/session-handoff-2026-10-04.md`, `ai_docs/operations/watching-openrig-seats.md`, `seat-approval-and-the-startup-call.md`, the comments in `agenthub-frontend/src/types/apiReference.ts:5` and `ApiReferenceView.real.test.tsx:5` (they credit go-dev2 for past work), and `agenthub_go/internal/clientbridge/testdata/*` with `parity_test.go:103-107` (captured fixtures, frozen on purpose).
- The stale state directory is a separate step that only the owner approves, and it goes after the code commit. Move it aside (for example to `~/.openrig/state/omp-retired/`) rather than deleting it, because it may hold the seat's transcripts.

Acceptance (dev seat: skills-dev, whose area is seat tooling; the lead may choose otherwise):
- May touch: the files named in Shape, CHANGELOG.md, TEST-CHANGELOG.md, and one new test under `agenthub_main/src/tests/scripts/`.
- Must not touch: the history files listed above; `~/.openrig/` (the owner's step); `scripts/openrig_team_setup.py`, `seatrenderer/`, the other guides' lock entries, and `.claude/`. Do not run either `apply`.
- Failing first: `agenthub_main/src/tests/scripts/test_team_roster.py` loads `team.json` and asserts:
  - the seat keys equal the live ten named above (written into the test as the roster measured 2026-10-08);
  - the architect seat has `runtime == "claude-code"`;
  - every `seat_overlays` key is a declared seat, and every module `file` exists;
  - the `omp` seats of `team.json` equal the keys of `SEAT_ROLES["4genthub-min"]`. This is the invariant that stops the two writes drifting apart again (rule 8).

  At HEAD the first two assertions are red, and the last passes only because both files carry go-dev2.
- Negative: the existing `test_apply_writes_every_seat_is_idempotent_and_check_reports_drift` still passes with the shortened table, and a seat whose state directory is missing still makes `apply` exit with `EXIT_USAGE`. The guard is kept, not loosened to step over the removal.
- Command, run at HEAD on 2026-10-08 before any change:
  - `cd agenthub_main && python3 -m pytest --noconftest -p no:cacheprovider src/tests/scripts/test_openrig_seat_policy.py -q` → 12 passed. After the change it adds `test_team_roster.py`, and both pass. Without `--noconftest` the run hangs on PostgreSQL.
  - `cd agenthub_go && go test ./fastmcp/seat_management/domain/seedlibrary/...` → ok.
  - `git grep -n "go-dev2" -- scripts/team scripts/openrig_seat_policy.py agenthub_go/fastmcp/seat_management ai_docs/operations/seat-guides` prints 18 lines at HEAD and must print none after.

Handoff: the lead assigns the code commit. After it lands, the lead takes the state-directory move to the owner. Both `apply` runs remain separate owner decisions, and nothing here authorises them. Dependencies: the `AGENTS.md` writer was deleted in `288fe6ac` and `apply` has never been run for this room. Neither blocks the code commit.
