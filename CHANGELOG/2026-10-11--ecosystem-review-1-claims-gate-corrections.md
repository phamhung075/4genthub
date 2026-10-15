## Ecosystem review 1 - the claims gate's two corrections

### Changed

- `ai_docs/operations/ecosystem-review-2026-10-11.md`: `GATE-8929646a-ecosystem-review-facts-2026-10-11.md` approves
  the note with two wording corrections. Both applied; no other line, finding or disposition touched.
  - **Finding 5's refused row is now carried as lead-reported and instrument-silent.** A refusal leaves no row, and
    `events` holds 0 rows mentioning `invalid_human_notification`. What is measurable at that destination is the
    accepted traffic: **59 rows to `human@4genthub-min`** (2026-10-09 19:54Z -> 2026-10-11 10:33Z), every one
    accepted, every one with `last_nudge_result` = "unroutable ... names no registered human". Consistent with a
    refusal, not proof of one: no row anywhere carries `human_intent` today (the only five are to `human@kernel`,
    2026-10-02 -> 10-08).
  - **The cost's count is corrected** from "twice today" to **two distinct owner-claiming claims in this rig's life**:
    2026-10-10 22:16Z ("OWNER DIRECTIVE, relayed by the lead", five retired seats' logs) and 2026-10-11 10:08Z (the
    charter-and-step-3 approval relay). No transcript carries an earlier owner-claiming message today.
- `CHANGELOG/2026-10-11--ecosystem-review-1-no-registered-human-and-a-probe-that-reports-up.md` (commit `8929646a`):
  the same count corrected in step, so the fragment does not keep a claim the note has withdrawn.

### Impact

- Documentation only. No code, no client change, no live rig action, no row created, no decision made.

### Verified

- Read-only: sqlite reads over `queue_items` (destination, `human_intent`, `last_nudge_result`) and the `events`
  table; a read-only search over `/home/daihu/.config/4genthub/transcripts/4genthub-min/`; the gate file itself. No test,
  build or formatter was run, because no code changed. Both claims trace to the lead's 10:21Z brief, which is now
  cited as their source rather than quoted as measurement.
