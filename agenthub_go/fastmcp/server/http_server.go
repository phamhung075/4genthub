// Package server holds the Go port of src/fastmcp/server/http_server.py.
//
// http_server.py is a Starlette/FastAPI/MCP ASGI app factory. The application
// construction helpers (StarletteWithLifespan, create_base_app,
// setup_auth_middleware_and_routes, create_http_server_factory, create_sse_app,
// create_streamable_http_app, RequestContextMiddleware, HTTPSRedirectMiddleware,
// set_http_request / _current_http_request, _register_websocket_lifecycle) have
// no Go meaning: they depend on Starlette routes/middleware/ASGI scopes,
// FastAPI routers, SseServerTransport, StreamableHTTPSessionManager and the
// FastMCP server object. Only the two pieces whose behaviour is ordinary HTTP
// logic are ported here, following the net/http pattern already used by
// fastmcp/config/cors_factory.go.
package server

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"

	"agenthub/fastmcp/auth/mcp_integration"
)

// TokenVerifierAdapter ports TokenVerifierAdapter from http_server.py: a bridge
// between FastMCP's OAuthProvider (load_access_token) and MCP's TokenVerifier
// (verify_token). Python uses hasattr duck-typing; Go uses method-set type
// assertions with the same branch order. The dependency packages have no Go
// OAuthProvider yet, so the minimal interfaces below are declared here.
type TokenVerifierAdapter struct {
	Provider any
}

// tokenVerifier mirrors the MCP TokenVerifier protocol.
type tokenVerifier interface {
	VerifyToken(ctx context.Context, token string) *mcp_integration.AccessToken
}

// accessTokenLoader mirrors FastMCP's OAuthProvider.load_access_token.
type accessTokenLoader interface {
	LoadAccessToken(ctx context.Context, token string) *mcp_integration.AccessToken
}

// userTokenExtractor mirrors the JWT middleware provider's
// extract_user_from_token.
type userTokenExtractor interface {
	ExtractUserFromToken(token string) string
}

// NewTokenVerifierAdapter ports TokenVerifierAdapter.__init__.
func NewTokenVerifierAdapter(provider any) *TokenVerifierAdapter {
	return &TokenVerifierAdapter{Provider: provider}
}

// VerifyToken ports TokenVerifierAdapter.verify_token. The Python logger.error
// for an unknown provider type is dropped (logging calls are dropped).
func (a *TokenVerifierAdapter) VerifyToken(ctx context.Context, token string) *mcp_integration.AccessToken {
	if p, ok := a.Provider.(tokenVerifier); ok {
		return p.VerifyToken(ctx, token)
	}
	if p, ok := a.Provider.(accessTokenLoader); ok {
		return p.LoadAccessToken(ctx, token)
	}
	if p, ok := a.Provider.(userTokenExtractor); ok {
		if userID := p.ExtractUserFromToken(token); userID != "" {
			return &mcp_integration.AccessToken{
				Token:    token,
				ClientID: userID,
				Scopes:   []string{"execute:mcp"},
			}
		}
		return nil
	}
	return nil
}

// MCPHeaderValidationMiddleware ports MCPHeaderValidationMiddleware: it enforces
// the MCP protocol headers for /mcp endpoints and adds CORS headers to its
// error responses.
type MCPHeaderValidationMiddleware struct {
	Next        http.Handler
	CORSOrigins []string
}

// NewMCPHeaderValidationMiddleware ports MCPHeaderValidationMiddleware.__init__
// (cors_origins or ["*"]).
func NewMCPHeaderValidationMiddleware(next http.Handler, corsOrigins []string) *MCPHeaderValidationMiddleware {
	if len(corsOrigins) == 0 {
		corsOrigins = []string{"*"}
	}
	return &MCPHeaderValidationMiddleware{Next: next, CORSOrigins: corsOrigins}
}

// ServeHTTP ports MCPHeaderValidationMiddleware.__call__ for http scopes.
func (m *MCPHeaderValidationMiddleware) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path
	method := strings.ToUpper(r.Method)

	header := func(name string) string { return r.Header.Get(name) }

	sendError := func(statusCode int, detail string) {
		body, _ := json.Marshal(map[string]string{"error": detail})
		w.Header().Set("Content-Type", "application/json")
		origin := header("Origin")
		if containsString(m.CORSOrigins, origin) || containsString(m.CORSOrigins, "*") {
			w.Header().Set("Access-Control-Allow-Origin", origin)
		} else if len(m.CORSOrigins) > 0 {
			w.Header().Set("Access-Control-Allow-Origin", m.CORSOrigins[0])
		}
		w.Header().Set("Access-Control-Allow-Credentials", "true")
		w.Header().Set("Access-Control-Allow-Methods", "*")
		w.Header().Set("Access-Control-Allow-Headers", "*")
		w.WriteHeader(statusCode)
		_, _ = w.Write(body)
	}

	if strings.HasPrefix(path, "/mcp") {
		switch method {
		case http.MethodPost:
			if header("Content-Type") != "application/json" {
				sendError(415, "Content-Type must be application/json")
				return
			}
			accept := header("Accept")
			if !strings.Contains(accept, "application/json") || !strings.Contains(accept, "text/event-stream") {
				sendError(406, "Accept header must include both application/json and text/event-stream")
				return
			}
			// /mcp/initialize only needs Content-Type and Accept; other POSTs
			// also pass through after validation.
			m.Next.ServeHTTP(w, r)
			return
		case http.MethodGet:
			if !strings.Contains(header("Accept"), "text/event-stream") {
				sendError(406, "Accept header must include text/event-stream for SSE")
				return
			}
		}
	}
	m.Next.ServeHTTP(w, r)
}

func containsString(list []string, s string) bool {
	for _, x := range list {
		if x == s {
			return true
		}
	}
	return false
}
