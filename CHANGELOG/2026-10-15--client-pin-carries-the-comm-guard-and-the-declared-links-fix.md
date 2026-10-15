## 2026-10-15 - Client pin carries the comm guard, the declaration fix and the sender-identity pin

### Changed
- `agenthub_client`: pin bumped `5bb6d9c` -> `ae3811c` (19 commits). It carries the comm guard that decides and audits on the send path (`01eaca8`), a pane never given a bare name with the reach inventory re-measured (`af26466`), the guard's native `4genteam` spellings (`892f867`, `8785915`), the T13 fixture half (`5a9a631b`), the declared-links acceptance case (`898cfcd`), the link-source measurement dated and scoped (`b4a6ffe`), and the send tests pinning the identity their fakes license (`ae3811c`).

### Testing
- The reviewer's gate (`agenthub_client/GATE-comm-guard-c5-verdict-2026-10-15.md`) measured the suite RED at `898cfcd` and GREEN at `ae3811c` in its own seat shell: `TestSendSocketAimsTheVerbAtThatDaemon` (`send_transport_test.go:199`) was refused by the communication policy because the sender's seat came from the ambient environment while the test pinned only `AGENTHUB_SESSION_NAME`; `ae3811c` pins room, seat and session name. The guard's notice path and its refusal path were both measured by mutating `allowedKinds[IntentNotice]`, which is the map the decision reads.

### Notes
- The guard is IN THE TREE at this pin, not ARMED in the running room: nothing has been rebuilt or installed from `main`, so the client the seats run is unchanged. The live `spec.json` still declares the `reviewer -> <dev>` pairs `delegates_to`; that table is the owner's decision (O9e), and branch `4genthub-min/declared-links` carries the two-row fix that lands after it.
