## Safeguard ruling addendum: a busy process is not stopped, and `up` is the only room entry point

### Added
- `ai_docs/core-architecture/rigd-boundaries.md`, two new sections ruling on the lead's two follow-up notes on `qitem-20261010225142-6d506ef31156b50b`. Ruling row: `a76d6d97`.
- **§7.7:**
  - Last activity is a heartbeat, or an `in_flight {op, since, deadline}` call the child declared. A declared call extends liveness only up to its deadline.
  - A seat's last activity is its last transcript write, or a tool call that is still open.
  - OpenRig's queue-stuck-sweep and liveness oracle false positives go to the OpenRig owner as a friction report. No seat edits OpenRig code.
- **§7.8:**
  - One compiled list, `clientservices.Obligatory`. Its rows are `daemon`, `gate`, `seats`, `rigd`, `bridge`, `compact` and `watchdog`.
  - The duplicate daemon-start and restore paths each become a single row.
  - The start order has no cycle.
  - The gate's check is "readable": a peak refusal means the gate is working.
  - The `continue` verb is deleted. The owner deletes the `~/.openrig/bin` scripts; no seat does.
  - One `Verify()` is shared by `up` and the read-only `doctor`, and both exit 3.

### Verified
- The architect read the client at `63fd184` for the cited lines: `lifecycle.go:193`, `:203`, `:251`, `restore.go:189`, `paths.go:7`.
- No code changed, so no tests apply. Ruling row `a76d6d97` was read back.
