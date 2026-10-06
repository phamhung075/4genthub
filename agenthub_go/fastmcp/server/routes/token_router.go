// token_router.go ports server/routes/token_router.py. FastAPI APIRouter and
// Depends plumbing dropped; handlers, response fields in Python declaration
// order and status codes kept. TokenAPIController has no Go port yet.
package routes

import (
	"context"
	"strings"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	taskdomain "agenthub/fastmcp/task_management/domain/entities"
)

// TokenCreateRequest mirrors TokenCreateRequest.
type TokenCreateRequest struct {
	Name          string
	Scopes        []string
	ExpiresInDays int
	RateLimit     *int
	Metadata      *taskdomain.OrderedMap[any]
}

// TokenResponse mirrors TokenResponse field order.
type TokenResponse struct {
	ID         string
	Name       string
	Scopes     []string
	CreatedAt  any
	ExpiresAt  any
	LastUsedAt any
	UsageCount *int
	RateLimit  *int
	UsageStats *taskdomain.OrderedMap[any]
	IsActive   bool
	Token      *string
	Metadata   *taskdomain.OrderedMap[any]
}

// ToOrderedMap serialises TokenResponse in declaration order.
func (t TokenResponse) ToOrderedMap() *taskdomain.OrderedMap[any] {
	scopes := t.Scopes
	if scopes == nil {
		scopes = []string{}
	}
	usageStats := t.UsageStats
	if usageStats == nil {
		usageStats = taskdomain.NewOrderedMap[any]()
	}
	metadata := t.Metadata
	if metadata == nil {
		metadata = taskdomain.NewOrderedMap[any]()
	}
	usageCount := 0
	if t.UsageCount != nil {
		usageCount = *t.UsageCount
	}
	out := taskdomain.NewOrderedMap[any]()
	out.Set("id", t.ID)
	out.Set("name", t.Name)
	out.Set("scopes", scopes)
	out.Set("created_at", t.CreatedAt)
	out.Set("expires_at", t.ExpiresAt)
	out.Set("last_used_at", t.LastUsedAt)
	out.Set("usage_count", usageCount)
	out.Set("rate_limit", t.RateLimit)
	out.Set("usage_stats", usageStats)
	out.Set("is_active", t.IsActive)
	out.Set("token", t.Token)
	out.Set("metadata", metadata)
	return out
}

// TokenRouteController is the minimal TokenAPIController surface.
type TokenRouteController interface {
	GenerateAPIToken(ctx context.Context, userID, name string, scopes []string, expiresInDays int, rateLimit *int) (TokenOperationResult, error)
	ListUserTokens(ctx context.Context, userID string) (TokenRouteListResult, error)
	GetTokenDetails(ctx context.Context, tokenID, userID string) (TokenOperationResult, error)
	DeleteToken(ctx context.Context, tokenID, userID string) (TokenOperationResult, error)
	RevokeToken(ctx context.Context, tokenID, userID string) (TokenOperationResult, error)
	ReactivateToken(ctx context.Context, tokenID, userID string) (TokenOperationResult, error)
	RotateToken(ctx context.Context, tokenID, userID string) (TokenOperationResult, error)
	ValidateToken(ctx context.Context, token string) (TokenValidateResult, error)
	CleanupExpiredTokens(ctx context.Context, userID string) (TokenCleanupResult, error)
}

// TokenOperationResult mirrors the controller dict for token operations.
type TokenOperationResult struct {
	Success   bool
	Error     *string
	Message   *string
	TokenData *taskdomain.OrderedMap[any]
}

// TokenRouteListResult mirrors list_user_tokens.
type TokenRouteListResult struct {
	Success bool
	Error   *string
	Tokens  []*taskdomain.OrderedMap[any]
	Total   int
}

// TokenValidateResult mirrors validate_token.
type TokenValidateResult struct {
	Success bool
	Error   *string
	Claims  *taskdomain.OrderedMap[any]
}

// TokenCleanupResult mirrors cleanup_expired_tokens.
type TokenCleanupResult struct {
	Success      bool
	Error        *string
	Message      *string
	DeletedCount int
}

