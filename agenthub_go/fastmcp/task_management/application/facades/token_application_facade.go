// Token Application Facade (Python
// task_management/application/facades/token_application_facade.py).
//
// The facade delegates to the auth JWT/MCP token services and the token repository. The
// Python repository returns ORM rows whose attributes are read via getattr; the Go
// ITokenRepository returns `any`, so attribute access is done with reflection here and the
// application layer never imports the infrastructure/database package.
//
// Two Python quirks are preserved deliberately because they are observable:
//   - generate_mcp_token_from_user reads mcp_token_obj.token_id, which MCPToken does not
//     define, so the method always returns the AttributeError response.
//   - validate_token calls JWTService.decode_token, which does not exist on the Python
//     JWTService, so the method always returns the AttributeError response.
package facades

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"time"

	authservices "agenthub/fastmcp/auth/domain/services"
	mcpservices "agenthub/fastmcp/auth/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// tokenFacadeMCPTokenService is the Python module-level `mcp_token_service` singleton.
var tokenFacadeMCPTokenService = mcpservices.NewMCPTokenService()

// TokenFacadeRepositoryBackend constructs a TokenRepository when none was injected
// (Python `_get_repository` imports it lazily from infrastructure). The application layer
// must not import infrastructure, so this hook is supplied during wiring.
var TokenFacadeRepositoryBackend func(session any) (repositories.ITokenRepository, error)

// TokenApplicationFacade mirrors token_application_facade.TokenApplicationFacade.
type TokenApplicationFacade struct {
	jwtService      *authservices.JWTService
	mcpTokenService *mcpservices.MCPTokenService
	tokenRepository repositories.ITokenRepository
}

// NewTokenApplicationFacade mirrors __init__: reads JWT_SECRET_KEY / JWT_ISSUER and builds
// the JWT service. An empty secret raises ValueError.
func NewTokenApplicationFacade(tokenRepository repositories.ITokenRepository) (*TokenApplicationFacade, error) {
	jwtSecret := os.Getenv("JWT_SECRET_KEY")
	if jwtSecret == "" {
		return nil, &value_objects.ValueError{Msg: "JWT_SECRET_KEY must be set in environment"}
	}
	issuer := os.Getenv("JWT_ISSUER")
	if issuer == "" {
		issuer = "agenthub"
	}
	jwtService, err := authservices.NewJWTService(jwtSecret, issuer)
	if err != nil {
		return nil, err
	}
	return &TokenApplicationFacade{
		jwtService:      jwtService,
		mcpTokenService: tokenFacadeMCPTokenService,
		tokenRepository: tokenRepository,
	}, nil
}

// zpTokenGetRepository mirrors _get_repository.
func (f *TokenApplicationFacade) zpTokenGetRepository(session any) repositories.ITokenRepository {
	if f.tokenRepository == nil && session != nil {
		if TokenFacadeRepositoryBackend != nil {
			repo, err := TokenFacadeRepositoryBackend(session)
			if err != nil {
				return nil
			}
			f.tokenRepository = repo
		}
	}
	return f.tokenRepository
}

// zpTokenSuccess builds {"success": true, ...} in the given order.
func zpTokenSuccess(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}

// zpTokenFailure builds {"success": false, "error": <msg>}.
func zpTokenFailure(msg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", msg)
	return m
}

// GenerateMCPTokenFromUser mirrors generate_mcp_token_from_user. The Python body reads
// mcp_token_obj.token_id, which does not exist, so the AttributeError is returned
// instead. The service call runs first and stores the (unreachable) token, as in Python.
func (f *TokenApplicationFacade) GenerateMCPTokenFromUser(ctx context.Context, userID, email string, expiresInHours int, metadata *entities.OrderedMap[any], session any) *entities.OrderedMap[any] {
	if metadata == nil {
		metadata = entities.NewOrderedMap[any]()
	}
	f.mcpTokenService.GenerateMCPTokenFromUserID(ctx, userID, &email, expiresInHours, metadata)
	return zpTokenFailure("'MCPToken' object has no attribute 'token_id'")
}

// RevokeUserTokens mirrors revoke_user_tokens.
func (f *TokenApplicationFacade) RevokeUserTokens(ctx context.Context, userID string) *entities.OrderedMap[any] {
	success := f.mcpTokenService.RevokeUserTokens(ctx, userID)
	message := "No tokens found to revoke"
	if success {
		message = "All tokens revoked successfully"
	}
	m := entities.NewOrderedMap[any]()
	m.Set("success", success)
	m.Set("revoked", success)
	m.Set("message", message)
	return m
}

