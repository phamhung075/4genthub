package httpapp

import (
	"encoding/json"
	"io"
	"net/http"
	"strings"
	"time"
)

// mcpSSEKeepaliveInterval is how often a comment is written to an idle GET
// /mcp stream. sse_starlette, which the Python streamable-HTTP transport uses
// through EventSourceResponse, pings every 15 seconds (DEFAULT_PING_INTERVAL).
const mcpSSEKeepaliveInterval = 15 * time.Second

// mcpSSEHandler serves GET /mcp as the MCP streamable-HTTP SSE transport.
//
// Python enforces the Accept header in MCPHeaderValidationMiddleware
// (http_server.py): without text/event-stream it answers 406 with
// {"error": "Accept header must include text/event-stream for SSE"}. With it,
// StreamableHTTPSessionManager._handle_get_request (mcp/server/streamable_http.py)
// opens a text/event-stream response and EventSourceResponse keeps it alive
// with comment pings until the client closes the connection. This ports that
// behaviour to net/http.
func mcpSSEHandler(w http.ResponseWriter, r *http.Request) {
	if !strings.Contains(r.Header.Get("Accept"), "text/event-stream") {
		body, _ := json.Marshal(map[string]string{"error": "Accept header must include text/event-stream for SSE"})
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotAcceptable)
		_, _ = w.Write(body)
		return
	}

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming unsupported", http.StatusInternalServerError)
		return
	}

	h := w.Header()
	h.Set("Content-Type", "text/event-stream")
	h.Set("Cache-Control", "no-cache, no-transform")
	h.Set("Connection", "keep-alive")
	h.Set("X-Accel-Buffering", "no")
	w.WriteHeader(http.StatusOK)
	flusher.Flush()

	ticker := time.NewTicker(mcpSSEKeepaliveInterval)
	defer ticker.Stop()

	for {
		if _, err := io.WriteString(w, ": keepalive\n\n"); err != nil {
			return
		}
		flusher.Flush()

		select {
		case <-r.Context().Done():
			return
		case <-ticker.C:
		}
	}
}
