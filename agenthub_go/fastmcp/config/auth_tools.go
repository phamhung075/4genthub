package config

import (
	"errors"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// TokenValidationError is raised when token validation fails.
type TokenValidationError struct{ Msg string }

func (e *TokenValidationError) Error() string { return e.Msg }

// RateLimitError is raised when the rate limit is exceeded.
type RateLimitError struct{ Msg string }

func (e *RateLimitError) Error() string { return e.Msg }

// TokenInfo is the subset of fastmcp.auth TokenInfo that AuthenticationTools reads.
type TokenInfo struct {
	UserID     string
	CreatedAt  time.Time
	ExpiresAt  *time.Time
	UsageCount int
	LastUsed   *time.Time
}

// AuthMiddleware is the fastmcp.auth.AuthMiddleware surface AuthenticationTools uses. That
// class has no Go implementation - the Go auth package ports the validator and the
// middlewares, not this surface - so what the consumer needs is declared here;
// AuthenticateRequest returning a nil *TokenInfo is Python's None.
type AuthMiddleware interface {
	Enabled() bool
	AuthenticateRequest(token string) (*TokenInfo, error)
	GetRateLimitStatus(token string) (any, error)
	RevokeToken(token string) (bool, error)
	GetAuthStatus() *entities.OrderedMap[any]
}

// AuthenticationTools is a container for authentication-related MCP tools.
type AuthenticationTools struct {
	AuthMiddleware AuthMiddleware
}

// NewAuthenticationTools builds the container.
func NewAuthenticationTools(authMiddleware AuthMiddleware) *AuthenticationTools {
	return &AuthenticationTools{AuthMiddleware: authMiddleware}
}

// ValidateToken validates an authentication token; it never returns an error, because the
// Python method catches every exception.
func (t *AuthenticationTools) ValidateToken(token string) *entities.OrderedMap[any] {
	enabled := t.AuthMiddleware.Enabled()
	tokenInfo, err := t.AuthMiddleware.AuthenticateRequest(token)
	if err != nil {
		var validationErr *TokenValidationError
		if errors.As(err, &validationErr) {
			return authErrorResult(enabled, "validation_error", validationErr.Error())
		}
		var rateLimitErr *RateLimitError
		if errors.As(err, &rateLimitErr) {
			return authErrorResult(enabled, "rate_limit_error", rateLimitErr.Error())
		}
		return authErrorResult(enabled, "internal_error", "Internal validation error")
	}
	if tokenInfo == nil {
		m := entities.NewOrderedMap[any]()
		m.Set("valid", true)
		m.Set("message", "Authentication disabled or MVP mode")
		m.Set("user_id", "mvp_user")
		m.Set("auth_enabled", enabled)
		return m
	}
	m := entities.NewOrderedMap[any]()
	m.Set("valid", true)
	m.Set("user_id", tokenInfo.UserID)
	m.Set("created_at", tmvo.IsoFormat(tokenInfo.CreatedAt))
	m.Set("expires_at", isoOrNilPtr(tokenInfo.ExpiresAt))
	m.Set("usage_count", tokenInfo.UsageCount)
	m.Set("last_used", isoOrNilPtr(tokenInfo.LastUsed))
	m.Set("auth_enabled", enabled)
	return m
}

// GetRateLimitStatus returns the current rate limit status for a token.
func (t *AuthenticationTools) GetRateLimitStatus(token string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	status, err := t.AuthMiddleware.GetRateLimitStatus(token)
	if err != nil {
		m.Set("success", false)
		m.Set("error", err.Error())
		return m
	}
	m.Set("success", true)
	m.Set("rate_limits", status)
	return m
}

// RevokeToken revokes an authentication token.
func (t *AuthenticationTools) RevokeToken(token string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	success, err := t.AuthMiddleware.RevokeToken(token)
	if err != nil {
		m.Set("success", false)
		m.Set("error", err.Error())
		return m
	}
	m.Set("success", success)
	if success {
		m.Set("message", "Token revoked successfully")
	} else {
		m.Set("message", "Failed to revoke token")
	}
	return m
}

// GetAuthStatus returns the authentication system status.
func (t *AuthenticationTools) GetAuthStatus() *entities.OrderedMap[any] {
	return t.AuthMiddleware.GetAuthStatus()
}

// GenerateToken returns the deprecation notice for MCP token generation.
func (t *AuthenticationTools) GenerateToken() *entities.OrderedMap[any] {
	example := entities.NewOrderedMap[any]()
	example.Set("name", "my-token")
	example.Set("expires_in_days", 30)
	example.Set("scopes", []string{"read", "write"})

	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", "Token generation via MCP tool is deprecated")
	m.Set("message", "Please use the API endpoint POST /api/v2/tokens to generate tokens. "+
		"This provides better security and integration with the authentication system.")
	m.Set("api_endpoint", "/api/v2/tokens")
	m.Set("method", "POST")
	m.Set("example", example)
	return m
}

// GetToolFunctions maps tool names to their implementation functions.
func (t *AuthenticationTools) GetToolFunctions() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("validate_token", t.ValidateToken)
	m.Set("get_rate_limit_status", t.GetRateLimitStatus)
	m.Set("revoke_token", t.RevokeToken)
	m.Set("get_auth_status", t.GetAuthStatus)
	m.Set("generate_token", t.GenerateToken)
	return m
}

// CreateAuthenticationTools creates the authentication tool functions for conditional
// registration.
func CreateAuthenticationTools(authMiddleware AuthMiddleware) *entities.OrderedMap[any] {
	return NewAuthenticationTools(authMiddleware).GetToolFunctions()
}

func authErrorResult(enabled bool, errorType, message string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("valid", false)
	m.Set("error", message)
	m.Set("error_type", errorType)
	m.Set("auth_enabled", enabled)
	return m
}

func isoOrNilPtr(t *time.Time) any {
	if t == nil {
		return nil
	}
	return tmvo.IsoFormat(*t)
}
