# The reviewer seed carries the decision check

Date: 2026-10-19
Task: c0c53a90 (`OWNER DECISION: seat decision-ladder enforcement`), owner ruling qitem-20261019155703-f89f341c6504

## What was wrong

The reviewer is the room's gate, and its seed text never named `4genteam decide`: a silent pick among
defensible options had no enforcement point, because `complete` refuses without evidence while nothing
read `~/.config/4genthub/jev_decisions.log`. Measured 2026-10-19: 148 decision lines in the log - seat 58,
room 55, lead 35 - and none on that day.

## What changed

`agenthub_go/fastmcp/seat_management/domain/seedlibrary/seat-types/reviewer.yaml` gains the rule `The
decision check` - read the handoff's `decision:` line and the task's Progress; a change that picks among
defensible options must point at its matching `jev=` line in `~/.config/4genthub/jev_decisions.log`, or
the gate fails with `decision-check: no jev=<subject>` - and the output line
`Decision check: <jev=<ts> | none-open | MISSING>`.

`seedVersion` rises 1.4.18 -> 1.4.19 in `domain/seedmap/seedmap.go`, because a stored seat type version is
immutable and the reviewer module set changed; `domain/seedlibrary/seedcontent.lock.json` records the new
content set, written by
`go test ./fastmcp/seat_management/domain/seedlibrary/ -run TestSeedVersionNamesOneContentSet -args -update-seedcontent-lock`.

Text only: no change to the queue daemon, `4genteam decide` or `4genteam complete` (that is the rejected
Option B). The seat-facing copy of the same rule lands in the client tree
(`skills/rooms/4genthub-min/reviewer/reviewer-role/SKILL.md`, provenance raised to 1.4.19).

## Evidence

- `cd agenthub_go && go test ./fastmcp/seat_management/domain/seedlibrary/` green.
- `grep` of the new strings in `reviewer.yaml` and the client copies.
