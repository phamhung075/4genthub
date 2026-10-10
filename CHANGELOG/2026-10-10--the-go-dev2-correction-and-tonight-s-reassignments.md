## The go-dev2 correction, tonight's reassignments, and where the communication deny actually binds

### Changed

- `agenthub_go/NEXT_GEN.md` — a second block at `:478`-`:481`, beside the ordered box plan, records three things:
  **the seat-naming correction** (`go-dev2` is not a seat in this rig: `rig ps --nodes --rig 4genthub-min` lists
  ten — lead, go-dev, reviewer, fe-dev, web-dev, writer, skills-dev, context-dev, feedback-dev, architect — a row
  addressed to it is unroutable, and the same correction already lives in the architecture doc at
  `ai_docs/core-architecture/agenthub-system-architecture.md:533`-`:543`, decision D7, owner-pending only the stale
  state directory and the two `apply` runs); **every remaining `go-dev2` in this file, with its class**
  (`:53` was a live definition using it as the example seat key and is corrected to `4genthub-min.go-dev`; `:93`,
  `:307` and `:342` are dated records and stay as written, with the note that their work — PACKET-5's A/B/C/E and
  the D5 teams slice 1 — is go-dev's now); and **tonight's reassignments** (guide-common rollout → architect;
  P2 + P3 → go-dev, after P1) with the rollout's code half verified shipped.
- **The rollout's code half, measured rather than relayed:** `42de79c2` (`feat(seats): pin an existing seat to a
  seat type version, and seedVersion 1.4.2`) is an ancestor of `origin/main`
  (`git merge-base --is-ancestor 42de79c2 origin/main` → true) and
  `agenthub_go/fastmcp/seat_management/domain/seedmap/seedmap.go:14` reads `const seedVersion = "1.4.2"`. What
  remains is the re-pin through the R1 route plus the operator's apply, not the bump.
- **One claim in the ordering did not reproduce, and the block says so:** the note that the D1-D4 pointer table
  names `go-dev2`. Measured, `:277`-`:281` name go-dev (three rows), web-dev and writer, and `go-dev2` appears
  nowhere in that table — recorded as a non-reproduction rather than filled in.
- **A measurement note beside G3's box (`:404`-`:405`), because the box's text is checkable and the check
  disagreed.** The box states that direct `rig send`, `rig queue`, `rig broadcast` and tmux "are denied in the
  seat's settings". **On this rig's omp seats they are not:** `rig send 4genthub-min-lead@4genthub-min` delivered
  twice from the writer seat at 21:00Z, while `seatcheck send` — the tool the comm-guard fragment allows —
  **exits 2 before it can decide anything**, on a policy path resolved one tree too deep
  (`~/.openrig/state/omp/<session>/.openrig/agenthub-seats/<rig>/<seat>/policy.json`, while the real file is
  `~/.openrig/agenthub-seats/<rig>/<seat>/policy.json` and reads `{"Links": [], "Seat": "writer"}`), and **no audit
  line is written for those failures** — the seat's `audit.jsonl` still holds only the earlier, correctly-resolved
  refusal `writer -> lead Allowed:false Reason:"no link"`. So the guard's own tool cannot read the policy, and the
  bypass-detection half of the check records none of the attempts it should. The enforcement that exists is the
  claude-code settings fragment (`:410`), which no omp seat carries. Filed as a friction report the same shift.
- `CHANGELOG/2026-10-10--the-owner-ordered-box-plan-and-its-gates.md` — **one quoted token corrected in the
  earlier entry:** `:405`'s tail cites the install that "nothing builds or links (`<pins dir>/bin/seatcheck`)",
  not `cmd/seatcheck`. The same correction landed in `NEXT_GEN.md`'s plan block (`:474`). **It was found by the
  mechanical citation check on the new block rather than by re-reading prose** — the check asserts the quoted
  string is on the cited line, and it was not.

### Verified

- A throwaway citation check on the new block: the five cited `NEXT_GEN.md` lines (`:53`, `:93`, `:307`, `:342`
  and the D1-D4 table's three seat cells) plus the architecture doc's `:533`, `:543` and `:725` and the T12 quote —
  all asserted, and the one failure it found is the token corrected above.
- Roster: `rig ps --nodes --rig 4genthub-min` → 10 nodes. Rollout: the ancestry command and `seedmap.go:14` as
  quoted.
- The `seatcheck` evidence is a fresh run this shift (`/home/daihu/.local/bin/seatcheck`, exit 2), and the seat's
  `audit.jsonl` tail is unchanged by it — which is the finding, not an omission of the measurement.

### Not touched

- No Go source, test, route, table, migration or frontend file. Two documents are edited (`NEXT_GEN.md`, the
  earlier entry) plus this entry; explicit paths only, because the tree carries other seats' in-flight work.
