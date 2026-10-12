# seedVersion 1.4.3, and a guard that refuses to let the library drift under one version

Date: 2026-10-12
Scope: `agenthub_go/fastmcp/seat_management/domain/seedmap`, `agenthub_go/fastmcp/seat_management/domain/seedlibrary`

## Summary
`seedmap.go:14` goes `1.4.2` -> `1.4.3`, and the library gains the guard that made the bump
necessary: `seedlibrary/seedcontent.lock.json` plus `seedlibrary/seedcontent_lock_test.go`. The const
is stamped onto every module of a seed (`seedmap.go:84`, `:87`, `:103`, `:109`, `:113`, `:118`), and
the contract beside it is that a stored seat type version is immutable, so a changed module set needs
a new version.

## Why 1.4.3: (slug, version) = 1.4.2 named two content sets
`42de79c2` (2026-10-10 22:23:21) flipped the const `1.4.1` -> `1.4.2`, and its seedmap diff is that
one line. `39105865` (2026-10-11 01:39:56, "name the tsc command instead of the retired 23-error
count") then changed the CONTENT of two seed blocks - `blocks/guide-fe-dev.md` and
`blocks/guide-reviewer.md` - and re-stamped their `guides.lock.json` sha256 pairs, 3h16m after the
bump, with no version change. Both commits are on `origin/main`, so `(block slug, 1.4.2)` resolves to
two different byte sets depending on when a reader looks, and a store that already holds `1.4.2` and
then meets the newer bytes hits exactly the conflict the version exists to prevent.

This is the third occurrence, and the first to go unrepaired. `b9e9b06f` changed
`shared-modules/guide-common.md` under `1.4.0` and was closed by `fb65bd2a` five minutes later, whose
own message says it moved the version to `1.4.1` because the guide text had changed and not the version
that names it; `a3eb0762` changed that same file again under `1.4.1` and was closed an hour later by
`42de79c2`'s bump to `1.4.2`; `39105865` changed two blocks under `1.4.2` and was closed by nobody until
this change. The rule was therefore already known, and already written down in a commit message, and it
recurred twice anyway - the reason this change adds a test rather than another note.

## The guard: content cannot move under a version that already names a set
`seedcontent.lock.json` records, APPEND-ONLY, which content set each `seedVersion` names: one record
per version, each carrying `content_sha256` and a per-file sha256 map over the 26 files a seed is built
from - `seat-types/*.yaml`, `shared-modules/*` and `blocks/*`, the same three sources the package
embeds. `seedcontent_lock_test.go` fails when the library differs from the set recorded for the version
the seeder stamps, naming every file that moved, and fails when that version has no record at all.

Four properties make the guard bite rather than decorate:

- **The version is not copied.** It is read through `seedmap.FromSpec`, so the guard cannot pass by
  comparing the record against a number nothing stamps.
- **A version recorded twice with two content sets is itself an error.** The record is the immutability
  evidence, not a cache, and the test also reports a record whose `content_sha256` its own files map
  does not reproduce.
- **The generator refuses to re-stamp.** `-update-seedcontent-lock` will not re-record a version that
  already has a set, so a content change cannot be silenced by regenerating the record: the only way to
  green is to raise `seedVersion`.
- **The record's own description is asserted, not trusted.** `_what` is the one string in this file that
  exists twice - on disk, and as the generator's constant - so the test compares them, and an edit to one
  without the other fails.

`SeedVersion 1.4.2` deliberately has no record: it named two sets, and recording either one would write
down a claim that is false.

## Proof: three rehearsals in a scratch worktree, one in place (none of them committed)
- The REAL pre-`39105865` bytes of `blocks/guide-reviewer.md`, under `1.4.3`: FAIL - "seedVersion 1.4.3
  already names a different content set ... blocks/guide-reviewer.md changed".
- The generator on that same state: FAIL - "REFUSING to re-record seedVersion 1.4.3", with the lock
  left naming `1.4.3` alone.
- `HEAD`'s own `seedmap.go` (const `1.4.2`) against a record naming `1.4.3`: FAIL - "seedVersion 1.4.2
  names no content set".
- The record's description mutated on disk with the generator's constant untouched: FAIL - "`seedcontent.lock.json`
  describes itself as ..., but the generator writes ...", naming both strings. Reverted immediately, and
  the guard re-run green.

## What did NOT need changing
`guides.lock.json` carries no version field: it records where each block was copied FROM and its sha256
pair, and `39105865` re-stamped it in the same commit as the content, so this change is the const and
this record. Verified rather than assumed: the pre-change hash `3fab6144…` is pinned by no file at all,
every guide-pairing case passes at this revision, and `seedmap_test.go` needed no edit because it
compares every module version against the const rather than a literal.

## Sequence this unblocks
Owner deploy, then `POST /api/v2/openrig/seat-types/seed`, then the per-seat re-pin through R1
(`PUT /api/v2/openrig/rooms/{room}/seats/{seat}/pin`) at `1.4.3`.

## The repair path, beside the forward one

The repair path — what to do when the store already holds a version, and when a seat keeps rendering the old
guide — is in `4genthub-min/ARCH-REPAIR-PATH-seed-version-conflict-2026-10-12.md` (architect, 2026-10-12).

**If the seed is refused.** Nothing was written, and the store already holds that version with a different
content: read the response rather than inferring success, because the refusal is a 409 naming both offenders —
*"version X of module Y already exists with different content"* — raised by comparing the stored checksum per
`(slug, version)`. No repair reuses that version. Re-seeding it changes nothing; overwriting or deleting the
stored row would break every seat already pinned to the text it resolved; and no pin can move a seat onto content
the store does not hold. The only legal repair is a new version, in one fixed order — freeze first, then bump:
stop editing the seed library and its lock file (seeding the new version freezes *its* content in turn, so an
edit after the seed needs yet another version), raise the version constant in
`agenthub_go/fastmcp/seat_management/domain/seedmap/seedmap.go`, commit that one line with its CHANGELOG entry,
have the owner deploy the commit, and have the owner call `POST /api/v2/openrig/seat-types/seed` from a binary
that contains the intended text — the call reports the stored count or the conflict, so read it, and name the
commit in the instruction, because a binary built before the content edit stores the old text under the new
number and that cannot be undone without yet another version.

**If a seat still renders the old guide after the version moved.** Seeding a version moves no existing seat:
`pinned_version` is read when a seat is created or resolved, an existing seat answers 409 `exists` so `team apply`
skips it, and apply skips the seed too once every seat-type slug is stored — so the pin must be moved explicitly
with `PUT /api/v2/openrig/rooms/{room}/seats/{seat}/pin {"pinned_version":"<version>"}`, which answers 400 when
the seat's type has no such version, 404 for an absent seat, and 200 with the row reading the new version. A moved
pin still does not change a running seat: the pin is read at resolve time and **a seat already launched keeps the
snapshot it was launched with**, so relaunch it — re-pin idle seats first and the lead last, so the last seat
re-pinned can confirm the others came up on the new version, then set `pinned_version` in the team files
(`scripts/team/*/team.json`) so the file matches the store. When a seat still renders the old text, read three
things in this order and stop at the first mismatch: the seat's pin and the version the resolution returns
(`GET /api/v2/openrig/seats/{room}/{seat}`, whose resolved `agent.yaml` carries the version); the seat's own
rendered `AGENTS.md`, whose `seat-type-version:` line names what it actually launched with; then the section list
under that line, where the new text would appear. A pin that moved while the rendered file stayed old means the
seat was never relaunched; a rendered version that is the one the store held *before* the repair means the store
is carrying the ambiguous version and no re-pin can fix it, only the new version can; a rendered version that
matches the new pin means the seat is correct and the stale text is being read from somewhere else.
