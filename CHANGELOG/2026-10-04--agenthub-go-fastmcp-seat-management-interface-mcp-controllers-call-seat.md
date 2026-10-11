### Added

**call_seat: resolve one exact seat** (2026-10-04)

Owner decision: the tool is `call_seat`, not `call_agent` — the name should say which layer it reaches. 4genthub stores the seat and its context, OpenRig runs the seat, and the brain (claude, openai, gemini, deepseek) is the occupant.

- `agenthub_go/fastmcp/seat_management/interface/mcp_controllers/call_seat_controller.go`: the `call_seat` MCP tool over a one-method `SeatResolver`. It resolves one seat by room and seat key through `SeatResolutionService.ResolveSeat` and returns the resolved snapshot hash, runtime, policy and rendered files. Failures are `success=false` with the reason, matching `manage_seat`.
- `agenthub_go/fastmcp/server/httpapp/call_seat_wiring.go`: wires it to the same resolution source the resolved-seat REST route uses, built per call, so an unset `AGENTHUB_PUBLIC_URL` is a tool-call failure with that reason rather than a failure to start the server (the route behaves the same way).
- `ddd_compliant_mcp_tools.go`, `app.go`, `mcp_routes.go`: registration, dependency and dispatch.
- Tests: `call_seat_controller_test.go` (resolve, input failures, tenant failure, tool registration, input schema) and `call_seat_mcp_test.go` (tools/list publishes it with the right schema and required fields; tools/call resolves a seat end to end; a resolver failure is reported as a tool result).
- `mcp_routes_test.go`: the golden file is the Python parity registry, so `call_seat` joins `manage_seat` as a Go-only tool excluded from it with the reason recorded, and covered by its own route tests.
- Checked: `gofmt` clean, `go vet ./...` clean, `go test ./...` green.
- Not done, deliberately: `call_agent` is untouched. Removing it is T6 (it also carries the routes, `-seed-agents`, the library path utils and the health field) and is the immediate follow-on so that two tools for one job do not coexist.

**omp runtime supported: a seat can now run DeepSeek** (2026-10-04)

- `agenthub_go/fastmcp/seat_management/domain/resolver/runtime.go`: `RuntimeOmp = "omp"` added to the one runtime list and to `CheckRuntime`, so API validation, rigspec, the seed library and the renderer all accept it. `omp` (Oh My Pi) is the runtime that carries a non-Anthropic provider: OpenRig passes a seat its provider key only when the model is written `provider/id` such as `deepseek/deepseek-flash`, which is how the DeepSeek supervisor seat in `~/.openrig/agenthub-seats/4genthub-deepseek/` runs. `pi` stays unsupported deliberately (no evidence, and no `pi` installed here).
- `agenthub_go/fastmcp/seat_management/domain/seatrenderer/renderer.go`: `receivesClaudeFragments` narrowed from "not codex and not agy" to `runtime == claude-code`, and the comment above the MCP fragment updated. Behavior for the existing runtimes is unchanged; the inversion makes a runtime added later default to no Claude MCP or settings fragment instead of silently receiving one.
- `agenthub_go/fastmcp/seat_management/interface/mcp_controllers/manage_seat_controller.go`: the `manage_seat` tool description and the `runtime` parameter text name all four runtimes instead of `claude-code|codex`.
- Tests corrected to the new truth: `domain/resolver/runtime_test.go` (`omp` moves from the invalid list to the valid one; `pi` stays invalid, with a comment saying why), `domain/repositories/names_test.go`, `domain/seatrenderer/renderer_test.go` (`TestRenderSeatRigValidate` gains an `omp` subtest), `server/httpapp/seat_status_mount_test.go`, and `server/httpapp/seat_admin_mount_test.go`, where `TestSeatAdminSetOccupantRuntimeNamesSupportedRuntimes` had asserted `omp` was a 400 and now asserts it is accepted while `pi` is still a 400 naming all four runtimes. Found by the suite rather than by reading: that assertion failed on the first full run.
- Checked: `gofmt -l fastmcp` clean, `go vet ./...` clean, `go test ./...` green. The `omp` subtest passes through the real `rig agent validate`, so a 4genthub-rendered omp seat is accepted by OpenRig itself.
- `agenthub_go/NEXT_GEN.md`: Request 16's open item, T3, and the "DeepSeek seats via OpenRig `omp`" section record this change; the same edit records the owner-stated 167-hour agy limit and the supervisor guidance change that follows from it. T3 stays open on `set_occupant` on production and the occupant panel.

**Recorded the DeepSeek supervisor seat and the stale runtime registry** (2026-10-04)

- `agenthub_go/NEXT_GEN.md`: a "DeepSeek seats via OpenRig `omp`" section (rig `4genthub-deepseek`, one seat `supervisor`, runtime `omp`, model `deepseek/deepseek-flash`, `builtin:yolo` required for a headless launch; the cloud cannot store this seat until `RuntimeOmp` is added to the one runtime list), the finding that `rig ps --nodes` and the rig's `rig.yaml` report runtime `agy` for all nine `4genthub-dev` seats while those seats emit Claude Code statusline samples, and the T3 clarification that `CheckRuntime` already rejects an unsupported runtime with an explicit error.
- Re-verified by the supervisor 2026-10-04 before recording: `rig usage series --lane provider_window --since 2026-10-04T05:00:00Z` returned 588 samples, emitted by all nine `4genthub-dev` seats and none by `4genthub-min`; `resolver/runtime.go:17-24` returns `unsupported runtime %q: supported runtimes are claude-code, codex, agy`.

**G5 ticked; its check wording corrected** (2026-10-04)

