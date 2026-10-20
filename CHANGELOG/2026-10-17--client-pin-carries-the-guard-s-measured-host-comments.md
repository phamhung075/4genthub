# The pin carries the guard's measured-host comments, and its record awaits a carrier

The hub's gitlink moves `858abf2e -> a40d9a0e` (hub `4e244a5a`, gitlink only). Client main took
`4genthub-min/c3-guard-comments` as a fast-forward: `858abf2 -> a40d9a0` (one commit).

## Changed (client)

The C3 close-out found the guard CODE already bound to the native spellings; only the prose claimed a
rig shim that the host does not have.

- `internal/commpolicy/policy.go`: the doc comment no longer says "rig on PATH is @reference/cli".
- `internal/clientseat/quiet.go`: the shim identity is dropped from the comment; both say the measured
  host (`rig` not on PATH, `~/.local/bin/rig` absent, the client is one file `4genteam`).

No behaviour changed - comments only. The mutation checks are what make that claim measurable: a
shim-only spelling fails the eight native spellings plus shape and nil-known checks.

## Evidence

- Reviewer gate PASS at `a40d9a0` (row `qitem-20261017040952`): `go build` rc 0; `go test ./...` 28
  packages ok; `TestBypassSuspected`, `KnownShapeIsNotALicence`, `NilKnown` pass; shim-only mutation
  fails as required; allow-shape mutation fails the licence test; the audit scan flags the native
  sends (rc 4) and leaves `ps` unflagged.
- The census re-cut `5a1c3161` landed on hub main first (row `qitem-20261017040646` PASS: `pytest
  scripts/tests/test_team_definition.py` 20 passed; full suite 96/1 with the deliberate live-spec
  red).
- Lead at the merged tip: client ff clean, hub pin `4e244a5a` is a bare gitlink bump (`numstat` 1
  file `+1 -1`).

## Held

Held record: a pin commit cannot carry its docs from a seat (pre-commit drops the gitlink, so a
pin+docs commit arrives as docs-only and the docs-only guard refuses it; no hook was bypassed). It
rides any commit that touches a non-doc file, or the owner's `types_or: [file, directory]` one-liner
(`qitem-20261017002819-8e1c6aff25f2`).

The push is not authorized and waits for the owner's word (`qitem-20261017030506`).
