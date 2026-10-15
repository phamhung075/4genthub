## 2026-10-15 - client pin carries the room-requires-links guard

### Changed
- `agenthub_client` pin: `729153d` -> `e41d827`. `feat/room-requires-links` (`f5514c1`) is merged into the client's `main`: a `team.json` with more than one seat and an empty `links[]` is now a usage error at `loadTeam`, so `4genteam up --team DIR` and `team apply` refuse before anything is sent (`a room of N seats needs its links; with none, no seat can message another and the topology has no edges`). One reader — `internal/clientteam/plan.go` — serves `up` (`roomspec.go:22`), `team apply` (`team.go:150`) and `prune`.
- The cherry-pick is not a plain replay: `skills/client/spawn-team/SKILL.md` had moved on since `f5514c1` was written, so the branch's paragraph (a `rig up <spec.yaml>` era) was re-expressed in the file's current `4genteam up <room> --team DIR` list — item 1 now carries the required-`links[]` rule, the minimum edge set and the after-the-fact check. The branch is preserved as `4genthub-min/client-links`.
- Details: `agenthub_client/CHANGELOG/2026-10-15--a-room-of-several-seats-is-refused-without-its-links.md`.

### Testing
- In the client: `go test ./...` — 29 packages ok, exit 0; `go test ./internal/clientteam` covers the two-seat/no-link refusal plus the one-seat and one-link controls.
- Not pushed: the client's `main` is a local fast-forward; the remote is the owner's gate.
