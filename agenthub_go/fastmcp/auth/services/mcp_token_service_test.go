package services

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestMCPTokenServiceGlobalInstance(t *testing.T) {
	if MCPTokenServiceInstance == nil {
		t.Fatal("MCPTokenServiceInstance is nil")
	}
	if MCPTokenServiceInstance.tokens == nil {
		t.Fatal("global service tokens map is nil")
	}
}

func TestMCPTokenGenerateFormat(t *testing.T) {
	svc := NewMCPTokenService()
	email := "test@example.com"
	tok := svc.GenerateMCPTokenFromUserID(context.Background(), "user_123", &email, 24, nil)

	if !strings.HasPrefix(tok.Token, "mcp_") {
		t.Fatalf("token %q does not start with mcp_", tok.Token)
	}
	if len(tok.Token) != len("mcp_")+64 {
		t.Fatalf("token length = %d, want 68", len(tok.Token))
	}
	if _, err := hex.DecodeString(tok.Token[len("mcp_"):]); err != nil {
		t.Fatalf("token suffix is not hex: %v", err)
	}
	if tok.UserID != "user_123" {
		t.Fatalf("user_id = %q", tok.UserID)
	}
	if tok.Email == nil || *tok.Email != email {
		t.Fatalf("email = %v", tok.Email)
	}
	if !tok.IsActive {
		t.Fatal("is_active should be true")
	}
	if tok.CreatedAt == nil || tok.ExpiresAt == nil {
		t.Fatalf("timestamps = %v, %v", tok.CreatedAt, tok.ExpiresAt)
	}
	if want := tok.CreatedAt.Add(24 * time.Hour); !tok.ExpiresAt.Equal(want) {
		t.Fatalf("expires_at = %v, want %v", tok.ExpiresAt, want)
	}
	if tok.Metadata == nil || tok.Metadata.Len() != 0 {
		t.Fatalf("metadata = %#v, want empty dict", tok.Metadata)
	}

	stored, ok := svc.tokens.Get(tok.Token)
	if !ok || stored != tok {
		t.Fatal("generated token was not stored in memory")
	}
}

func TestMCPTokenGenerateCustomExpiration(t *testing.T) {
	svc := NewMCPTokenService()
	tok := svc.GenerateMCPTokenFromUserID(context.Background(), "user_456", nil, 48, nil)
	if got := tok.ExpiresAt.Sub(*tok.CreatedAt); got != 48*time.Hour {
		t.Fatalf("expiration = %v, want 48h", got)
	}
}

func TestMCPTokenGenerateMetadata(t *testing.T) {
	svc := NewMCPTokenService()
	meta := entities.NewOrderedMap[any]()
	meta.Set("scope", "admin")
	meta.Set("client", "web")

	tok := svc.GenerateMCPTokenFromUserID(context.Background(), "user_789", nil, 24, meta)
	if tok.Metadata != meta {
		t.Fatal("provided metadata should be stored as-is")
	}
	if v, _ := tok.Metadata.Get("scope"); v != "admin" {
		t.Fatalf("scope = %v", v)
	}

	// An empty dict is falsy, so Python replaces it with a new empty dict.
	empty := entities.NewOrderedMap[any]()
	other := svc.GenerateMCPTokenFromUserID(context.Background(), "user_000", nil, 24, empty)
	if other.Metadata == empty {
		t.Fatal("empty metadata should be replaced by a new dict")
	}
	if other.Metadata.Len() != 0 {
		t.Fatalf("metadata = %#v, want empty dict", other.Metadata)
	}
}

func TestMCPTokenValidateInvalidOrMissing(t *testing.T) {
	svc := NewMCPTokenService()
	ctx := context.Background()
	for _, token := range []string{"", "invalid_token", "token_mcp_x", "mcp_nonexistent"} {
		if got := svc.ValidateMCPToken(ctx, token); got != nil {
			t.Fatalf("ValidateMCPToken(%q) = %#v, want nil", token, got)
		}
	}
}

func TestMCPTokenValidateInactive(t *testing.T) {
	svc := NewMCPTokenService()
	now := time.Now().UTC()
	expires := now.Add(time.Hour)
	tok := &MCPToken{Token: "mcp_inactive", UserID: "user_1", CreatedAt: &now, ExpiresAt: &expires, IsActive: false}
	svc.tokens.Set(tok.Token, tok)

	if got := svc.ValidateMCPToken(context.Background(), tok.Token); got != nil {
		t.Fatalf("inactive token validated: %#v", got)
	}
}

