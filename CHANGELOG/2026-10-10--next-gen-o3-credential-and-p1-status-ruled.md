## Unreleased — NEXT_GEN: O3's credential corrected, P1's landed state recorded

### Changed
- `agenthub_go/NEXT_GEN.md` O3: T4 (the per-machine token) no longer exists after `e5ecff63`. O3 now authenticates with `AGENTHUB_TOKEN` through `authed`, and nothing has to land before it.
- `agenthub_go/NEXT_GEN.md` P1: the schema and the per-user lock landed in `fa74db0a` (plus `1e0a53e6`, `a0313d5f`, `2bbda1e7`). The architect ran the 14 ledger tests at `76b800b9` on a clean export against testpg: 14/14 PASS. The embedded-runner check is T12 stage 1's.
- Ruling row `d2587de7-e8c7-4079-8da2-c6ac7cee7049`; the lead's request is `qitem-20261010214408-8b10b92077127a87`.
