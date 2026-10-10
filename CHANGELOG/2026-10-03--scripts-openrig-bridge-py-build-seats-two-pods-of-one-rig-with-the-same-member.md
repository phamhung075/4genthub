### Fixed

**Bridge: duplicate seat keys were reported as invalid names** (2026-10-03)

- `scripts/openrig_bridge.py` `build_seats`: two pods of one rig with the same member name (e.g. `agy.check` and `dev.check` in rig `4genthub-go`) were skipped as a duplicate but reported as `skipped 2 seat(s) with invalid names`. Invalid names and duplicates are now counted separately: invalid keeps `skipped N seat(s) with invalid names`; a duplicate prints `seat 'check' in rig 4genthub-go exists in pods agy and dev; rename one`. The seat key is unchanged (member name only; architect decision: room = rig, seat = member); the first node is sent.
