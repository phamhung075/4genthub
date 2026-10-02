package middleware

// Port of auth/middleware/request_context_middleware.py. Python stores the
// authentication context in ContextVars; Go carries it on the request context.

import (
	"context"
	"net/http"
	"strings"
)

type requestAuthContextKey struct{}

// RequestAuthContext holds the ContextVar values (user id, email, auth method, auth info,
// authenticated flag, token id).
type RequestAuthContext struct {
	UserID        *string
	Email         *string
	AuthMethod    *string
	AuthInfo      map[string]any
	Authenticated bool
	TokenID       *string
}

// AuthState is what DualAuthMiddleware leaves on request.state.
type AuthState struct {
	UserID   *string
	AuthType *string
	AuthInfo map[string]any
}

// WithRequestAuthContext returns ctx carrying c.
func WithRequestAuthContext(ctx context.Context, c *RequestAuthContext) context.Context {
	return context.WithValue(ctx, requestAuthContextKey{}, c)
}

func requestAuthContext(ctx context.Context) *RequestAuthContext {
	if c, ok := ctx.Value(requestAuthContextKey{}).(*RequestAuthContext); ok && c != nil {
		return c
	}
	return &RequestAuthContext{}
}

// CaptureAuthContextFromState is _capture_auth_context_from_request_state.
func CaptureAuthContextFromState(state AuthState) *RequestAuthContext {
	c := &RequestAuthContext{}
	if state.UserID == nil || *state.UserID == "" {
		return c
	}
	c.UserID = state.UserID
	c.Authenticated = true
	if len(state.AuthInfo) > 0 {
		if email, ok := state.AuthInfo["email"].(string); ok && email != "" {
			c.Email = &email
		}
		if tokenID, ok := state.AuthInfo["token_id"].(string); ok && tokenID != "" {
			c.TokenID = &tokenID
		}
		method := state.AuthType
		if raw, present := state.AuthInfo["auth_method"]; present {
			method = nil
			if m, ok := raw.(string); ok {
				method = &m
			}
		}
		c.AuthMethod = method
		c.AuthInfo = state.AuthInfo
	}
	return c
}

// RequestContextMiddleware captures the authentication state into the request context.
// stateFor reads the DualAuthMiddleware state of the request.
func RequestContextMiddleware(stateFor func(*http.Request) AuthState, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		state := stateFor(r)
		c := CaptureAuthContextFromState(state)
		if c.UserID != nil && strings.HasPrefix(r.URL.Path, "/mcp") {
			r = r.WithContext(context.WithValue(r.Context(), mcpScopeUserKey{}, McpScopeUser(*c.UserID, state.AuthType)))
		}
		next.ServeHTTP(w, r.WithContext(WithRequestAuthContext(r.Context(), c)))
	})
}

type mcpScopeUserKey struct{}

// McpScopeUser is the ASGI scope["user"] dict set for /mcp requests. Python reads the email
// with getattr(auth_info, "email", None) on a dict, which is always None, and the method from
// request.state.auth_type ("unknown" when unset).
func McpScopeUser(userID string, authType *string) map[string]any {
	method := "unknown"
	if authType != nil {
		method = *authType
	}
	return map[string]any{"user_id": userID, "email": nil, "auth_method": method}
}

// ScopeUser returns the user set by RequestContextMiddleware for /mcp requests.
func ScopeUser(ctx context.Context) map[string]any {
	u, _ := ctx.Value(mcpScopeUserKey{}).(map[string]any)
	return u
}

// GetCurrentUserID is get_current_user_id.
func GetCurrentUserID(ctx context.Context) *string { return requestAuthContext(ctx).UserID }

// GetCurrentUserEmail is get_current_user_email.
func GetCurrentUserEmail(ctx context.Context) *string { return requestAuthContext(ctx).Email }

// GetCurrentAuthMethod is get_current_auth_method.
func GetCurrentAuthMethod(ctx context.Context) *string { return requestAuthContext(ctx).AuthMethod }

// GetCurrentAuthInfo is get_current_auth_info.
func GetCurrentAuthInfo(ctx context.Context) map[string]any { return requestAuthContext(ctx).AuthInfo }

// IsRequestAuthenticated is is_request_authenticated.
func IsRequestAuthenticated(ctx context.Context) bool { return requestAuthContext(ctx).Authenticated }

// GetCurrentTokenID is get_current_token_id.
func GetCurrentTokenID(ctx context.Context) *string { return requestAuthContext(ctx).TokenID }

// GetAuthenticationContext is get_authentication_context.
func GetAuthenticationContext(ctx context.Context) map[string]any {
	c := requestAuthContext(ctx)
	return map[string]any{
		"user_id":       deref(c.UserID),
		"email":         deref(c.Email),
		"auth_method":   deref(c.AuthMethod),
		"auth_info":     c.AuthInfo,
		"authenticated": c.Authenticated,
	}
}

func deref(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

// UserContext is BackwardCompatUserContext / RequestContext.user.
type UserContext struct {
	UserID     string
	Email      *string
	AuthMethod *string
	Token      map[string]any
	Roles      []string
}

// GetCurrentUserContext is get_current_user_context (nil when unauthenticated).
func GetCurrentUserContext(ctx context.Context) *UserContext {
	c := requestAuthContext(ctx)
	if c.UserID == nil || *c.UserID == "" {
		return nil
	}
	return &UserContext{UserID: *c.UserID, Email: c.Email, Roles: []string{}}
}

// GetCurrentRequestContext is get_current_request_context (the RequestContext.user object).
func GetCurrentRequestContext(ctx context.Context) *UserContext {
	c := requestAuthContext(ctx)
	if c.UserID == nil || *c.UserID == "" {
		return nil
	}
	token := c.AuthInfo
	if token == nil {
		token = map[string]any{}
	}
	return &UserContext{UserID: *c.UserID, Email: c.Email, AuthMethod: c.AuthMethod, Token: token}
}
