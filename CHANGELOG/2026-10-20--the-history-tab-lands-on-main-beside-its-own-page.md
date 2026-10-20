# The History tab lands on main, beside main's own page

45a034df shipped the seat History tab on the frontend line; **main did not carry it** - neither
`SeatOccupantHistoryPanel.tsx` nor `ModuleContentView.tsx` existed there, and a cherry-pick of
45a034df conflicted in `SeatDetailPage.tsx` because that commit imports `ModuleContentView`, a
frontend-only change (`cad91428`) main never received. main is the source line, so the change is
ported onto main's own tree instead of merged there (hub task `31ae703b`).

## What main gains

- `agenthub-frontend/src/components/seats/SeatOccupantHistoryPanel.tsx` (new): renders
  `GET /api/v2/rooms/{room}/seats/{seat}/occupant-history` in the order the route returns it - newest
  first, no cap. A row is the actor, the instant and `from_runtime`/`from_model` →
  `to_runtime`/`to_model`; an empty trail says no occupant change has been recorded rather than
  drawing an empty list; a failed read shows the server's message with Retry.
- `src/pages/SeatDetailPage.tsx`: a `History` tab beside `LLM`, wired against main's own import
  block. **It does not import `ModuleContentView` and does not touch the modules tab**, which keeps
  main's `<pre>` dump; that change stays on the frontend line.
- `src/services/seatApi.ts`, `src/types/seatTypes.ts`: `listOccupantHistory`,
  `SeatOccupantChange` and `SeatOccupantHistoryResponse`, one definition each.
- `src/hooks/useSeats.ts`: `useSeatOccupantHistory` under `seatKeys.occupantHistory`; an LLM save
  invalidates the trail because the save wrote one record.
- `src/hooks/useRealtimeSync.ts`: a seat `updated` frame re-reads the trail - the frame carries
  neither the runtime nor the model, so a second client's switch is never patched from the frame.

## Checks

- `npx tsc --noEmit -p .` exits 0.
- `npx vitest run` - 130 files / 1926 tests passed; the two touched files 58 passed.
- The browser check ran on the deployed frontend bundle carrying this same panel:
  `/seats/4genthub-min/fe-dev` drew the empty trail, and with its GET answered by two server-shaped
  changes drew both rows in server order (an empty `to_model` reading `default model`).

## Not carried

The other ten frontend-line commits - `ModuleContentView`, the captain-definition deletion, the lint
scripts, the timeline fixes - are a separate drift, named in the queue row. Nothing on the frontend
branch changes.
