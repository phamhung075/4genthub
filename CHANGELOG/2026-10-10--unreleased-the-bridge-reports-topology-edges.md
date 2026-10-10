## Unreleased — the bridge reports topology edges

### Added
- `agenthub_client/src/agenthub_client/bridge.py`: the machine report now carries `edges` (`{room, from, to, kind}`), read per rig from `rig export <rigId> -o /dev/stdout` (pod `edges`; `parse_rig_edges`, `build_edges`). This is the bridge half that `02bfd416` held until the server was gated; production reports `0.0.29`, which accepts the key. The server refuses the whole report for one bad edge, so `build_edges` drops an unknown kind, a self edge, an invalid name and a repeat. Live measurement on rig `4genthub-min`: 5 edges (2 `delegates_to`, 1 `collaborates_with`, 2 `escalates_to`).
- `agenthub_client/tests/test_bridge.py`: the payload-shape test names `edges`; two new tests pin the trailing `Exported to` line and the per-room, server-safe edge list. `PYTHONPATH=src python3 -m pytest` in `agenthub_client`: 320 passed.

### Not done
- `agenthub_go/internal/clientbridge` (the Go port of the bridge) does not report edges yet.
