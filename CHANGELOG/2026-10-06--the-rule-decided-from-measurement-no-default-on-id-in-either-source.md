### Changed

**The schema file and the runtime DDL agree on column defaults — ids come from the application** (2026-10-06)

- **The rule, decided from measurement: no `DEFAULT` on `id` in EITHER source.** The runtime TableDefs
  supply the value in Go (`ColumnDef.Default = taskdb.DefaultUUIDv4`), and the schema FILE's
  `id ... DEFAULT uuid_generate_v4()` was the side that disagreed — production takes the runtime path, so
  the file described a default production does not have, and `createAll` never creates `uuid-ossp`, so the
  default was not honourable on a fresh runtime database at all. The file's 14 `id` columns lose it, and
  the `CREATE EXTENSION` goes with it.
- **Why it mattered:** a test's result depended on which path had built the database —
  `TestRoomSharingVisibilityIntegration` failed on a runtime-built one (`null value in column "id" …
  violates not-null constraint`, SQLSTATE 23502) and passed on a file-built one. It now passes on BOTH.
- **`TestSeatDDLParity` compares the DEFAULT expression of every column in both sources** beside the
  columns, the `REFERENCES` and the `CHECK`s, and it CAUGHT this divergence before the fix — every seat
  table reported `file: id:uuid_generate_v4()` against `runtime: <absent>`.


- **`NEXT_GEN.md`: the socket gap closed by measurement, the five-field socket form, and the vintage clause proving itself twice in an hour (2026-10-06)** — **the closure:** on a binary that **contains** the fix, the session-viewer socket **completes the handshake and closes `1008` with the same required-credential reason as the realtime and connector paths**, in **both auth settings and both token shapes (nine cells, uniform)** — the bare pre-upgrade `403` is gone, **no path is stricter or less legible than its siblings**, and go-dev's fix is confirmed **on the shape it named rather than inferred from its title.** **The method did its work before the probe: the ancestry check showed the fix was newer than both binaries the verifier had run, so the gap was STALE BY CONSTRUCTION** — the **same rule used twice in one hour in opposite directions** (once to stop a false gap being filed, once to close a real one), **the strongest evidence that the vintage clause changes decisions rather than describing them.** **And the standard form now kept for socket claims: FIVE FIELDS PER OBSERVATION — path, port, setting, token shape, and open-versus-closed-with-a-reason** — because all three of tonight's socket disagreements would have been **impossible to state** without them. **One gap remains named and unmeasured: which default the runtime substitutes for an empty model.**
