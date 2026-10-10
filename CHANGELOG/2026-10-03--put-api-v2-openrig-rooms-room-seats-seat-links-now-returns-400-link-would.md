### Fixed

**Seat links could form a launch cycle that `rig up` refuses** (2026-10-03)

- `PUT /api/v2/openrig/rooms/{room}/seats/{seat}/links` now returns 400 `link would create a launch cycle: a -> b -> a` when an allowed delegates_to/spawned_by link closes a cycle with the room's other allowed links (before: stored and rendered, then `rig up` failed with `Cycle detected in rig topology`). `rigspec.FindLaunchCycle` is the pure rule (delegates_to: source launches first; spawned_by: the target is the parent and launches first; can_observe, collaborates_with and escalates_to are not counted); `SeatLinkService` (new, with its own `SeatLinkStore`) runs it over the active seats and allowed links of the room, ignoring the link being replaced. Links with `allow: false` are never checked because the rig spec does not render them.
- A seat key is still the only link target, so a cycle across rooms is not possible.
