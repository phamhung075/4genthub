## The safeguard frame says room_safeguard, and the copy says room

Slice C of `DECISION-2026-10-20-rig-gone.md` (architect, 2026-10-20): the hub's safeguard push names
`room_safeguard` and carries `room`, and the two user-visible lines that named a rig say room.

### Changed

- `agenthub-frontend/src/types/websocket-protocol.ts`: `RigSafeguardAlertPayload` ->
  `RoomSafeguardAlertPayload`, its wire key `rig?: string` -> `room?: string` (the hub's own rename:
  `rig_safeguard` -> `room_safeguard` for the entity, `rig` -> `room` for the payload key). The
  interface's doc block names the entity the server now emits, and says why the row kind
  `room_safeguard` may sit beside a safeguard NAMED `roomguard`: the entity names the row, `safeguard`
  names the client axis, and neither is derived from the other (the six names, `roomguard` included,
  are unchanged).
- `agenthub-frontend/src/hooks/useRealtimeSync.ts`: the dispatcher's `case 'rig_safeguard'` ->
  `case 'room_safeguard'`, `handleRigSafeguardAlert` -> `handleRoomSafeguardAlert`, the cast to the
  renamed payload, and the inbox sentence's `rig <name>` part -> `room <name>`. The consumer reads
  only the new key: nothing here accepts both, because the owner's ruling forbids a dual emission.
- `agenthub-frontend/src/tests/hooks/test_useRealtimeSync_rigSafeguard.test.tsx` ->
  `test_useRealtimeSync_roomSafeguard.test.tsx`: the frame builder's `entity`/`entity_type`
  literals, the seven frame ids, the row fixture's `room: 'demo'` and the two expected inbox lines
  follow the wire. The six cases and their assertions are otherwise unchanged.
- `agenthub-frontend/src/pages/LandingPage.tsx`: step 3's description becomes the ruling's wording,
  "Pull the room and start the seats on your machine with 4genteam, the client that runs them."
  (`DECISION-2026-10-20-rig-gone.md`, Q10)
- `agenthub-frontend/src/components/seats/SeatLlmPanel.tsx`: the runtime-restart hint names the
  command that exists, `4genteam up <room>`, where it named the retired `rig up` (Q10).
- The `@` placeholder in session prose (Q7): `sessionTypes.ts:42` says the suffix is `@<room>` and
  names the canonical address `<room>-<seat>@<room>`; `SessionsPage.tsx:37` and the same sentence in
  `SessionsPage.test.tsx` spell it `@<room>`. No live session name changes and nothing parses a room
  out of a name - the never-derive rule stands.
- The prose that called the unit a rig: `useTopology.ts` (2 comments), `seatTypes.ts` (`MachineEdge`,
  `MachineStatus.edges`), `decisionApi.ts`, `RoomDecisionPanel.tsx`, `SessionList.tsx`,
  `sessionTypes.ts:50`, and the two comments and one test title in `useTopology.test.tsx` /
  `SessionsPage.test.tsx`. The `MachinesPanel.test.tsx` fixture machine id `'rig-box'` becomes
  `'machine-box'`; the fixture `'web-dev@other-rig'` becomes `'web-dev@demo-room'` (Q7's example).
- `TopologyPage.test.tsx`'s machine-report fixture room is named `Min Room`, not `Rig Room`: the last
  word-bounded `rig` in `src/` outside the document citations that moved in D-frontend below, and
  nothing asserts the name.

### D-frontend, in the same file set (the component's name and the document's)

- The 11 citations of `rigd-boundaries.md` now name `ai_docs/core-architecture/agent-boundaries.md`
  with their sections unchanged (2.3a, 3, 4.4, 7.3): `useRealtimeSync.ts:1011`,
  `websocket-protocol.ts:263`, `sessionTypes.ts:26`, `SessionsPage.tsx:39`, `SessionList.tsx:44`,
  `SessionLiveView.tsx:10`, `test_useRealtimeSync_session.test.tsx:3`, `SeatInputBox.test.tsx:5` and
  `SessionsPage.test.tsx:108,132,186`. It is not a renaming of the row kind: the component was
  renamed `rigd` -> `agent` on 2026-10-15 and the document's own naming note records that the filename
  was the last `rigd` left, so the rename repairs four client files that already cite the new path
  (`internal/clientservices/services.go:3`, `internal/clientsync/agent.go:5`,
  `internal/clientsync/redaction.go:4`, `internal/clientlifecycle/agent.go:2`) and `main` does not
  serve. This commit is held with the rest of the slice: the document itself lands with D-hub, so the
  path resolves only in the landing that carries both.
- The four prose tokens that called the component `rigd` now say `agent`, which is the component's
  name and NOT the row's (`room`): `sessionTypes.ts:25` ("as the agent last reported it") and `:26`
  ("no agent has reported one"), `SessionsPage.test.tsx:132` ("the agent fails CLOSED per event") and
  `SessionLiveView.tsx:9` ("phase 1 of the agent slice").

### Not changed, on purpose

- `decisionApi.ts:27`'s `rigspec` names a hub route family (`/api/v2/rooms` is the root those routes
  serve). The route's own rename is the hub's, so the comment follows it rather than leading it.

### Testing

- `npx tsc --noEmit -p .` in `agenthub-frontend`: **exit 0**.
- `npx vitest run src/tests/hooks/test_useRealtimeSync_roomSafeguard.test.tsx`: **6 passed**. The
  red-first run was not captured: the frames now carry `room_safeguard`, a value the previous
  dispatcher matched in no case, so the alert would have been logged and dropped.
- `npx vitest run src/tests/hooks src/tests/pages/LandingPage.test.tsx src/tests/components/MachinesPanel.test.tsx src/tests/pages/SeatsPage.test.tsx`: **19 files, 173 tests passed**.
- `npx tsc --noEmit -p .` after D-frontend, and `npx vitest run src/tests/pages/SessionsPage.test.tsx
  src/tests/components/SeatInputBox.test.tsx src/tests/hooks/test_useRealtimeSync_session.test.tsx`:
  **3 files, 13 tests passed**, tsc exit 0. Each of those files' comments is where the token changes,
  so the suite is the check that nothing else did; `grep -rn '\brigd\b\|rigd-boundaries' src` is empty.
- No check can resolve `ai_docs/core-architecture/agent-boundaries.md` yet: the document's rename is
  D-hub's commit, and this one is held with it.
- No browser check: the dashboard is checked against a deployed origin after the owner's deploy, and
  this slice lands only after the hub's slice B is on `main`.
