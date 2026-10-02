package httpapp

import (
	"bufio"
	"errors"
	"fmt"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestMCPSseHandlerRejectsMissingEventStream(t *testing.T) {
	cases := []struct {
		name   string
		accept string
	}{
		{name: "no accept header"},
		{name: "json only", accept: "application/json"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := httptest.NewRecorder()
			req := httptest.NewRequest(http.MethodGet, "/mcp", nil)
			if tc.accept != "" {
				req.Header.Set("Accept", tc.accept)
			}
			mcpSSEHandler(rec, req)

			if rec.Code != http.StatusNotAcceptable {
				t.Fatalf("status = %d, want %d", rec.Code, http.StatusNotAcceptable)
			}
			if got := rec.Header().Get("Content-Type"); got != "application/json" {
				t.Fatalf("Content-Type = %q, want application/json", got)
			}
			want := `{"error":"Accept header must include text/event-stream for SSE"}`
			if got := rec.Body.String(); got != want {
				t.Fatalf("body = %s, want %s", got, want)
			}
		})
	}
}

func TestMCPSseHandlerStreamsKeepaliveUntilDisconnect(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(mcpSSEHandler))
	defer srv.Close()

	addr := srv.Listener.Addr().String()
	conn, err := net.Dial("tcp", addr)
	if err != nil {
		t.Fatalf("dial: %v", err)
	}
	defer conn.Close()

	// GET with the SSE Accept header; GET does not need application/json.
	fmt.Fprintf(conn, "GET /mcp HTTP/1.1\r\nHost: %s\r\nAccept: text/event-stream\r\n\r\n", addr)

	br := bufio.NewReader(conn)
	resp, err := http.ReadResponse(br, nil)
	if err != nil {
		t.Fatalf("read response: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusOK)
	}
	if got := resp.Header.Get("Content-Type"); got != "text/event-stream" {
		t.Fatalf("Content-Type = %q, want text/event-stream", got)
	}
	if got := resp.Header.Get("Cache-Control"); got != "no-cache, no-transform" {
		t.Fatalf("Cache-Control = %q, want no-cache, no-transform", got)
	}
	if got := resp.Header.Get("X-Accel-Buffering"); got != "no" {
		t.Fatalf("X-Accel-Buffering = %q, want no", got)
	}

	body := bufio.NewReader(resp.Body)
	comment, err := body.ReadString('\n')
	if err != nil {
		t.Fatalf("read keepalive: %v", err)
	}
	if !strings.HasPrefix(comment, ":") {
		t.Fatalf("keepalive = %q, want a comment line starting with ':'", comment)
	}
	blank, err := body.ReadString('\n')
	if err != nil {
		t.Fatalf("read event terminator: %v", err)
	}
	if strings.TrimRight(blank, "\r\n") != "" {
		t.Fatalf("event terminator = %q, want a blank line", blank)
	}

	// The stream must stay open until the client disconnects, so a read with a
	// short deadline times out instead of reaching EOF.
	_ = conn.SetReadDeadline(time.Now().Add(500 * time.Millisecond))
	if _, err := body.ReadByte(); err == nil {
		t.Fatal("unexpected data before the keepalive interval")
	} else {
		var ne net.Error
		if !errors.As(err, &ne) || !ne.Timeout() {
			t.Fatalf("stream closed before client disconnect: %v", err)
		}
	}
}
