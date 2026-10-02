package middleware

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"net/http"
	"os"
	"strings"
	"time"

	auth "agenthub/fastmcp/auth"
	domainservices "agenthub/fastmcp/auth/domain/services"
	authinfra "agenthub/fastmcp/auth/infrastructure"
	entities "agenthub/fastmcp/task_management/domain/entities"
	valueobjects "agenthub/fastmcp/task_management/domain/value_objects"
)

// AuthErrorResponse is the Go shape of the Starlette JSONResponse returned by
// DualAuthMiddleware._create_auth_error_response.
type AuthErrorResponse struct {
	StatusCode int
	Content    *entities.OrderedMap[any]
	Headers    *entities.OrderedMap[any]
}

// DualAuthMiddleware ports auth/middleware/dual_auth_middleware.py:
// DualAuthMiddleware.
//
// The Starlette BaseHTTPMiddleware dispatch/http-mounting surface is not
// ported: there is no ASGI chain in Go. The request classification, token
// extraction, fallback validation chain and error payloads are kept as plain
// methods over *http.Request.
type DualAuthMiddleware struct {
	SupabaseAuth   *authinfra.SupabaseAuthService
	TokenValidator *auth.TokenValidator
}

// NewDualAuthMiddleware mirrors DualAuthMiddleware.__init__.
func NewDualAuthMiddleware() *DualAuthMiddleware {
	authProvider := valueobjects.PyLower(os.Getenv("AUTH_PROVIDER"))
	if authProvider == "" {
		authProvider = "supabase"
	}

	var supabaseAuth *authinfra.SupabaseAuthService
	if authProvider == "supabase" {
		s, err := authinfra.NewSupabaseAuthService()
		if err == nil {
			supabaseAuth = s
		}
	}

	return &DualAuthMiddleware{
		SupabaseAuth:   supabaseAuth,
		TokenValidator: auth.NewTokenValidator(nil),
	}
}

// DetectRequestType ports _detect_request_type.
func (m *DualAuthMiddleware) DetectRequestType(r *http.Request) string {
	path := r.URL.Path
	contentType := valueobjects.PyLower(r.Header.Get("content-type"))
	userAgent := valueobjects.PyLower(r.Header.Get("user-agent"))

	if strings.HasPrefix(path, "/mcp") {
		return "mcp"
	}
	if _, ok := r.Header[http.CanonicalHeaderKey("mcp-protocol-version")]; ok {
		return "mcp"
	}
	if strings.Contains(contentType, "application/json") && strings.Contains(r.Header.Get("accept"), "jsonrpc") {
		return "mcp"
	}
	if strings.HasPrefix(path, "/api/v2/") {
		return "frontend"
	}
	for _, indicator := range []string{"mozilla", "chrome", "safari", "firefox", "edge"} {
		if strings.Contains(userAgent, indicator) {
			return "frontend"
		}
	}
	if strings.HasPrefix(path, "/api/") {
		return "frontend"
	}
	return "unknown"
}

// ShouldSkipAuth ports _should_skip_auth.
func (m *DualAuthMiddleware) ShouldSkipAuth(r *http.Request) bool {
	skipPaths := []string{"/health", "/ai_docs", "/redoc", "/openapi.json", "/favicon.ico", "/static/"}
	path := r.URL.Path
	for _, skipPath := range skipPaths {
		if strings.HasPrefix(path, skipPath) {
			return true
		}
	}
	return false
}

// ExtractToken ports _extract_token.
func (m *DualAuthMiddleware) ExtractToken(r *http.Request) *string {
	authHeader := r.Header.Get("authorization")
	if strings.HasPrefix(authHeader, "Bearer ") {
		v := strings.TrimSpace(authHeader[7:])
		return &v
	}
	if strings.HasPrefix(authHeader, "Token ") {
		v := strings.TrimSpace(authHeader[6:])
		return &v
	}

	if token := r.Header.Get("x-mcp-token"); token != "" {
		return &token
	}
	if token := r.Header.Get("mcp-token"); token != "" {
		return &token
	}

	if cookie, err := r.Cookie("access_token"); err == nil {
		return &cookie.Value
	}

	if values, ok := r.URL.Query()["token"]; ok && len(values) > 0 {
		v := values[0]
		return &v
	}
	return nil
}

