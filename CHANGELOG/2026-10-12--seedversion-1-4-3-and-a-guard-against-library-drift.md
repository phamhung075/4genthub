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

This is the second occurrence. `a3eb0762` did the same to `shared-modules/guide-common.md` under
`1.4.1`, and `fb65bd2a` - the commit that raised the version to `1.4.1` - says in its own message that
it moved the version so the new guide text could be stored at all.

## The guard: content cannot move under a version that already names a set
`seedcontent.lock.json` records, APPEND-ONLY, which content set each `seedVersion` names: one record
per version, each carrying `content_sha256` and a per-file sha256 map over the 26 files a seed is built
from - `seat-types/*.yaml`, `shared-modules/*` and `blocks/*`, the same three sources the package
embeds. `seedcontent_lock_test.go` fails when the library differs from the set recorded for the version
the seeder stamps, naming every file that moved, and fails when that version has no record at all.

Three properties make the guard bite rather than decorate:

- **The version is not copied.** It is read through `seedmap.FromSpec`, so the guard cannot pass by
  comparing the record against a number nothing stamps.
- **A version recorded twice with two content sets is itself an error.** The record is the immutability
  evidence, not a cache, and the test also reports a record whose `content_sha256` its own files map
  does not reproduce.
- **The generator refuses to re-stamp.** `-update-seedcontent-lock` will not re-record a version that
  already has a set, so a content change cannot be silenced by regenerating the record: the only way to
  green is to raise `seedVersion`.

`SeedVersion 1.4.2` deliberately has no record: it named two sets, and recording either one would write
down a claim that is false.

## Proof, rehearsed in a scratch worktree (never committed here)
- The REAL pre-`39105865` bytes of `blocks/guide-reviewer.md`, under `1.4.3`: FAIL - "seedVersion 1.4.3
  already names a different content set ... blocks/guide-reviewer.md changed".
- The generator on that same state: FAIL - "REFUSING to re-record seedVersion 1.4.3", with the lock
  left naming `1.4.3` alone.
- `HEAD`'s own `seedmap.go` (const `1.4.2`) against a record naming `1.4.3`: FAIL - "seedVersion 1.4.2
  names no content set".

## What did NOT need changing
`guides.lock.json` carries no version field: it records where each block was copied FROM and its sha256
pair, and `39105865` re-stamped it in the same commit as the content, so this change is the const and
this record. Verified rather than assumed: the pre-change hash `3fab6144…` is pinned by no file at all,
every guide-pairing case passes at this revision, and `seedmap_test.go` needed no edit because it
compares every module version against the const rather than a literal.

## Sequence this unblocks
Owner deploy, then `POST /api/v2/openrig/seat-types/seed`, then the per-seat re-pin through R1
(`PUT /api/v2/openrig/rooms/{room}/seats/{seat}/pin`) at `1.4.3`.
