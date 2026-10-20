## The nine seat types drop their curated module_refs

Ruling of record: `seats/architect/RULING-2026-10-20-seat-type-module-refs.md` (architect, 2026-10-20).

### Changed

- `fastmcp/seat_management/domain/seedlibrary/seat-types/*.yaml` (nine files): the `module_refs` block
  is gone - 52 refs, 24 distinct names, all `slug@1.0.0` from the OpenRig inventory. None is replaced:
  six have an exact live share skill, six are rehomed in the client skill tree, and twelve have no live
  carrier (the ruling's keep/drop table records each).
- `fastmcp/seat_management/domain/seedmap/seedmap.go`: `Spec.ExtraRefs` and the append that put curated
  refs after the authored ones are removed; `Seed.ModuleRefs` is now exactly `Seed.Modules`. `seedVersion`
  1.4.20 -> **1.4.21** with its note line. (The ruling says 1.4.20; that number was already recorded by
  `3b49c580`, the room/rig text change earlier the same session, and a recorded content set is immutable -
  so this change is 1.4.21.)
- `fastmcp/seat_management/domain/seedlibrary/seedlibrary.go`: `seatTypeFile.ModuleRefs` and the parse
  loop go; the unused `repositories` import goes with them. `decoder.KnownFields(true)` means a file that
  still carries `module_refs` is now refused by name ("field module_refs not found"), so the trap cannot be
  re-entered by the next author.
- `fastmcp/seat_management/application/services/seat_seeder.go`: the ref-verification loop STAYS - it still
  guards the authored modules against a store that fails to round-trip, and against a hand-built `Seed` -
  with its comment corrected: it no longer describes curated refs to publish first.
- `ai_docs/core-architecture/seat-skills.md:149`: the sentence that pointed at the inventory now says the
  two inventory files are deleted and that the seed library, this file and the client pin are all the hub
  holds about a seat's skills.

### Removed

- `ai_docs/agent-system/skill-library.md` and `ai_docs/agent-system/skill-library.json` (the 52-skill
  inventory and its curated/unused split). Nothing wired a seat from it after the refs went, and the one
  paragraph the change had put in the `.md` was the only remainder of its use as history.
- `TestFromSpecExtraRefs` (`seedmap_test.go`) - the behaviour it pinned no longer exists.
- `TestSeedSeatTypesSucceedsWhenTheCatalogHasTheRefs` (`seat_seeder_test.go`) - it asserted "authored plus
  the two curated", a shape a loaded seed can no longer produce.

### Changed (tests)

- `seedlibrary_test.go`: the `skillInventory` struct and `loadSkillInventory` are deleted with the JSON they
  read, and `TestLoadEmbeddedSeedsCarryOnlyAuthoredModules` drops the `curated` set and its "a curated name
  must not be wired" check - the ref check against the seed's own modules is what remains.
- `scripts/tests/test_team_definition.py`: the `INVENTORY` constant, `_curation_gaps` and
  `test_the_inventory_curation_accounts_for_every_skill` are deleted; the case existed only to keep the
  hand-maintained curation honest, and the file it read is gone.
- `TestLoadEmbeddedSeedsCarryCuratedSkillRefs` -> `TestLoadEmbeddedSeedsCarryOnlyAuthoredModules`: every
  ref names a module the seed authors, no ref is a name from the retired inventory, no ref repeats, and the
  count equals the authored module count.
- The `bad module ref` parse case -> `module_refs refused`: the key itself is now the error.
- `TestSeedSeatTypesRefusesMissingRef` keeps its assertion; its comment now says what it guards.

### Testing

- `go test ./fastmcp/seat_management/... -count=1`: exit 0.
- `go test ./... -count=1` in `agenthub_go`: **exit 0**, 138 packages ok.
- `go build ./...`: clean. `gofmt -w` applied to the one edited test file.
- `seedcontent.lock.json`: the 1.4.21 record written by
  `go test ./fastmcp/seat_management/domain/seedlibrary -run TestSeedVersionNamesOneContentSet --args -update-seedcontent-lock`.
- Not run here: the ruling's live-hub acceptance (`POST /api/v2/seat-types/seed` on a clean catalog, the
  resolved snapshot's module list, the rendered file list). The seeder test with an empty fake catalog is
  the same assertion in-process; a live seed would write 1.4.21 seat-type versions onto the running hub,
  which this seat does not do unasked.