func TestMCPTokenValidateValidUpdatesUsage(t *testing.T) {
	svc := NewMCPTokenService()
	calls := 0
	var gotHash string
	svc.updateUsage = func(_ context.Context, tokenHash string) {
		calls++
		gotHash = tokenHash
	}

	tok := svc.GenerateMCPTokenFromUserID(context.Background(), "user_123", nil, 24, nil)
	got := svc.ValidateMCPToken(context.Background(), tok.Token)
	if got != tok {
		t.Fatalf("ValidateMCPToken = %#v, want the stored token", got)
	}
	if calls != 1 {
		t.Fatalf("update usage calls = %d, want 1", calls)
	}
	sum := sha256.Sum256([]byte(tok.Token))
	if want := hex.EncodeToString(sum[:]); gotHash != want {
		t.Fatalf("token hash = %q, want %q", gotHash, want)
	}
}

func TestMCPTokenValidateExpiredRemoved(t *testing.T) {
	svc := NewMCPTokenService()
	now := time.Now().UTC()
	created := now.Add(-25 * time.Hour)
	expired := now.Add(-1 * time.Hour)
	tok := &MCPToken{Token: "mcp_expired_token", UserID: "user_exp", CreatedAt: &created, ExpiresAt: &expired, IsActive: true}
	svc.tokens.Set(tok.Token, tok)

	if got := svc.ValidateMCPToken(context.Background(), tok.Token); got != nil {
		t.Fatalf("expired token validated: %#v", got)
	}
	if svc.tokens.Has(tok.Token) {
		t.Fatal("expired token should be removed")
	}
}

func TestMCPTokenRevokeUserTokens(t *testing.T) {
	svc := NewMCPTokenService()
	ctx := context.Background()
	t1 := svc.GenerateMCPTokenFromUserID(ctx, "user_multi", nil, 24, nil)
	t2 := svc.GenerateMCPTokenFromUserID(ctx, "user_multi", nil, 24, nil)
	t3 := svc.GenerateMCPTokenFromUserID(ctx, "other_user", nil, 24, nil)

	if !svc.RevokeUserTokens(ctx, "user_multi") {
		t.Fatal("RevokeUserTokens = false, want true")
	}
	if svc.tokens.Has(t1.Token) || svc.tokens.Has(t2.Token) {
		t.Fatal("revoked tokens should be removed")
	}
	if !svc.tokens.Has(t3.Token) {
		t.Fatal("other user's token should remain")
	}
	if svc.RevokeUserTokens(ctx, "nonexistent_user") {
		t.Fatal("RevokeUserTokens(no tokens) = true, want false")
	}
}

func TestMCPTokenRevokeAlreadyInactive(t *testing.T) {
	svc := NewMCPTokenService()
	tok := &MCPToken{Token: "mcp_inactive", UserID: "user_1", IsActive: false}
	svc.tokens.Set(tok.Token, tok)

	if svc.RevokeUserTokens(context.Background(), "user_1") {
		t.Fatal("RevokeUserTokens(inactive) = true, want false")
	}
	if !svc.tokens.Has(tok.Token) {
		t.Fatal("inactive token should not be removed")
	}
}

func TestMCPTokenCleanupExpiredTokens(t *testing.T) {
	svc := NewMCPTokenService()
	ctx := context.Background()
	now := time.Now().UTC()
	expired := now.Add(-time.Hour)
	et := &MCPToken{Token: "mcp_expired", UserID: "user_exp", CreatedAt: &now, ExpiresAt: &expired, IsActive: true}
	svc.tokens.Set(et.Token, et)
	valid := svc.GenerateMCPTokenFromUserID(ctx, "user_valid", nil, 24, nil)

	if got := svc.CleanupExpiredTokens(ctx); got != 1 {
		t.Fatalf("CleanupExpiredTokens = %d, want 1", got)
	}
	if svc.tokens.Has(et.Token) {
		t.Fatal("expired token should be removed")
	}
	if !svc.tokens.Has(valid.Token) {
		t.Fatal("valid token should remain")
	}
}

func TestMCPTokenCleanupNoneExpired(t *testing.T) {
	svc := NewMCPTokenService()
	ctx := context.Background()
	svc.GenerateMCPTokenFromUserID(ctx, "user_1", nil, 24, nil)
	svc.GenerateMCPTokenFromUserID(ctx, "user_2", nil, 24, nil)

	if got := svc.CleanupExpiredTokens(ctx); got != 0 {
		t.Fatalf("CleanupExpiredTokens = %d, want 0", got)
	}
	if svc.tokens.Len() != 2 {
		t.Fatalf("token count = %d, want 2", svc.tokens.Len())
	}
}

