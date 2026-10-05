package authinterface

import (
	"context"
	"errors"
	"testing"

	authpkg "agenthub/fastmcp/auth"
	authEntities "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities"
)

// Expectations mirror agenthub_main/src/fastmcp/auth/interface/fastapi_auth.py.

func withProvider(t *testing.T, provider string) {
	t.Helper()
	prev := authProvider
	authProvider = provider
	t.Cleanup(func() { authProvider = prev })
}

func TestGetCurrentUserKeycloakSuccess(t *testing.T) {
	withProvider(t, "keycloak")
	id := "11111111-1111-1111-1111-111111111111"
	want := &authEntities.User{ID: &id, Email: "k@example.com", Username: "k"}
	prev := GetCurrentUserUniversal
	GetCurrentUserUniversal = func(context.Context, string) (*authEntities.User, error) { return want, nil }
	t.Cleanup(func() { GetCurrentUserUniversal = prev })

	tok := "abc"
	got, err := GetCurrentUser(context.Background(), &tok, nil)
	if err != nil || got != want {
		t.Fatalf("got %v, %v", got, err)
	}
}

func TestGetCurrentUserKeycloakDevFallback(t *testing.T) {
	withProvider(t, "keycloak")
	prev := GetCurrentUserUniversal
	GetCurrentUserUniversal = func(context.Context, string) (*authEntities.User, error) {
		return nil, errors.New("keycloak down")
	}
	t.Cleanup(func() { GetCurrentUserUniversal = prev })
	t.Setenv("ENV", "development")

	tok := "abc"
	got, err := GetCurrentUser(context.Background(), &tok, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.ID == nil || *got.ID != "dev-user-001" || got.Email != "dev@example.com" ||
		got.Username != "dev-user" || got.PasswordHash != "dev-hash" {
		t.Fatalf("unexpected dev user: %+v", got)
	}
}

func TestGetCurrentUserKeycloakProductionRaises(t *testing.T) {
	withProvider(t, "keycloak")
	sentinel := errors.New("keycloak down")
	prev := GetCurrentUserUniversal
	GetCurrentUserUniversal = func(context.Context, string) (*authEntities.User, error) { return nil, sentinel }
	t.Cleanup(func() { GetCurrentUserUniversal = prev })
	t.Setenv("ENV", "production")

	tok := "abc"
	if _, err := GetCurrentUser(context.Background(), &tok, nil); !errors.Is(err, sentinel) {
		t.Fatalf("expected sentinel, got %v", err)
	}
}

func TestGetCurrentUserDefaultFallback(t *testing.T) {
	withProvider(t, "something-else")
	got, err := GetCurrentUser(context.Background(), nil, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.ID == nil || *got.ID != "test-user-001" || got.Email != "test@example.com" ||
		got.Username != "test-user" || got.PasswordHash != "test-hash" {
		t.Fatalf("unexpected test user: %+v", got)
	}
}

func TestGetCurrentUserSupabaseRequiresCredentials(t *testing.T) {
	withProvider(t, "supabase")
	if _, err := GetCurrentUser(context.Background(), nil, nil); err == nil {
		t.Fatal("expected error")
	} else if he, ok := err.(*authpkg.HTTPException); !ok || he.StatusCode != 401 || he.Detail != "Authentication required" {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestGetOptionalUser(t *testing.T) {
	withProvider(t, "keycloak")
	prev := GetCurrentUserUniversal
	GetCurrentUserUniversal = func(context.Context, string) (*authEntities.User, error) {
		return nil, errors.New("nope")
	}
	t.Cleanup(func() { GetCurrentUserUniversal = prev })
	t.Setenv("ENV", "production")

	if got := GetOptionalUser(context.Background(), nil, nil); got != nil {
		t.Fatalf("nil credentials should give nil, got %+v", got)
	}
	tok := "abc"
	if got := GetOptionalUser(context.Background(), &tok, nil); got != nil {
		t.Fatalf("failing auth should give nil, got %+v", got)
	}
}

func TestRequireRolesDelegates(t *testing.T) {
	withProvider(t, "something-else")
	got, err := RequireRoles(context.Background(), []string{"admin"}, nil, nil)
	if err != nil || got == nil || *got.ID != "test-user-001" {
		t.Fatalf("got %v, %v", got, err)
	}
}

func TestGetCurrentUserFromMiddlewareNoContext(t *testing.T) {
	_, err := GetCurrentUserFromMiddleware(context.Background(), &MiddlewareAuthState{}, nil)
	he, ok := err.(*authpkg.HTTPException)
	if !ok || he.StatusCode != 401 || he.Detail != "Authentication required - no user context found" {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestOrderedString(t *testing.T) {
	m := &entities.OrderedMap[any]{}
	m.Set("email", "a@b.com")
	if got := orderedString(m, "email"); got != "a@b.com" {
		t.Fatalf("got %q", got)
	}
	if got := orderedString(nil, "email"); got != "" {
		t.Fatalf("got %q", got)
	}
}
