## Rule 76: a parked row that cannot wake anyone is queued for a sweep

Filed from the lead's handoff (`qitem-20261010185505-d0d24bada2a7e15f` and its retraction companion `qitem-20261010185608-04cb93c434160d70`), from `fe-dev`'s rule and its own damage.

### Fixed
- `agenthub_go/NEXT_GEN.md`, the numbered rule series: **rule 76** — *a row parked on something the owner cannot act on must carry a wake, and a named deliverer; a parked row that cannot wake anyone is not parked, it is queued for a sweep.* It carries the mechanism **as read from `rig queue block --help`** (`--on` required; `--wake-watchdog <jobId>` or `--wake-after <duration>`, armed atomically with the park; the help's own sentence "Every deliberate HELD row should name its continuation and one live wake"), the bare form that records the reason and **arms nothing**, the two clauses that make it usable (the wake must reach the parked **owner**; the park must name the **deliverer** of the unblock), the cost (sweeps manufacturing wakes that prove only that a row is unchanged), and the two instances (fe-dev's O1c row; `qitem-recovery-cbad0f8f0cea79bf`).

### Verified
- The CLI surface is quoted from `rig queue block --help` as the lead read it, not from a relay; this seat did not re-run that help text, and the rule says so by attributing it.

### Fixed (same commit, the platform fact the lead asked to place beside it)
- The environment-facts section gains **the unroutable human-seat row and the ~512-byte body cap**, both measured: the lead's push-ask row `qitem-20261010185109-be8657f9429fcc7c` (`lastNudgeResult = "unroutable: 'human@4genthub-min' … no registered human"` while `state = pending` and nothing pushed it), and the cap that truncated two handoffs tonight — with the recovery (long text in a file, summary in the row) and the read path (`rig queue transitions`, since `rig queue show` returns no notes even with `--full`).

### Not run
- No queue row was blocked or parked by this seat to test the mechanism: the rule records the CLI's contract and the instances that motivated it. Nothing was edited outside `NEXT_GEN.md` in this repository.

### Companion filed 2026-10-10 19:25Z — the destination half is RULE 77, not a clause here
- The lead handed this rule's **address** half on the same row set: **a row whose destination cannot receive** (16 pending rows, 8 asks + 8 recovery rows, all unroutable to `human@4genthub-min`/`human@kernel`), the instrument that shows the class (`rig queue undelivered`), the measured empty address class (`rig gateway human list` → *"no human configured yet"*, with the fix shape it prints), and the practice until registration (an ask that must be noticed rides a seat that can reach the owner; the human-addressed row stays as the record).
- **Filed as rule 77 rather than folded in here, and the lead left the choice to this seat**, because the verb, the failure and the remedy are all different: this rule is about the **PARK** (`rig queue block`, a wake, a deliverer), and 77 is about the **DESTINATION** (an address with no transport, a registry with no binding). The three clauses are still one idea, and the cross-reference runs both ways: **76's clause (a) is the REACH half; 77 is the RECEIVE half.**