func TestMCPTokenGetTokenStatsEmpty(t *testing.T) {
	svc := NewMCPTokenService()
	stats := svc.GetTokenStats()

	wantKeys := []string{"total_tokens", "active_tokens", "expired_tokens", "service_status", "storage_type"}
	assertMCPStats(t, stats, wantKeys, 0, 0, 0)
}

func TestMCPTokenGetTokenStatsWithTokens(t *testing.T) {
	svc := NewMCPTokenService()
	now := time.Now().UTC()
	future := now.Add(time.Hour)
	past := now.Add(-time.Hour)

	active := &MCPToken{Token: "mcp_active", UserID: "user_1", ExpiresAt: &future, IsActive: true}
	expired := &MCPToken{Token: "mcp_expired", UserID: "user_2", ExpiresAt: &past, IsActive: true}
	inactive := &MCPToken{Token: "mcp_inactive", UserID: "user_3", ExpiresAt: &future, IsActive: false}
	noExpiry := &MCPToken{Token: "mcp_no_expiry", UserID: "user_4", IsActive: true}
	for _, tok := range []*MCPToken{active, expired, inactive, noExpiry} {
		svc.tokens.Set(tok.Token, tok)
	}

	stats := svc.GetTokenStats()
	wantKeys := []string{"total_tokens", "active_tokens", "expired_tokens", "service_status", "storage_type"}
	assertMCPStats(t, stats, wantKeys, 4, 2, 2)
}

func assertMCPStats(t *testing.T, stats *entities.OrderedMap[any], wantKeys []string, total, active, expired int) {
	t.Helper()
	gotKeys := stats.Keys()
	if len(gotKeys) != len(wantKeys) {
		t.Fatalf("stat keys = %v, want %v", gotKeys, wantKeys)
	}
	for i, k := range wantKeys {
		if gotKeys[i] != k {
			t.Fatalf("stat keys = %v, want %v", gotKeys, wantKeys)
		}
	}
	if v, _ := stats.Get("total_tokens"); v != total {
		t.Fatalf("total_tokens = %v, want %d", v, total)
	}
	if v, _ := stats.Get("active_tokens"); v != active {
		t.Fatalf("active_tokens = %v, want %d", v, active)
	}
	if v, _ := stats.Get("expired_tokens"); v != expired {
		t.Fatalf("expired_tokens = %v, want %d", v, expired)
	}
	if v, _ := stats.Get("service_status"); v != "running" {
		t.Fatalf("service_status = %v", v)
	}
	if v, _ := stats.Get("storage_type"); v != "in-memory" {
		t.Fatalf("storage_type = %v", v)
	}
}

func TestMCPTokenGetUserTokens(t *testing.T) {
	svc := NewMCPTokenService()
	ctx := context.Background()
	t1 := svc.GenerateMCPTokenFromUserID(ctx, "user_multi", nil, 24, nil)
	t2 := svc.GenerateMCPTokenFromUserID(ctx, "user_multi", nil, 24, nil)
	svc.GenerateMCPTokenFromUserID(ctx, "other_user", nil, 24, nil)

	got := svc.GetUserTokens(ctx, "user_multi")
	if len(got) != 2 {
		t.Fatalf("GetUserTokens = %d tokens, want 2", len(got))
	}
	if got[0] != t1 || got[1] != t2 {
		t.Fatal("tokens should keep insertion order")
	}

	none := svc.GetUserTokens(ctx, "nonexistent_user")
	if none == nil || len(none) != 0 {
		t.Fatalf("GetUserTokens(none) = %#v, want empty list", none)
	}
}

func TestMCPTokenGetUserTokensMarksExpired(t *testing.T) {
	svc := NewMCPTokenService()
	now := time.Now().UTC()
	created := now.Add(-25 * time.Hour)
	expired := now.Add(-1 * time.Hour)
	tok := &MCPToken{Token: "mcp_expired", UserID: "user_exp", CreatedAt: &created, ExpiresAt: &expired, IsActive: true}
	svc.tokens.Set(tok.Token, tok)

	got := svc.GetUserTokens(context.Background(), "user_exp")
	if len(got) != 1 {
		t.Fatalf("GetUserTokens = %d tokens, want 1", len(got))
	}
	if got[0].IsActive {
		t.Fatal("expired token should be marked inactive")
	}
}
