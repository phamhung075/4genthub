## NEXT-GEN2 R2 records that compacting a fresh seat blocks it

### Changed
- `NEXT-GEN2.md` (R2): the `forcecompact` bullet carries a measured defect. omp answers a compact on a seat with no turns with `Nothing to compact (session too small)`; `classify_failure` in `rust/agenthub-runtime/src/runner/mod.rs` treats it as a terminal refusal, so the seat is `blocked`, writes no session log and shows no events in the watch grid. Fixed on client branch `fix/compact-reply-not-a-turn`: a failed reply carrying the compact frame's id never enters the resume ladder.

### Tested
Fix: `cargo test --offline` 87 passed on the branch (commit a8e18eb, not merged or installed). Observed on the live room `4genthub-min` at client tree `4567c37`: go-dev, fe-dev and reviewer `blocked` with empty `sessions/` directories; the lead, which resumed an older session, was not affected.
