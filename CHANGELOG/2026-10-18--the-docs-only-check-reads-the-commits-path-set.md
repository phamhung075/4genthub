# The docs-only check reads the commit's path set, in the commit wrapper

Date: 2026-10-18. Queue row `qitem-20261018082606-5461c2e5aa6f` (lead, decision `opt_b`).

## What the tree held at HEAD

`scripts/git-hooks/docs-only-guard` ran as a `pre-commit` hook and judged `git diff --cached`. AGENTS.md
rule 4 has seats commit by pathspec, and `git commit -- <paths>` takes those files' worktree content
without touching the index for them. So the hook answered the wrong question:

- a docs-only PATHSPEC COMMIT left the index untouched and the hook exited 0 - the rule was unenforced on
  exactly the commits it describes;
- the same doc merely STAGED (carried by no commit) exited 1.

Measured on the shipped guard before the change (`sh scripts/git-hooks/docs-only-guard`, seat env set):
rc 0 with the doc change unstaged, rc 1 with it staged. The two probes are pinned as tests now.

## What changed

- **The check moved into `scripts/git-hooks/git_commit_capture.py`**, the wrapper rule 4 already prescribes
  for commits. It is the one place that holds the arguments the commit will run with, so it expands the
  pathspec after git's `--` against HEAD and refuses when EVERY path the commit carries is documentation.
  A bare commit (no pathspec) still judges the index, because with no pathspec the index IS the path set.
  The seat marker (`AGENTHUB_SESSION_NAME`), the owner's host and `OWNER_DOCS_COMMIT=1` are unchanged.
- **`docs-only-guard` is `.obsolete` and its `pre-commit` entry is gone** - one check, one place. The
  config keeps a note saying why the rule is not a hook.
- **AGENTS.md rule 4 names the wrapper** as the commit form that carries the check, and says a seat that
  runs `git commit` directly skips it.
- **The Go witness moved with the check.** `agenthub_go/internal/repoguards/docs_only_guard_test.go` ran
  the deleted script and is `.obsolete`; its cases - every doc shape, the gitlink control, the two
  exemptions, an empty path set - now run the wrapper in `scripts/tests/test_git_commit_capture.py`.

## Evidence

- Red before: the two new refusal cases against the HEAD wrapper fail (`assert 0 == 1`, and the missing
  `is_document` entry point); the three unchanged-behaviour cases pass.
- Green after: `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests/test_git_commit_capture.py
  -q` -> 13 passed.

## Delivered as a patch

The seat guard refuses a seat writing `scripts/git-hooks/` (`protected-paths`): the hooks are the owner's.
The change ships as `seats/go-dev/PARKED-docs-only-check-in-the-wrapper.patch`, applied by the owner.
