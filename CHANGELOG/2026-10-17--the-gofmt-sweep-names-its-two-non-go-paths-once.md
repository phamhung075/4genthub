# The gofmt sweep names its two non-Go paths once, and the sweep is an instrument

`gofmt -l $(git ls-files '*.go')` run from the repository root printed **nothing on stdout and
exited 2** at hub main `7c45ca1f`. Two tracked files carry a `.go` suffix and are not Go, and gofmt
names them on stderr (`captain-definition.backend.go:1:1: expected 'package', found '{'`;
`docker-system/docker/Dockerfile.backend.go:1:1: illegal character U+0023 '#'`). So a sweep reading
stdout passed, a sweep reading the exit code failed for a reason that is not formatting, and the
pair had been recorded in a dozen changelog entries as a "decoy" without ever having one home.

## Changed

- **`.gofmt-excludes` (new) - the ONE named place.** It lists the two paths and, beside each, the
  mechanism that makes the name load-bearing, so the exclusion is a recorded fact rather than
  folklore. The sweep's consumer is `scripts/gofmt-check.sh`.
- **`scripts/gofmt-check.sh` (new) - the sweep itself.** It reads the exclusion, checks every other
  tracked `.go` file, and makes three things visible that the raw sweep hid: the skipped paths and
  their count (the green is not vacuous), a rotting exclusion (a named path that is no longer a
  tracked `.go` file exits 2), and a gofmt failure that is not a formatting finding (a parse error
  in a checked file exits 1, never 0). Exit: 0 clean / 1 findings listed / 2 misconfigured.

## Why the two names stay (acceptance route (a): quote the mechanism)

Neither file is renamed, because both are referenced by NAME and a rename is a deploy change:

- `captain-definition.backend.go` is a CapRover JSON definition. Its *name* is the app's Captain
  Definition Path, a per-app setting the tree does not record (`CHANGELOG/2026-10-09--the-captain-definition-uses-the-documented-form-and-the-report-stops-claiming.md:11`
  records that open question), and `captain-definition.backend` already exists with different
  content - so a rename either collides or moves which definition a deploy reads.
- `docker-system/docker/Dockerfile.backend.go` is a Dockerfile named BY PATH from three
  definitions' `dockerfilePath`: `captain-definition.backend:3`,
  `captain-definition.backend.go:1`, `docker-system/docker/captain-definition:3`.

## Evidence (measured at `7c45ca1f` + this change, in `wt/go-dev-root`)

- Before: raw root sweep -> stdout empty, `rc=2`, the two parse errors on stderr; 1254 tracked
  `.go` paths, 2 of them these.
- After: `scripts/gofmt-check.sh` -> `skipped 2 named non-Go path(s)` (both named), `clean over
  1252 tracked .go file(s)`, `rc=0`.
- Not vacuous: a probe file (`package probe` + an unformatted func) tracked with `git add -N`
  -> `1253 checked, unformatted: probe_unformatted.go`, `rc=1`; probe removed, tree clean.
- Cannot rot: a fake name appended to `.gofmt-excludes` -> `names a path that is not a tracked
  .go file: no-such-file.go`, `rc=2`; restored -> green again.

## Limits

- No CI workflow or hook runs a gofmt sweep (`grep` over `*.sh`, `*.yml`, `Makefile*` finds no
  `gofmt` invocation), so this is the instrument seats and the owner run by hand, not a pipeline
  gate. Adding such a gate is a separate decision.
