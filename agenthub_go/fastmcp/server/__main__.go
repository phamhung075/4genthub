// Package server ports fastmcp/server/__main__.py.
package server

import "context"

// Main is the programmatic entry point mirroring python -m fastmcp.server.
func Main() {
	_ = RunServer(context.Background())
}
