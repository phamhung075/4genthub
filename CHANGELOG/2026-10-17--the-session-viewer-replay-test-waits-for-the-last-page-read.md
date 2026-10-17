# The session viewer replay test waits for the last page read

CI on `main` failed on `TestSessionViewerReplaysInPagesOf500` ("2 page reads, want 3"), which stopped the build of both apps.

## Fixed

- `agenthub_go/fastmcp/server/httpapp/ws_session_viewer_test.go`: the test waited for one hub subscriber, but the viewer subscribes before the replay, so the wait proved nothing and the final empty page read could land after it. It now waits for the expected number of page reads. No production code changed.

## Tested

- `go test ./fastmcp/server/httpapp -run TestSessionViewer -count=30` and the full package pass.
