// Package mcpblock defines the content payload of an mcp module: one whole MCP server,
// expressed the way .mcp.json expresses it. A seat's mcp blocks decide which servers mount;
// a tool module (kind tool) only narrows permissions within a server that is mounted.
//
// The block carries no secret value. A field that needs one names an environment variable
// as ${VAR}; the client runtime expands it from the seat's environment, so the stored block
// and the rendered fragment never hold the credential. A credential-shaped literal is
// refused by Parse, reusing the same scanner the module publish path already applies.
package mcpblock

import (
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	"agenthub/fastmcp/seat_management/domain/secretscan"
)

// The server transports .mcp.json (and this payload) distinguish.
const (
	TypeHTTP  = "http"
	TypeStdio = "stdio"
)

// PlatformURLPlaceholder is the one deployment value a block may name but cannot carry: the
// workspace's own MCP endpoint, known only to the server that renders the seat. RenderSeat
// substitutes it from its configuration. Every other ${VAR} reference is left verbatim for
// the client runtime to expand from the seat's environment.
const PlatformURLPlaceholder = "${AGENTHUB_MCP_URL}"

// SeatHeader is the header every rendered http MCP block carries and the MCP route reads back: the
// seat's identity, `<room>/<seat>`. It is an ATTRIBUTION claim, never an authorization one - the
// route reads it to say who made a call, and decides nothing else from it.
const SeatHeader = "X-Agenthub-Seat"

// SeatValue is that header's value, in one place so the renderer that writes it and the route that
// reads it cannot drift into two shapes.
func SeatValue(roomSlug, seatKey string) string {
	return roomSlug + "/" + seatKey
}

// Server is one MCP server as a block's content describes it.
type Server struct {
	// Name is the server key in the rendered MCP fragment.
	Name string `json:"name"`
	// Type is TypeHTTP or TypeStdio.
	Type string `json:"type"`
	// URL is the endpoint of an http server.
	URL string `json:"url,omitempty"`
	// Command is the executable of a stdio server.
	Command string `json:"command,omitempty"`
	// Args are the arguments of a stdio server.
	Args []string `json:"args,omitempty"`
	// Headers are the HTTP headers of an http server; a value may reference ${VAR}.
	Headers map[string]string `json:"headers,omitempty"`
	// Env is the environment of a stdio server; a value may reference ${VAR}.
	Env map[string]string `json:"env,omitempty"`
}

// Parse validates one block's content. The payload is a single JSON object with only the
// fields above; an unknown field, a missing or contradictory field, or a credential-shaped
// value is an error, so a bad block fails at the store or seed path instead of rendering a
// half-defined server.
func Parse(content string) (Server, error) {
	if secretscan.Contains(content) {
		return Server{}, errors.New("carries a credential-shaped value: reference a secret as ${ENV_VAR} instead of writing it into the block")
	}
	if !json.Valid([]byte(content)) {
		return Server{}, errors.New("content is not one JSON value")
	}
	decoder := json.NewDecoder(strings.NewReader(content))
	decoder.DisallowUnknownFields()
	var server Server
	if err := decoder.Decode(&server); err != nil {
		return Server{}, fmt.Errorf("content is not a server object: %w", err)
	}
	if strings.TrimSpace(server.Name) == "" {
		return Server{}, errors.New("field name is required: it becomes the server key in the MCP fragment")
	}
	switch server.Type {
	case TypeHTTP:
		if server.URL == "" {
			return Server{}, fmt.Errorf("field url is required for a %q server", TypeHTTP)
		}
		if server.Command != "" || len(server.Args) > 0 || len(server.Env) > 0 {
			return Server{}, fmt.Errorf("a %q server takes url and headers, not command, args or env", TypeHTTP)
		}
	case TypeStdio:
		if server.Command == "" {
			return Server{}, fmt.Errorf("field command is required for a %q server", TypeStdio)
		}
		if server.URL != "" || len(server.Headers) > 0 {
			return Server{}, fmt.Errorf("a %q server takes command, args and env, not url or headers", TypeStdio)
		}
	default:
		return Server{}, fmt.Errorf("field type must be %q or %q, got %q", TypeHTTP, TypeStdio, server.Type)
	}
	if err := CheckURL(server.URL); err != nil {
		return Server{}, err
	}
	return server, nil
}

// CheckURL accepts a http(s) URL, the empty string (a stdio server has no URL), or a value
// that still holds a ${VAR} reference the client runtime expands. Anything else is rejected
// so a fragment never names a transport the client cannot open.
func CheckURL(url string) error {
	if url == "" || strings.Contains(url, "${") {
		return nil
	}
	if !strings.HasPrefix(url, "http://") && !strings.HasPrefix(url, "https://") {
		return fmt.Errorf("url must be http(s), got %q", url)
	}
	return nil
}

// WithPlatformURL returns the server with PlatformURLPlaceholder replaced by url in every
// field. Other ${VAR} references are left untouched for the client runtime.
func (s Server) WithPlatformURL(url string) Server {
	if url == "" {
		return s
	}
	replace := func(value string) string {
		return strings.ReplaceAll(value, PlatformURLPlaceholder, url)
	}
	s.URL = replace(s.URL)
	s.Command = replace(s.Command)
	s.Args = replaceAll(s.Args, replace)
	s.Headers = replaceMap(s.Headers, replace)
	s.Env = replaceMap(s.Env, replace)
	return s
}

func replaceAll(values []string, replace func(string) string) []string {
	if values == nil {
		return nil
	}
	out := make([]string, len(values))
	for i, value := range values {
		out[i] = replace(value)
	}
	return out
}

func replaceMap(values map[string]string, replace func(string) string) map[string]string {
	if values == nil {
		return nil
	}
	out := make(map[string]string, len(values))
	for key, value := range values {
		out[key] = replace(value)
	}
	return out
}

// Fragment returns the server as the value the MCP fragment maps Name to; the name itself is
// the fragment's map key, so it is not repeated. Only the fields the server's type uses are
// emitted.
func (s Server) Fragment() map[string]any {
	out := map[string]any{"type": s.Type}
	if s.URL != "" {
		out["url"] = s.URL
	}
	if s.Command != "" {
		out["command"] = s.Command
	}
	if len(s.Args) > 0 {
		out["args"] = s.Args
	}
	if len(s.Headers) > 0 {
		out["headers"] = s.Headers
	}
	if len(s.Env) > 0 {
		out["env"] = s.Env
	}
	return out
}
