## The Go bridge reported no topology edges, so a room reported by it drew no graph

### Added
- `agenthub_go/internal/clientbridge/edges.go`: `ParseRigEdges` (the `pods[].edges` of `rig export <rigId> -o /dev/stdout`, minus the trailing `Exported to` line), `RigRooms` and `BuildEdges`, a port of `parse_rig_edges` and `build_edges` in `agenthub_client/bridge.py`. `BuildEdges` drops what the server would refuse the whole report for: an unknown kind, a self edge, an invalid name, a repeated link.
- `bridge.go`/`payload.go`: `Payload` carries `edges`, always `[]` rather than `null`, read through the same rig contract or Runner seam as the nodes. A rig that cannot be exported reports no edges and a note.
- `agenthub_go/internal/clientbridge/edges_test.go`: the Python test's fixture and expectations (status line, drops, per-room report), plus a no-pods spec and the empty-list wire shape.

### Verified
- `gofmt` nothing, `go vet` clean, `go test ./internal/...` ok. Not run: a live report against production.
