# The ops guide records the frontend deploy path, and a 200 is delivery, not a build

Date: 2026-10-19
Task: 5216e891 (`Record the measured frontend deploy path: CapRover webhook on branch frontend; a webhook 200 is delivery, not a build`)

## What was wrong

No document said how `agenthub-frontend` reaches production. The operations guide's Quick Reference
rows for deploy, health check and rollback are struck 2026-10-09 (their scripts are deleted; the
deletion is held), and nothing replaced them with the path that is actually live: a push to the
`frontend` branch that CapRover's GitHub webhook builds. So a deploy was reported off the wrong signal.
Measured 2026-10-19: the push of `408a304c` at 17:11Z returned **200 Delivered** on the webhook and
produced no build at all; only the re-trigger at 17:56Z produced one, which served
`/assets/index-BAhshU-p.js` at 18:03:24Z. A 200 on the webhook means the event was accepted, nothing
more.

## What changed

`ai_docs/operations/complete-operations-guide.md`, the operator's entry point, in two places:

- **Quick Reference** gains a live `Deploy frontend` row: the branch, the webhook, and the correction
  that a webhook 200 is delivery rather than a build.
- **A new subsection, *Frontend deploy path (measured 2026-10-19)***, under *CapRover Deployment*:
  the branch and webhook, the two measured timestamps above, and the rule in words - a 200 says the
  event was accepted; it says nothing about a build, a deploy, or what is serving. The two surfaces
  that answer that are the CapRover app's build log and the served entry chunk compared against a
  local build of HEAD:

  ```bash
  curl -s https://www.4genthub.com | grep -o '<script[^>]*src="/assets/index-[A-Za-z0-9_-]*\.js"'
  python3 scripts/check_served_frontend.py --base-url https://www.4genthub.com \
      --expect-dist agenthub-frontend/build
  ```

  Plus the procedure when a 200 yields no build: re-trigger from the CapRover app's deployment tab,
  wait for the build log's end line, re-run both checks.

The subsection also records a gap it found while being written, and does not paper over it: **the build
definition is not pinned in the tree.** CapRover reads `captain-definition` from the branch root, and
`origin/frontend` carries none - only `captain-definition.backend`, `captain-definition.backend.go` and
`captain-definition.frontend`. `agenthub-frontend/captain-definition` names `./Dockerfile.production`,
which exists at neither HEAD nor on `origin/frontend` (`9787bce2` introduced it), and
`scripts/deploy-frontend.sh` stops at that same missing file (`:110`). Until a root
`captain-definition` exists, the definition a build used lives only in the CapRover app's
configuration and cannot be reproduced from the repository.

## Evidence

- The live site serves `/assets/index-BAhshU-p.js` - the same entry chunk the re-trigger produced at
  18:03:24Z - and the curl line above, run verbatim, prints it.
- `origin/frontend` tip `408a304c`, authored 17:01:36Z, is the commit the 17:11Z push carried.
- `git apply --check` clean at `b58c7e25`; applied on a scratch copy with `patch -p1`; the inserted
  section is fence-balanced (two fences).
- No code changed: documentation only.