func tokenResponseFromMap(m *taskdomain.OrderedMap[any]) TokenResponse {
	resp := TokenResponse{}
	if m == nil {
		return resp
	}
	if v, ok := m.Get("id"); ok {
		resp.ID = trStr(v)
	}
	if v, ok := m.Get("name"); ok {
		resp.Name = trStr(v)
	}
	if v, ok := m.Get("scopes"); ok {
		if s, ok := v.([]string); ok {
			resp.Scopes = s
		} else if s, ok := v.([]any); ok {
			for _, x := range s {
				if str, ok := x.(string); ok {
					resp.Scopes = append(resp.Scopes, str)
				}
			}
		}
	}
	resp.CreatedAt = trOmGet(m, "created_at")
	resp.ExpiresAt = trOmGet(m, "expires_at")
	resp.LastUsedAt = trOmGet(m, "last_used_at")
	if v, ok := m.Get("usage_count"); ok {
		if n, ok := v.(int); ok {
			resp.UsageCount = &n
		}
	}
	if v, ok := m.Get("rate_limit"); ok {
		if n, ok := v.(int); ok {
			resp.RateLimit = &n
		}
	}
	if v, ok := m.Get("usage_stats"); ok {
		if om, ok := v.(*taskdomain.OrderedMap[any]); ok {
			resp.UsageStats = om
		}
	}
	if v, ok := m.Get("is_active"); ok {
		if b, ok := v.(bool); ok {
			resp.IsActive = b
		}
	}
	if v, ok := m.Get("token"); ok {
		if s, ok := v.(string); ok {
			resp.Token = &s
		}
	}
	if v, ok := m.Get("metadata"); ok {
		if om, ok := v.(*taskdomain.OrderedMap[any]); ok {
			resp.Metadata = om
		}
	}
	return resp
}

// GenerateTokenHandler ports generate_token_handler.
func GenerateTokenHandler(ctx context.Context, req TokenCreateRequest, currentUser *authdomain.User, c TokenRouteController) (*taskdomain.OrderedMap[any], error) {
	result, err := c.GenerateAPIToken(ctx, currentUserID(currentUser), req.Name, req.Scopes, req.ExpiresInDays, req.RateLimit)
	if err != nil {
		// Propagate the controller's error instead of replacing it with a bare
		// "Failed to generate token": an unset JWT_SECRET_KEY arrives here as the
		// same *auth.HTTPException (500, "Server configuration error: JWT secret
		// not set") the REST dependency path raises.
		return nil, err
	}
	if result.Success {
		resp := tokenResponseFromMap(result.TokenData)
		return resp.ToOrderedMap(), nil
	}
	return nil, httpErr(500, pyOrStr(result.Error, "Failed to generate token"))
}

// ListTokensHandler ports list_tokens_handler.
func ListTokensHandler(ctx context.Context, currentUser *authdomain.User, c TokenRouteController, skip, limit int) (*taskdomain.OrderedMap[any], error) {
	result, err := c.ListUserTokens(ctx, currentUserID(currentUser))
	if err != nil {
		// Propagate the controller's error instead of replacing it with a bare
		// "Failed to list tokens": a facade-resolution failure (unset JWT_SECRET_KEY)
		// arrives here as the same *auth.HTTPException the REST dependency path raises.
		return nil, err
	}
	if !result.Success {
		return nil, httpErr(500, pyOrStr(result.Error, "Failed to list tokens"))
	}
	tokens := result.Tokens
	if skip != 0 || limit != 100 {
		end := skip + limit
		if skip > len(tokens) {
			tokens = []*taskdomain.OrderedMap[any]{}
		} else {
			if end > len(tokens) {
				end = len(tokens)
			}
			tokens = tokens[skip:end]
		}
	}
	data := []any{}
	for _, t := range tokens {
		resp := tokenResponseFromMap(t)
		data = append(data, resp.ToOrderedMap())
	}
	out := taskdomain.NewOrderedMap[any]()
	out.Set("data", data)
	out.Set("total", result.Total)
	return out, nil
}

// ListTokens ports list_tokens (GET /), without the skip/limit pagination of the
// standalone handler.
func ListTokens(ctx context.Context, currentUser *authdomain.User, c TokenRouteController, skip, limit int) (*taskdomain.OrderedMap[any], error) {
	return ListTokensHandler(ctx, currentUser, c, skip, limit)
}

// GetTokenDetails ports get_token_details.
func GetTokenDetails(ctx context.Context, tokenID string, currentUser *authdomain.User, c TokenRouteController) (*taskdomain.OrderedMap[any], error) {
	result, err := c.GetTokenDetails(ctx, tokenID, currentUserID(currentUser))
	if err != nil {
		// Propagate the controller's error instead of a bare "Failed to get token
		// details" (same facade-resolution cause as ListTokensHandler).
		return nil, err
	}
	if result.Success {
		resp := tokenResponseFromMap(result.TokenData)
		return resp.ToOrderedMap(), nil
	}
	if result.Error != nil && strings.Contains(strings.ToLower(*result.Error), "not found") {
		return nil, httpErr(404, "Token not found")
	}
	return nil, httpErr(500, pyOrStr(result.Error, "Failed to get token details"))
}