// GetTokenStats mirrors get_token_stats.
func (f *TokenApplicationFacade) GetTokenStats() *entities.OrderedMap[any] {
	stats := f.mcpTokenService.GetTokenStats()
	return zpTokenSuccess("stats", stats)
}

// CleanupExpiredTokens mirrors cleanup_expired_tokens.
func (f *TokenApplicationFacade) CleanupExpiredTokens(ctx context.Context) *entities.OrderedMap[any] {
	cleaned := f.mcpTokenService.CleanupExpiredTokens(ctx)
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("cleaned_count", cleaned)
	m.Set("message", fmt.Sprintf("Cleaned up %d expired tokens", cleaned))
	return m
}

// CreateAPIToken mirrors create_api_token.
func (f *TokenApplicationFacade) CreateAPIToken(ctx context.Context, userID, name string, scopes []string, expiresInDays int, rateLimit *int, metadata *entities.OrderedMap[any], session any) *entities.OrderedMap[any] {
	effectiveRateLimit := 1000
	if rateLimit != nil {
		effectiveRateLimit = *rateLimit
	}
	if effectiveRateLimit > 1000 {
		return zpTokenFailure("Rate limit must be 1000 or less requests per hour")
	}

	repository := f.zpTokenGetRepository(session)
	if repository == nil {
		return zpTokenFailure("'NoneType' object has no attribute 'create_token'")
	}

	tokenID := "tok_" + zpTokenHex(8)

	jwtToken, err := f.jwtService.GenerateToken(userID, scopes, expiresInDays, tokenID, "mcp-server")
	if err != nil {
		return zpTokenFailure(err.Error())
	}

	expiresAt := time.Now().UTC().Add(time.Duration(expiresInDays) * 24 * time.Hour)
	sum := sha256.Sum256([]byte(jwtToken))
	tokenHash := hex.EncodeToString(sum[:])

	var metadataValue any = map[string]any{}
	if metadata != nil {
		metadataValue = metadata
	}
	var scopesValue any = scopes
	if scopes == nil {
		scopesValue = nil
	}
	tokenData := map[string]any{
		"id":             tokenID,
		"user_id":        userID,
		"name":           name,
		"token_hash":     tokenHash,
		"scopes":         scopesValue,
		"expires_at":     expiresAt,
		"rate_limit":     effectiveRateLimit,
		"token_metadata": metadataValue,
	}

	createdToken, err := repository.CreateToken(ctx, tokenData)
	if err != nil {
		return zpTokenFailure(err.Error())
	}
	if createdToken != nil {
		tokenMap := entities.NewOrderedMap[any]()
		tokenMap.Set("id", zpTokenField(createdToken, "id"))
		tokenMap.Set("name", zpTokenField(createdToken, "name"))
		tokenMap.Set("token", jwtToken)
		tokenMap.Set("scopes", zpTokenScopes(zpTokenField(createdToken, "scopes")))
		tokenMap.Set("created_at", zpTokenTimeISO(zpTokenField(createdToken, "created_at")))
		tokenMap.Set("expires_at", zpTokenTimeISO(zpTokenField(createdToken, "expires_at")))
		tokenMap.Set("rate_limit", zpTokenField(createdToken, "rate_limit"))
		tokenMap.Set("is_active", zpTokenField(createdToken, "is_active"))
		return zpTokenSuccess("token", tokenMap)
	}
	return zpTokenFailure("Failed to create token")
}

// ListUserTokens mirrors list_user_tokens.
func (f *TokenApplicationFacade) ListUserTokens(ctx context.Context, userID string, session any, skip, limit int) *entities.OrderedMap[any] {
	repository := f.zpTokenGetRepository(session)
	if repository == nil {
		return zpTokenListFailure("'NoneType' object has no attribute 'get_user_tokens'")
	}

	tokens, err := repository.GetUserTokens(ctx, userID, skip, limit)
	if err != nil {
		return zpTokenListFailure(err.Error())
	}
	total, err := repository.CountUserTokens(ctx, userID)
	if err != nil {
		return zpTokenListFailure(err.Error())
	}

	tokenList := []any{}
	for _, token := range tokens {
		entry := entities.NewOrderedMap[any]()
		entry.Set("id", zpTokenField(token, "id"))
		entry.Set("name", zpTokenField(token, "name"))
		entry.Set("scopes", zpTokenScopes(zpTokenField(token, "scopes")))
		entry.Set("created_at", zpTokenTimeISO(zpTokenField(token, "created_at")))
		entry.Set("expires_at", zpTokenTimeISO(zpTokenField(token, "expires_at")))
		entry.Set("last_used_at", zpTokenTimeISO(zpTokenField(token, "last_used_at")))
		entry.Set("usage_count", zpTokenField(token, "usage_count"))
		entry.Set("rate_limit", zpTokenField(token, "rate_limit"))
		entry.Set("usage_stats", zpTokenStatsValue(zpTokenField(token, "usage_stats")))
		entry.Set("is_active", zpTokenField(token, "is_active"))
		tokenList = append(tokenList, entry)
	}

	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("tokens", tokenList)
	m.Set("total", total)
	return m
}

