package middleware

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestRequestContextMiddlewareCapturesState(t *testing.T) {
	uid, typ, email := "u1", "jwt", "a@b.co"
	var got *string
	var scope map[string]any
	h := RequestContextMiddleware(func(*http.Request) AuthState {
		return AuthState{UserID: &uid, AuthType: &typ, AuthInfo: map[string]any{"email": email, "token_id": "t1"}}
	}, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		got = GetCurrentUserID(r.Context())
		scope = ScopeUser(r.Context())
		if !IsRequestAuthenticated(r.Context()) || *GetCurrentTokenID(r.Context()) != "t1" || *GetCurrentAuthMethod(r.Context()) != "jwt" {
			t.Fatalf("ctx: %v", GetAuthenticationContext(r.Context()))
		}
	}))
	h.ServeHTTP(httptest.NewRecorder(), httptest.NewRequest("POST", "/mcp", nil))
	if got == nil || *got != "u1" || scope["user_id"] != "u1" || scope["email"] != nil || scope["auth_method"] != "jwt" {
		t.Fatalf("got %v scope %v", got, scope)
	}
}

func TestRequestContextUnauthenticated(t *testing.T) {
	ctx := context.Background()
	if GetCurrentUserID(ctx) != nil || IsRequestAuthenticated(ctx) || GetCurrentUserContext(ctx) != nil || GetCurrentRequestContext(ctx) != nil {
		t.Fatal("expected empty context")
	}
}

func TestRequestContextAuthMethodFromInfo(t *testing.T) {
	uid, typ := "u1", "jwt"
	capture := func(info map[string]any) *RequestAuthContext {
		return CaptureAuthContextFromState(AuthState{UserID: &uid, AuthType: &typ, AuthInfo: info})
	}
	if c := capture(map[string]any{}); c.AuthMethod != nil || c.AuthInfo != nil {
		t.Fatalf("empty auth_info must be skipped: %+v", c)
	}
	if c := capture(map[string]any{"auth_method": "api_token"}); *c.AuthMethod != "api_token" {
		t.Fatalf("auth_method override lost: %+v", c)
	}
	if c := capture(map[string]any{"auth_method": 3}); c.AuthMethod != nil {
		t.Fatalf("non-string auth_method must be nil: %+v", c)
	}
	if c := capture(map[string]any{"x": 1}); *c.AuthMethod != "jwt" {
		t.Fatalf("auth_type default lost: %+v", c)
	}
}
