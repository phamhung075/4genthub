### Fixed

**Seat on codex failed to render when its seat type carried comm-guard** (2026-10-03)

- `seatrenderer/renderer.go`: a tool module on a codex seat is skipped instead of failing the render with `runtime "codex" cannot carry tool modules` (a tool module is a Claude settings fragment). `SetOccupant` can switch a seat's runtime while its pinned seat type version keeps the seeded `comm-guard` tool module, so the decision belongs to the seat's runtime at render time. A codex seat renders the skill and no `runtime/` files, so it is not deny-guarded; a codex-default seat type switched to claude-code now gets the deny.
- `seedmap.go`: both shared modules are attached to every seed regardless of the seat type's default runtime (the `DefaultRuntime` special case from the comm-guard change is gone).
- `renderer.go` `mergePermissions`: an empty `deny`/`allow`/`ask` list with no earlier value stayed nil and marshalled to `null`; it is now `[]`.
- A fresh `POST /seat-types/seed` adds seat type version 1.1.0 next to 1.0.0 (module versions too); seats that follow latest resolve to 1.1.0 (`LatestVersion` orders by `created_at`), seats pinned to 1.0.0 keep resolving 1.0.0 without comm-guard. Read from the seeder and resolution service, not run against Postgres.