// CreateAuthErrorResponse ports _create_auth_error_response.
func (m *DualAuthMiddleware) CreateAuthErrorResponse(requestType, errorMessage string) *AuthErrorResponse {
	if requestType == "mcp" {
		data := entities.NewOrderedMap[any]()
		data.Set("detail", errorMessage)
		data.Set("auth_type", "mcp_token_required")

		errObj := entities.NewOrderedMap[any]()
		errObj.Set("code", -32001)
		errObj.Set("message", "Authentication failed")
		errObj.Set("data", data)

		content := entities.NewOrderedMap[any]()
		content.Set("jsonrpc", "2.0")
		content.Set("error", errObj)
		content.Set("id", nil)

		headers := entities.NewOrderedMap[any]()
		headers.Set("Content-Type", "application/json")
		return &AuthErrorResponse{StatusCode: 401, Content: content, Headers: headers}
	}

	content := entities.NewOrderedMap[any]()
	content.Set("detail", errorMessage)
	content.Set("auth_type", "bearer_or_cookie_required")

	headers := entities.NewOrderedMap[any]()
	headers.Set("WWW-Authenticate", "Bearer")
	return &AuthErrorResponse{StatusCode: 401, Content: content, Headers: headers}
}

// AuthenticateRequest ports _authenticate_request. The returned error is the
// Python TokenValidationError/RateLimitError propagation used by dispatch;
// with all methods failing it returns (nil, nil).
func (m *DualAuthMiddleware) AuthenticateRequest(ctx context.Context, r *http.Request, requestType string) (*entities.OrderedMap[any], error) {
	tokenPtr := m.ExtractToken(r)
	if tokenPtr == nil {
		return nil, nil
	}
	token := *tokenPtr

	if strings.HasPrefix(token, "eyJ") {
		unverified, decodeErr := dualUnverifiedClaims(token)
		if decodeErr == nil {
			authProvider := valueobjects.PyLower(os.Getenv("AUTH_PROVIDER"))
			if authProvider == "" {
				authProvider = "supabase"
			}
			issuer, _ := unverified["iss"].(string)
			keycloakURL := os.Getenv("KEYCLOAK_URL")

			if authProvider == "keycloak" && keycloakURL != "" && strings.HasPrefix(issuer, keycloakURL) {
				if user, err := auth.ValidateKeycloakToken(ctx, token); err == nil {
					userData := entities.NewOrderedMap[any]()
					userData.Set("id", *user.ID)
					userData.Set("email", user.Email)
					userData.Set("username", user.Username)

					result := entities.NewOrderedMap[any]()
					result.Set("user_id", *user.ID)
					result.Set("email", user.Email)
					result.Set("auth_method", "keycloak")
					result.Set("user_data", userData)
					return result, nil
				}
			} else if valueobjects.PyTruthy(unverified["token_id"]) || unverified["type"] == "api_token" {
				if authResult := m.validateAPIToken(token); authResult != nil {
					return authResult, nil
				}
			}

			if authResult := m.validateLocalJWT(token); authResult != nil {
				return authResult, nil
			}
		}
	}

	if m.SupabaseAuth != nil {
		result := m.SupabaseAuth.VerifyToken(ctx, token)
		if result.Success && result.User != nil {
			userIDAny, _ := result.User.Get("id")
			if valueobjects.PyTruthy(userIDAny) {
				out := entities.NewOrderedMap[any]()
				out.Set("user_id", userIDAny)
				out.Set("email", payloadGetMap(result.User, "email"))
				out.Set("auth_method", "supabase")
				out.Set("user_data", result.User)
				return out, nil
			}
		}
	}

	clientInfo := entities.NewOrderedMap[any]()
	clientInfo.Set("user_agent", r.Header.Get("user-agent"))
	clientInfo.Set("path", r.URL.Path)
	clientInfo.Set("method", r.Method)

	tokenInfo, err := m.TokenValidator.ValidateToken(ctx, token, clientInfo)
	if err != nil {
		return nil, err
	}
	if tokenInfo == nil {
		return nil, nil
	}

	out := entities.NewOrderedMap[any]()
	out.Set("user_id", tokenInfo.UserID)
	out.Set("auth_method", "mcp_token")
	out.Set("token_info", tokenInfo)
	out.Set("created_at", isoOrNil(tokenInfo.CreatedAt))
	out.Set("expires_at", isoOrNilPtr(tokenInfo.ExpiresAt))
	return out, nil
}

