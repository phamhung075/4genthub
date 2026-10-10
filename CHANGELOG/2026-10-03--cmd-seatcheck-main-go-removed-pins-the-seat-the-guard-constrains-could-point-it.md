### Fixed

**`seatcheck send` hardening (reviewer majors)** (2026-10-03)

- `cmd/seatcheck/main.go`: removed `--pins`. The seat the guard constrains could point it at a forged `policy.json` and move the audit trail; the pins directory is now only `~/.openrig/agenthub-seats` (tests replace the `pinsDir` variable). The policy must belong to the caller: `policy.Seat` differing from the `rig whoami` member is refused (exit 2, nothing audited or delivered), and rig or member names that are not one directory name (`..`, `a/b`) are refused.
- Delivery runs `rig send -- <session> <text>` with stdin detached: a message such as `--rig=x` is text, never an option that fans the message out beyond the checked recipient (checked against the installed `rig`: with `--` the token is a session name).
- Exit codes: a delivery that cannot start or fails (unknown or ambiguous recipient, `rig send` failing) is exit 5 and never rig's own code, so it cannot read as a policy result (2 usage/policy, 3 denied, 4 bypass). The skill text `comm-guard-skill` explains exit 5.
- Audit: `AuditRecord.Outcome` (`delivered` or `delivery_failed`) on a second line after an allowed send; the decision line is fsynced before delivery, the close error is returned, and an audit file that others can read or write is refused (exit 1).
- A member name repeated across pods is no longer an error for the whole rig: all sessions per member are kept and only a send to the repeated name is ambiguous (exit 5 naming both sessions); the other peers still resolve (architect G3).
