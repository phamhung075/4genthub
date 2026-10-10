## The last seat without a guide gets one, and the `architect` overlay stops being empty

### Added
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/blocks/guide-architect.md` (**NEW**): `architect` was the single seat of ten with no `guide-*` module, no `policy-*` module and no overlay, while every other seat has all three and its `agent_ref` is `local:agents/architect` — the same shape as lead, go-dev, reviewer, fe-dev, web-dev and writer. The guide owns design decisions, records them where the next reader finds them, and hands implementation to the development seat. Drift, not design: the pair was never authored when the seat arrived.
- `scripts/team/4genthub-min/policy-architect.json` (**NEW**, role `architect`): the room's deny set copied **verbatim** (so every module keeps the same commit-form siblings), plus `edit` and `ast_edit` denied with the sibling "you do not implement. Write the decision note instead, and hand implementation to the development seat." That is the seat type's own "No implementation" rule expressed where the runtime enforces it, and it is the shape `policy-reviewer.json` already uses for its two refusals.
- `ai_docs/operations/seat-guides/architect.md` (**NEW**): the interim source for that block. The library pairs a block with its interim copy and fails on any divergence, so the two files are byte-identical — sha256 `b586aeef61724e7b41b79ad9fd10e13f54e01549d7277671d7f1d7a5b8120835` for both — and `guides.lock.json` gains the pairing entry, its counts moving ten → eleven.

### Tested
- The apply dry-run composes all three: **40 steps before → 43 after**, naming `guide-architect@1.0.0`, `policy-architect@1.1.0` and `overlay seat architect`. No API call, no publish, no version moved.
- `go test ./fastmcp/seat_management/domain/seedlibrary/... ./modulecontent/... ./seatrenderer/...` → all **ok**: the block loads, renders into the seat's context verbatim with its heading appearing once, the lock pairing verifies and the content gate accepts the policy.
- `sha256sum` over the block and its interim source → identical, `b586aeef…`.
- The policy was additionally checked against the renderer's own rule by hand (role non-empty, every rule has a match, every approval is allow or deny, every denial has a sibling): no violations, 30 shell rules and 5 tool rules.

### Not in this commit
- The `team.json` rows that reference the two new modules (`+guide-architect@1.0.0`, `+policy-architect@1.1.0`, `+overlay seat architect`). That file is `MM` in a shared index — it carries another work's nine-guide re-point as well — so a pathspec commit cannot take one without the other. It lands as a single commit naming both.
