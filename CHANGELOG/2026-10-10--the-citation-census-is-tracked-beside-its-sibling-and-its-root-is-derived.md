## The citation census is tracked beside its sibling, and its root is derived

### Changed
- `scripts/CITATION-AUDIT.py` (**NEW**; it was `/home/daihu/.openrig/agenthub-seats/4genthub-min/CITATION-AUDIT.py`, seat-local and unversioned, until this commit):
  - **ROOT is derived from the file's own location** (`scripts/CITATION-AUDIT.py` -> `scripts/` -> the repository root) instead of the hardcoded `/home/daihu/__projects__/4genthub`, so a clean clone at any path runs it.
  - **The checking mode is the default and is now gate-safe.** It writes nothing, and it exits **1** when any row is stale or unresolved — it exited **0** on `stale 59` before, so a gate running it could not have failed. Exit codes are documented in the docstring: 0 clean, 1 stale/unresolved, 2 refused.
  - **`--write` is explicit AND guarded.** It refuses (exit 2, tree untouched) while any gate marker is present, naming the marker it found; the marker set is `CI` plus the `PRE_COMMIT_*` family pre-commit sets while it runs this repository's hooks (and rewinds the whole worktree to the index). In a shell where `CI` is set for other reasons, the deliberate form is explicit and visible rather than silent: `CI= python3 scripts/CITATION-AUDIT.py --write`.
  - **It verifies its own work**: after a rewrite it re-runs the check and exits 1 if anything is still stale or unwritable, so it cannot report a tree it did not leave. Arguments other than the three modes are refused with exit 2.
  - `--self-test` keeps its method, and its verdict now reaches the process exit code (`sys.exit(main())`), which it did not before — it returned 0 whatever it found.
- `scripts/COUNTS-AUDIT.py`: two sentences that named CITATION-AUDIT.py as seat-local and outside `scripts/` now name it as the tracked sibling, with the rewriting mode described as an explicit guarded flag.
- `ai_docs/api-integration/surface-inventory.md`: the live pointer paragraph names `scripts/CITATION-AUDIT.py` for the §1 citations as it already named `scripts/COUNTS-AUDIT.py` for the counts, and states that the pass records naming a `~/.openrig/agenthub-seats/<seat>/` path are the runs made before the move. Those records are history and are not rewritten.

### Why (the defect, reframed)
- **Not a dangling reference — the document already named the seat path.** The defect is REPRODUCIBILITY: the census that justified 144 lines of change in `79e54a50` existed only on one seat's disk, and ROOT was a personal absolute path, so a successor could not re-run the check the document relies on. `COUNTS-AUDIT.py` made this move on 2026-10-09; this is its sibling, and it closes the same class for the citation half.

### Verified
- The default check on this tree: `python3 scripts/CITATION-AUDIT.py` -> `rows 144  stale 0  unresolved 0`, **rc 0**.
- `python3 scripts/CITATION-AUDIT.py --self-test` -> `perturbed the citation on line 62 by +7 -> 1 stale reported against a baseline of 0, the perturbed row named (PASS)`, **rc 0**.
- **The refusal, `CI=true` being set in this shell:** `python3 scripts/CITATION-AUDIT.py --write` -> `refusing --write: a gate marker is set (CI=true)...`, **rc 2**, and `git status --porcelain` on the document is empty.
- The deliberate form: `CI= python3 scripts/CITATION-AUDIT.py --write` -> `rewrote 0 citations: nothing is stale`, **rc 0** (nothing was stale, so nothing was written).
- A stray argument: `python3 scripts/CITATION-AUDIT.py --fix` -> `unknown argument(s): --fix`, **rc 2**.
- `python3 scripts/COUNTS-AUDIT.py` still exits 0 with all eleven rows matching after the docstring edit.
- The clean-clone and seeded-stale runs (a `git worktree` at this hash, then a citation perturbed inside it) are run after this commit and reported with the hash — a worktree cannot contain the file before it is committed.

### Not changed, said rather than left to inference
- `TEST-CHANGELOG.md` gets no entry: no test file changed. The instrument's falsifiability is its own `--self-test`, which is the sibling's pattern too (`COUNTS-AUDIT.py` has no pytest file either), and it is demonstrated above rather than asserted.

### Found by
- Lead row `0578cc7c`, from the reviewer's gate on `79e54a50` and the seat-local path this seat disclosed there.