// zpTokenListFailure builds {"success": false, "error": msg, "tokens": [], "total": 0}.
func zpTokenListFailure(msg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", msg)
	m.Set("tokens", []any{})
	m.Set("total", 0)
	return m
}

// GetTokenDetails mirrors get_token_details.
func (f *TokenApplicationFacade) GetTokenDetails(ctx context.Context, tokenID, userID string, session any) *entities.OrderedMap[any] {
	repository := f.zpTokenGetRepository(session)
	if repository == nil {
		return zpTokenFailure("'NoneType' object has no attribute 'get_token'")
	}
	token, err := repository.GetToken(ctx, tokenID, userID)
	if err != nil {
		return zpTokenFailure(err.Error())
	}
	if token == nil {
		return zpTokenFailure("Token not found")
	}

	tokenData := entities.NewOrderedMap[any]()
	tokenData.Set("id", zpTokenField(token, "id"))
	tokenData.Set("name", zpTokenField(token, "name"))
	tokenData.Set("scopes", zpTokenScopes(zpTokenField(token, "scopes")))
	tokenData.Set("created_at", zpTokenTimeISO(zpTokenField(token, "created_at")))
	tokenData.Set("expires_at", zpTokenTimeISO(zpTokenField(token, "expires_at")))
	tokenData.Set("last_used_at", zpTokenTimeISO(zpTokenField(token, "last_used_at")))
	tokenData.Set("usage_count", zpTokenField(token, "usage_count"))
	tokenData.Set("rate_limit", zpTokenField(token, "rate_limit"))
	tokenData.Set("usage_stats", zpTokenStatsValue(zpTokenField(token, "usage_stats")))
	tokenData.Set("is_active", zpTokenField(token, "is_active"))
	if _, ok := zpTokenHasField(token, "token_metadata"); ok {
		tokenData.Set("metadata", zpTokenStatsValue(zpTokenField(token, "token_metadata")))
	} else {
		tokenData.Set("metadata", entities.NewOrderedMap[any]())
	}
	return zpTokenSuccess("token_data", tokenData)
}

// RevokeToken mirrors revoke_token.
func (f *TokenApplicationFacade) RevokeToken(ctx context.Context, tokenID, userID string, session any) *entities.OrderedMap[any] {
	repository := f.zpTokenGetRepository(session)
	if repository == nil {
		return zpTokenFailure("'NoneType' object has no attribute 'revoke_token'")
	}
	success, err := repository.RevokeToken(ctx, tokenID, userID)
	if err != nil {
		return zpTokenFailure(err.Error())
	}
	if success {
		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("message", "Token revoked successfully")
		return m
	}
	return zpTokenFailure("Token not found or could not be revoked")
}

// DeleteToken mirrors delete_token.
func (f *TokenApplicationFacade) DeleteToken(ctx context.Context, tokenID, userID string, session any) *entities.OrderedMap[any] {
	repository := f.zpTokenGetRepository(session)
	if repository == nil {
		return zpTokenFailure("'NoneType' object has no attribute 'delete_token'")
	}
	success, err := repository.DeleteToken(ctx, tokenID, userID)
	if err != nil {
		return zpTokenFailure(err.Error())
	}
	if success {
		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("message", "Token deleted successfully")
		return m
	}
	return zpTokenFailure("Token not found or could not be deleted")
}

// ReactivateToken mirrors reactivate_token.
func (f *TokenApplicationFacade) ReactivateToken(ctx context.Context, tokenID, userID string, session any) *entities.OrderedMap[any] {
	repository := f.zpTokenGetRepository(session)
	if repository == nil {
		return zpTokenFailure("'NoneType' object has no attribute 'reactivate_token'")
	}
	success, err := repository.ReactivateToken(ctx, tokenID, userID)
	if err != nil {
		return zpTokenFailure(err.Error())
	}
	if success {
		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("message", "Token reactivated successfully")
		return m
	}
	return zpTokenFailure("Token not found or could not be reactivated")
}

