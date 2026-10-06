package httpapp

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	authpkg "agenthub/fastmcp/auth"
	authdomain "agenthub/fastmcp/auth/domain/entities"
	authinterface "agenthub/fastmcp/auth/interface"
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/interface/api_controllers"
)

type fakeMemoryTokenRepo struct {
	tokens []any
}

func (m *fakeMemoryTokenRepo) CreateToken(ctx context.Context, data map[string]any) (any, error) {
	row := entities.NewOrderedMap[any]()
	row.Set("id", data["id"])
	row.Set("name", data["name"])
	row.Set("scopes", data["scopes"])
	row.Set("created_at", "2026-10-02T20:00:00Z")
	row.Set("expires_at", "2026-11-02T20:00:00Z")
	row.Set("rate_limit", data["rate_limit"])
	row.Set("is_active", true)
	m.tokens = append(m.tokens, row)
	return row, nil
}

func (m *fakeMemoryTokenRepo) GetUserTokens(ctx context.Context, userID string, skip, limit int) ([]any, error) {
	return m.tokens, nil
}

func (m *fakeMemoryTokenRepo) CountUserTokens(ctx context.Context, userID string) (int, error) {
	return len(m.tokens), nil
}

func (m *fakeMemoryTokenRepo) GetToken(ctx context.Context, tokenID, userID string) (any, error) {
	return nil, nil
}
func (m *fakeMemoryTokenRepo) GetTokenByID(ctx context.Context, tokenID string) (any, error) {
	return nil, nil
}
func (m *fakeMemoryTokenRepo) RevokeToken(ctx context.Context, tokenID, userID string) (bool, error) {
	return true, nil
}
func (m *fakeMemoryTokenRepo) ReactivateToken(ctx context.Context, tokenID, userID string) (bool, error) {
	return true, nil
}
func (m *fakeMemoryTokenRepo) DeleteToken(ctx context.Context, tokenID, userID string) (bool, error) {
	return true, nil
}
func (m *fakeMemoryTokenRepo) UpdateTokenUsage(ctx context.Context, tokenID string) (bool, error) {
	return true, nil
}
func (m *fakeMemoryTokenRepo) CleanupExpiredTokens(ctx context.Context, expiryDate time.Time) (int, error) {
	return 0, nil
}

type fakeTokenFactory struct {
	repo repositories.ITokenRepository
}

func (f fakeTokenFactory) CreateTokenFacade() (any, error) {
	return facades.NewTokenApplicationFacade(f.repo)
}

func TestMountTokenRoutesWithWiredFacade(t *testing.T) {
	os.Setenv("JWT_SECRET_KEY", "test-secret-key-32-bytes-minimum!!")
	prevUserUniversal := authinterface.GetCurrentUserUniversal
	testUID := "test-user-id-12345"
	testEmail := "tester@4genthub.com"
	authinterface.GetCurrentUserUniversal = func(ctx context.Context, token string) (*authdomain.User, error) {
		return &authdomain.User{ID: &testUID, Email: testEmail}, nil
	}
	defer func() { authinterface.GetCurrentUserUniversal = prevUserUniversal }()

	repo := &fakeMemoryTokenRepo{}
	tf := fakeTokenFactory{repo: repo}
	svc := services.NewFacadeService(nil, nil, nil, nil, nil, nil, tf)
	services.SetInstance(svc)

	mux := http.NewServeMux()
	deps := routeDeps{
		tokens: tokenRoutesAdapter{c: api_controllers.NewTokenAPIController(facadeServiceTokenProvider{})},
	}
	mountTokenRoutes(mux, deps)

	// Test GET /api/v2/tokens
	req := httptest.NewRequest(http.MethodGet, "/api/v2/tokens", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("GET /api/v2/tokens returned status %d: %s", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), `"data"`) || !strings.Contains(w.Body.String(), `"total"`) {
		t.Fatalf("GET /api/v2/tokens body missing data or total: %s", w.Body.String())
	}

	// Test POST /api/v2/tokens/generate
	body := `{"name":"test-token","scopes":["tasks:read"],"expires_in_days":30,"rate_limit":500}`
	req = httptest.NewRequest(http.MethodPost, "/api/v2/tokens/generate", strings.NewReader(body))
	req.Header.Set("Authorization", "Bearer valid-token")
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("POST /api/v2/tokens/generate returned status %d: %s", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), `"name":"test-token"`) || !strings.Contains(w.Body.String(), `"token"`) {
		t.Fatalf("POST /api/v2/tokens/generate body unexpected: %s", w.Body.String())
	}

	// Test GET /api/v2/tokens again to ensure listed
	req = httptest.NewRequest(http.MethodGet, "/api/v2/tokens", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("GET /api/v2/tokens returned status %d: %s", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), `"total":1`) {
		t.Fatalf("expected total:1, got: %s", w.Body.String())
	}
}

