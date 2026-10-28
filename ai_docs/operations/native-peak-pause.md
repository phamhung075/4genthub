# Native peak pause (design, not implemented)

Status: design, 2026-10-28. Requested by the aa2-rs director; not built because the pieces it touches
(agent's child set, the watchdog's restore, `room stop`) are shared by every room and the facts below
include one unknown that must be measured first.

## Problem

A DeepSeek room billed at peak costs twice the off-peak rate (01:00-04:00 and 06:00-10:00 UTC, Mon-Fri;
`4genteam offpeak`). Today aa2-rs is paused by a Claude director woken by cron only to run
`4genteam room stop aa2-rs` before a peak block and `4genteam continue aa2-rs` after it. Each wake spends
scarce Claude quota on two shell commands the client could run itself.

## Facts (with source)

- observed: `room stop ROOM` sends StopRoom, "exactly that room's own sessions ... never agent, never its
  children" (`agenthub_client/internal/clientroom/room.go:16`).
- observed: after `room stop aa2-rs` (01:35 CET) the 05:37 `continue` found compact, watchdog, messages,
  roomguard and budget down (aa2-rs director report, 2026-10-28). The cause of that drop is **unknown**:
  either the per-room children exit once the room's sessions are gone, or the cron also ran a machine-wide
  `4genteam stop`. Measure before building (step 0 below).
- observed: `continue` now starts the safeguards a stop left down (client branch
  `maint/continue-heals`, 88932c72), so a park/resume pair no longer needs `heal`.
- observed: the watchdog restores a dead room, and its restore is peak-gated (`watchdog` refuses at peak
  under OFFPEAK_ONLY), so after a peak block ends an unparked watchdog could restore a parked room on its
  own; a park must therefore be a state the watchdog reads, not just stopped sessions.
- observed: `clientoffpeak.At` / `NextChange` (client branch `maint/clock-verb`, 5b9c668b) answer the
  window and the next boundary for any instant, holidays included.

## Design

One opt-in, per-room setting the always-on `agent` honours. Rooms without it behave exactly as today.

1. **Setting.** `rooms/<room>/peak-pause.json`: `{"enabled": true, "quiet_seconds": 120,
   "max_wait_minutes": 15, "lead_minutes": 5}`. Written by a new verb `4genteam room peak-pause ROOM
   on|off|status`. No env var: the setting is per room, and the file is the room's own state.
2. **Park record.** `rooms/<room>/parked.json` `{"since": ..., "reason": "peak", "until": "<next change>"}`.
   It is the one fact every verb reads: the watchdog skips a parked room (no restore), `continue` refuses a
   room parked for peak unless `--allow-peak` or the park has expired, and `status`/`doctor` print it.
3. **Who acts.** A new per-room agent child `peak-run --room R` (one more `agentSpec`, the same shape as
   `budget-run`), started only when the setting is enabled. It is NOT stopped by the park: it is the thing
   that resumes the room, so a park stops seats only, never agent or this child.
4. **Park.** At `next peak start - lead_minutes`: wait until every seat is quiet (`GetRoomStatus`:
   no seat mid-turn, `quiet_seconds` since its last tool call; the same reading `idle-run` uses), at most
   `max_wait_minutes`; then write `parked.json` and send StopRoom. A seat still busy at the deadline is
   stopped anyway at the peak boundary (a resumed session keeps its context), and the line says so.
   Before StopRoom it sends each seat one line through the room's own transport
   ("parking for DeepSeek peak until HH:MM; commit or note your state") and waits `quiet_seconds` again.
5. **Resume.** At the off-peak boundary (`NextChange`): remove `parked.json`, then run the same restore
   `continue` runs (`clientrestore.restorer` with `startsSupervision`), so seats resume their own sessions,
   the safeguards are checked and started, and the brief goes out. A failed resume is an alert row
   (`TailAlerts`) and the room stays parked-off so the watchdog can take over.
6. **Clock.** Every decision reads `clientoffpeak.At(time.Now())`; a pinned `OFFPEAK_UTC` makes the
   boundaries testable. A machine clock off by more than 5 s (`4genteam clock`) is logged on each decision.

## Steps

0. Measure which process takes the room's safeguards down after `room stop` (agent log at the stop
   minute). If the per-room children exit with their room, `peak-run` must be exempt by design (item 3).
1. `room peak-pause` verb and `parked.json` reader, with tests (no daemon).
2. Watchdog and `continue` honour `parked.json`, with tests.
3. `peak-run` child: pure decision function `(now, seats, setting, parked) -> action`, table-tested at
   each boundary (Friday evening, holiday, a busy seat at the deadline, a resume that fails); the loop
   around it only reads and acts.
4. Agent starts `peak-run` for enabled rooms; `doctor` shows the row.
5. Pilot on aa2-rs with the director's cron left in place for one day (it becomes a no-op), then remove it.

## Not in scope

Partial pauses (one seat), non-DeepSeek rooms (the setting is refused for a room with no DeepSeek seat,
the same reading the peak gate uses), and moving work between rooms.
