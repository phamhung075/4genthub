package config_test

import (
	"errors"
	"testing"
	"time"

	"agenthub/fastmcp/config"
	"agenthub/fastmcp/task_management/domain/entities"
)

type fakeAuthMiddleware struct {
	enabled    bool
	info       *config.TokenInfo
	authErr    error
	rateStatus any
	rateErr    error
	revokeOK   bool
	revokeErr  error
	status     *entities.OrderedMap[any]
}

func (f *fakeAuthMiddleware) Enabled() bool { return f.enabled }
func (f *fakeAuthMiddleware) AuthenticateRequest(string) (*config.TokenInfo, error) {
	return f.info, f.authErr
}
func (f *fakeAuthMiddleware) GetRateLimitStatus(string) (any, error) { return f.rateStatus, f.rateErr }
func (f *fakeAuthMiddleware) RevokeToken(string) (bool, error)       { return f.revokeOK, f.revokeErr }
func (f *fakeAuthMiddleware) GetAuthStatus() *entities.OrderedMap[any] {
	return f.status
}

func TestAuthenticationToolsValidateToken(t *testing.T) {
	created := time.Date(2025, 1, 2, 3, 4, 5, 0, time.UTC)
	expires := time.Date(2025, 1, 3, 3, 4, 5, 0, time.UTC)
	mw := &fakeAuthMiddleware{enabled: true, info: &config.TokenInfo{
		UserID: "user-1", CreatedAt: created, ExpiresAt: &expires, UsageCount: 5,
	}}
	tools := config.NewAuthenticationTools(mw)
	got := tools.ValidateToken("token")

	if v, _ := got.Get("valid"); v != true {
		t.Fatalf("valid = %v", v)
	}
	if v, _ := got.Get("user_id"); v != "user-1" {
		t.Fatalf("user_id = %v", v)
	}
	if v, _ := got.Get("created_at"); v != "2025-01-02T03:04:05+00:00" {
		t.Fatalf("created_at = %v", v)
	}
	if v, _ := got.Get("expires_at"); v != "2025-01-03T03:04:05+00:00" {
		t.Fatalf("expires_at = %v", v)
	}
	if v, _ := got.Get("usage_count"); v != 5 {
		t.Fatalf("usage_count = %v", v)
	}
	if v, _ := got.Get("last_used"); v != nil {
		t.Fatalf("last_used = %v", v)
	}
	if v, _ := got.Get("auth_enabled"); v != true {
		t.Fatalf("auth_enabled = %v", v)
	}
}

func TestAuthenticationToolsValidateTokenMVP(t *testing.T) {
	tools := config.NewAuthenticationTools(&fakeAuthMiddleware{enabled: false, info: nil})
	got := tools.ValidateToken("token")
	want := []struct {
		k string
		v any
	}{
		{"valid", true},
		{"message", "Authentication disabled or MVP mode"},
		{"user_id", "mvp_user"},
		{"auth_enabled", false},
	}
	for _, w := range want {
		if v, _ := got.Get(w.k); v != w.v {
			t.Fatalf("%s = %v, want %v", w.k, v, w.v)
		}
	}
}

func TestAuthenticationToolsValidateTokenErrors(t *testing.T) {
	cases := []struct {
		name      string
		authErr   error
		errorType string
		message   string
	}{
		{"validation", &config.TokenValidationError{Msg: "bad token"}, "validation_error", "bad token"},
		{"rate", &config.RateLimitError{Msg: "too many"}, "rate_limit_error", "too many"},
		{"internal", errors.New("boom"), "internal_error", "Internal validation error"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			mw := &fakeAuthMiddleware{enabled: true, authErr: tc.authErr}
			got := config.NewAuthenticationTools(mw).ValidateToken("t")
			if v, _ := got.Get("valid"); v != false {
				t.Fatalf("valid = %v", v)
			}
			if v, _ := got.Get("error"); v != tc.message {
				t.Fatalf("error = %v", v)
			}
			if v, _ := got.Get("error_type"); v != tc.errorType {
				t.Fatalf("error_type = %v", v)
			}
			if v, _ := got.Get("auth_enabled"); v != true {
				t.Fatalf("auth_enabled = %v", v)
			}
		})
	}
}

