package auth

import (
	"context"
	"fmt"
	"strings"
	"time"

	taskentities "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TokenValidationError is raised when token validation fails.
type TokenValidationError struct{ Msg string }

func (e *TokenValidationError) Error() string { return e.Msg }

// RateLimitError is raised when a rate limit is exceeded.
type RateLimitError struct{ Msg string }

func (e *RateLimitError) Error() string { return e.Msg }

// RateLimitConfig is the rate limiting configuration.
type RateLimitConfig struct {
	RequestsPerMinute int
	RequestsPerHour   int
	BurstLimit        int
	WindowSize        int
}

// DefaultRateLimitConfig is the dataclass default.
func DefaultRateLimitConfig() RateLimitConfig {
	return RateLimitConfig{RequestsPerMinute: 100, RequestsPerHour: 1000, BurstLimit: 20, WindowSize: 60}
}

// rateDeque is collections.deque with an optional maxlen.
type rateDeque struct {
	items  []float64
	maxLen int
}

func (d *rateDeque) append(v float64) {
	if d.maxLen > 0 && len(d.items) >= d.maxLen {
		d.items = d.items[1:]
	}
	d.items = append(d.items, v)
}

func (d *rateDeque) popleft() {
	if len(d.items) > 0 {
		d.items = d.items[1:]
	}
}

type cachedTokenInfo struct {
	info      *TokenInfo
	cacheTime float64
}

// MCPTokenRecord is the minimal shape of an MCP token used by TokenValidator.
type MCPTokenRecord struct {
	UserID    string
	CreatedAt time.Time
	ExpiresAt *time.Time
}

// MCPTokenValidationService is the minimal interface for the Python
// auth.services.mcp_token_service singleton, which has no Go port.
type MCPTokenValidationService interface {
	ValidateMCPToken(ctx context.Context, token string) (*MCPTokenRecord, error)
}

// MCPTokenServiceInstance is the injected MCP token service (nil = unavailable).
var MCPTokenServiceInstance MCPTokenValidationService

// TokenValidator is the token validation and rate limiting system.
type TokenValidator struct {
	SupabaseClient *SupabaseTokenClient
	RateConfig     RateLimitConfig

	rateLimits     map[string]*rateDeque
	tokenCache     map[string]cachedTokenInfo
	cacheTTL       float64
	failedAttempts map[string]*rateDeque

	// Now is time.time(); injectable for tests.
	Now func() float64
}

// NewTokenValidator initializes the validator.
func NewTokenValidator(rateLimitConfig *RateLimitConfig) *TokenValidator {
	cfg := DefaultRateLimitConfig()
	if rateLimitConfig != nil {
		cfg = *rateLimitConfig
	}
	return &TokenValidator{
		SupabaseClient: NewSupabaseTokenClient(),
		RateConfig:     cfg,
		rateLimits:     map[string]*rateDeque{},
		tokenCache:     map[string]cachedTokenInfo{},
		cacheTTL:       300,
		failedAttempts: map[string]*rateDeque{},
		Now:            func() float64 { return float64(time.Now().UnixNano()) / 1e9 },
	}
}

func (v *TokenValidator) rateDeque(tokenHash string) *rateDeque {
	d, ok := v.rateLimits[tokenHash]
	if !ok {
		d = &rateDeque{maxLen: v.RateConfig.RequestsPerHour}
		v.rateLimits[tokenHash] = d
	}
	return d
}

func (v *TokenValidator) failureDeque(tokenHash string) *rateDeque {
	d, ok := v.failedAttempts[tokenHash]
	if !ok {
		d = &rateDeque{maxLen: 10}
		v.failedAttempts[tokenHash] = d
	}
	return d
}

// ValidateToken validates a token and checks rate limits.
func (v *TokenValidator) ValidateToken(ctx context.Context, token string, clientInfo *taskentities.OrderedMap[any]) (*TokenInfo, error) {
	if token == "" {
		return nil, &TokenValidationError{Msg: "Token is required"}
	}

	token = value_objects.PyStrip(token)
	if strings.HasPrefix(token, "Bearer ") {
		token = token[7:]
	}

	tokenHash := v.SupabaseClient.HashToken(token)

	if err := v.checkRateLimit(tokenHash); err != nil {
		v.logFailedAttempt(ctx, tokenHash, "rate_limit_exceeded", clientInfo)
		return nil, err
	}

	tokenInfo, err := v.getTokenInfo(ctx, token)
	if err != nil {
		v.logFailedAttempt(ctx, tokenHash, "validation_error", clientInfo)
		return nil, &TokenValidationError{Msg: "Token validation failed"}
	}

	if tokenInfo == nil {
		v.logFailedAttempt(ctx, tokenHash, "invalid_token", clientInfo)
		v.logFailedAttempt(ctx, tokenHash, "validation_failed", clientInfo)
		return nil, &TokenValidationError{Msg: "Invalid or expired token"}
	}

	details := taskentities.NewOrderedMap[any]()
	details.Set("user_id", tokenInfo.UserID)
	details.Set("client_info", clientInfoValue(clientInfo))
	details.Set("usage_count", tokenInfo.UsageCount)
	v.SupabaseClient.LogSecurityEvent(ctx, "token_validated", tokenHash, details)

	return tokenInfo, nil
}

// clientInfoValue is `client_info or {}`.
func clientInfoValue(clientInfo *taskentities.OrderedMap[any]) any {
	if clientInfo == nil || clientInfo.Len() == 0 {
		return taskentities.NewOrderedMap[any]()
	}
	return clientInfo
}

func (v *TokenValidator) getTokenInfo(ctx context.Context, token string) (*TokenInfo, error) {
	tokenHash := v.SupabaseClient.HashToken(token)
	currentTime := v.Now()

	if cached, ok := v.tokenCache[tokenHash]; ok {
		if currentTime-cached.cacheTime < v.cacheTTL {
			return cached.info, nil
		}
		delete(v.tokenCache, tokenHash)
	}

	if strings.HasPrefix(token, "mcp_") {
		tokenInfo := v.validateMCPToken(ctx, token)
		if tokenInfo != nil {
			v.tokenCache[tokenHash] = cachedTokenInfo{info: tokenInfo, cacheTime: currentTime}
			return tokenInfo, nil
		}
	}

	tokenInfo := v.SupabaseClient.ValidateToken(ctx, token)
	if tokenInfo != nil {
		v.tokenCache[tokenHash] = cachedTokenInfo{info: tokenInfo, cacheTime: currentTime}
	}
	return tokenInfo, nil
}

func (v *TokenValidator) checkRateLimit(tokenHash string) error {
	currentTime := v.Now()
	requests := v.rateDeque(tokenHash)

	cutoffTime := currentTime - 3600
	for len(requests.items) > 0 && requests.items[0] < cutoffTime {
		requests.popleft()
	}

	minuteCutoff := currentTime - 60
	recentRequests := 0
	for _, reqTime := range requests.items {
		if reqTime > minuteCutoff {
			recentRequests++
		}
	}
	if recentRequests >= v.RateConfig.RequestsPerMinute {
		return &RateLimitError{Msg: fmt.Sprintf(
			"Rate limit exceeded: %d/%d requests per minute",
			recentRequests, v.RateConfig.RequestsPerMinute)}
	}

	burstCutoff := currentTime - 10
	burstRequests := 0
	for _, reqTime := range requests.items {
		if reqTime > burstCutoff {
			burstRequests++
		}
	}
	if burstRequests >= v.RateConfig.BurstLimit {
		return &RateLimitError{Msg: fmt.Sprintf(
			"Burst limit exceeded: %d/%d requests per 10 seconds",
			burstRequests, v.RateConfig.BurstLimit)}
	}

	requests.append(currentTime)
	return nil
}

func (v *TokenValidator) logFailedAttempt(ctx context.Context, tokenHash, reason string, clientInfo *taskentities.OrderedMap[any]) {
	currentTime := v.Now()
	failures := v.failureDeque(tokenHash)

	cutoffTime := currentTime - 3600
	for len(failures.items) > 0 && failures.items[0] < cutoffTime {
		failures.popleft()
	}
	failures.append(currentTime)

	details := taskentities.NewOrderedMap[any]()
	details.Set("reason", reason)
	details.Set("failure_count", len(failures.items))
	details.Set("client_info", clientInfoValue(clientInfo))
	details.Set("timestamp", nowUTCISO())

	v.SupabaseClient.LogSecurityEvent(ctx, "validation_failed", tokenHash, details)
}

// RevokeToken revokes a token and clears it from cache.
func (v *TokenValidator) RevokeToken(ctx context.Context, token string) bool {
	tokenHash := v.SupabaseClient.HashToken(token)

	if _, ok := v.tokenCache[tokenHash]; ok {
		delete(v.tokenCache, tokenHash)
	}

	success := v.SupabaseClient.RevokeToken(ctx, token)

	if success {
		details := taskentities.NewOrderedMap[any]()
		details.Set("revoked_at", nowUTCISO())
		v.SupabaseClient.LogSecurityEvent(ctx, "token_revoked", tokenHash, details)
	}

	return success
}

// GetRateLimitStatus returns the current rate limit status for a token.
func (v *TokenValidator) GetRateLimitStatus(token string) *taskentities.OrderedMap[any] {
	tokenHash := v.SupabaseClient.HashToken(token)
	requests := v.rateDeque(tokenHash)
	currentTime := v.Now()

	minuteCutoff := currentTime - 60
	hourCutoff := currentTime - 3600

	minuteRequests := 0
	hourRequests := 0
	for _, reqTime := range requests.items {
		if reqTime > minuteCutoff {
			minuteRequests++
		}
		if reqTime > hourCutoff {
			hourRequests++
		}
	}

	d := taskentities.NewOrderedMap[any]()
	d.Set("requests_per_minute", minuteRequests)
	d.Set("minute_limit", v.RateConfig.RequestsPerMinute)
	d.Set("requests_per_hour", hourRequests)
	d.Set("hour_limit", v.RateConfig.RequestsPerHour)
	d.Set("remaining_minute", maxInt(0, v.RateConfig.RequestsPerMinute-minuteRequests))
	d.Set("remaining_hour", maxInt(0, v.RateConfig.RequestsPerHour-hourRequests))
	return d
}

// ClearCache clears the token cache.
func (v *TokenValidator) ClearCache() {
	v.tokenCache = map[string]cachedTokenInfo{}
}

// GetCacheStats returns cache statistics.
func (v *TokenValidator) GetCacheStats() *taskentities.OrderedMap[any] {
	d := taskentities.NewOrderedMap[any]()
	d.Set("cached_tokens", len(v.tokenCache))
	d.Set("rate_limited_tokens", len(v.rateLimits))
	d.Set("failed_attempt_records", len(v.failedAttempts))
	return d
}

func (v *TokenValidator) validateMCPToken(ctx context.Context, token string) *TokenInfo {
	service := MCPTokenServiceInstance
	if service == nil {
		return nil
	}
	tokenObj, err := service.ValidateMCPToken(ctx, token)
	if err != nil || tokenObj == nil {
		return nil
	}
	return &TokenInfo{
		TokenHash:  v.SupabaseClient.HashToken(token),
		UserID:     tokenObj.UserID,
		CreatedAt:  tokenObj.CreatedAt,
		ExpiresAt:  tokenObj.ExpiresAt,
		IsActive:   true,
		UsageCount: 0,
		LastUsed:   nil,
	}
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}
