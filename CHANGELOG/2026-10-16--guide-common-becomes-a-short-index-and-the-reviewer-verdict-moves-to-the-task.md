## guide-common becomes a short index and the reviewer verdict moves to the task

### Changed
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/shared-modules/guide-common.md`: rewritten as an index (how to call a tool, the loop, the five rules, deepseek offload, writing style, stuck handling). Removed "Commits in the shared tree", "Startup and the approval gate", the pytest block and the manage_subtask/manage_context ritual. Commits now follow the `seat-worktree` skill: own worktree, stage normally, main changes only by the lead's gated merge.
- `blocks/guide-reviewer.md`: the verdict goes in the task or queue row; no `GATE-*.md` file; no `vite build` (tsc only). `blocks/guide-lead.md`: no `vite build`, a PASS is not re-verified; both at most 20 lines.
- `seedmap.go` seedVersion 1.4.11 -> 1.4.12; `guides.lock.json` and `seedcontent.lock.json` re-recorded.
- Tests `guide_commit_form_test.go`, `guide_script_tests_test.go`, `seatrenderer/library_guide_render_test.go` assert the new text (the pytest and no-pipe rules now live in the reviewer block).

### Impact
Seats get the new guide only after the owner pushes, the pin moves and the room is reseated.

### Testing
`go build ./... && go vet ./... && go test ./...` in `agenthub_go`, and `go run ./cmd/blockdrift -root ..`.
