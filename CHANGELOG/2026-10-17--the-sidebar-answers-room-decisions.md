## The sidebar answers a room lead's decision requests

The cloud now serves the room decision channel
(`agenthub_go/fastmcp/server/httpapp/room_decisions_mount.go`: `GET /api/v2/rooms/{room}/decisions`
and `POST /api/v2/rooms/{room}/decisions/{id}/answer`, plus the four rig-scoped crossing routes), and
the frontend had no consumer: the dashboard sidebar was one scrolling column holding the Project &
Branch hierarchy, with nothing in it that could carry the owner's answer back to a room.

### Changed
- `agenthub-frontend/src/App.tsx`: the sidebar `<aside>` becomes a flex column of two sections. The
  upper section is the existing `ProjectList` with its five props unchanged, scrolled as it was; the
  lower section is the room decision panel, capped at 45% of the column and lazily imported so the
  dashboard's initial chunk is unchanged.
- `agenthub-frontend/src/components/RoomDecisionPanel.tsx` (new): lists the room's asks - `pending`
  and `answered` only - and renders each stored question and its options verbatim. One button per
  option and one "Send answer" per question, so a click is a choice and the POST is the transfer; a
  question already recorded shows "Answer recorded" and cannot post again. `pending` rows carry a
  count badge; an `answered` row stays in the list as "awaiting the room", because only the daemon's
  apply moves it to `resolved`/`superseded`. A refusal (403 not-the-asked-human, 409 state-answered,
  422 unknown option) and an unreadable list are both rendered with their message, never swallowed.
- `agenthub-frontend/src/services/decisionApi.ts` (new): the two calls over the shared
  authenticated `apiRequest`, on the room family's own prefix (`/api/v2/rooms`, `{room}` the slug).
- `agenthub-frontend/src/hooks/useSeats.ts`, `src/hooks/index.ts`: `useRoomDecisions` (keyed on the
  room, disabled while there is no room) and `useAnswerRoomDecision` (invalidates that key on
  success); `seatKeys.roomDecisions(room)`.
- `agenthub-frontend/src/types/seatTypes.ts`: the row, question, option, answer and response types
  exactly as the handler serializes them (`id`, `qitem_id`, `author_seat_key`, `summary`, `detail`,
  `questions[]`, `answers{}`, `state`, `created_at`, `answered_at`).

### Testing
- NEW `agenthub-frontend/src/tests/components/RoomDecisionPanel.test.tsx` (6 cases, services mocked so
  the real hooks and query keys run): options render verbatim for the room named in the URL; a choice
  posts exactly `{question_id, option_id}` for the clicked option; an `answered` row stays while a
  `resolved` one is dropped and its buttons disable; a refused answer and an unreadable list each show
  their message; and on a page that names no room the panel reads the first room and follows the
  picker to another.
- Not proven here: the live round trip against a running hub (needs an authenticated session and a
  room with a pending ask). The panel's requests match the handler's serialization read from source;
  the wire proof remains a live run.
