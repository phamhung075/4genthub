## Changed

- `agenthub_client` pin moves `e901b94` -> `08d8bbf` (3 commits); the pin commit's own subject records a gated PASS on client main.

### Removed

- The orphaned `skills-delivery` package leaves, while the link guard it existed for stays (`08d8bbf`).
- The seat's skills are the runtime's to install, so the client stops installing them (`0a266c8`).
- The rigspec verbs leave together with their route, and the tree is swept for their names (`ba96fee`). 37 files, `+357/-4360`.

Late entry: the pin commit `67cb47d7` carried the gitlink alone - one of exactly three such pins across all 105 gitlink bumps, found by the reviewer's audit. Written after the fact from the client's own commit record.
