## The mirror side of rule 64: a peer's worktree edit is taken by your pathspec commit, and no guard exists

### The finding

`git commit -- <path>` takes the **worktree** content of the path it names, so an uncommitted edit by
another seat to that path rides the committer's commit. Instance: `f344a64f` (go-dev's database
commit) took `CHANGELOG.md` at numstat **15/1** - go-dev's own 14-line entry plus the writer's 1 line -
with the committer's message as the only attribution.

Measured 2026-10-17 in a scratch repository (throwaway, `git init`): seat A appends one line
(`git status --porcelain` = ` M CHANGELOG.md`, `git diff HEAD --numstat` = `1 0`); seat B stages the
path and commits it by pathspec; `git show HEAD:CHANGELOG.md` carries A's line; afterwards A's
`git status --porcelain -- CHANGELOG.md` is EMPTY and `git diff HEAD --quiet -- CHANGELOG.md` exits 0.
The edit did not vanish - it moved into another seat's commit.

### The candidates, measured or ruled out

- **(a) A pre-commit check that refuses a path whose diff carries hunks the committer cannot account
  for: RULED OUT - no in-tree instrument can attribute a hunk.** The worktree holds every seat's
  uncommitted work by design; nothing in git records which seat wrote a line. The only non-forgeable
  source is the committer's *stated intent*, and a hook comparing the diff to that statement compares
  the committer to their own declaration - the same reading rule 64 already requires, not a guard.
  Measured blind spot of the cheap check: `f344a64f` added exactly **1** `## ` heading (the
  committer's own) and **16** added lines over `CHANGELOG.md`; a heading count excluding the
  committer's heading reports 0 surplus while a foreign one-line replacement sits inside an existing
  entry.
- **(b) The victim side: STAGING DOES NOT HELP, and nothing short of committing immediately does.**
  The probe staged the victim's path before the committer's commit and the content still moved.
- **(c) The capture wrapper preserves the bytes** (`<git-dir>/parked-diffs/`, verified by its own
  `--list` contract), so the residual harm is **attribution and message-truth, not loss**. Stated in
  the wrapper and in rule 64 rather than implied as a guarantee.

### Changed

- `agenthub_go/NEXT_GEN.md` rule 64 gains the mirror side: the committer's check is **set equality**
  (`git diff HEAD --numstat -- <path>` vs the intended hunk, stop on surplus), not a heading count;
  the victim's detection is post-hoc and one command - a path whose `git diff HEAD -- <path>` goes
  empty while an edit is still expected - with `git log -1 --numstat -S'<the line>' -- <path>` naming
  the commit, and the bytes in `parked-diffs/`.
- `scripts/git-hooks/git_commit_capture.py`: the module docstring carries the same limit beside its
  existing untracked-files limit.

No new machinery: no hook, no env var, no instrument was added.
