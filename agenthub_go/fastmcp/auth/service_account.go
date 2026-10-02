package auth

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"

	taskentities "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ServiceAccountConfig is the service account configuration.
type ServiceAccountConfig struct {
	KeycloakURL  string
	Realm        string
	ClientID     string
	ClientSecret string
	Scopes       []string
}

// ServiceToken is the service account token data.
type ServiceToken struct {
	AccessToken  string
	RefreshToken *string
	TokenType    string
	ExpiresIn    int
	Scope        string
	CreatedAt    time.Time
}

// NewServiceToken mirrors __post_init__ (a zero created_at becomes now).
func NewServiceToken(accessToken string, refreshToken *string, tokenType string, expiresIn int, scope string, createdAt time.Time) *ServiceToken {
	if createdAt.IsZero() {
		createdAt = time.Now().UTC()
	}
	return &ServiceToken{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		TokenType:    tokenType,
		ExpiresIn:    expiresIn,
		Scope:        scope,
		CreatedAt:    createdAt,
	}
}

// ExpiresAt calculates the token expiration time.
func (t *ServiceToken) ExpiresAt() time.Time {
	return t.CreatedAt.Add(time.Duration(t.ExpiresIn) * time.Second)
}

// IsExpired checks if the token has expired (with a 30 second buffer).
func (t *ServiceToken) IsExpired() bool {
	const bufferSeconds = 30
	expiryWithBuffer := t.ExpiresAt().Add(-time.Duration(bufferSeconds) * time.Second)
	return !time.Now().UTC().Before(expiryWithBuffer)
}

// SecondsUntilExpiry gets seconds until the token expires.
func (t *ServiceToken) SecondsUntilExpiry() int {
	delta := t.ExpiresAt().Sub(time.Now().UTC())
	seconds := int(delta.Seconds())
	if seconds < 0 {
		return 0
	}
	return seconds
}

// ServiceAccountAuth is the Keycloak service account authentication for MCP.
type ServiceAccountAuth struct {
	Config *ServiceAccountConfig

	RealmURL         string
	TokenEndpoint    string
	UserinfoEndpoint string
	JWKSEndpoint     string

	Client *http.Client

	tokenMu      sync.Mutex
	currentToken *ServiceToken

	refreshMu      sync.Mutex
	refreshCancel  context.CancelFunc
	refreshRunning bool

	jwksClient *KeycloakJWKSClient

	lastRequestTime    float64
	minRequestInterval float64
}

// loadServiceAccountConfigFromEnv loads the configuration from environment variables.
func loadServiceAccountConfigFromEnv() *ServiceAccountConfig {
	return &ServiceAccountConfig{
		KeycloakURL:  os.Getenv("KEYCLOAK_URL"),
		Realm:        envOr("KEYCLOAK_REALM", "agenthub"),
		ClientID:     envOr("KEYCLOAK_SERVICE_CLIENT_ID", "mcp-service-account"),
		ClientSecret: os.Getenv("KEYCLOAK_SERVICE_CLIENT_SECRET"),
		Scopes:       value_objects.PySplit(envOr("KEYCLOAK_SERVICE_SCOPES", "openid profile email mcp:read mcp:write")),
	}
}

// NewServiceAccountAuth initializes service account authentication.
func NewServiceAccountAuth(config *ServiceAccountConfig) (*ServiceAccountAuth, error) {
	cfg := config
	if cfg == nil {
		cfg = loadServiceAccountConfigFromEnv()
	}

	a := &ServiceAccountAuth{
		Config:             cfg,
		Client:             &http.Client{Timeout: 30 * time.Second},
		minRequestInterval: 1,
	}

	if err := a.validateConfig(); err != nil {
		return nil, err
	}

	a.RealmURL = a.Config.KeycloakURL + "/realms/" + a.Config.Realm
	a.TokenEndpoint = a.RealmURL + "/protocol/openid-connect/token"
	a.UserinfoEndpoint = a.RealmURL + "/protocol/openid-connect/userinfo"
	a.JWKSEndpoint = a.RealmURL + "/protocol/openid-connect/certs"
	return a, nil
}

// validateConfig validates the service account configuration.
func (a *ServiceAccountAuth) validateConfig() error {
	requiredFields := []struct {
		field string
		value string
	}{
		{"keycloak_url", a.Config.KeycloakURL},
		{"realm", a.Config.Realm},
		{"client_id", a.Config.ClientID},
		{"client_secret", a.Config.ClientSecret},
	}
	for _, r := range requiredFields {
		if r.value == "" {
			upper := strings.ToUpper(r.field)
			return &value_objects.ValueError{Msg: fmt.Sprintf(
				"Missing required service account configuration: %s. Please set KEYCLOAK_%s environment variable.",
				upper, upper)}
		}
	}
	a.Config.KeycloakURL = strings.TrimRight(a.Config.KeycloakURL, "/")
	return nil
}

