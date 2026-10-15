# Room Decisions Jev AI Selection & Human Escalation Routing

Route all team room decisions through Jev AI (TypeSafe AI System One `jev-1.13.0`). Automatically answer decisions when evaluation confidence is $\ge 0.8$ (configurable via `JEV_DECISION_THRESHOLD`), and keep decisions in `pending` for human operators in the 4genthub Decision Requests UI when confidence is $< 0.8$. All Jev evaluations and metrics are logged to `jev_decisions.log` for offline benchmarking.

## Summary of Changes

- **AI Choice Evaluation**: Extended `TypeSafeJevClient` with `SelectDecisionChoices`, mapping human decision questions and choices into System One choice requests sent to `/v1/systemone` using Bearer authentication and returning confidence-scored choice selections.
- **Automated Decision Answering Hook**: Enhanced `RoomDecisionService` with `WithEvaluator` and an automated evaluation hook during decision creation. If all questions reach $\ge 0.8$ confidence (or custom threshold), options are auto-answered and marked `answered`. If confidence is below threshold, questions remain unanswered so the decision stays `pending` for human resolution.
- **Benchmark Logging**: Implemented structured JSON logging (`JevDecisionLogEntry`) recording timestamp, decision ID, user/room, questions, chosen options, confidence scores, and auto-answer outcome to `jev_decisions.log` (configurable via `JEV_DECISION_LOG_PATH`).
- **Dynamic Configuration via .env**: Wired `newRoomDecisionService` in `room_decisions_mount.go` to dynamically read `JEV_DECISION_THRESHOLD` (default 0.8) and `JEV_DECISION_MODEL` (default `jev-1.13.0`) from `~/.config/4genthub/.env`. Documented in `.env.sample` and `agenthub_client/.env.sample` that seat LLMs (Gemini, DeepSeek, Claude Code) run on the client PC and Jev tokens are used for AI calls/sessions, while the server does not handle or host client LLMs.
- **API Reference Synchronization**: Re-generated `agenthub-frontend/src/docs/apiReference.ts` to keep the committed API specification in exact alignment with server routes.
- **Test Suite Updates**: Added unit tests in `typesafe_jev_client_test.go` and `room_decision_service_test.go` verifying automated selection, pending human escalation, and benchmark log file generation. All tests across `agenthub_go` pass cleanly.
