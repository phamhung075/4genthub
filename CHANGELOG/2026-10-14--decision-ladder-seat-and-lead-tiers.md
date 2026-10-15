## 2026-10-14 - The decision ladder: seat and lead tiers on the owner's Jev evaluator

### Added
- `POST /api/v2/decisions/evaluate`: one stateless ladder step for a seat or a lead. It returns `decided` with the answers when Jev's confidence is at or above `JEV_DECISION_THRESHOLD` (default 0.8) on every question, otherwise `escalate_to` the next tier with each question's recommended option.
- `agenthub_go/fastmcp/room_decisions/domain/decisions/ladder.go`: `Tier` (seat, lead, owner), `Category` (a free token, so any project names its own cases) and `OwnerOnlySet`.
- `agenthub_go/fastmcp/room_decisions/application/services/room_decision_ladder.go`: `RoomDecisionService.Evaluate` and `WithOwnerOnly`.
- `DECISION_OWNER_ONLY_CATEGORIES`: comma-separated categories a project adds to the built-in `credentials` and `spend`. These reach the owner whatever the confidence, and Jev is not called for them.
- `agenthub_client/skills/share/room-decision-request/SKILL.md`: a "Decision Ladder" section.

### Changed
- `JevDecisionLogEntry` carries `tier`, `category` and `outcome`; the owner path logs `tier: owner`.

### Testing
- `go test ./fastmcp/room_decisions/... ./fastmcp/server/httpapp/`: a seat at 0.9 decides, a seat at 0.6 escalates to the lead with its recommendation, a lead below 0.8 escalates to the owner, a `credentials` question at 0.95 reaches the owner with no Jev call, an evaluator error escalates, and the owner tier is refused.
- Not done: the `4genteam` client verb that calls the route, and setting `DECISION_OWNER_ONLY_CATEGORIES=omp_cap` for this project.
