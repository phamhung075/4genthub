# The worktrees doc restores the pathspec form

`ai_docs/core-architecture/seat-worktrees.md` §(c) still taught the staged form: its table kept "Stage by
explicit path … **stays**" and said `git commit -- <paths>` was "**no longer required**". The owner's
2026-10-17 ruling is pathspec fleet-wide (`AGENTS.md` rule 4,
`CHANGELOG/2026-10-17--the-commit-form-is-pathspec-fleet-wide.md`), so the section now states the standing
form instead.

## Changed

- §(c) is renamed "The commit form is pathspec, fleet-wide" and its rows say it: commit by pathspec,
  `git add -N -- <new>` only for a new file, no pre-staging, and the per-path read before the commit for
  lines that are not yours. The keep-out row and the never-rules keep their wording.
- This entry rides the same carrier commit: the file's diff alone is refused by
  `scripts/git-hooks/docs-only-guard`, and `OWNER_DOCS_COMMIT` is the owner's alone.

## Not in this change

No code, no test, no other document. The `seat-guard.ts:135` advice is the owner's own row and is untouched.
