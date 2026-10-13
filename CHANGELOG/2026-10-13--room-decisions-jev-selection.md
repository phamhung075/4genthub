# Room Decisions Jev AI Selection & Human Escalation Routing

Route all team room decisions through Jev AI (TypeSafe AI System One `jev-1.13.0`). Automatically answer decisions when evaluation confidence is $\ge 0.8$, and keep decisions in `pending` for human operators in the 4genthub Decision Requests UI when confidence is $< 0.8$.

## Summary of Changes

- **AI Choice Evaluation**: Extended `TypeSafeJevClient` with `SelectDecisionChoices`, mapping human decision questions and choices into System One choice requests sent to `/v1/systemone` using Bearer authentication and returning confidence-scored choice selections.
- **Automated Decision Answering Hook**: Enhanced `RoomDecisionService` with `WithEvaluator` and an automated evaluation hook during decision creation. If all questions reach $\ge 0.8$ confidence, options are auto-answered and marked `answered`. If confidence is below threshold, questions remain unanswered so the decision stays `pending` for human resolution.
- **HTTP App Wiring**: Configured `newRoomDecisionService` in `room_decisions_mount.go` to instantiate `TypeSafeJevClient` and attach it as the evaluator using model `jev-1.13.0` and threshold `0.8`.
- **API Reference Synchronization**: Re-generated `agenthub-frontend/src/docs/apiReference.ts` to keep the committed API specification in exact alignment with server routes.
- **Test Suite Updates**: Added unit tests in `typesafe_jev_client_test.go` and `room_decision_service_test.go` verifying automated selection at $\ge 0.8$ and pending human escalation at $< 0.8$. All tests across `agenthub_go` pass cleanly.
