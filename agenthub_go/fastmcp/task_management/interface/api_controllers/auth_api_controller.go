// Package api_controllers ports task_management/interface/api_controllers.
package api_controllers

import (
	"context"
	"strings"

	authuser "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/task_management/application/facades"
	tmdb "agenthub/fastmcp/task_management/infrastructure/database"
)

// AuthAPIController ports AuthAPIController. The Python singleton/global auth
// facade is created lazily from the session on first use.
type AuthAPIController struct {
	authFacade *facades.AuthApplicationFacade
}

// NewAuthAPIController mirrors __init__: lazy initialization, no facade yet.
func NewAuthAPIController() *AuthAPIController { return &AuthAPIController{} }

// ensureFacade lazily builds the application facade from the session.
func (c *AuthAPIController) ensureFacade(session *tmdb.SessionManager) (*facades.AuthApplicationFacade, error) {
	if c.authFacade == nil {
		facade, err := facades.NewAuthApplicationFacade(session)
		if err != nil {
			return nil, err
		}
		c.authFacade = facade
	}
	return c.authFacade, nil
}

// VerifyJWTToken ports verify_jwt_token. All errors yield nil (Python swallows them).
func (c *AuthAPIController) VerifyJWTToken(ctx context.Context, token string, session *tmdb.SessionManager) *authuser.User {
	facade, err := c.ensureFacade(session)
	if err != nil {
		return nil
	}
	return facade.VerifyJWTToken(ctx, token)
}

// DualAuthenticate ports dual_authenticate.
func (c *AuthAPIController) DualAuthenticate(ctx context.Context, token string, session *tmdb.SessionManager) *authuser.User {
	if token == "" {
		return nil
	}
	facade, err := c.ensureFacade(session)
	if err != nil {
		return nil
	}
	return facade.DualAuthenticate(ctx, token)
}

// ExtractTokenFromHeaders ports extract_token_from_headers.
func (c *AuthAPIController) ExtractTokenFromHeaders(headers map[string]string) *string {
	authHeader := headers["authorization"]
	if strings.HasPrefix(authHeader, "Bearer ") {
		token := strings.TrimSpace(authHeader[7:])
		return &token
	}
	if apiToken := headers["x-api-token"]; apiToken != "" {
		return &apiToken
	}
	return nil
}

// ExtractTokenFromCookies ports extract_token_from_cookies.
func (c *AuthAPIController) ExtractTokenFromCookies(cookies map[string]string) *string {
	if accessToken := cookies["access_token"]; accessToken != "" {
		return &accessToken
	}
	return nil
}