// TestMountTokenRoutesUnsetSecretNamesVariable pins the mint endpoint's failure with
// JWT_SECRET_KEY unset: the same 500 and the same actionable sentence as the REST
// dependency path, naming the variable instead of the bare "Failed to generate token".
func TestMountTokenRoutesUnsetSecretNamesVariable(t *testing.T) {
	t.Setenv("JWT_SECRET_KEY", "")
	prevUserUniversal := authinterface.GetCurrentUserUniversal
	testUID := "test-user-id-12345"
	testEmail := "tester@4genthub.com"
	authinterface.GetCurrentUserUniversal = func(ctx context.Context, token string) (*authdomain.User, error) {
		return &authdomain.User{ID: &testUID, Email: testEmail}, nil
	}
	defer func() { authinterface.GetCurrentUserUniversal = prevUserUniversal }()

	tf := fakeTokenFactory{repo: &fakeMemoryTokenRepo{}}
	services.SetInstance(services.NewFacadeService(nil, nil, nil, nil, nil, nil, tf))

	mux := http.NewServeMux()
	mountTokenRoutes(mux, routeDeps{
		tokens: tokenRoutesAdapter{c: api_controllers.NewTokenAPIController(facadeServiceTokenProvider{})},
	})

	req := httptest.NewRequest(http.MethodPost, "/api/v2/tokens/generate", strings.NewReader(`{"name":"t"}`))
	req.Header.Set("Authorization", "Bearer valid-token")
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	he := authpkg.JWTSecretNotSetError()
	if w.Code != he.StatusCode {
		t.Fatalf("status = %d, want %d: %s", w.Code, he.StatusCode, w.Body.String())
	}
	want := `{"detail":"` + he.Detail + `"}`
	if w.Body.String() != want {
		t.Fatalf("body = %s, want %s", w.Body.String(), want)
	}
	if strings.Contains(w.Body.String(), "Failed to generate token") {
		t.Fatalf("body still carries the bare mint phrasing: %s", w.Body.String())
	}
}

// TestMountTokenRoutesSiblingsCarryCause pins the sibling repair end to end through all
// three layers (controller -> adapter -> route) with JWT_SECRET_KEY unset: every REST token
// endpoint must answer the same 500 and the same actionable sentence as the mint endpoint,
// not the bare per-endpoint phrasing the route used to substitute after swallowing the
// cause.
func TestMountTokenRoutesSiblingsCarryCause(t *testing.T) {
	t.Setenv("JWT_SECRET_KEY", "")
	prevUserUniversal := authinterface.GetCurrentUserUniversal
	testUID := "test-user-id-12345"
	testEmail := "tester@4genthub.com"
	authinterface.GetCurrentUserUniversal = func(ctx context.Context, token string) (*authdomain.User, error) {
		return &authdomain.User{ID: &testUID, Email: testEmail}, nil
	}
	defer func() { authinterface.GetCurrentUserUniversal = prevUserUniversal }()

	tf := fakeTokenFactory{repo: &fakeMemoryTokenRepo{}}
	services.SetInstance(services.NewFacadeService(nil, nil, nil, nil, nil, nil, tf))

	mux := http.NewServeMux()
	mountTokenRoutes(mux, routeDeps{
		tokens: tokenRoutesAdapter{c: api_controllers.NewTokenAPIController(facadeServiceTokenProvider{})},
	})

	cases := []struct {
		name    string
		method  string
		path    string
		notBare string
	}{
		{"list", http.MethodGet, "/api/v2/tokens", "Failed to list tokens"},
		{"details", http.MethodGet, "/api/v2/tokens/abc", "Failed to get token details"},
		{"delete", http.MethodDelete, "/api/v2/tokens/abc", "Failed to delete token"},
		{"revoke", http.MethodPatch, "/api/v2/tokens/abc/revoke", "Failed to revoke token"},
		{"reactivate", http.MethodPatch, "/api/v2/tokens/abc/reactivate", "Failed to reactivate token"},
		{"rotate", http.MethodPost, "/api/v2/tokens/abc/rotate", "Failed to rotate token"},
		{"validate", http.MethodPost, "/api/v2/tokens/validate?token=abc", "Invalid token"},
		{"cleanup", http.MethodPost, "/api/v2/tokens/cleanup", "Failed to cleanup tokens"},
	}
	he := authpkg.JWTSecretNotSetError()
	want := `{"detail":"` + he.Detail + `"}`
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest(tc.method, tc.path, nil)
			req.Header.Set("Authorization", "Bearer valid-token")
			w := httptest.NewRecorder()
			mux.ServeHTTP(w, req)

			if w.Code != he.StatusCode {
				t.Fatalf("%s %s status = %d, want %d: %s", tc.method, tc.path, w.Code, he.StatusCode, w.Body.String())
			}
			if w.Body.String() != want {
				t.Fatalf("%s %s body = %s, want %s", tc.method, tc.path, w.Body.String(), want)
			}
			if strings.Contains(w.Body.String(), tc.notBare) {
				t.Fatalf("%s %s body still carries the bare phrasing %q: %s", tc.method, tc.path, tc.notBare, w.Body.String())
			}
		})
	}
}
