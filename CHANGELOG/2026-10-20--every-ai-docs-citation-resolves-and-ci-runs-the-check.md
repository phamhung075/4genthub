# Every `ai_docs` citation resolves, and CI runs the check

On 2026-10-20 `ai_docs/core-architecture/seat-occupant-record.md` reached main citing
`TestSeatAdminSetOccupantEmitsOneFrame` at `seat_admin_mount_test.go:527` - a name in NO commit of this
repository, at a line that had moved to `:547`. A reader caught it; no check did. `scripts/CITATION-AUDIT.py`
resolves only the surface inventory's route tables, and nothing ran the other 50 documents at all.

**`scripts/DOC-CITATIONS.py`** (new) audits `ai_docs/**/*.md` (except `ai_docs/reports-status/**`, dated records
a later tree cannot make wrong) against the tracked tree:

1. every `path/to/file:NNN` and `:NNN-MMM` resolves inside the repository - root-relative, as a unique path
   suffix (`httpapp/task_routes.go` for `agenthub_go/.../httpapp/task_routes.go`), or by an unambiguous
   basename - and the file has at least that many lines, with the range's ends in order;
2. every backticked `TestXxx` is defined as `func TestXxx(` under `agenthub_go/` or `agenthub_client/`.

A basename matching more than one file is REPORTED with both candidates, never guessed. Default mode writes
nothing and exits 0 clean / 1 violation / 2 refused (an unknown argument, a scope holding no markdown, a
`--docs` directory that does not exist). `--self-test` perturbs one resolvable citation in a COPY of the
documents and requires the audit to name that exact document line, against a measured baseline.

**The index is the TRACKED tree** (`git ls-files` plus each submodule's content), not a disk walk: a seat's
untracked scratch directory (`.lane-commit-form/` mirrored the whole repository) made every basename ambiguous
against its own copy and resolved citations into files no commit carries.

**Before and after, at this tree.** First run against the tracked index: **152 violations** over 50 documents
(103 ambiguous basenames, 46 paths with no file, 2 citations past the end of their file, 1 invented test name).
The 13 documents were fixed at the citation - the ambiguous ones resolved by reading which candidate holds the
claimed code, the stale ones (the retired TypeScript daemon, the Python client, `manage_agent`,
`seat_rigspec_mount.go`) restated as the fact they are instead of a live `path:line`, third-party and template
examples no longer shaped as citations. Now: **0 violations**, 726 citations and 23 test names read. The count
fell 771 -> 726 because 45 tokens stopped pretending to be citations of this tree.

**Wired**: `.github/workflows/ci.yml` gains the `scripts` job (`:36-45`) - `python3 scripts/DOC-CITATIONS.py`
then `python3 -m pytest scripts/tests/test_doc_citations.py -q`. The same check as a `pre-push` hook was
PREPARED for `scripts/git-hooks/pre-commit-config.yaml` and NOT applied: that file is owner-protected and the
seat guard refused the write. It is the owner's call to add the `doc-citations` local hook there.

**Tests** (`scripts/tests/test_doc_citations.py`, new, 10 cases): the instrument is clean and reports a non-zero
quantity read; a drifted line, an unbackticked citation, an inverted range and an invented test name are each
NAMED; an ambiguous basename is reported with both candidates; `reports-status` is outside the scope; an empty
scope and an unknown argument are refusals, not passes; `--self-test` names what it perturbs.

**Verified at this tree**: `python3 scripts/DOC-CITATIONS.py` -> `docs 50  citations 726  test names 23
violations 0`, exit 0; `--self-test` -> PASS; `python3 scripts/CITATION-AUDIT.py` -> `rows 149  stale 0
unresolved 0`, exit 0 (the inventory's route rows were re-pointed to unique paths and still re-derive);
`python3 -m pytest --noconftest -p no:cacheprovider scripts/tests/test_doc_citations.py -q` -> 10 passed;
`go -C agenthub_go test ./... -count=1` -> exit 0.
