## 2026-10-10

### Removed
- `agenthub_go/fastmcp/server/httpapp/seat_feedback_script_test.go`: two tests executed `agenthub_client/src/agenthub_client/seat_feedback.sh` by relative path. The Python client and that script are gone, and the Go client's `feedback` verb now owns the no-MCP submission path with its own tests, so the server no longer reaches into the client checkout. CI (`go` job, run 38054546147) failed on the missing file.

### Testing
- `go vet` and `go test ./fastmcp/server/httpapp/` pass.
