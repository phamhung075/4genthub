# 2026-10-10 — NEXT_GEN records the guide-common rollout decision

### Changed
- `agenthub_go/NEXT_GEN.md` (Checklist): new open item. guide-common reaches running teams through seedVersion 1.4.2 plus a re-pin of the min and client teams. ab re-pins after its A/B experiment. The lead accepted this at 20:04Z.
- The item also records a verified gap: `team apply` neither seeds a new version when every slug is already stored nor re-pins an existing seat (client `internal/clientteam/team.go:151`, `plan.go:234`). The re-pin path is still open with the lead.

Docs only; no code or tests changed.
