package repositories

// Tests for TokenRepository against a real PostgreSQL instance.

import (
	"context"
	"testing"
	"time"

	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

func tokenRepoTestNew(t *testing.T, sessions *database.SessionManager) *TokenRepository {
	t.Helper()
	repo, err := NewTokenRepository(sessions)
	if err != nil {
		t.Fatalf("NewTokenRepository: %v", err)
	}
	return repo
}

func tokenRepoTestData(user string) map[string]any {
	return map[string]any{
		"id":         tmvo.NewUUIDv4(),
		"user_id":    user,
		"name":       "token",
		"token_hash": "hash",
		"scopes":     []any{"read"},
		"expires_at": time.Now().UTC().Add(24 * time.Hour),
	}
}

func TestTokenRepoCRUD(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := tmvo.NewUUIDv4()
	repo := tokenRepoTestNew(t, sessions)

	data := tokenRepoTestData(user)
	createdAny, err := repo.CreateToken(ctx, data)
	if err != nil {
		t.Fatalf("CreateToken: %v", err)
	}
	created, ok := createdAny.(*database.APIToken)
	if !ok || created == nil {
		t.Fatalf("CreateToken = %#v", createdAny)
	}
	if created.ID != data["id"] || created.UserID != user {
		t.Fatalf("created = %+v", created)
	}
	if created.RateLimit != 1000 {
		t.Fatalf("rate_limit = %d", created.RateLimit)
	}
	if !created.IsActive {
		t.Fatal("is_active should default to true")
	}
	if string(created.TokenMetadata) != "{}" {
		t.Fatalf("token_metadata = %s", created.TokenMetadata)
	}

	// A missing primary key is an insert failure, swallowed to nil.
	if failed, err := repo.CreateToken(ctx, map[string]any{"user_id": user}); err != nil || failed != nil {
		t.Fatalf("CreateToken(missing id) = %#v, %v", failed, err)
	}

	got, err := repo.GetToken(ctx, data["id"].(string), user)
	if err != nil || got == nil {
		t.Fatalf("GetToken = %#v, %v", got, err)
	}
	if other, _ := repo.GetToken(ctx, data["id"].(string), tmvo.NewUUIDv4()); other != nil {
		t.Fatal("GetToken must be user-scoped")
	}
	byID, err := repo.GetTokenByID(ctx, data["id"].(string))
	if err != nil || byID == nil {
		t.Fatalf("GetTokenByID = %#v, %v", byID, err)
	}
	if missing, _ := repo.GetTokenByID(ctx, tmvo.NewUUIDv4()); missing != nil {
		t.Fatalf("GetTokenByID(missing) = %#v", missing)
	}

	count, err := repo.CountUserTokens(ctx, user)
	if err != nil || count != 1 {
		t.Fatalf("CountUserTokens = %d, %v", count, err)
	}

	// Usage increments the counter and stamps last_used_at.
	if ok, err := repo.UpdateTokenUsage(ctx, data["id"].(string)); err != nil || !ok {
		t.Fatalf("UpdateTokenUsage = %v, %v", ok, err)
	}
	used, _ := repo.GetTokenByID(ctx, data["id"].(string))
	usedToken := used.(*database.APIToken)
	if usedToken.UsageCount != 1 || usedToken.LastUsedAt == nil {
		t.Fatalf("usage = %+v", usedToken)
	}

	if ok, err := repo.RevokeToken(ctx, data["id"].(string), user); err != nil || !ok {
		t.Fatalf("RevokeToken = %v, %v", ok, err)
	}
	revoked, _ := repo.GetTokenByID(ctx, data["id"].(string))
	if revoked.(*database.APIToken).IsActive {
		t.Fatal("token should be inactive after revoke")
	}
	if ok, err := repo.ReactivateToken(ctx, data["id"].(string), user); err != nil || !ok {
		t.Fatalf("ReactivateToken = %v, %v", ok, err)
	}
	if ok, _ := repo.RevokeToken(ctx, tmvo.NewUUIDv4(), user); ok {
		t.Fatal("RevokeToken(missing) must be false")
	}

	if ok, err := repo.DeleteToken(ctx, data["id"].(string), user); err != nil || !ok {
		t.Fatalf("DeleteToken = %v, %v", ok, err)
	}
	if ok, _ := repo.DeleteToken(ctx, data["id"].(string), user); ok {
		t.Fatal("second DeleteToken must be false")
	}
}

func TestTokenRepoGetUserTokensOrdering(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := tmvo.NewUUIDv4()
	repo := tokenRepoTestNew(t, sessions)

	early, late := tokenRepoTestData(user), tokenRepoTestData(user)
	if _, err := repo.CreateToken(ctx, early); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.CreateToken(ctx, late); err != nil {
		t.Fatal(err)
	}
	base := time.Now().UTC().Add(-2 * time.Hour).Truncate(time.Microsecond)
	if _, err := repo.Update(ctx, early["id"].(string), NewKwargs("created_at", base)); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.Update(ctx, late["id"].(string), NewKwargs("created_at", base.Add(time.Hour))); err != nil {
		t.Fatal(err)
	}

	tokens, err := repo.GetUserTokens(ctx, user, 0, 100)
	if err != nil || len(tokens) != 2 {
		t.Fatalf("GetUserTokens = %d, %v", len(tokens), err)
	}
	first := tokens[0].(*database.APIToken)
	if first.ID != late["id"].(string) {
		t.Fatalf("ordering = %q first, want %q", first.ID, late["id"])
	}
	paged, err := repo.GetUserTokens(ctx, user, 1, 100)
	if err != nil || len(paged) != 1 || paged[0].(*database.APIToken).ID != early["id"].(string) {
		t.Fatalf("paged = %+v, %v", paged, err)
	}
}

func TestTokenRepoCleanupExpired(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := tmvo.NewUUIDv4()
	repo := tokenRepoTestNew(t, sessions)

	expired := tokenRepoTestData(user)
	expired["expires_at"] = time.Now().UTC().Add(-48 * time.Hour)
	future := tokenRepoTestData(user)
	if _, err := repo.CreateToken(ctx, expired); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.CreateToken(ctx, future); err != nil {
		t.Fatal(err)
	}

	count, err := repo.CleanupExpiredTokens(ctx, time.Now().UTC())
	if err != nil || count != 1 {
		t.Fatalf("CleanupExpiredTokens = %d, %v", count, err)
	}
	if gone, _ := repo.GetTokenByID(ctx, expired["id"].(string)); gone != nil {
		t.Fatal("expired token should be deleted")
	}
	if kept, _ := repo.GetTokenByID(ctx, future["id"].(string)); kept == nil {
		t.Fatal("future token should remain")
	}
}
