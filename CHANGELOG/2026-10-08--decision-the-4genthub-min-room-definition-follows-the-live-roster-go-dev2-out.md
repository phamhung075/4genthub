## Decision: the 4genthub-min room definition follows the live roster (go-dev2 out, architect in), before any apply

### Added
- `ai_docs/architecture-design/decision-team-json-live-roster.md`: `scripts/team/4genthub-min/team.json`, `SEAT_ROLES` and the guide shelf still declare go-dev2 and have no architect seat, while the live rig is the opposite. `openrig_team_setup.py apply` only creates and deletes nothing, so its first run would build a removed seat and never create a live one. `openrig_seat_policy.py apply` stops at the first missing state directory, so the code fix has to land before the stale `~/.openrig/state/omp/4genthub-min-go-dev2@4genthub-min` is moved away (an owner step). Recommends aligning the definition now. The acceptance commands were run at HEAD: 12 passed, seedlibrary ok, and the scope grep prints 18 lines that must go to 0.
- `ai_docs/index.json`: regenerated with the note's entry.
