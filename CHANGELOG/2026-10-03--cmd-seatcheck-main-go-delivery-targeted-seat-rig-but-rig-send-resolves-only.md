### Fixed

**`seatcheck send` could not deliver an allowed message** (2026-10-03)

- `cmd/seatcheck/main.go`: delivery targeted `<seat>@<rig>`, but `rig send` resolves only full session names (`<pod>-<member>@<rig>`), so an allowed send failed with `Session beta@scratchcomm not found` (exit 1). The target session is now taken from the `peers` roster of `rig whoami --json` (`parseWhoami`, keyed by member name), the one place that names sessions, instead of rebuilding the name from the rig. A recipient that the policy allows but the rig roster does not list exits 1 with `"x" is not a seat of rig "r"` after the allowed decision is audited, and nothing is delivered. Reported by the tester's live run.
