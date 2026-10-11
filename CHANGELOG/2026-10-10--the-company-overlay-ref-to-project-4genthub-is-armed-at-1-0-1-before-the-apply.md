## The company-overlay ref to project-4genthub is armed at 1.0.1 before the apply

### Changed
- `scripts/team/4genthub/team.json:9`: module `project-4genthub` version `1.0.0` -> `1.0.1` (row `9651609a`). One line, nothing else in the file.

### Why it lands before the apply
- `4genteam team apply` publishes changed module content at the next patch (`agenthub_client/internal/clientteam/cloud.go` resolveModules, `nextPatch`). The repo text of `project-4genthub.txt` differs from the stored 1.0.0, so the apply publishes it as 1.0.1.
- The company overlay it then sends (`PUT /api/v2/openrig/overlay`, `plan.go:244-249`) takes each module's version from `team.json` (`overlayBody`, `plan.go:165-178`), not from the advanced version.
- Left at 1.0.0, the apply would publish 1.0.1 and then re-pin the overlay to 1.0.0. That publish is referenced by nothing: the run reports success and no seat changes. With 1.0.1 here, the same apply publishes and moves the ref in one run.

### Expected intermediate state, not a defect
- The ref is ARMED and inert. Until the principal's apply runs, the repo declares 1.0.1 while the stored company overlay still pins 1.0.0, and every served snapshot keeps the 1.0.0 text, including `(23 known pre-existing errors)`. No publish, apply, sync rig, or rig/agents edit was made.

### Blast radius of the apply
- The company overlay is user-wide (`seat_resolution_service.go` overlayStack, scope company, room "" and seat ""). It sits under every seat of every room: 4genthub-dev, 4genthub-min and smoke re-resolve together.
- 4genthub-min's own `team.json` names no company overlay and does not need to: apply skips an empty `company_overlay`, so the min room inherits this one.

### Testing
- `python3 -c json.load(...)` parses the file; `project-4genthub` reads `1.0.1`; `company_overlay` is unchanged. A grep of scripts, agenthub_client and agenthub_go finds no other pin of this version (one test cites the `.txt` path only).
