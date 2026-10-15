## 2026-10-15

### Added
- `ai_docs/development-guides/seat-runtime-switch-agy.md`: specification for running a seat under `agy` and switching a seat's runtime in place with its context carried as a handoff brief. Measured: the native runner has paths for `omp` and `claude-code` only; `agy` 1.3.5 offers the stream-json print mode needed for a runner like the claude bridge. Specification only; no code yet.
