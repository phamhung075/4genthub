# The ai_docs citation audit runs at pre-push, not only in CI

A drifted `file:line` or a backticked `Test` name in `ai_docs` was caught only by CI, one push too late: the
instrument (`scripts/DOC-CITATIONS.py`) had no local entry, and the entry's home
(`scripts/git-hooks/pre-commit-config.yaml`) is a protected path no seat may write. The owner added it as a
`repo: local` hook with `stages: [pre-push]`, `always_run: true` and `pass_filenames: false`, so the
pre-push stage scans the working tree rather than a filename list.

Measured at the gate: a clean populated tree passes (`49 docs, 733 citations, 23 test names, 0 violations`,
rc0); a citation past EOF (`scripts/DOC-CITATIONS.py:99999`) fails with `violations 1`, rc1 and names the
file:line; an unpopulated `agenthub_client/` hits the script's exit-2 refusal, which the hook reports as a
failure - a refusal, not a violation, and the push is blocked either way. The audit takes about 23 s. No
hook reinstall is needed: the installed pre-push shim already passes
`--config=scripts/git-hooks/pre-commit-config.yaml`.

Residual, recorded by the gate: the installed shim delegates to `.git/hooks/pre-push.pre-4genteam` by a
relative path, so from a linked worktree (where `.git` is a file) the pre-commit stage is skipped silently.
No reachable loss today - the 4genteam guard refuses every seat push, and the owner pushes from the checkout.

- Files: `scripts/git-hooks/pre-commit-config.yaml:71-82` (owner commit `83a12d8b`)
- Proof: `owner/doc-citations-prepush` `83a12d8b` on hub main `7c13eb7a`, numstat 1 file +13; reviewer gate
  PASS at `qitem-20261021210804-dd2d329c9ced`; landed as a `--no-ff` merge carrying this entry. Task
  `17063dbd`.