// RotateToken mirrors rotate_token.
func (f *TokenApplicationFacade) RotateToken(ctx context.Context, tokenID, userID string, session any) *entities.OrderedMap[any] {
	repository := f.zpTokenGetRepository(session)
	if repository == nil {
		return zpTokenFailure("'NoneType' object has no attribute 'get_token'")
	}
	oldToken, err := repository.GetToken(ctx, tokenID, userID)
	if err != nil {
		return zpTokenFailure(err.Error())
	}
	if oldToken == nil {
		return zpTokenFailure("Token not found")
	}

	if _, err := repository.RevokeToken(ctx, tokenID, userID); err != nil {
		return zpTokenFailure(err.Error())
	}

	oldName := value_objects.PyStr(zpTokenField(oldToken, "name"))
	oldScopes := zpTokenStringSlice(zpTokenField(oldToken, "scopes"))
	oldRateLimit := zpTokenIntPtr(zpTokenField(oldToken, "rate_limit"))
	oldID := value_objects.PyStr(zpTokenField(oldToken, "id"))

	rotateMetadata := entities.NewOrderedMap[any]()
	rotateMetadata.Set("rotated_from", oldID)

	newResult := f.CreateAPIToken(ctx, userID, oldName+" (rotated)", oldScopes, 30, oldRateLimit, rotateMetadata, session)
	if value_objects.PyTruthy(zpUCFGet(newResult, "success")) {
		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("token_data", zpUCFGet(newResult, "token"))
		return m
	}
	return newResult
}

// ValidateToken mirrors validate_token. The Python body calls JWTService.decode_token,
// which does not exist, so the AttributeError is returned instead of any branch result.
func (f *TokenApplicationFacade) ValidateToken(ctx context.Context, token string, session any) *entities.OrderedMap[any] {
	return zpTokenFailure("'JWTService' object has no attribute 'decode_token'")
}

// zpTokenHex is secrets.token_hex(n_bytes).
func zpTokenHex(nBytes int) string {
	b := make([]byte, nBytes)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	return hex.EncodeToString(b)
}

// zpTokenHasField reports whether the reflected object has the named field.
func zpTokenHasField(obj any, name string) (any, bool) {
	value := reflect.ValueOf(obj)
	for value.Kind() == reflect.Ptr || value.Kind() == reflect.Interface {
		if value.IsNil() {
			return nil, false
		}
		value = value.Elem()
	}
	if value.Kind() != reflect.Struct {
		return nil, false
	}
	field := value.FieldByName(name)
	if !field.IsValid() {
		return nil, false
	}
	return field.Interface(), true
}

// zpTokenField is getattr(obj, name, None): nil when the object or field is absent.
func zpTokenField(obj any, name string) any {
	v, ok := zpTokenHasField(obj, name)
	if !ok {
		return nil
	}
	return v
}

// zpTokenTimeISO is `x.isoformat() if x else None`.
func zpTokenTimeISO(v any) any {
	switch t := v.(type) {
	case time.Time:
		if t.IsZero() {
			return nil
		}
		return value_objects.IsoFormat(t)
	case *time.Time:
		if t == nil || t.IsZero() {
			return nil
		}
		return value_objects.IsoFormat(*t)
	}
	return nil
}

// zpTokenScopes returns the Python list value of a scopes column (json.RawMessage) or the
// value itself.
func zpTokenScopes(v any) any {
	if raw, ok := v.(json.RawMessage); ok {
		if len(raw) == 0 {
			return nil
		}
		decoded, err := entities.DecodeJSON(raw)
		if err != nil {
			return nil
		}
		return decoded
	}
	return v
}

// zpTokenStringSlice converts a reflected scopes value to []string (best effort).
func zpTokenStringSlice(v any) []string {
	decoded := zpTokenScopes(v)
	switch s := decoded.(type) {
	case []string:
		return s
	case []any:
		out := []string{}
		for _, item := range s {
			out = append(out, value_objects.PyStr(item))
		}
		return out
	case nil:
		return nil
	}
	return nil
}

// zpTokenIntPtr converts a reflected rate_limit value to *int.
func zpTokenIntPtr(v any) *int {
	switch n := v.(type) {
	case int:
		return &n
	case int64:
		i := int(n)
		return &i
	case float64:
		i := int(n)
		return &i
	}
	return nil
}

// zpTokenStatsValue is `value or {}` for a json.RawMessage metadata/stats column.
func zpTokenStatsValue(v any) any {
	raw, ok := v.(json.RawMessage)
	if !ok {
		if v == nil {
			return entities.NewOrderedMap[any]()
		}
		return v
	}
	if len(raw) == 0 {
		return entities.NewOrderedMap[any]()
	}
	decoded, err := entities.DecodeJSON(raw)
	if err != nil || !value_objects.PyTruthy(decoded) {
		return entities.NewOrderedMap[any]()
	}
	return decoded
}
