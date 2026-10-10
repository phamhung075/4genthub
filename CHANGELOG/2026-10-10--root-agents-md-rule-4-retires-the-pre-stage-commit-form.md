## Root AGENTS.md rule 4 retires the pre-stage commit form

### Changed
- `AGENTS.md:46-52` (rule 4, "Keep-out files and staging"): "Stage by explicit path; never `git add -A`" is marked **RETIRED** and replaced by the settled fleet form — commit by pathspec and do not stage first (`git commit -m "<type(scope): subject>" -- <paths>`), a brand-new file being the one exception, marked with `git add -N -- <new>` (intent-to-add, nothing enters the index) before the same commit; never `git add .`, `-A` or `--amend`. The pre-stage form is the hazard in a shared worktree, because a staged line can be taken by another seat's commit. Removal is attributed by the COMMIT that carries it (`git show --numstat --format= <sha> -- <path>`), never by the staging area.
- `ai_docs/agent-system/repo-agent-rules.md:77-81` carries the settled form and `:124-127` carries the RETIRED statement, so the root rule and the detail page agree. This closes the writer's queue row `qitem-20261008193851-3610567090675db6`.

### Fixed
- This change reached `HEAD` inside `33f8aae8`, whose subject is the `ai_docs` cut — the held hunk rode into another change's commit and carried no entry of its own. That commit's diff names `AGENTS.md` (14 insertions, 5 deletions) while its message does not, and the entry it does have (`CHANGELOG/2026-10-10--unreleased-ai-docs-cut-from-57-files-to-21.md`) records the `ai_docs` deletions and the reworded `AGENTS.md` pointers only. Recorded here rather than left silent: it is the failure shape the rule above exists to close, and it happened after the rule was written.

### Measured
- `git diff --quiet HEAD -- AGENTS.md` → no output, so the worktree equals `HEAD` for that file; `git merge-base --is-ancestor 33f8aae8 origin/main` → 0, so the retired form survives a fresh clone.
- `git status --porcelain AGENTS.md ai_docs/agent-system/repo-agent-rules.md` → empty: neither file is dirty, and the "staged and uncommitted" state the handoff described was true on 2026-10-09 and is stale now.

### Tested
- Not a code change. Verification is the two `git` checks and the grep for `do not stage first|git add -N|RETIRED` over `AGENTS.md` and `ai_docs/agent-system/repo-agent-rules.md`, run 2026-10-10 at tip `d036e32e`.
