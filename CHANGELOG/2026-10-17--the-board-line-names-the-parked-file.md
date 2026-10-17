## 2026-10-17 — the board line names the parked file

### Changed
- `AGENTS.md` §2: "The board and decisions" no longer names `NEXT-GEN2.md`. Commit `9636848d` parked that
  file on 2026-10-16 as `NEXT-GEN2.md.obsolete`, so the bullet named a file no seat could open. It now
  names the hub board's five Outcome tasks (Outcome 1-5) through `manage_task`, with the queue row as the
  handoff and the Outcome task as the record.
- `ai_docs/agent-system/repo-agent-rules.md` (Docs conventions): the root-keeps list names the parked
  file `NEXT-GEN2.md.obsolete` instead of a standing board file that no longer exists.

### Tested
- `grep -rn NEXT-GEN2 --exclude-dir=.git --exclude-dir=CHANGELOG --exclude='*.obsolete' .` leaves one hit
  outside the gitignored `logs/`: `agenthub_go/internal/repoguards/docs_only_guard_test.go:102`, which
  lists `NEXT-GEN2.md` as a document-path fixture for the guard's extension rule and never opens it.
- The three pointer paths in `AGENTS.md` §4 exist, and the two edits are the only hunks in their files
  (`git diff --stat`: one hunk in `AGENTS.md`, two lines in `repo-agent-rules.md`).

### Notes
- All three paths are documents, so a seat's own commit of them is refused by `docs-only-guard`; this
  rides a non-doc carrier commit (client pin or a `*_test.go`), with `PRE_COMMIT_NO_CONCURRENCY=1` when
  the staged set exceeds one framework batch.
