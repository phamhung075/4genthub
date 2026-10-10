## The auto-fix is ruled: bypass mode, with no power except the client's repair verbs

### Added
- `ai_docs/core-architecture/rigd-boundaries.md`, section 7.10 (board row `411f5351`; the lead's note on `qitem-20261010230121-aba9ffb6153fb3fa`).
  - The headless repair runs `claude -p` in bypass mode with `--tools ""` and `--strict-mcp-config`. Its only tools are the client's four MCP verbs: `recheck`, `restart_service`, `up_room` and `rebrief_seat`, each refusing any argument outside the room's own lists.
  - Rejected: a prompt-only guard, and `--restricted`, which refuses bypass.
  - Also ruled:
    - `AUTO_FIX` is off by default.
    - A closed anomaly list, every item from an existing source.
    - A breaker at N=2 per anomaly per hour, which then alerts through 7.3.
    - One run per room, under a `flock`.
    - A 10-minute deadline.
    - The re-check is the client's.
    - The run is held at peak.
    - The prompt is embedded in the client.
    - Log and `auto_fix` event.
    - Secrets are kept out of the log by test.
    - Evidence is structured rows only.
  - Six named tests.
- Section 7.9a records two inputs from the same row: arm a wake timer only when the blocker can clear inside the interval, and `--wake-after` reminders recur, which goes to the OpenRig friction report.

### Verified
- `claude --help` (2.1.296), run by the architect: `--tools`, `--strict-mcp-config`, `--mcp-config` and `--permission-mode` exist, and `--restricted` "refuses bypassPermissions".
- No code changed, so no tests apply.
