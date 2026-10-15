## NEXT-GEN2 topology is the minimum team and its edges

### Changed
- `NEXT-GEN2.md` (section 2): the cloud/client/core layer diagram is removed. Topology now shows only the `4genthub-min` team (lead, architect, go-dev, fe-dev, reviewer) with a seat table, a diagram and 12 directed edges using the five server edge kinds. The edges are proposed: the live room's `spec.json` still has `"links": []`.

### Tested
Documentation only. Edge kinds read from `agenthub_client/internal/clientbridge/edges.go`; seats and runtimes from `rooms/4genthub-min/spec.json`.
