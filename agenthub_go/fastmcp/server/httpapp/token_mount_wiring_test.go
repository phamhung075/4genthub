package httpapp

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

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
