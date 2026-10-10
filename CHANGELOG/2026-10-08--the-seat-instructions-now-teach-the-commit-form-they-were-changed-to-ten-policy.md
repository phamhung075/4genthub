## The seat instructions now teach the commit form they were changed to (ten policy modules, three guide-common copies, one lock re-record)

### Changed
- `scripts/team/4genthub-min/policy-*.json` (ten files, nine identical siblings each, 90 strings): the sibling every denied git command answers with no longer says "stage explicit paths (`git add -- <path>`)" first. It now says to commit with `git commit -m "..." -- <paths>` **without** staging first, that the index is shared so a staged line can be taken by another seat's commit, that a new file is the one exception and is marked with `git add -N -- <new>` (intent-to-add, no content enters the index), and that just before committing the seat reads `git status --porcelain -- <paths>` (MM: stop) and `git diff HEAD -- <paths>` and names every line: if a line is not yours, do not commit that file, commit your other paths and hold it until its owner commits. Copied verbatim from `ai_docs/architecture-design/decision-commit-form-in-seat-instructions.md` at `4cc8790b`, which carries both later corrections (`4f375115`: add -N; `4cc8790b`: hold the file).
- `ai_docs/operations/seat-guides/_common.md` (the source) and `scripts/team/4genthub-min/guide-common.md`: line 22 rewritten to the same form, keeping its commit-types and changelog sentences; a new paragraph beside it adds the canonical script-test command and the reason the flag is not decoration (`--noconftest`), which until now lived only in the reviewer's guide.
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/shared-modules/guide-common.md`: re-copied from the source, so the shelf is no longer behind it — it was missing the whole "Startup and the approval gate" section. All three copies are now one byte-identical file (`1b0a2f11`).
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/guides.lock.json`: guide-common's `sha256` and `source_sha256` re-recorded to `1b0a2f11…`; both had been `1df9362d…`, stale for the shelf and for the source.

### Added
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/guide_commit_form_test.go` and `agenthub_main/src/tests/scripts/test_seat_policy_commit_form.py` — both red before this change; see `TEST-CHANGELOG.md`.

### Not in this commit
- The ten live `~/.openrig/state/omp/*/agent/AGENTS.md`: outside the repository, and the lead takes that step separately.
- `ai_docs/index.json`: the generated docs index, whose diff is the architect's two decision notes rather than this change.
