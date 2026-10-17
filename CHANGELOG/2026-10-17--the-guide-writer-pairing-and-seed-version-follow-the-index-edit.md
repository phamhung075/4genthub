## 2026-10-17

### Fixed
- `c2bf3b23` edited `blocks/guide-writer.md` (the retired `ai_docs/index.json` line) without re-recording its digest, so `go test ./...` failed on `main` (CI run 39051049660): `guides.lock.json` recorded `591698b1d8d6`, the shelf carries `6f2d001e82a5`.
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/guides.lock.json`: `guide-writer` `sha256` re-recorded; `source_sha256` is re-recorded too, because `TestBlockDriftNamesEveryWayAFileCanMove` treats the shelf as the faithful copy.
- `agenthub_go/fastmcp/seat_management/domain/seedmap/seedmap.go`: `seedVersion` 1.4.15 -> 1.4.16, because a stored seat type version is immutable.
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/seedcontent.lock.json`: re-stamped with `-update-seedcontent-lock`.
- `agenthub_go/internal/repoguards/docs_only_guard_test.go`: the harness runs the guard in a real repository with the paths staged, because `e8a3cba4` made the guard read `git diff --cached` and the old harness (arguments, no repository) exited 129.

### Tested
- `cd agenthub_go && go test ./...`
