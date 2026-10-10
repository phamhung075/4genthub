### Changed

**`NEXT_GEN.md` G1a CHECK and UI-drive defect** (2026-10-03)

- `agenthub_go/NEXT_GEN.md`: G1a adds `ck_seats_permission_policy` and the startup column check (`d3b45a5f`); records `275f900b` and the missing-Authorization UI defect (`c1b17ba8`). Documentation only, no tests run.

**`NEXT_GEN.md` commit citation fix and process lesson** (2026-10-03)

- `agenthub_go/NEXT_GEN.md`: the no-migrate startup log cites `1b7e7bdc` only (`cf7908e4` is a docs cleanup); new "Process lessons" section. Documentation only, no tests run.

**`in_sync` wording** (2026-10-03)

- `seat_management/domain/seatsync/seatsync.go`: the package and constant comments say what `in_sync` means: the running hash equals the newest stored resolved snapshot hash. It is not "up to date" with the seat type or its modules. No code or UI text said "up to date"; the UI label `in sync` is unchanged.
