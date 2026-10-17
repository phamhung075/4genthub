# The session viewer tests wait for each viewer to leave the hub

CI on `main` failed again in `ws_session_viewer_test.go`: the auth tests saw "1 hub subscriptions for an unauthenticated caller" because the previous test's viewer had not yet dropped its subscription on the shared hub.

## Fixed

- `agenthub_go/fastmcp/server/httpapp/ws_session_viewer_test.go`: the dial helpers close the client socket and wait for the hub to show no subscriber before the test ends. No production code changed.

## Tested

- `go test ./fastmcp/server/httpapp` (package, and the viewer tests 30 times) passes.
