// Package mcp_integration ports fastmcp/auth/mcp_integration/mcp_auth_middleware.py.
package mcp_integration

import (
	"context"
	"log"
	"net/http"
	"strings"

	"agenthub/fastmcp/auth/middleware"
)

type mcpAuthContextKey struct{}

// MCPAuthContext carries user details on request context.
type MCPAuthContext struct {
	UserID *string
	Email  *string
	Roles  []string
	Scopes []string
}

// WithMCPAuthContext attaches MCPAuthContext to a context.
func WithMCPAuthContext(ctx context.Context, authCtx *MCPAuthContext) context.Context {
	return context.WithValue(ctx, mcpAuthContextKey{}, authCtx)
}

// GetMCPAuthContext retrieves MCPAuthContext from context if present.
func GetMCPAuthContext(ctx context.Context) *MCPAuthContext {
	if ctx == nil {
		return nil
	}
	c, _ := ctx.Value(mcpAuthContextKey{}).(*MCPAuthContext)
	return c
}

// MCPAuthMiddleware extracts JWT tokens from HTTP Authorization headers and sets user context.
type MCPAuthMiddleware struct {
	jwtBackend *JWTAuthBackend
}

// NewMCPAuthMiddleware creates a new MCPAuthMiddleware.
func NewMCPAuthMiddleware(jwtBackend *JWTAuthBackend) *MCPAuthMiddleware {
	return &MCPAuthMiddleware{
		jwtBackend: jwtBackend,
	}
}

// Handler wraps an http.Handler with MCP authentication.
func (m *MCPAuthMiddleware) Handler(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		authHeader := r.Header.Get("Authorization")
		reqCtx := r.Context()

		if strings.HasPrefix(authHeader, "Bearer ") {
			token := strings.TrimPrefix(authHeader, "Bearer ")

			if m.jwtBackend != nil {
				func() {
					defer func() {
						if rec := recover(); rec != nil {
							log.Printf("[WARN] panic in MCPAuthMiddleware token verification: %v", rec)
						}
					}()

					accessToken := m.jwtBackend.VerifyToken(reqCtx, token)
					if accessToken != nil {
						userID := accessToken.ClientID
						userCtx := m.jwtBackend.getUserContext(reqCtx, userID, nil)
						if userCtx != nil {
							email := userCtx.Email
							uid := userCtx.UserID
							// Set RequestAuthContext
							authContext := &middleware.RequestAuthContext{
								UserID:        &uid,
								Email:         &email,
								Authenticated: true,
								AuthInfo: map[string]any{
									"roles":  userCtx.Roles,
									"scopes": accessToken.Scopes,
								},
							}
							reqCtx = middleware.WithRequestAuthContext(reqCtx, authContext)

							// Set MCPAuthContext
							reqCtx = WithMCPAuthContext(reqCtx, &MCPAuthContext{
								UserID: &uid,
								Email:  &email,
								Roles:  userCtx.Roles,
								Scopes: accessToken.Scopes,
							})
							log.Printf("[DEBUG] MCP user context set for user %s", uid)
						} else {
							log.Printf("[WARN] Could not get user context for user_id: %s", userID)
						}
					}
				}()
			}
		} else {
			log.Printf("[DEBUG] No Bearer token found in Authorization header")
		}

		next.ServeHTTP(w, r.WithContext(reqCtx))
	})
}

// GetMCPAuthMiddleware is the factory function matching Python's get_mcp_auth_middleware.
func GetMCPAuthMiddleware(jwtBackend *JWTAuthBackend) func(http.Handler) http.Handler {
	mw := NewMCPAuthMiddleware(jwtBackend)
	return mw.Handler
}
