## The seat roles and the shared modules say room, where the text said rig

### Changed

- The nine seat-type roles (`fastmcp/seat_management/domain/seedlibrary/seat-types/*.yaml`) and the
  three shared modules (`shared-modules/comm-guard-skill.md`, `guide-common.md`, `mcp-usage.md`)
  say **room** wherever the text said rig: "the seats your room defines", "the seat your room names
  for review", "in the room", `<room>/<seat>`, `<room>/integration`, `4genteam send <room> <seat>`.
  Text only - no CLI verb, flag or argument changed, so every command a seat copies still runs as
  written. Owner ruling 2026-10-20: the unit is the room.
- `fastmcp/seat_management/domain/seedmap/seedmap.go`: `seedVersion` 1.4.19 -> 1.4.20, with the
  reason on the constant. A stored seat type version is immutable and names one content set, so a
  content change is a new version; `seedcontent.lock.json` gains the 1.4.20 record and keeps 1.4.19.
- `guides.lock.json`: the `guide-common` entry re-records the pairing - `sha256` and
  `source_sha256` both move to the new digest (`c8bca63a...`). The interim source
  `ai_docs/operations/seat-guides/_common.md` was retired earlier; the drift fixture rebuilds it
  from the shelf copy, which is the pairing the lock has to hold.
- `agenthub_client/skills`: the same text in the seat role skills, `share/seat-worktree/SKILL.md`
  and `share/safe-file-removal/` (`SKILL.md`, `EXAMPLES.md`, `TEMPLATES.md`, `VALIDATION.md`).
  That half is a documentation-only diff, so it does not commit from a seat
  (`scripts/git-hooks/git_commit_capture.py`'s docs-only check: `is_document` counts any `.md`);
  the lead lands it with the client pin.

### Testing

- `go test ./... -count=1` in `agenthub_go`: **exit 0**, 138 packages ok.
- `go test ./... -count=1` in `agenthub_client`: **exit 0**, 35 packages ok.
- `gofmt -l` over the two changed Go files: empty.
- The lock regeneration ran the documented procedure:
  `go test ./fastmcp/seat_management/domain/seedlibrary -run TestSeedVersionNamesOneContentSet --args -update-seedcontent-lock`.
- `TestBlockDriftNamesEveryWayAFileCanMove` failed on the first pass with
  `guide-common: ai_docs/operations/seat-guides/_common.md source-differs` - it rebuilds the retired
  interim file from the shelf copy and compares it to the recorded digest, so the recorded
  `source_sha256` had to move with the block. Green after the re-record.
