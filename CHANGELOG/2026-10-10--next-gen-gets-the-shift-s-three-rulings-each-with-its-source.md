# NEXT_GEN gets the shift's three rulings, each with the source a successor can check

One doc, one insertion, no code. `agenthub_go/NEXT_GEN.md` only, plus this entry.

### Added
- **`T13` — the pin-bump consumers** (work row `06e20876`; asked by go-dev 12:39Z). The ruling: a consumer is kept or deleted by WHERE ITS SUBJECT LIVES, not by where its instrument sits. The `fastmcp/server/httpapp` pair keeps and repoints as INTEGRATION (its subject is the door), `scripts/tests/test_seatcheck_guard.py` repoints the same way, and `test_team_definition.py` / `test_team_roster.py` are not deleted without replacement, because their subject is this repository's `scripts/team/*/team.json` while the client packages test their own fixtures. NO DELETION WITHOUT A NAMED GO TEST.
- **`T14` — Shape A for the DDL mirror** (work row `0e71b8c2`; landed `788bdd2c` + `25c81a36`; the re-gate is the reviewer's). `fastmcp/session_stream/testdata/stream_tables_python_ddl.txt` stays a pure frozen snapshot with a four-fact header and no regeneration recipe, and its divergences become a typed ledger `{table,kind,name,line,commit,why}` compared as a set in both directions, where a declaration replaces the snapshot's line for its key, the commit must exist by `git cat-file -e`, and the ordinal noise is accepted on purpose.
- **`T15` — the arm and its trap** (work row `9651609a`; commits `f2c5520f`, `a5555729`, corrected by `694a7141`; owner action (2) in `DEPLOY-READY`). `scripts/team/4genthub/team.json:9` is the module entry whose version the company overlay op resolves, and that overlay is stacked under every seat of every room, so the three rooms re-resolve together. The arm is local by design: it sits above the sealed `7fe3b837`, so the owner's apply must run from the checkout that carries it, not from a clone of the pushed hash.

### Corrected
- **T15 lands the mechanism `694a7141` corrected, not the version the ruling arrived in.** The earlier statement — that apply publishes changed content at `nextPatch`, re-pins the overlay and succeeds silently at `1.0.0` — is wrong, and the reasoning row that carried it was corrected the same day. The true behaviour: apply PUTs each module at the version `team.json` declares, a different checksum at an existing version is `ErrModuleVersionConflict` (`module_repository.go:76-77`) answered 409 (`seat_admin_mount.go:962-963`), and the module step does not tolerate it, so apply **stops loudly before any overlay or seat PUT**. `nextPatch` is not on the apply path. The owner's gate is stated with it: `1.0.1` absent, or present with identical content.

### Verified
- Every source in the three entries was re-measured rather than copied. The commits exist, each with the subject the entry claims: `788bdd2c` (the snapshot declares its divergences and the dead recipe goes), `25c81a36`, `f2c5520f` (the company-overlay ref armed at `1.0.1`), `a5555729`, `a50929c6` (remove `agenthub_main`), `7fe3b837` (the 0.0.32 deploy marker), `694a7141` (the corrected mechanism).
- `git -C agenthub_client cat-file -e 6869fe7e` succeeds and `git -C agenthub_client ls-tree -r --name-only 6869fe7e | grep -c '\.py$'` is **0**, so T13's measured context holds: the client at that hash has no Python under `src`.
- `scripts/team/4genthub/team.json:9` reads `"version": "1.0.1"`, and `git merge-base --is-ancestor 7fe3b837 HEAD` succeeds, so the seal is still an ancestor of the tip and the arm sits above it as T15 says.
- The parity citation T14 carries was checked where it is written: `TEST-CHANGELOG.md` entry 4046 names the frozen snapshot, its freeze at `a50929c6` and the parity evidence as "this file's entry 3040". The line numbers `694a7141` itself cites are attributed to that commit rather than re-measured here.

### Note
- Doc-only: no code, no test, no route and no count changed. `agenthub_go/NEXT_GEN.md` and this entry, both by explicit pathspec, committed above the `0.0.32` marker. NO PUSH.
