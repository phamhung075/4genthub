package auth

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"crypto/tls"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"os"
	"time"

	taskentities "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TokenInfo is the pydantic BaseModel token information from Supabase.
type TokenInfo struct {
	TokenHash  string
	UserID     string
	CreatedAt  time.Time
	ExpiresAt  *time.Time
	IsActive   bool
	UsageCount int
	LastUsed   *time.Time
}

// SupabaseTokenClient is the client for Supabase token operations.
type SupabaseTokenClient struct {
	SupabaseURL        *string
	SupabaseAnonKey    *string
	SupabaseServiceKey *string
	APIKey             *string

	IsSelfHosted bool
	Enabled      bool
}

// supabaseEnvPtr is os.environ.get(key): nil when the variable is unset.
func supabaseEnvPtr(key string) *string {
	if v, ok := os.LookupEnv(key); ok {
		return &v
	}
	return nil
}

// NewSupabaseTokenClient initializes the client with environment variables.
func NewSupabaseTokenClient() *SupabaseTokenClient {
	c := &SupabaseTokenClient{
		SupabaseURL:        supabaseEnvPtr("SUPABASE_URL"),
		SupabaseAnonKey:    supabaseEnvPtr("SUPABASE_ANON_KEY"),
		SupabaseServiceKey: supabaseEnvPtr("SUPABASE_SERVICE_KEY"),
	}
	// self.api_key = self.supabase_service_key or self.supabase_anon_key
	c.APIKey = pyOrStr(c.SupabaseServiceKey, c.SupabaseAnonKey)

	url := ""
	if c.SupabaseURL != nil {
		url = *c.SupabaseURL
	}
	c.IsSelfHosted = selfHostedIPPattern.MatchString(url)

	if c.SupabaseURL == nil || *c.SupabaseURL == "" || c.APIKey == nil || *c.APIKey == "" {
		c.Enabled = false
	} else {
		c.Enabled = true
	}
	return c
}

// APIHeaders returns the headers for Supabase API requests.
func (c *SupabaseTokenClient) APIHeaders() map[string]string {
	key := ""
	if c.APIKey != nil {
		key = *c.APIKey
	}
	return map[string]string{
		"apikey":        key,
		"Authorization": "Bearer " + key,
		"Content-Type":  "application/json",
		"Prefer":        "return=minimal",
	}
}

// HashToken creates a secure SHA-256 hash of the token for storage.
func (c *SupabaseTokenClient) HashToken(token string) string {
	sum := sha256.Sum256([]byte(token))
	return hex.EncodeToString(sum[:])
}

// httpClient returns the HTTP client with the SSL configuration for self-hosted
// instances (verification disabled), otherwise a default client.
func (c *SupabaseTokenClient) httpClient() *http.Client {
	if c.IsSelfHosted {
		return &http.Client{Transport: &http.Transport{TLSClientConfig: &tls.Config{InsecureSkipVerify: true}}}
	}
	return &http.Client{}
}

func (c *SupabaseTokenClient) baseURL() string {
	if c.SupabaseURL == nil {
		return ""
	}
	return *c.SupabaseURL
}

// ValidateToken validates a token against the Supabase database.
func (c *SupabaseTokenClient) ValidateToken(ctx context.Context, token string) *TokenInfo {
	if !c.Enabled {
		return nil
	}

	tokenHash := c.HashToken(token)

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.baseURL()+"/rest/v1/api_tokens", nil)
	if err != nil {
		return nil
	}
	q := req.URL.Query()
	q.Set("token_hash", "eq."+tokenHash)
	q.Set("is_active", "eq.true")
	req.URL.RawQuery = q.Encode()
	for k, v := range c.APIHeaders() {
		req.Header.Set(k, v)
	}

	resp, err := c.httpClient().Do(req)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil
	}

	var tokens []map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&tokens); err != nil {
		return nil
	}
	if len(tokens) == 0 {
		return nil
	}
	tokenData := tokens[0]

	if v, ok := tokenData["expires_at"]; ok && value_objects.PyTruthy(v) {
		s, ok := v.(string)
		if !ok {
			return nil
		}
		expiresAt, err := value_objects.ParseISO(s)
		if err != nil {
			return nil
		}
		if expiresAt.Before(time.Now().UTC()) {
			return nil
		}
	}

	c.updateTokenUsage(ctx, tokenHash)

	createdRaw, ok := tokenData["created_at"].(string)
	if !ok {
		return nil
	}
	createdAt, err := value_objects.ParseISO(createdRaw)
	if err != nil {
		return nil
	}

	var expiresAt *time.Time
	if v, ok := tokenData["expires_at"]; ok && value_objects.PyTruthy(v) {
		if s, ok := v.(string); ok {
			if t, err := value_objects.ParseISO(s); err == nil {
				expiresAt = &t
			}
		}
	}

	isActive, ok := tokenData["is_active"].(bool)
	if !ok {
		return nil
	}

	usageCount := 0
	if v, ok := tokenData["usage_count"]; ok {
		usageCount = pyIntValue(v)
	}

	var lastUsed *time.Time
	if v, ok := tokenData["last_used"]; ok && value_objects.PyTruthy(v) {
		if s, ok := v.(string); ok {
			if t, err := value_objects.ParseISO(s); err == nil {
				lastUsed = &t
			}
		}
	}

	return &TokenInfo{
		TokenHash:  tokenHash,
		UserID:     pyStringValue(tokenData["user_id"]),
		CreatedAt:  createdAt,
		ExpiresAt:  expiresAt,
		IsActive:   isActive,
		UsageCount: usageCount,
		LastUsed:   lastUsed,
	}
}

