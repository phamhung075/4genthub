## The ten policy modules advance to `1.1.0`, which is the version the seat overlays resolve

- **Owner ruling 2026-10-07.** A **minor** bump rather than the patch the apply's self-heal would have picked,
  because the change adds a capability — an **allowance** in every seat's policy (the `rig whoami` startup
  exemption) — and semver gives an added capability a minor. `scripts/team/4genthub-min/team.json`'s ten
  `policy-<seat>` entries move `1.0.0` → `1.1.0`; the eleven `guide-*` entries stay `1.0.0`, and the seat overlays
  carry **slugs only** and resolve their version from that array, so they follow in the same change: **the PUT
  target and the overlay refs name the same thing**, which the apply's own plan shows (`module policy-<seat>@1.1.0`
  for all ten, then the ten seat-overlay PUTs).
- **Why the version had to move at all, measured:** the published `1.0.0` predates `6ef91fc2`, which wrote the
  exemption into all ten module files at 20:23Z — *after* the apply (≤19:58Z) — and versions are immutable with the
  content gate on the PUT, so the exemption could only ever reach the room as a **new version**. The audit that
  established it ran the ten committed files through the real `ParsePolicyModule`/`FoldPolicies` twice (the room's
  `add` shape, and the seat-scoped-`override` shape the fold refuses by name) and read one live render: repo side 30
  bash rules with the allow at index 0, published side 29 patterns all `deny` and no allowance section.
- **And why the bump is not optional:** the apply plans `NEW_VERSION` and pushes changed content as the next patch
  by itself, but `overlay_body` resolves `module_versions(team)` — the **declared** version — so while `team.json`
  said `1.0.0` a successful-looking run would print a new version, and each seat would keep adding `1.0.0` and
  rendering the old content: a green run, a correct-looking plan, and no exemption in the room.
- **Not published here** — the publish is the owner's, and it is now one `apply` run: this commit puts the code in
  the state that makes that run correct.
