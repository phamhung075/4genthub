## Changed

- `agenthub_go/fastmcp/seat_management/domain/seatrenderer`: the render is a resolution RECORD, not a delivery (`RULING-seat-context-delivery-model.md`, R1). `RenderSeat` stops writing `agent.yaml`, a `startup.files` list, a `skills/<slug>/SKILL.md` list and `guidance/role.md`, and keeps what has a reader: the seat's guides and limits in `AGENTS.md`, the claude mcp and settings fragments, the codex rules file, and the omp MCP document with its startup setting. A module that is not a `guide-<seat>` block — a role, a rule, a document, a skill — is recorded by the resolver and written nowhere; `modulecontent`'s doc no longer claims those kinds render.

### Measured, so the retirement is checkable

- The live hub renders 12 files for `4genthub-min/go-dev` today (`call_seat`, hash `126260a9…`): `agent.yaml`, `guidance/role.md`, `AGENTS.md`, the seven `skills/<slug>/SKILL.md` its refs name and the two runtime documents. Nine are the retired half; after this change the same seat renders `AGENTS.md` plus `runtime/omp-mcp.json` and `runtime/omp-config.yml`.
- The retired files were never installed: no `agent.yaml`, no `role.md` and no `guidance/` exists under the room root for any of the five seats, which is why the file half had no delivery to lose.
- L-2's hygiene line found no dangling ref to repair: every `module_refs` entry of the nine `seat-types/*.yaml` resolves in the live catalog (the seven skills above are the developer's own refs, rendered there), and `default_runtime: claude-code` against a seat running `omp` is the record-versus-live gap, not a defect.

### The absence is asserted, not assumed

- `seatrenderer/retired_file_half_absent_test.go` renders every runtime with a guide, a tool module and the platform's mcp block, requires that runtime's live files to appear first, then fails on any `agent.yaml`, `startup.files`, `guidance/` or `skills/` path — the shape `manage_agent_absent_test.go` uses for a retired tool. The landmark half is the vacuity guard: a render that produced nothing would satisfy the absence for the wrong reason.
- The tests that used the retired paths as their observable moved to the live channel: the seat-type create-route acceptance authors a guide beside the role module and asserts it reaches `AGENTS.md`; the published-module case publishes a guide; the version-pinning case observes a guide module; three pass-through fixtures name `AGENTS.md`.
