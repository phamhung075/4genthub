## Unreleased — the shell spec's screenshots cannot be committed, and the tagline's class is corrected

### Changed

- `agenthub-frontend/.gitignore`: `/audit-runs/`. `e2e/shell.spec.ts` writes one directory per shell run
  there (`E2E_SHELL_OUT`, default `audit-runs/shell`) and the directory is 24 MB on this workstation. It was
  NOT ignored - `git check-ignore -v agenthub-frontend/audit-runs` exited 1 and `git status` listed it as
  untracked - so this is a leak surface rather than clutter: every run screenshots the signed-in header, and
  at 1280 and 1440 that header renders the account's name and email (the profile block only yields in the
  768-1023 band - frontend CHANGELOG, the band entry). A stray `git add -A` would have committed them.
- `agenthub-frontend/CHANGELOG.md`, the "shell fits a 1280 laptop" entry: the clause saying the tagline
  became `hidden sm:block lg:hidden` is corrected in place to `hidden sm:block md:hidden`, and the entry now
  records the correction rather than the false claim surviving as history. Read, not recalled:
  `Header.tsx:108` is `hidden sm:block md:hidden`, so the tagline yields from md, while the `lg:hidden` at
  `:132` is the tablet navigation's own class.

### Why a commit of its own

Doc and config only, and one of the two files is a committed entry being corrected rather than rewritten
silently. The 768-1023 band change (`9e3a4b4d`) stayed scoped to its four paths, so this lands the two things
the lead asked for together instead of inside the product commit. Do not push: the seat never pushes.

### Verified

- `git check-ignore -v agenthub-frontend/audit-runs` now names `/audit-runs/` and exits 0, and the directory
  no longer appears in `git status --porcelain`.
- No product file, no test file and no assertion is touched, so no suite is re-run for this commit: the two
  class values were read from the files at the paths named, and the sentences that moved are prose.

### Not done

- `playwright-report/` gets no entry: no spec here configures that reporter (`reporter: [['list']]`), so there
  is no directory to ignore. `test-results/` and `/e2e-test-account` were already covered by the root
  `.gitignore` (`5d12d057`).
- `agenthub-frontend/e2e/ws-discriminator.spec.ts` stays untracked and is deliberately not ignored: it is
  another seat's throwaway instrument and the lead's call, not this commit's.