// updateTokenUsage updates token usage statistics.
func (c *SupabaseTokenClient) updateTokenUsage(ctx context.Context, tokenHash string) {
	if !c.Enabled {
		return
	}

	body, _ := json.Marshal(map[string]any{
		"last_used":   nowUTCISO(),
		"usage_count": "usage_count + 1",
	})
	req, err := http.NewRequestWithContext(ctx, http.MethodPatch, c.baseURL()+"/rest/v1/api_tokens", bytes.NewReader(body))
	if err != nil {
		return
	}
	q := req.URL.Query()
	q.Set("token_hash", "eq."+tokenHash)
	req.URL.RawQuery = q.Encode()
	for k, v := range c.APIHeaders() {
		req.Header.Set(k, v)
	}

	resp, err := c.httpClient().Do(req)
	if err != nil {
		return
	}
	defer resp.Body.Close()
}

// RevokeToken revokes a token by marking it as inactive.
func (c *SupabaseTokenClient) RevokeToken(ctx context.Context, token string) bool {
	if !c.Enabled {
		return false
	}

	tokenHash := c.HashToken(token)
	body, _ := json.Marshal(map[string]any{"is_active": false})
	req, err := http.NewRequestWithContext(ctx, http.MethodPatch, c.baseURL()+"/rest/v1/api_tokens", bytes.NewReader(body))
	if err != nil {
		return false
	}
	q := req.URL.Query()
	q.Set("token_hash", "eq."+tokenHash)
	req.URL.RawQuery = q.Encode()
	for k, v := range c.APIHeaders() {
		req.Header.Set(k, v)
	}

	resp, err := c.httpClient().Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == 204
}

// LogSecurityEvent logs security events to Supabase.
func (c *SupabaseTokenClient) LogSecurityEvent(ctx context.Context, eventType, tokenHash string, details *taskentities.OrderedMap[any]) {
	if !c.Enabled {
		return
	}

	var detailsVal any
	if details != nil {
		detailsVal = details
	}
	body, err := json.Marshal(map[string]any{
		"event_type": eventType,
		"token_hash": tokenHash,
		"details":    detailsVal,
		"timestamp":  nowUTCISO(),
	})
	if err != nil {
		return
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL()+"/rest/v1/security_logs", bytes.NewReader(body))
	if err != nil {
		return
	}
	for k, v := range c.APIHeaders() {
		req.Header.Set(k, v)
	}

	resp, err := c.httpClient().Do(req)
	if err != nil {
		return
	}
	defer resp.Body.Close()
}

// GenerateToken generates a secure 32-byte random token (64 hex characters).
func (c *SupabaseTokenClient) GenerateToken() string {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	return hex.EncodeToString(b)
}

// pyStringValue is Python's str() for a JSON scalar, with "" for None.
func pyStringValue(v any) string {
	if v == nil {
		return ""
	}
	return value_objects.PyStr(v)
}

// pyIntValue is int(v) for JSON numbers (0 when it cannot be converted).
func pyIntValue(v any) int {
	switch n := v.(type) {
	case float64:
		return int(n)
	case int:
		return n
	case int64:
		return int(n)
	case bool:
		if n {
			return 1
		}
		return 0
	}
	return 0
}

// nowUTCISO is datetime.now(UTC).isoformat().
func nowUTCISO() string {
	return value_objects.IsoFormat(time.Now().UTC().Truncate(time.Microsecond))
}

// pyOrStr is `a or b` for optional strings.
func pyOrStr(a, b *string) *string {
	if a != nil && *a != "" {
		return a
	}
	return b
}
