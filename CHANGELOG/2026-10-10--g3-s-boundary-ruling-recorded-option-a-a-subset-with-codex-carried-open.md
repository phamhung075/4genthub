## G3's boundary ruling recorded: Option A, a named subset, with the codex clause carried open

From the architect's `DESIGN-G3-communication-enforcement-scope-2026-10-10.md` (answering `qitem-20261010183010-4dffdd204e12f291`) and the lead's closure call. **Record only — no code, no schema, and deliberately not the gate sentence.**

### Added
- `agenthub_go/NEXT_GEN.md`, G3's entry: a dated boundary-ruling record stating the decision rather than the gate.
  - **Option B (all five clauses in full) is REJECTED because it WIDENS THE OWNER'S LEVEL** — it needs schema (an audit-sync table and endpoint plus a client uploader), reverses or works around the owner's omp decision, and the sync/feed is a feature rather than enforcement of an existing policy module. **Option A is adopted**: each clause is required only as far as the owner's 2026-10-07 level reaches.
  - **Per clause, as measured:** C1 MET in full; **C2 enforcement point MET with "ships with the seat" OPEN** (nothing builds/links `<pins>/bin/seatcheck` per seat; the one machine-wide binary is stale, `vcs.revision=8a7598ec`, `modified=true`); **C3 required only for runtimes that can hold an allowing link** — claude-code MET, **codex OPEN**, and **omp NOT REQUIRED because its links stay empty by the owner's decision, so its raw `rig send` belongs to `b8c71fdb` and not to G3**; C4's local two-line audit MET with cloud sync ABSENT; C5's scan over an export MET with an automatic feed ABSENT.
  - **The lead's closure call, verbatim in substance:** G3 closes for claude-code once A0-A4 pass, with the codex clause carried as a named open item tied to the owner's install decision. A0-A4 summarised from the ruling's §4, with the four owner follow-ons listed as follow-ons and not blockers.
  - **The gate sentence is named as deliberately absent**, with the reason: the architect's §6 sentence is verbatim and lands only after A0-A4 pass, at the lead's order.

### Verified
- The ruling was read in full at its own frame (superproject HEAD `5c834674`, client files at the gitlink `bae2c86d`), and every clause status, line citation and acceptance criterion in the record is the architect's, attributed rather than re-measured by this seat.
- The two ids the record turns on are the ruling's own: the stale machine binary at `vcs.revision=8a7598ec` with `modified=true`, and the omp design `b8c71fdb`, which the ruling places out of G3's scope.

### Not run
- Nothing was run: this is a documentation record of a reading someone else made, and the acceptance it describes (A0-A4) has not been run by anyone yet.
