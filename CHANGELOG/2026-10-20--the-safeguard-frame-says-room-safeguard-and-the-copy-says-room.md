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

### Not changed, on purpose

- The ten citations that name `rigd-boundaries.md` by section, in `useRealtimeSync.ts:1011`,
  `websocket-protocol.ts:263`, `sessionTypes.ts:25-26`, `SessionsPage.tsx:39`, `SessionList.tsx:44`,
  `SessionLiveView.tsx:9-10`, `test_useRealtimeSync_session.test.tsx:3`,
  `SeatInputBox.test.tsx:5` and `SessionsPage.test.tsx:108,132,186`. Slice D renames the document to
  `room-daemon-boundaries.md` and extends `DOC-CITATIONS.py` to fail on a `.md` filename token that
  resolves to no file (Q9's open half); a citation changed before its target exists dangles the
  other way, so these move in D's window.
- `decisionApi.ts:27`'s `rigspec` names a hub route family (`/api/v2/rooms` is the root those routes
  serve). The route's own rename is the hub's, so the comment follows it rather than leading it.

### Testing

- `npx tsc --noEmit -p .` in `agenthub-frontend`: **exit 0**.
- `npx vitest run src/tests/hooks/test_useRealtimeSync_roomSafeguard.test.tsx`: **6 passed**. The
  red-first run was not captured: the frames now carry `room_safeguard`, a value the previous
  dispatcher matched in no case, so the alert would have been logged and dropped.
- `npx vitest run src/tests/hooks src/tests/pages/LandingPage.test.tsx src/tests/components/MachinesPanel.test.tsx src/tests/pages/SeatsPage.test.tsx`: **19 files, 173 tests passed**.
- No browser check: the dashboard is checked against a deployed origin after the owner's deploy, and
  this slice lands only after the hub's slice B is on `main`.
