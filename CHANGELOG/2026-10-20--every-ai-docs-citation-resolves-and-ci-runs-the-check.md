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
2. every backticked `TestXxx` is defined as `func TestXxx(` under `agenthub_go/` or `agenthub_client/`;
3. a citation in PARENTHESES DIRECTLY after a test name claims that test's own definition line -
   `TestFoo` (`x_test.go:196`) must find `func TestFoo(` at 196 of that file. Nothing but whitespace may stand between
   the name and the parenthesis; a pair may break across one line. This is the ruling of
   `seats/architect/DECISION-2026-10-20-doc-citation-instrument.md` (A + B tight): it is the only rule that
   answers the defect that started this work AFTER the name is corrected, because the name was real and the
   line had moved twenty lines. The document's escape is to state a production line as its own claim rather
   than in a parenthetical there. The tight form was measured before it was built: 7 pairs on this tree, 7
   correct, 0 false positives - and a perturbed copy of `seat-occupant-record.md:38` is named with the true
   line 547.

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

**Tests** (`scripts/tests/test_doc_citations.py`, new, 15 cases): the instrument is clean and reports a non-zero
quantity read; a drifted line, an unbackticked citation, an inverted range and an invented test name are each
NAMED; an ambiguous basename is reported with both candidates; `reports-status` is outside the scope; an empty
scope and an unknown argument are refusals, not passes; `--self-test` names what it perturbs. Five pin the tight
pairing against a real test read from the tree at run time: the wrong line is named with the true one, the
definition's own line passes, a pair split across one line break is read, a same-line adjacency is NOT a
pairing, and the documented escape (a production line after the name) is not mistaken for one.

**Three checks the ruling measured and REJECTED** are recorded in the tool's docstring with their counts, so the
next reader does not re-add them: loose same-line pairing (8 co-citation lines, 5 agreeing, the 3 others pairings
no document made), a bare `:NNN` parsed against the nearest preceding file (76 lines carry both forms, 32 bare
references attributable, ZERO out of range), and every backticked `Type.Method` resolved to a member (35 of 38
resolve; the three exceptions are two struct fields and a method named BECAUSE IT WAS REMOVED).

**Verified at this tree**: `python3 scripts/DOC-CITATIONS.py` -> `docs 50  citations 726  test names 23
violations 0`, exit 0; `--self-test` -> PASS; `python3 scripts/CITATION-AUDIT.py` -> `rows 149  stale 0
unresolved 0`, exit 0 (the inventory's route rows were re-pointed to unique paths and still re-derive);
`python3 -m pytest --noconftest -p no:cacheprovider scripts/tests/test_doc_citations.py -q` -> 15 passed;
`go -C agenthub_go test ./... -count=1` -> exit 0.

## Amendment: the checkout decides, so the tool refuses a tree it cannot read

The architect re-ran the instrument in a CLEAN DETACHED WORKTREE, which is what CI gets: with
`agenthub_client` an empty submodule gitlink the audit reported **108 violations**, exit 1, and the
suite was 1 failed / 14 passed; `git submodule update --init` on the SAME commit gave 0 violations and
15 passed, with the doc/citation/test counts (50/726/23) identical in both runs. The tree was the only
variable, so a document was being blamed for files the checkout did not carry.

Two changes, per the ruling's amendment of 19:57Z:

- `scripts/DOC-CITATIONS.py` REFUSES that state: if a tree in `CODE_TREES` holds no tracked file it
  prints `refusing: agenthub_client/ holds no tracked file ...` and exits **2**, not 1. Its MODES line
  says so. Every code tree with zero tracked files is a refusal, not a wall of violations.
- `.github/workflows/ci.yml`: the `scripts` job checks out with `submodules: recursive`, so the gate
  never enters that state. It also takes `fetch-depth: 0`, because `S3-REDERIVE.py` attributes a stale
  anchor against a base revision.

The refusal is pinned by a 16th case in `scripts/tests/test_doc_citations.py`: a module fixture makes a
detached worktree at HEAD (no submodule population), runs that export's own instrument, and requires
rc 2 with the tree named and no violation line. Proved in the real failing state before the fix: the
same checkout printed `agenthub_client/ holds no tracked file`, exit 2.
