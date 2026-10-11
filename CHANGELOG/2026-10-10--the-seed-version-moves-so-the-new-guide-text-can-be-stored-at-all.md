## The seed version moves, so the new guide text can be stored at all

### Changed
- `agenthub_go/fastmcp/seat_management/domain/seedmap/seedmap.go:14`: `seedVersion` **`1.4.0` -> `1.4.1`**. The
  const carries its own rule — a stored seat type version is immutable, so a changed module set needs a new
  version — and the module set changed in `b9e9b06f` (`shared-modules/guide-common.md`, two lines:
  `### Reply voice (caveman)` became `### Writing style`), which moved the guide's bytes without moving the
  version that names them.

### Why this one line gates the reseat, measured rather than argued
- **The render does not read the running binary's embedded shelf; it reads the seat's PINNED stored
  version.** Measured at HEAD before this commit: `call_seat(room=4genthub-min, seat=go-dev)` returned a
  9732-byte `AGENTS.md` whose shared part has 5 sections — `Writing style` ×0 and `caveman` ×0 — while
  `git show 7c7edf48:agenthub_go/fastmcp/seat_management/domain/seedlibrary/shared-modules/guide-common.md`
  has `### Reply voice (caveman)` at `:29` and 9 sections. The room's seats are `pinned_version` `1.3.0`, so
  what they read is a 1.3.0-era copy: a deploy alone changes nothing the seats see.
- `seedmap.go:113` and `:118` stamp `guide-common` and the per-seat guide blocks with `seedVersion`, and
  `seat_seeder.go:11-13` states that different content under the same version FAILS instead of being
  overwritten. Until the version moves, the new guide text cannot be stored at all — the same gate the
  previous bump (`1.3.0` -> `1.4.0`) recorded in its own entry.

### Tested
- `go test -count=1 ./fastmcp/seat_management/...` -> exit **0**, **17 packages ok**, 0 FAIL. The whole suite
  `go test -count=1 ./...` -> exit **0**, **141 packages ok**, 0 FAIL. `go build ./...` exit **0**;
  `go vet ./...` exit **0**; `gofmt -l fastmcp/seat_management/domain/seedmap/` prints nothing.
- **`seedmap_test.go` needs no edit, confirmed rather than assumed:** it compares against the CONST and never
  the literal — `seed.Version != seedVersion` (`:20`), `role.Version != seedVersion` (`:25`), the writer rule
  (`:48`), the output document (`:68`), every shared module (`:122`) and every block (`:164`) — so the
  expectation moves with the const by construction.

### Not in this commit
- The order after the bump, which is not this seat's to run: the principal pushes and deploys, runs
  `POST /api/v2/openrig/seat-types/seed` so the new immutable version is stored, and moves the `4genthub-min`
  seat pins off `1.3.0`. 4genthub row `0a502904` carries that chain and its acceptance line —
  `call_seat(room=4genthub-min, seat=go-dev)` carrying `### Writing style` and zero `caveman`.

### Found by
- The lead's order on the reseat, after the measurement above; landed by go-dev.
