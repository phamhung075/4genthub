# The criteria vocabulary a seat can settle

`4genteam complete` judges a task's acceptance criteria from the evidence alone (hub task `2a6e6d5e`,
Outcome 2), so a criterion that asks for a file's contents or a command's output can only be answered low -
and every closure in room 4genthub-min waits on that gate. The architect's ruling
`seats/architect/RULING-outcome2-proof-shape.md` (2026-10-16) measured it on one task's own evidence and its
own command: the four criteria as written answered .57/.42/.41/.49 -> uncertain, exit 6; the same claims
re-worded into what the evidence carries answered .97/.96/.96 -> accept. This entry is the doc half of that
ruling's routed work; the client half pins the request shape and the verdict, and changes no production
code.

## Changed

- **`ai_docs/agent-system/task-workflow-and-reporting.md`** gains two sections: the GOOD/BAD criterion
  vocabulary with the measured band, and which verb writes which surface.
- **`AGENTS.md` section 5** names that split where a seat reads it: progress, notes and status of a task go
  through `manage_task` `update` with `details`; `manage_context` carries context, and a task-level
  `manage_context add_progress` note does not reach the board item's Details (measured, hub task
  `4138904d`).
- **And that `details` appends.** The first version of that bullet would have corrupted the item it keeps:
  `manage_task` `update` stores the submitted text after the stored field, so a reader who resends the field
  with one new section added stores the whole history twice (measured 2026-10-17: 8.8k sent back became 41k
  in the item, which then carried its own history two and a half times). The bullet now says to send the new
  section only, one `=== Progress N ===` per call. Reported as feedback `67149348-ba5c-4f90-8255-fe57407adb7b`.
- **`TEST-CHANGELOG.md`** records the client pins at the top (client commit `11a77ca`).

## Not in this change

- **No code, no payload field.** Route (a) - a field the judge reads - is priced out in the ruling: the
  payload's no-content rule is pinned (`clientevidence/evidence.go`; `evidence_test.go`'s `assertKeys` fails
  on an extra field), a field's content would be either source text sent to a third-party API or a seat's own
  prose (a claim, not a measurement), and the hub builds no judge prompt at all.
- **No instruction prefix in the criteria call.** Measured: a fixed instruction line moved a content
  criterion .14 -> .15 and a mechanical one .97 -> .94, and changed no verdict.
- **Content correctness stays with the reviewer's gate.** The judge's verdict is a shape verdict - a touched
  path plus a passing command; a criterion naming a test is only as strong as that test's assertion.
