# The pin carries the commit-form skill half, and its record awaits a carrier

The hub's gitlink moves `ca8f5f5f -> 50b97132` (hub `2051fc3c`, gitlink only). Client `50b9713`, the
second half of the commit-form ruling (`dbaf6892`), landed on client main as a fast-forward.

## Changed (client 50b9713, 2 files +26/-1)

- **`skills/share/seat-worktree/SKILL.md`.** The ruled "Staging" bullet becomes "The commit form
  (owner, pathspec fleet-wide, 2026-10-17)": `git commit -m "<type(scope): subject>" -- <paths>`, a
  new file's `git add -N -- <new>` first and then the same pathspec commit; `add -A`/`.`/`commit -a`
  stay forbidden. It names the owner's ruling because the section header cites
  `ai_docs/core-architecture/seat-worktrees.md`, whose staging section the ruling supersedes.

## Evidence

- Both halves PASS, measured on the commits themselves: hub `b76a85a2` (6 files, +77/-11) and
  `b1fb405a` (the ledger nit, 2 files), client `50b9713` (2 files). Hub at `b1fb405a`: `gofmt-check`
  clean over 1252 files, `go test ./...` 139 packages ok, `blockdrift -root ..` rc 0. Client:
  `go test ./internal/clientskills/... ./internal/clientseat/...` rc 0, `go build ./...` rc 0.
- Delivery measured: the seat's skills directory is byte-rebuilt from the client source at every
  seat start (`install_seat_skills`), so the next seat start installs the new text; the pending
  reseat is what carries it.

## Held

This entry is a held record: a pin commit cannot carry its docs from a seat (the gitlink is dropped
by pre-commit's `types: [file]`, so a pin+docs commit arrives as docs-only and the docs-only guard
refuses it; no hook was bypassed). It rides any commit that touches a non-doc file, or lands with
the owner's `types_or: [file, directory]` one-liner (`qitem-20261017002819-8e1c6aff25f2`).

The push is not authorized and waits for the owner's word.