// JWKSClient returns the lazy JWKS client for token validation.
func (a *ServiceAccountAuth) JWKSClient() *KeycloakJWKSClient {
	if a.jwksClient == nil {
		a.jwksClient = NewKeycloakJWKSClient(a.JWKSEndpoint, 3600*time.Second, nil)
	}
	return a.jwksClient
}

// rateLimit is simple rate limiting to prevent overwhelming Keycloak.
func (a *ServiceAccountAuth) rateLimit(ctx context.Context) {
	now := float64(time.Now().UnixNano()) / 1e9
	elapsed := now - a.lastRequestTime

	if elapsed < a.minRequestInterval {
		sleepTime := a.minRequestInterval - elapsed
		select {
		case <-ctx.Done():
		case <-time.After(time.Duration(sleepTime * float64(time.Second))):
		}
	}
	a.lastRequestTime = float64(time.Now().UnixNano()) / 1e9
}

// Authenticate authenticates the service account and gets an access token.
func (a *ServiceAccountAuth) Authenticate(ctx context.Context, forceRefresh bool) *ServiceToken {
	a.tokenMu.Lock()
	if !forceRefresh && a.currentToken != nil && !a.currentToken.IsExpired() {
		token := a.currentToken
		a.tokenMu.Unlock()
		return token
	}
	a.tokenMu.Unlock()

	a.rateLimit(ctx)

	data := url.Values{}
	data.Set("grant_type", "client_credentials")
	data.Set("client_id", a.Config.ClientID)
	data.Set("client_secret", a.Config.ClientSecret)
	data.Set("scope", strings.Join(a.Config.Scopes, " "))

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, a.TokenEndpoint, strings.NewReader(data.Encode()))
	if err != nil {
		return nil
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := a.Client.Do(req)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()

	if resp.StatusCode == 200 {
		var tokenData map[string]any
		if err := json.NewDecoder(resp.Body).Decode(&tokenData); err != nil {
			return nil
		}
		token := NewServiceToken(
			optMapString(tokenData, "access_token"),
			optMapStringPtr(tokenData, "refresh_token"),
			optMapStringDefault(tokenData, "token_type", "Bearer"),
			optMapIntDefault(tokenData, "expires_in", 300),
			optMapStringDefault(tokenData, "scope", ""),
			time.Now().UTC(),
		)
		a.tokenMu.Lock()
		a.currentToken = token
		a.tokenMu.Unlock()
		a.startTokenRefreshTask()
		return token
	}

	var errorData map[string]any
	_ = json.NewDecoder(resp.Body).Decode(&errorData)
	return nil
}

// startTokenRefreshTask starts the background token refresh loop.
func (a *ServiceAccountAuth) startTokenRefreshTask() {
	a.refreshMu.Lock()
	defer a.refreshMu.Unlock()
	if a.refreshRunning {
		return
	}
	ctx, cancel := context.WithCancel(context.Background())
	a.refreshCancel = cancel
	a.refreshRunning = true
	go a.tokenRefreshLoop(ctx)
}

// tokenRefreshLoop refreshes tokens before expiry.
func (a *ServiceAccountAuth) tokenRefreshLoop(ctx context.Context) {
	defer func() {
		a.refreshMu.Lock()
		a.refreshRunning = false
		a.refreshMu.Unlock()
	}()

	for {
		a.tokenMu.Lock()
		token := a.currentToken
		a.tokenMu.Unlock()
		if token == nil {
			return
		}

		if token.IsExpired() {
			a.Authenticate(ctx, true)
		}

		a.tokenMu.Lock()
		token = a.currentToken
		a.tokenMu.Unlock()
		if token == nil {
			return
		}

		sleepSeconds := token.SecondsUntilExpiry() - 30
		if sleepSeconds < 30 {
			sleepSeconds = 30
		}

		select {
		case <-ctx.Done():
			return
		case <-time.After(time.Duration(sleepSeconds) * time.Second):
		}
	}
}

// GetValidToken gets a valid access token, refreshing if necessary.
func (a *ServiceAccountAuth) GetValidToken(ctx context.Context) *string {
	token := a.Authenticate(ctx, false)
	if token == nil {
		return nil
	}
	return &token.AccessToken
}

// ValidateToken validates a service account token.
func (a *ServiceAccountAuth) ValidateToken(ctx context.Context, token string) map[string]any {
	signingKey, err := a.JWKSClient().GetSigningKeyFromJWT(token)
	if err != nil {
		return nil
	}

	payload, err := jwtDecodeRS256Claims(token, signingKey, jwtDecodeOptions{
		VerifyAud: true,
		Audience:  a.Config.ClientID,
		VerifyIss: true,
		Issuer:    a.RealmURL,
		VerifyExp: true,
		VerifyIat: true,
		VerifyNbf: true,
	})
	if err != nil {
		return nil
	}

	if typ, _ := payload["typ"].(string); typ != "Bearer" {
		return nil
	}
	if azp, _ := payload["azp"].(string); azp != a.Config.ClientID {
		return nil
	}
	return payload
}

