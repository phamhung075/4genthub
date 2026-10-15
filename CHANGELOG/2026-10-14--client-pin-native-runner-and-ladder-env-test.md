## Client pin moves to the native runner; the ladder reads owner-only categories from the environment

### Changed

- `agenthub_client` gitlink: d84da76 -> a118585 (`feat/support-agy-watch` with `4genthub-min/u2-native-runner` merged). The client
  keeps its state in `~/.config/4genthub`, has no 4genteam fallbacks and adds `4genteam decide`.

### Added

- `agenthub_go/fastmcp/server/httpapp/room_decisions_ladder_test.go`:
  `TestRoomDecisionServiceReadsOwnerOnlyCategoriesFromTheEnvironment` (`DECISION_OWNER_ONLY_CATEGORIES`).

### Tested
`go test ./fastmcp/server/httpapp/ -run TestRoomDecisionService`; U3 acceptance on `cutover-lab`, 124 pass, 0 fail.
