package httpapp

// The API-token usage counters: a token the token path mints is authenticated through
// ValidateTokenUniversal, and the api_tokens row it belongs to must record the use.
//
// WHY THIS IS A DATABASE CASE AND NOT A FAKE: both claims are claims about a ROW - usage_count
// and last_used_at on the token that was just used - and a fake repository would only write this
// file's hypothesis back to its author. G3 is the gate this case settles: the deleted Python
// oracle advanced both fields on an authenticated API-token request (DualAuthMiddleware), and the
// Go port accepted the token while writing nothing, so the token UI read two fields that no writer
// touched. TokenRepository.UpdateTokenUsage is the ported writer; this case pins that the live
// path reaches it.
//
// IT SKIPS WITHOUT AGENTHUB_TEST_PG_URL, like its neighbours in this package, and the skip is loud
// on purpose because .github/workflows/ci.yml runs the suite with no database. To run it:
//
//	bash tools/testpg/start.sh
//	AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55451/postgres go test -count=1 -run TestAuthenticatedAPITokenRequestAdvancesItsUsageCounters ./fastmcp/server/httpapp/

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/auth/domain/services"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"
)

const apiTokenUsageTestSecret = "api-token-usage-test-secret"

func TestAuthenticatedAPITokenRequestAdvancesItsUsageCounters(t *testing.T) {
	sessions := newMissedNotificationAppEnv(t) // skips loudly without a database
	t.Setenv("AUTH_ENABLED", "true")
	t.Setenv("AUTH_PROVIDER", "keycloak")
	t.Setenv("JWT_SECRET_KEY", apiTokenUsageTestSecret)
	t.Setenv("KEYCLOAK_URL", "")
	ctx := context.Background()

	// The token the real creation path mints: TokenApplicationFacade.CreateAPIToken signs this JWT
	// (type api_token, jti = the row id) and stores sha256(jwt) in api_tokens
	// (token_application_facade.go:138-178).
	jwtService, err := services.NewJWTService(apiTokenUsageTestSecret, services.DefaultIssuer)
	if err != nil {
		t.Fatal(err)
	}
	userID := tmvo.NewUUIDv4()
	tokenID := "tok_" + userID[:16]
	jwtToken, err := jwtService.GenerateToken(userID, []string{"read"}, 30, tokenID, "mcp-server")
	if err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256([]byte(jwtToken))
	repo, err := infrarepos.NewTokenRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := repo.CreateToken(ctx, map[string]any{
		"id":         tokenID,
		"user_id":    userID,
		"name":       "usage counter",
		"token_hash": hex.EncodeToString(sum[:]),
		"scopes":     []any{"read"},
		"expires_at": time.Now().UTC().Add(30 * 24 * time.Hour),
	}); err != nil {
		t.Fatal(err)
	}

	before := apiTokenUsageRow(t, repo, tokenID)

	app, err := NewApp(ctx, sessions)
	if err != nil {
		t.Fatal(err)
	}
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/mcp",
		strings.NewReader(`{"jsonrpc":"2.0","id":1,"method":"tools/list"}`))
	req.Header.Set("Authorization", "Bearer "+jwtToken)
	app.Handler().ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("the minted API token must be accepted: POST /mcp = %d %s", rec.Code, rec.Body.String())
	}

	after := apiTokenUsageRow(t, repo, tokenID)
	if after.UsageCount != before.UsageCount+1 || after.LastUsedAt == nil {
		t.Fatalf("an authenticated API-token request must advance the row's counters: before "+
			"usage_count=%d last_used_at=%v, after usage_count=%d last_used_at=%v",
			before.UsageCount, before.LastUsedAt, after.UsageCount, after.LastUsedAt)
	}
}

func apiTokenUsageRow(t *testing.T, repo *infrarepos.TokenRepository, tokenID string) *database.APIToken {
	t.Helper()
	row, err := repo.GetTokenByID(context.Background(), tokenID)
	if err != nil || row == nil {
		t.Fatalf("GetTokenByID(%s) = %#v, %v", tokenID, row, err)
	}
	return row.(*database.APIToken)
}
