## Changed

- `agenthub_client` pin moves `de98247` -> `e901b94` (2 commits).

### Fixed

- An `agy` seat is launched with its model (`e901b94`).
- The `agy` seat's hook records its conversation id, so `watch` can find it (`58a1035`; the client carries its own `CHANGELOG/2026-10-15--agy-seat-hook-records-its-conversation.md`).

Late entry: the pin commit `5a38d601` carried the gitlink alone - the third of exactly three such pins the reviewer's audit found across all 105 gitlink bumps. Written after the fact from the client's own commit record.
