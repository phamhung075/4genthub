### Fixed

**`seatcheck send` found no recipient in a multi-pod rig** (2026-10-03)

- `cmd/seatcheck/main.go` `parseWhoami`: the peer roster was keyed by stripping `<rig>.` from the logical id, but a logical id is `<pod>.<member>` and the pod equals the rig name only for room-generated rigs, so in a rig with several pods every allowed send failed with `not a seat of rig`. The member is now the part after the first dot (the rule of `openrig_bridge.py seat_name`). Two peers with the same member name are an error naming the member and both sessions (exit 2) instead of the last one winning. The audit line records the policy decision only (commented).
