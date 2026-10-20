The dead frontend captain-definition leaves the tree

`agenthub-frontend/captain-definition` carried `{"schemaVersion": 2, "dockerfilePath":
"./Dockerfile.production"}`, and `agenthub-frontend/Dockerfile.production` exists neither on disk nor
at `origin/frontend`: production builds `docker-system/docker/Dockerfile.frontend.production` from
the root `captain-definition.frontend`. Board task `a369c414`, row
`qitem-20261019184741-ec4aa1b7a02a`.

The file is deleted, and so is the `if` block in `scripts/backup-production.sh` that copied it into
the configuration backup. The root `cp -f captain-definition …` line above it is unchanged, and
`ai_docs` is not touched. No other reader existed: `grep -rn 'agenthub-frontend/captain-definition'`
over the worktree (node_modules and `.git` excluded) returns nothing.

Verified:

- `bash -n scripts/backup-production.sh` → exit 0.
- The configuration-backup section run in a scratch directory, once from `HEAD`'s script and once
  from this change, with `agenthub-frontend/captain-definition` present in both: `HEAD`'s archive
  carries `smoke_config/frontend-captain-definition`, the new one carries `smoke_config/` only, and
  `set -e` raises nothing.
- `git status --short` → ` D agenthub-frontend/captain-definition`, ` M scripts/backup-production.sh`.