// tokenMessage builds {"message": ...} for delete/revoke/reactivate.
func tokenMessage(result TokenOperationResult, def, failDef string) (*taskdomain.OrderedMap[any], error) {
	if result.Success {
		out := taskdomain.NewOrderedMap[any]()
		out.Set("message", pyOrStr(result.Message, def))
		return out, nil
	}
	if result.Error != nil && strings.Contains(strings.ToLower(*result.Error), "not found") {
		return nil, httpErr(404, "Token not found")
	}
	return nil, httpErr(500, pyOrStr(result.Error, failDef))
}

// DeleteToken ports delete_token.
func DeleteToken(ctx context.Context, tokenID string, currentUser *authdomain.User, c TokenRouteController) (*taskdomain.OrderedMap[any], error) {
	result, err := c.DeleteToken(ctx, tokenID, currentUserID(currentUser))
	if err != nil {
		// Propagate the controller's error instead of a bare "Failed to delete token"
		// (same facade-resolution cause as ListTokensHandler).
		return nil, err
	}
	return tokenMessage(result, "Token deleted successfully", "Failed to delete token")
}

// RevokeToken ports revoke_token.
func RevokeToken(ctx context.Context, tokenID string, currentUser *authdomain.User, c TokenRouteController) (*taskdomain.OrderedMap[any], error) {
	result, err := c.RevokeToken(ctx, tokenID, currentUserID(currentUser))
	if err != nil {
		// Propagate the controller's error instead of a bare "Failed to revoke token"
		// (same facade-resolution cause as ListTokensHandler).
		return nil, err
	}
	return tokenMessage(result, "Token revoked successfully", "Failed to revoke token")
}

// ReactivateToken ports reactivate_token.
func ReactivateToken(ctx context.Context, tokenID string, currentUser *authdomain.User, c TokenRouteController) (*taskdomain.OrderedMap[any], error) {
	result, err := c.ReactivateToken(ctx, tokenID, currentUserID(currentUser))
	if err != nil {
		// Propagate the controller's error instead of a bare "Failed to reactivate
		// token" (same facade-resolution cause as ListTokensHandler).
		return nil, err
	}
	return tokenMessage(result, "Token reactivated successfully", "Failed to reactivate token")
}

// RotateToken ports rotate_token.
func RotateToken(ctx context.Context, tokenID string, currentUser *authdomain.User, c TokenRouteController) (*taskdomain.OrderedMap[any], error) {
	result, err := c.RotateToken(ctx, tokenID, currentUserID(currentUser))
	if err != nil {
		// Propagate the controller's error instead of a bare "Failed to rotate token"
		// (same facade-resolution cause as ListTokensHandler).
		return nil, err
	}
	if result.Success {
		resp := tokenResponseFromMap(result.TokenData)
		return resp.ToOrderedMap(), nil
	}
	if result.Error != nil && strings.Contains(strings.ToLower(*result.Error), "not found") {
		return nil, httpErr(404, "Token not found")
	}
	return nil, httpErr(500, pyOrStr(result.Error, "Failed to rotate token"))
}

// ValidateTokenEndpoint ports validate_token_endpoint.
func ValidateTokenEndpoint(ctx context.Context, token string, c TokenRouteController) (*taskdomain.OrderedMap[any], error) {
	result, err := c.ValidateToken(ctx, token)
	if err != nil {
		// A facade-resolution failure is a server misconfiguration, not an invalid
		// token: propagate the cause (the same *auth.HTTPException the REST dependency
		// path raises, 500 + the actionable sentence) instead of masking it as a 401.
		return nil, err
	}
	if result.Success {
		return result.Claims, nil
	}
	return nil, httpErr(401, pyOrStr(result.Error, "Invalid token"))
}

// CleanupExpiredTokens ports cleanup_expired_tokens.
func CleanupExpiredTokens(ctx context.Context, currentUser *authdomain.User, c TokenRouteController) (*taskdomain.OrderedMap[any], error) {
	result, err := c.CleanupExpiredTokens(ctx, currentUserID(currentUser))
	if err != nil {
		// Propagate the controller's error instead of a bare "Failed to cleanup
		// tokens" (same facade-resolution cause as ListTokensHandler).
		return nil, err
	}
	if result.Success {
		out := taskdomain.NewOrderedMap[any]()
		out.Set("message", pyOrStr(result.Message, "Cleanup completed"))
		out.Set("deleted_count", result.DeletedCount)
		return out, nil
	}
	return nil, httpErr(500, pyOrStr(result.Error, "Failed to cleanup tokens"))
}

// TokenServiceHealth ports token_service_health.
func TokenServiceHealth() *taskdomain.OrderedMap[any] {
	out := taskdomain.NewOrderedMap[any]()
	out.Set("status", "healthy")
	out.Set("service", "token_management")
	out.Set("ddd_compliant", true)
	return out
}