// GetServiceInfo gets service account information from Keycloak.
func (a *ServiceAccountAuth) GetServiceInfo(ctx context.Context) map[string]any {
	token := a.GetValidToken(ctx)
	if token == nil {
		return nil
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, a.UserinfoEndpoint, nil)
	if err != nil {
		return nil
	}
	req.Header.Set("Authorization", "Bearer "+*token)
	resp, err := a.Client.Do(req)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()
	if resp.StatusCode == 200 {
		var result map[string]any
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			return nil
		}
		return result
	}
	return nil
}

// GetAuthHeaders gets authorization headers for authenticated requests.
func (a *ServiceAccountAuth) GetAuthHeaders() map[string]string {
	a.tokenMu.Lock()
	token := a.currentToken
	a.tokenMu.Unlock()
	if token != nil && !token.IsExpired() {
		return map[string]string{"Authorization": "Bearer " + token.AccessToken}
	}
	return map[string]string{}
}

// HealthCheck checks service account authentication health.
func (a *ServiceAccountAuth) HealthCheck(ctx context.Context) *taskentities.OrderedMap[any] {
	health := taskentities.NewOrderedMap[any]()
	health.Set("service_account_configured", a.Config.ClientID != "" && a.Config.ClientSecret != "")
	a.tokenMu.Lock()
	token := a.currentToken
	a.tokenMu.Unlock()
	health.Set("token_available", token != nil)
	health.Set("token_valid", false)
	health.Set("token_expires_in", 0)
	health.Set("keycloak_reachable", false)
	health.Set("last_auth_success", nil)

	configuration := taskentities.NewOrderedMap[any]()
	configuration.Set("keycloak_url", a.Config.KeycloakURL)
	configuration.Set("realm", a.Config.Realm)
	configuration.Set("client_id", a.Config.ClientID)
	configuration.Set("scopes", a.Config.Scopes)
	health.Set("configuration", configuration)

	if token != nil {
		health.Set("token_valid", !token.IsExpired())
		health.Set("token_expires_in", token.SecondsUntilExpiry())
		health.Set("last_auth_success", value_objects.IsoFormat(token.CreatedAt))
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, a.RealmURL+"/.well-known/openid-configuration", nil)
	if err != nil {
		health.Set("keycloak_error", err.Error())
		return health
	}
	resp, err := a.Client.Do(req)
	if err != nil {
		health.Set("keycloak_error", err.Error())
		return health
	}
	defer resp.Body.Close()
	health.Set("keycloak_reachable", resp.StatusCode == 200)
	return health
}

// Close cleans up resources.
func (a *ServiceAccountAuth) Close() {
	a.refreshMu.Lock()
	if a.refreshCancel != nil {
		a.refreshCancel()
	}
	a.refreshMu.Unlock()
}

// Singleton instance for easy access.
var serviceAuthInstance *ServiceAccountAuth

// GetServiceAccountAuth gets or creates the singleton service account auth instance.
func GetServiceAccountAuth() (*ServiceAccountAuth, error) {
	if serviceAuthInstance == nil {
		auth, err := NewServiceAccountAuth(nil)
		if err != nil {
			return nil, err
		}
		serviceAuthInstance = auth
	}
	return serviceAuthInstance, nil
}

// AuthenticateServiceRequest authenticates a service request using a service
// account token.
func AuthenticateServiceRequest(ctx context.Context, authorizationHeader *string) (*taskentities.OrderedMap[any], error) {
	if authorizationHeader == nil || *authorizationHeader == "" {
		return nil, nil
	}

	parts := value_objects.PySplit(*authorizationHeader)
	if len(parts) != 2 || value_objects.PyLower(parts[0]) != "bearer" {
		return nil, nil
	}
	token := parts[1]

	auth, err := GetServiceAccountAuth()
	if err != nil {
		return nil, err
	}
	payload := auth.ValidateToken(ctx, token)
	if payload == nil {
		return nil, nil
	}

	scope, _ := payload["scope"].(string)
	result := taskentities.NewOrderedMap[any]()
	result.Set("service_account", true)
	result.Set("client_id", payload["azp"])
	result.Set("subject", payload["sub"])
	result.Set("scopes", value_objects.PySplit(scope))
	result.Set("authenticated", true)
	result.Set("auth_provider", "keycloak_service_account")
	result.Set("token_exp", payload["exp"])
	result.Set("permissions", []string{"mcp:*"})
	return result, nil
}

// optMapIntDefault reads an int with a Python dict.get default.
func optMapIntDefault(m map[string]any, key string, def int) int {
	if v := optMapIntPtr(m, key); v != nil {
		return *v
	}
	return def
}