- `agenthub_go/NEXT_GEN.md` (G5): ticked after `fab45cee` (service test) and `c92121cf` (overlay `add` needs a concrete version). The check text is corrected, not just met: it said a module publish changes a follow-latest seat, but the owner's policy is that nothing moves until a new resolved version is published, so a follow-latest seat moves with a new seat type version. Open lines kept: fakes only, no Postgres run, client lock (`--update`) not re-tested.

**G2 check re-run and ticked** (2026-10-04)

- `agenthub_go/NEXT_GEN.md` (G2): the three clauses of the check (same modules for `claude-code` and `codex` pass `rig agent validate`, resolving twice gives the same hash, a `remove` overlay removes a base module) were re-run and pass; ticked with the evidence and two open lines. The follow-latest sentence is reworded: only the seat type follows latest, module and overlay refs are concrete since `c92121cf`. Documentation only, no code.

**Open owner decision D6 recorded: source of the assignee names** (2026-10-04)

- `agenthub_go/NEXT_GEN.md` (D6): the assignee pickers use a hard-coded 42-name list in `agenthub-frontend/src/api.ts:389`; per the debugger inventory 2026-10-04, 14 names are not in the agent library, `GET /api/v2/agents/metadata` serves 4 static agents, and six agent routes are dead and being deleted. Recommendation recorded: use the user's seat keys. Documentation only; no behavior change, no tests.

**F4 client bridge check recorded in NEXT_GEN.md** (2026-10-04)

- `agenthub_go/NEXT_GEN.md` (F4): records the tester's scratch-environment run (evidence sections 1 to 7). Verified: edge-order launch of a 3-seat rig, reported state `in_sync` with hash equal to `expected_hash` and the pin, a seat stopped with `rig seat stop` shown as `stopped`, relaunch of a stopped seat, recovery of a killed-claude seat with `rig seat launch --fresh --stop` (`rig seat clean` is refused while the tmux session lives), `seatcheck` deny and delivery run with a live scratch seat's environment. Caveat recorded: `seatcheck` reads `$HOME/.openrig/agenthub-seats`, so a scratch run must override `HOME`. Open, owner decision: a seat that dies any way other than `rig seat stop` shows `blocked`, not `stopped`; accept it and reword the check, or change the bridge. Not run: Claude-level deny of `rig send` typed into a seat prompt, herdr agents, codex/agy rigs, bundle launch, production. F4 stays unticked. Documentation only; no behavior change, no tests.

**G5 version policy tested through the resolution service** (2026-10-04)

- `agenthub_go/fastmcp/seat_management/application/services/seat_resolution_service_test.go`: `TestResolveSeatModulesMoveOnlyWithANewSeatTypeVersion`. Test only, no behavior change: publishing a module version moves no seat, a new seat type version moves only follow-latest seats, a pinned seat keeps its snapshot hash. `agenthub_go/NEXT_GEN.md` (G5) records the evidence and the open lines; the box is not ticked.

**Renderer: stale codex defect record corrected, agy covered by the runtime test** (2026-10-04)

- `agenthub_go/NEXT_GEN.md` (G3): the "open defect" that a seat switched to codex fails to render while `comm-guard` is present is recorded as fixed (`297ef2ed` for codex, `3caf088f` for agy), with the 2026-10-04 evidence (all 9 seat types render on claude-code, codex and agy). Documentation only.
- `agenthub_go/fastmcp/seat_management/domain/seatrenderer/renderer_test.go`: `TestRenderSeatSameModulesOnBothRuntimes` now loops codex and agy. Coverage only: no behavior changed, and the test passed before the edit.

**T1 open line updated with the tester run** (2026-10-04)

- `agenthub_go/NEXT_GEN.md` (T1): cites the tester's scratch-rig run (real Claude seats under `yolo`, which passes `--dangerously-skip-permissions`: `rig send` and tmux `send-keys` denied, `seatcheck` deny exits 3, delivery works) and keeps the open lines: deny under the default policy not tested, nothing verified on production, Codex and agy seats have no deny. Documentation only; no behavior change, no tests.

**delegate-deepseek module 1.1.0: chef/worker wording** (2026-10-04)

- `scripts/team/4genthub/delegate-deepseek.txt`: opens with the owner's culture rule (Request 17): each seat's session is the chef (takes the demands, decides, answers the owner and the lead, accountable for the result); `deepseek_agent` workers only do bounded jobs for it, get priority for delegable work, and their output is never forwarded unreviewed. `scripts/team/4genthub/team.json`: module version `1.0.0` to `1.1.0`, so the next `openrig_team_setup.py apply` publishes a new immutable version and the company overlay pins it; version 1.0.0 is not edited. Not applied to any server.

**Team culture recorded as an owner demand** (2026-10-04)

- `agenthub_go/NEXT_GEN.md`: "Request 17" (added in `f5bb43f0`): each seat's session is the chef (takes demands, decides, answers the owner and the lead, accountable for the result); `deepseek_agent` workers do bounded jobs, get priority for delegable work, and their output is never forwarded unreviewed. Documentation only; no behavior change, no tests.

**Support for agy (Gemini/Antigravity) runtime** (2026-10-03)

- `agenthub_go/fastmcp/seat_management/domain/resolver/runtime.go`: `CheckRuntime` now accepts `"agy"`.
- `agenthub_go/fastmcp/seat_management/domain/seatrenderer/renderer.go`: `RenderSeat` uses a shared predicate to explicitly reject both `codex` and `agy` runtimes from receiving Claude fragments, treating `agy` similarly to `codex`.
- `agenthub_go/fastmcp/seat_management/domain/repositories/names.go`: `ValidateOccupant` rejects Claude models on `codex` only, while allowing them on `agy` (which supports Claude models such as `claude-opus-5-5-high` and `claude-sonnet-5-5-medium` alongside Gemini and GPT models).