// validateAPIToken ports _validate_api_token. The Python background
// asyncio.create_task that opens SessionLocal/TokenRepository to bump
// usage_count is not ported: the application layer must not use the database
// package directly.
func (m *DualAuthMiddleware) validateAPIToken(token string) *entities.OrderedMap[any] {
	jwtSecret := os.Getenv("JWT_SECRET_KEY")
	if jwtSecret == "" {
		return nil
	}
	jwtService, err := domainservices.NewJWTService(jwtSecret, domainservices.DefaultIssuer)
	if err != nil {
		return nil
	}
	payload := jwtService.VerifyToken(token, "api_token", "")
	if payload == nil {
		return nil
	}

	out := entities.NewOrderedMap[any]()
	out.Set("user_id", firstPayloadString(payload, "user_id", "sub"))
	out.Set("auth_method", "api_token")
	out.Set("jwt_secret_used", "JWT_SECRET_KEY")
	out.Set("token_id", firstPayloadString(payload, "token_id", "jti"))
	out.Set("scopes", payloadGet(payload, "scopes", []any{}))
	out.Set("type", "api_token")
	out.Set("email", payload["email"])
	out.Set("roles", payloadGet(payload, "roles", []any{}))
	return out
}

// validateLocalJWT ports _validate_local_jwt.
func (m *DualAuthMiddleware) validateLocalJWT(token string) *entities.OrderedMap[any] {
	jwtSecret := os.Getenv("JWT_SECRET_KEY")
	if jwtSecret == "" {
		jwtSecret = "default-secret-key-change-in-production"
	}
	supabaseJWTSecret := os.Getenv("SUPABASE_JWT_SECRET")

	type secretPair struct{ name, value string }
	var secretsToTry []secretPair
	if supabaseJWTSecret != "" {
		secretsToTry = append(secretsToTry, secretPair{"SUPABASE_JWT_SECRET", supabaseJWTSecret})
	}
	if jwtSecret != "" && jwtSecret != "default-secret-key-change-in-production" {
		secretsToTry = append(secretsToTry, secretPair{"JWT_SECRET_KEY", jwtSecret})
	}

	for _, sp := range secretsToTry {
		jwtService, err := domainservices.NewJWTService(sp.value, domainservices.DefaultIssuer)
		if err != nil {
			continue
		}

		if sp.name == "SUPABASE_JWT_SECRET" {
			if payload := jwtService.VerifyAccessToken(token, "authenticated"); payload != nil {
				out := entities.NewOrderedMap[any]()
				out.Set("user_id", firstPayloadString(payload, "user_id", "sub"))
				out.Set("auth_method", "local_jwt")
				out.Set("jwt_secret_used", sp.name)
				out.Set("email", payload["email"])
				out.Set("roles", payloadGet(payload, "roles", []any{}))
				return out
			}
		}

		for _, tokenType := range []string{"api_token", "access"} {
			if payload := jwtService.VerifyToken(token, tokenType, ""); payload != nil {
				out := entities.NewOrderedMap[any]()
				out.Set("user_id", firstPayloadString(payload, "user_id", "sub"))
				out.Set("auth_method", "local_jwt")
				out.Set("jwt_secret_used", sp.name)
				out.Set("token_id", firstPayloadString(payload, "token_id", "jti"))
				out.Set("scopes", payloadGet(payload, "scopes", []any{}))
				out.Set("type", payloadGet(payload, "type", "api_token"))
				out.Set("email", payload["email"])
				out.Set("roles", payloadGet(payload, "roles", []any{}))
				return out
			}
		}
	}
	return nil
}

// dualUnverifiedClaims mirrors pyjwt.decode(options={"verify_signature": False}).
func dualUnverifiedClaims(token string) (map[string]any, error) {
	parts := strings.Split(token, ".")
	if len(parts) < 2 {
		return nil, &valueobjects.ValueError{Msg: "Not enough segments"}
	}
	payloadBytes, err := base64.RawURLEncoding.DecodeString(strings.TrimRight(parts[1], "="))
	if err != nil {
		return nil, err
	}
	var payload map[string]any
	if err := json.Unmarshal(payloadBytes, &payload); err != nil {
		return nil, err
	}
	return payload, nil
}

func isoOrNil(t time.Time) any {
	if t.IsZero() {
		return nil
	}
	return valueobjects.IsoFormat(t)
}

func isoOrNilPtr(t *time.Time) any {
	if t == nil {
		return nil
	}
	return valueobjects.IsoFormat(*t)
}

func payloadGet(payload map[string]any, key string, def any) any {
	if v, ok := payload[key]; ok {
		return v
	}
	return def
}

func payloadGetMap(m *entities.OrderedMap[any], key string) any {
	v, _ := m.Get(key)
	return v
}

func firstPayloadString(payload map[string]any, keys ...string) any {
	for _, key := range keys {
		if v, ok := payload[key]; ok && valueobjects.PyTruthy(v) {
			return v
		}
	}
	return nil
}
