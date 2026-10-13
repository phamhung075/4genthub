# Jev evaluator tests no longer write to the operator's decision log

### Fixed
- `agenthub_go/fastmcp/room_decisions/application/services/room_decision_service_test.go`: `TestRoomDecisionServiceEvaluatorAutoSelectAndPending` now points `SetJevDecisionLogPath` at a temp file for all its subtests. Two subtests (`auto_selects_when_confidence_gte_threshold`, `leaves_pending_when_confidence_lt_threshold`) used the default path, so every `go test` run appended fixture rows (`rig-1`, `seat-1`, `rd-0001`) to `~/.config/4genthub/jev_decisions.log` and polluted the benchmark data.

### Testing
- `go test -count=1` for `room_decisions`, `server/httpapp`, `ai_services`: pass; the real log stayed at 1382 bytes across the run before the 4 existing fixture rows were removed.
- Live `POST /v1/systemone` with `jev-1.13.0` and one choice question returned HTTP 200 with `choice` and `confidence` in the shape `SelectDecisionChoices` parses.
