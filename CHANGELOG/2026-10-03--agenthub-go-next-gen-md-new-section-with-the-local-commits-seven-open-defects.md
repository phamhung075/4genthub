### Changed

**`NEXT_GEN.md` records team progress and open work** (2026-10-03)

- `agenthub_go/NEXT_GEN.md`: new section with the local commits, seven open defects, the planner's T1 to T10 plan and the pending decisions D1 to D3 and G1a. Documentation only, no tests run.

**`NEXT_GEN.md` matches the owner decisions** (2026-10-03)

- `agenthub_go/NEXT_GEN.md`: F0b to F0d, F2 and F3 marked superseded; F1 and F4 marked implemented; one open item F0e (retire `call_agent` and `agenthub_main/agent-library`) and G1a (production schema change for `961e1da1`) added; G1, G2, G6 and Requests 12 to 16 status updated; standing owner permissions, deploy loop and production facts recorded. Documentation only, no tests run.

**`default_runtime` is versioned** (2026-10-03)

- `agenthub_go/fastmcp/seat_management`: `default_runtime` moved from `seat_types` to the immutable `seat_type_versions` (ORM structs, `seat_tables.go`, `seat_management_postgresql.sql`). A version is written in one insert, `SeatTypeRepository.SetDefaultRuntime` is gone, and `AddVersion` takes the runtime; the same version with another runtime or module refs is `ErrSeatTypeVersionConflict`. `SeatResolutionService` takes the runtime of a seat that sets none from its pinned version, so a new version never changes a pinned seat. The seed library writes its runtime on the version.
- `GET /api/v2/openrig/seat-types`: `default_runtime` is the latest version's runtime, `null` when the seat type has no version.
- `POST /api/v2/openrig/seat-types/{slug}/versions`: logic moved from the handler to `SeatAdminService.CreateSeatTypeVersion`; errors map by type: 400 invalid input or unknown module ref, 404 unknown seat type, 409 a concurrent writer took the version with different content, 500 anything else.
- Production note: tables created by the earlier DDL still have `seat_types.default_runtime` and no `seat_type_versions.default_runtime`; the new schema is not applied over them by `CREATE TABLE IF NOT EXISTS`.
