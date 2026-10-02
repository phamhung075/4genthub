package application

import (
	"context"
	"testing"

	"agenthub/fastmcp/auth/infrastructure"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

// fakeSupabase implements SupabaseAuthProvider for the adapter tests.
type fakeSupabase struct {
	signInResult infrastructure.SupabaseAuthResult
}

func (f *fakeSupabase) SignUp(ctx context.Context, email, password string, metadata *tmentities.OrderedMap[any]) infrastructure.SupabaseAuthResult {
	return infrastructure.SupabaseAuthResult{}
}
func (f *fakeSupabase) SignIn(ctx context.Context, email, password string) infrastructure.SupabaseAuthResult {
	return f.signInResult
}
func (f *fakeSupabase) SignOut(ctx context.Context, accessToken string) bool { return false }
func (f *fakeSupabase) RefreshSession(ctx context.Context, refreshToken string) infrastructure.SupabaseAuthResult {
	return infrastructure.SupabaseAuthResult{}
}
func (f *fakeSupabase) VerifyToken(ctx context.Context, accessToken string) infrastructure.SupabaseAuthResult {
	return infrastructure.SupabaseAuthResult{}
}
func (f *fakeSupabase) ResetPasswordRequest(ctx context.Context, email string) infrastructure.SupabaseAuthResult {
	return infrastructure.SupabaseAuthResult{}
}
func (f *fakeSupabase) UpdatePassword(ctx context.Context, accessToken, newPassword string) infrastructure.SupabaseAuthResult {
	return infrastructure.SupabaseAuthResult{}
}

// TestSupabaseFormatUserMatchesPython checks _format_user key order and values
// against the Python dict literal in auth_factory.py.
func TestSupabaseFormatUserMatchesPython(t *testing.T) {
	metadata := tmentities.NewOrderedMap[any]()
	metadata.Set("username", "alice")
	metadata.Set("full_name", "Alice A")

	user := tmentities.NewOrderedMap[any]()
	user.Set("id", "11111111-1111-1111-1111-111111111111")
	user.Set("email", "alice@example.com")
	user.Set("user_metadata", metadata)
	user.Set("confirmed_at", "2024-05-01T00:00:00Z")
	user.Set("created_at", "2024-01-01T00:00:00Z")

	got := supabaseFormatUser(user)
	wantKeys := []string{"id", "email", "username", "full_name", "email_verified", "created_at", "roles"}
	if got.Len() != len(wantKeys) {
		t.Fatalf("len = %d, want %d", got.Len(), len(wantKeys))
	}
	for i, k := range wantKeys {
		if got.Keys()[i] != k {
			t.Fatalf("key[%d] = %q, want %q", i, got.Keys()[i], k)
		}
	}
	if v, _ := got.Get("username"); v != "alice" {
		t.Fatalf("username = %v", v)
	}
	if v, _ := got.Get("email_verified"); v != true {
		t.Fatalf("email_verified = %v", v)
	}
	if v, _ := got.Get("created_at"); v != "2024-01-01T00:00:00Z" {
		t.Fatalf("created_at = %v", v)
	}
	roles, _ := got.Get("roles")
	if r, ok := roles.([]string); !ok || len(r) != 1 || r[0] != "user" {
		t.Fatalf("roles = %v", roles)
	}
}

// TestSupabaseSignInPropagatesResult mirrors SupabaseAuthAdapter.sign_in.
func TestSupabaseSignInPropagatesResult(t *testing.T) {
	session := tmentities.NewOrderedMap[any]()
	session.Set("access_token", "at")
	session.Set("refresh_token", "rt")
	adapter := NewSupabaseAuthAdapter(&fakeSupabase{signInResult: infrastructure.SupabaseAuthResult{
		Success: true, User: nil, Session: session, RequiresEmailVerification: true,
	}})
	r := adapter.SignIn(context.Background(), "a@b.c", "pw")
	if !r.Success || r.ExpiresIn != 900 {
		t.Fatalf("result = %+v", r)
	}
	if r.AccessToken == nil || *r.AccessToken != "at" || r.RefreshToken == nil || *r.RefreshToken != "rt" {
		t.Fatalf("tokens = %v %v", r.AccessToken, r.RefreshToken)
	}
	if !r.RequiresEmailVerification {
		t.Fatalf("requires_email_verification = false")
	}
}

// TestFactoryProviderFallback mirrors create_auth_service/get_current_provider.
func TestFactoryProviderFallback(t *testing.T) {
	t.Setenv("AUTH_PROVIDER", "bogus")
	f := NewAuthFactory(nil, nil, nil)
	if p := f.GetCurrentProvider(); p != AuthProviderLocal {
		t.Fatalf("provider = %q, want local", p)
	}
	local := &LocalAuthAdapter{}
	f.BuildLocal = func() AuthServiceInterface { return local }
	got := f.CreateAuthService(nil)
	if got != local {
		t.Fatalf("create_auth_service did not use local builder")
	}
	// Singleton cache: same pointer on second call.
	if f.CreateAuthService(nil) != local {
		t.Fatalf("create_auth_service did not cache")
	}
}

// TestIsProviderAvailableLocal checks the local branch (JWT_SECRET_KEY).
func TestIsProviderAvailableLocal(t *testing.T) {
	t.Setenv("JWT_SECRET_KEY", "secret")
	f := NewAuthFactory(nil, nil, nil)
	if !f.IsProviderAvailable(AuthProviderLocal) {
		t.Fatalf("local should be available when JWT_SECRET_KEY set")
	}
	t.Setenv("JWT_SECRET_KEY", "")
	if f.IsProviderAvailable(AuthProviderLocal) {
		t.Fatalf("local should be unavailable when JWT_SECRET_KEY empty")
	}
}