func TestAuthenticationToolsRateLimitAndRevoke(t *testing.T) {
	status := entities.NewOrderedMap[any]()
	status.Set("requests_per_minute", 100)
	mw := &fakeAuthMiddleware{enabled: true, rateStatus: status}
	tools := config.NewAuthenticationTools(mw)

	got := tools.GetRateLimitStatus("t")
	if v, _ := got.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
	if v, _ := got.Get("rate_limits"); v != status {
		t.Fatalf("rate_limits = %v", v)
	}

	mw.rateErr = errors.New("nope")
	got = tools.GetRateLimitStatus("t")
	if v, _ := got.Get("success"); v != false {
		t.Fatalf("success = %v", v)
	}
	if v, _ := got.Get("error"); v != "nope" {
		t.Fatalf("error = %v", v)
	}

	mw.revokeOK = true
	got = tools.RevokeToken("t")
	if v, _ := got.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
	if v, _ := got.Get("message"); v != "Token revoked successfully" {
		t.Fatalf("message = %v", v)
	}

	mw.revokeOK = false
	got = tools.RevokeToken("t")
	if v, _ := got.Get("message"); v != "Failed to revoke token" {
		t.Fatalf("message = %v", v)
	}

	mw.revokeErr = errors.New("write failed")
	got = tools.RevokeToken("t")
	if v, _ := got.Get("error"); v != "write failed" {
		t.Fatalf("error = %v", v)
	}
}

func TestAuthenticationToolsGenerateAndFunctions(t *testing.T) {
	tools := config.NewAuthenticationTools(&fakeAuthMiddleware{enabled: true})
	got := tools.GenerateToken()
	if v, _ := got.Get("success"); v != false {
		t.Fatalf("success = %v", v)
	}
	if v, _ := got.Get("api_endpoint"); v != "/api/v2/tokens" {
		t.Fatalf("api_endpoint = %v", v)
	}
	if v, _ := got.Get("method"); v != "POST" {
		t.Fatalf("method = %v", v)
	}
	example, _ := got.Get("example")
	em := example.(cmap)
	if v, _ := em.Get("name"); v != "my-token" {
		t.Fatalf("name = %v", v)
	}
	if v, _ := em.Get("expires_in_days"); v != 30 {
		t.Fatalf("expires_in_days = %v", v)
	}
	if v, _ := em.Get("scopes"); !eqStrings(v, []string{"read", "write"}) {
		t.Fatalf("scopes = %v", v)
	}

	fns := tools.GetToolFunctions()
	wantKeys := []string{"validate_token", "get_rate_limit_status", "revoke_token", "get_auth_status", "generate_token"}
	if len(fns.Keys()) != len(wantKeys) {
		t.Fatalf("keys = %v", fns.Keys())
	}
	for i, k := range wantKeys {
		if fns.Keys()[i] != k {
			t.Fatalf("keys = %v", fns.Keys())
		}
		if _, ok := fns.Get(k); !ok {
			t.Fatalf("missing %s", k)
		}
	}

	created := config.CreateAuthenticationTools(&fakeAuthMiddleware{enabled: true})
	if len(created.Keys()) != len(wantKeys) {
		t.Fatalf("created keys = %v", created.Keys())
	}
}

func TestAuthenticationToolsAuthStatus(t *testing.T) {
	status := entities.NewOrderedMap[any]()
	status.Set("auth_enabled", true)
	mw := &fakeAuthMiddleware{enabled: true, status: status}
	if got := config.NewAuthenticationTools(mw).GetAuthStatus(); got != status {
		t.Fatalf("GetAuthStatus = %v", got)
	}
}
