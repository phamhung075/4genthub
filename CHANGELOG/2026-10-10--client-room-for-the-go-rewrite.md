## Unreleased — a room and team for the Go rewrite of the client

### Added
- `scripts/team/4genthub-client/team.json` and `mission.md`: room `4genthub-client` with five seats (`lead`, `go-dev-a`, `go-dev-b`, `reviewer`, `writer`) on `omp` / `deepseek/deepseek-flash`. Module slugs carry a `client-` prefix, so no module of another room is written. The mission module `client-go-mission` states the owner decision: the client becomes Go (Rust only for modules), Python is removed, in six phases, with the Go client moving into the client repo as its own module.
- Applied with `4genteam team apply --team scripts/team/4genthub-client`, materialized with `4genteam sync rig 4genthub-client`, launched with `rig up`; all five seats reported `working`. The lead was briefed with `rig send`. Room `4genthub-min` was not touched.
