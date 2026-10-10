### Fixed

**seatcheck's unknown-recipient hint lists only seats the caller may message** (2026-10-03)

- `agenthub_go/cmd/seatcheck/main.go`: the hint after a denied unknown recipient named every roster member and policy link end. It now lists only the seat keys the caller's own policy allows for the intent (via `commpolicy.Decide`), or says `your policy allows no recipient for intent "<intent>"`. Exit code and audit are unchanged.
