# The acceptance criteria name the counts the wire carries

`ai_docs/agent-system/task-workflow-and-reporting.md` told a seat to settle a criterion with "the numstat names
<path>". The register admits that wording, the transport redacts the path to `<path>`, and the judge then
answers on an opinion - friction `e2056bf9` (go-dev, 2026-10-18), board item `a2db075c`. The gate wire now
carries per-path counts and the added/deleted split (client `4c8f18e`, pinned at `8d9237d`; board `86e4d618`),
so the section is rewritten to the register the gate and the wire actually are. This entry supersedes the
GOOD/BAD advice of `2026-10-16--the-criteria-vocabulary-a-seat-can-settle.md`; that entry's `8bd075eb`
measurements still hold and remain in the doc.

## Changed

- **The judge's state is the counts, and the criteria text is redacted.** `countsState` sends ten keys - the
  seven it sent before plus `lines_added`, `lines_deleted`, and the per-path rows with every name removed -
  and `RedactForWire` turns each path into `<path>` and each `Test*`/`Benchmark*`/`Example*` name into
  `<test>` at the transport, so it shapes the criteria text too.
- **The gate refuses before the judge is asked.** `register.carries` admits a criterion only when it names
  the command, the run's exit code, a path THIS run's numstat lists, a base/head sha prefix of at least seven
  hex characters, or a count key stated with THIS bundle's value in the same clause (the first number after
  the key, before the next count key); anything else makes the whole task `unjudgeable` with no judge call.
- **The trap is named.** A listed path is admitted and then judged blind; an unlisted path is refused. What
  is both admitted and visible is the command, its exit code, a sha prefix and the counts.
- **A count is about the change, not a file.** The per-path rows reach the judge with no names, so "one path
  adds 34 lines" cannot be stated; "lines_added 34" can.
- **Two edges, measured on the gate.** The exit branch is command-agnostic, so a criterion must name the
  command the bundle actually ran; and a claim no fact can carry - a screenshot, a rendered page, "reachable
  by tap" - has no admissible wording, so the command must produce the proof or the claim goes in the details.
- **The completion base is stated as a rule.** It is required, resolved to a full sha, and the numstat is a
  two-dot diff: the tip's FIRST parent when the tip is a landing merge, otherwise the merge-base of `HEAD` and
  the line being landed on.
- **The GOOD/BAD examples are rewritten to those facts** and the measured bands updated: a listed path
  .16-.34, a sha plus the totals .93-.97, and the count band NOT measured yet - so the count form is the
  fallback when a run has no sha to name.

## Measured, at the pinned client `8d9237d`

- `clientjev/countsonly.go` `countsState` returns `test_command_ran`, `test_exit_code`, `tests_failed`,
  `files_changed`, `lines_changed`, `lines_added`, `lines_deleted`, `changes`, `base_sha`, `head_sha`; the
  `changes` rows come from `NumstatStats.WireRows` and carry counts only.
- `clientcomplete/gate.go` `register` carries `counts`, `names` answers five facts, and the refusal text names
  the four count keys.
- `clientjev/countsonly.go` `RedactForWire` maps any token containing `/` or ending in a source extension to
  `<path>`, and `Test*`/`Benchmark*`/`Example*` names to `<test>`; the call sits in `jev.go`'s `call`.

## Not in this change

- **No product change in this commit.** The doc names what the client already does; the wire itself landed in
  the client as `4c8f18e`, and the hub pin names it.
- **The older parked doc hunk is superseded.** `seats/architect/patches/2026-10-18--acceptance-criteria-register/criteria-register-doc.patch`
  and the `rooms/4genthub-min/patches/2026-10-18--acceptance-criteria-register/` copies predate the wire:
  their "there is no count branch" and "the added/deleted split does not reach the judge" sentences are false
  at the pin, and landing them would recreate the doc-vs-gate drift this entry removes.
- **No new wire field.** The ten keys are the wire's own (board `86e4d618`); this commit documents them.

## Testing

No test: documentation. Every claim was re-read at the pin's source lines named above, and the doc's examples
were checked against the register's count window and the redaction rule. The wire's own tests pin the
behaviour (the count table, the window rule, the ten-key state, the redacted fixture).
