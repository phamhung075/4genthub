# The room definition carries the two gate-return edges

Date: 2026-10-15

## What was wrong

The declared link table for `4genthub-min` carried **34** links, and among them the two edges a gate
needs to hand work back to a producer — `reviewer delegates_to go-dev` and `reviewer delegates_to
fe-dev` — existed only as `collaborates_with`. The policy authorizes an intent by link kind
(`commpolicy.allowedKinds`: a `task` is authorized by `delegates_to`, not by `collaborates_with`), so
under the table the room was running, a reviewer that found a defect could ask a question but could
not send the fix back as work. The architect found it by diffing the declared table against the ruled
23 and by the instrument: the per-seat cloud route that answers this table answers 404 on all five
seats today.

## Changed

- `scripts/team/4genthub-min/team.json` — two rows added to the `delegates_to` group:
  `reviewer -> go-dev` and `reviewer -> fe-dev`.
- The live room definition (`<state-dir>/rooms/4genthub-min/spec.json`) carries the same two rows, so
  the running room's policy has the gate return now rather than at the next sync.

`9` of the links are `delegates_to` now, `7` are `escalates_to`, `20` are `collaborates_with`, and both
files parse.

## Not in this change, and deliberately

- **The blanket of 20 `collaborates_with` rows is untouched.** Declaring the room's whole general
  channel is a policy choice that changes what the guard means, so the architect did not ratify it and
  it goes to the owner. Removing the rows before that answer would decide it by edit.
- No code, no test, no pin.

## Provenance

The architect's finding and ruling is `seats/architect/RULING-declared-links-blanket-vs-ruled.md`,
raised as rail row `qitem-20261015195945-f55f7ba66f3f`. The 34-row table it examines landed as
`658ba0fd` ("feat(team): the room definition carries its 34 declared links"), whose own changelog
records that the table was uncommitted in the shared working tree at 17:27:39Z and appeared in the live
room's `spec.json` seventeen seconds later.
