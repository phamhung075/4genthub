## The compaction supervisor compacts at 250k without waiting for quiet, and cuts the turn at 300k

### Changed
- `agenthub_client/src/agenthub_client/compact.py`: three tiers. 150k: the seat is told to find its own safe point, compacted once its log is quiet (unchanged). 250k: compacted now, not after quiet (omp: RPC compact through `forcecompact`, applied at its next turn boundary; other runtimes: `/compact` as soon as the seat is idle). 300k, if still not compacted: omp seats get `/abort` then the RPC compact; other runtimes are interrupted (Escape) then sent `/compact`.
- New `abort()` helper; `warning()` now says a compaction is requested and the turn is aborted at 300k. `watch.py` limit comments match the tiers.

### Fixed
- `tests/test_compact_supervisor.py`: the two hard-limit tests failed since the omp RPC path was added, because the fixture's omp runtime reached the unmocked `rpc_compact`. `run_step` now mocks `rpc_compact` and `abort` and takes a runtime; four tests cover the 250k and 300k behaviour per runtime.

### Verified
- `pytest tests/test_compact_supervisor.py tests/test_cli.py`: 15 passed. The supervisor's own 300k path has not fired in production (no seat past 300k).
