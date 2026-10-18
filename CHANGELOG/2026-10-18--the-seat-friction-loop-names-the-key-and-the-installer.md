## The seat-friction-loop design names the front-matter key and the installer

### Changed

- `ai_docs/operations/seat-friction-loop.md` §1: the front-matter key is `metadata.agenthub` — it read the mangled
  `metadataconfig/4genthub` — and the optional keys named are the ones the tree writes: `allowed-tools`, `license`,
  `metadata.agenthub`, `seat-type-version`.
- §1: delivery is `install_seat_skills` (`agenthub_client/rust/agenthub-runtime/src/supervisor/mod.rs:411`, called
  at seat start at `:733`): it clears `<seat dir>/skills/` and copies the resolved tree share → room → seat. The
  `sync rig ROOM` claim, its `agent.yaml` declarations and the second omp copy (`internal/clientseat/skills.go`)
  are gone, and the format citation moves from the deleted `internal/clientskills/tree.go` to
  `rust/agenthub-runtime/src/skills/mod.rs`.
- §10: the inventory keeps its 2026-10-11 counts as the baseline and adds the 2026-10-18 measurement — `share/` 21,
  `client/` 6, `rooms/4genthub-min/` 16 (15 seat-level across 5 seat dirs plus the room-level
  `architect-ecosystem-review`), 43 `SKILL.md` in the tree — because `rooms/` was described as an empty
  placeholder and no longer is. The four cloud leftovers drop through the per-start install, not a `sync rig` run.

### Measured

- Front-matter census over `agenthub_client/skills/**/SKILL.md` (43 files): `name` and `description` on all 31;
  `allowed-tools` 2, `license` 1, `metadata.agenthub` 7, `seat-type-version` 5. `skills/share/jev-decisions/SKILL.md`
  `:4-5` writes `metadata:` then `agenthub:`.
- The `sync` verbs are pull, messages, connector, bundle, switch, install-checker, offline-install and respawn
  (`agenthub_client/internal/clientsync/sync.go:22-46`); `rig` and `room` are absent, and the file says why.
- `install_seat_skills` (`supervisor/mod.rs:411`) reads `AGENTHUB_CLIENT_SKILLS`, clears `<seat dir>/skills/` and
  copies each resolved skill, so an absent skill does not linger.

### Testing

No test: documentation, checked against the code each corrected sentence cites. Carried by go-dev through
`scripts/git-hooks/git_commit_capture.py` in one pathspec commit with the gitlink pin: the docs-only guard judges
the path set, and `agenthub_client` is not a doc path, so the seat's commit clears it.
