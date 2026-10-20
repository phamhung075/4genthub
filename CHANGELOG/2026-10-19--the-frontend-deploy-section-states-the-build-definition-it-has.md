# The frontend deploy section states the build definition it has

Date: 2026-10-19
Task: 5216e891 (`Record the measured frontend deploy path: CapRover webhook on branch frontend; a webhook 200 is delivery, not a build`)

## What was wrong

The section landed by `ae15ce7c` kept a claim its own next sentence contradicts: *"The build definition
is not pinned in the tree."* The definition is in the tree. `origin/frontend` carries
`captain-definition.frontend`, which names `docker-system/docker/Dockerfile.frontend.production`, and
that Dockerfile resolves at HEAD and on `origin/frontend` (`git cat-file -e` both). What is not in the
repository is the CapRover app setting that selects which of the three suffixed definitions to read -
the branch has no root `captain-definition` - and that is a different statement.

The same section also left four facts the task's acceptance names unwritten: the app is
`4genthub-frontend`, `main` and `frontend` are separate lines, a build takes about 4-11 minutes
(04:35Z -> 04:46Z; 17:56Z -> 18:03Z) with a trigger vanishing while the webhook answers 200, and the
served entry's `Last-Modified` is the cheap proof that a deploy landed.

## What changed

`ai_docs/operations/complete-operations-guide.md`, the *Frontend deploy path* subsection only:

- The opening paragraph names the CapRover app (`4genthub-frontend`), says `main` and `frontend` are
  separate lines, and records the measured build span and the silently lost trigger.
- The code block gains `curl -sI https://www.4genthub.com/ | grep -i last-modified` as the first
  check, beside the entry-chunk hash and `scripts/check_served_frontend.py`.
- The bolded build-definition paragraph is replaced: the frontend definition is the suffixed
  `captain-definition.frontend` naming `docker-system/docker/Dockerfile.frontend.production` (present
  at HEAD and on the branch); `agenthub-frontend/captain-definition` is the stale second definition
  naming a `./Dockerfile.production` that resolves nowhere; what a reader cannot recover from the
  repository is which definition the app is configured to read.

## Evidence

- `curl -sI https://www.4genthub.com/ | grep -i last-modified` -> `Mon, 19 Oct 2026 18:03:24 GMT`, the
  re-trigger's build time.
- `git show origin/frontend:captain-definition.frontend` -> `dockerfilePath` is
  `./docker-system/docker/Dockerfile.frontend.production`; `git cat-file -e` finds that path at HEAD and
  on `origin/frontend`. The three branch-root definitions are `.backend`, `.backend.go`, `.frontend`;
  there is no root `captain-definition`.
- `git apply --check` clean at `ae15ce7c`; applied on a scratch copy; the subsection's fences balance.
- Documentation only: no code path changed.
