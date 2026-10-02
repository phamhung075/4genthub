package repositories

import (
	"context"
	"database/sql"
	"fmt"
	"net/url"
	"os"
	"testing"
	"time"

	authEntities "agenthub/fastmcp/auth/domain/entities"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// newAuthRepoEnv creates a throwaway database with all tables (auth models included via
// their init registration) and returns a session manager over it.
func newAuthRepoEnv(t *testing.T) *database.SessionManager {
	t.Helper()
	admin := os.Getenv("AGENTHUB_TEST_PG_URL")
	if admin == "" {
		t.Skip("AGENTHUB_TEST_PG_URL not set")
	}
	adm, err := sql.Open("pgx", admin)
	if err != nil {
		t.Fatal(err)
	}
	name := fmt.Sprintf("agenthub_auth_%d", time.Now().UnixNano())
	if _, err := adm.Exec("CREATE DATABASE " + name); err != nil {
		t.Fatal(err)
	}
	adm.Close()
	u, _ := url.Parse(admin)
	u.Path = "/" + name
	env := map[string]string{"DATABASE_TYPE": "postgresql", "DATABASE_HOST": "x", "DATABASE_PASSWORD": "x"}
	database.ResetInstance()
	deps := database.Deps{
		Getenv: func(k string) (string, bool) { v, ok := env[k]; return v, ok },
		Sleep:  func(time.Duration) {},
		Open: func(string, database.EngineOptions) (*sql.DB, error) {
			return database.PgxOpener(u.String(), database.EngineOptions{PoolSize: 4, MaxOverflow: 4, PoolRecycle: 60})
		},
	}
	cfg, err := database.GetInstance(context.Background(), deps)
	if err != nil {
		t.Fatal(err)
	}
	if err := cfg.CreateTables(context.Background()); err != nil {
		t.Fatal(err)
	}
	database.SetupTimestampEvents()
	t.Cleanup(func() {
		database.ResetInstance()
		adm, err := sql.Open("pgx", admin)
		if err == nil {
			_, _ = adm.Exec("DROP DATABASE IF EXISTS " + name + " WITH (FORCE)")
			adm.Close()
		}
	})
	return database.NewSessionManager(cfg)
}

func authTestNewUser(t *testing.T, email, username string) *authEntities.User {
	t.Helper()
	u, err := authEntities.NewUser(authEntities.User{Email: email, Username: username, PasswordHash: "hash-1"})
	if err != nil {
		t.Fatalf("NewUser: %v", err)
	}
	return u
}

func TestAuthUserRepositorySaveAndRead(t *testing.T) {
	env := newAuthRepoEnv(t)
	repo, err := NewUserRepository(env)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()

	saved, err := repo.Save(ctx, authTestNewUser(t, "alice@example.com", "alice"))
	if err != nil {
		t.Fatalf("Save: %v", err)
	}
	if saved.ID == nil || *saved.ID == "" {
		t.Fatal("Save did not set an id")
	}
	if saved.Status != authEntities.UserStatusPendingVerification {
		t.Fatalf("status = %q", saved.Status)
	}

	got, err := repo.GetByID(ctx, *saved.ID)
	if err != nil || got == nil {
		t.Fatalf("GetByID = %v, %v", got, err)
	}
	if got.Email != "alice@example.com" || got.Username != "alice" || got.PasswordHash != "hash-1" {
		t.Fatalf("unexpected user: %+v", got)
	}
	if len(got.Roles) != 1 || got.Roles[0] != authEntities.UserRoleUser {
		t.Fatalf("roles = %v", got.Roles)
	}
	if len(got.Metadata) != 0 {
		t.Fatalf("metadata = %v", got.Metadata)
	}

	direct, err := repo.FindByID(ctx, *saved.ID)
	if err != nil || direct == nil {
		t.Fatalf("FindByID = %v, %v", direct, err)
	}
	// GetByEmail lowercases the lookup.
	byEmail, err := repo.GetByEmail(ctx, "ALICE@EXAMPLE.COM")
	if err != nil || byEmail == nil || byEmail.Username != "alice" {
		t.Fatalf("GetByEmail = %v, %v", byEmail, err)
	}
	byName, err := repo.GetByUsername(ctx, "alice")
	if err != nil || byName == nil {
		t.Fatalf("GetByUsername = %v, %v", byName, err)
	}
	if ok, _ := repo.ExistsByEmail(ctx, "alice@example.com"); !ok {
		t.Fatal("ExistsByEmail = false")
	}
	if ok, _ := repo.ExistsByUsername(ctx, "nobody"); ok {
		t.Fatal("ExistsByUsername(nobody) = true")
	}
	if missing, _ := repo.GetByID(ctx, "00000000-0000-0000-0000-0000000000ff"); missing != nil {
		t.Fatalf("GetByID(unknown) = %v", missing)
	}
	if missing, _ := repo.GetByEmail(ctx, "nobody@example.com"); missing != nil {
		t.Fatalf("GetByEmail(unknown) = %v", missing)
	}
}

func TestAuthUserRepositorySaveUpdateSkipsSensitiveFields(t *testing.T) {
	env := newAuthRepoEnv(t)
	repo, _ := NewUserRepository(env)
	ctx := context.Background()

	saved, err := repo.Save(ctx, authTestNewUser(t, "bob@example.com", "bob"))
	if err != nil {
		t.Fatal(err)
	}
	fullName := "Bob B"
	updated, err := repo.Save(ctx, &authEntities.User{
		ID:                  saved.ID,
		Email:               "bob@example.com",
		Username:            "bob",
		PasswordHash:        "hash-2",                  // to_dict excludes password_hash, so this must not change
		BaseTimestampEntity: saved.BaseTimestampEntity, // to_dict writes created_at back, which is NOT NULL
		FullName:            &fullName,
		Status:              authEntities.UserStatusActive,
		Roles:               []authEntities.UserRole{authEntities.UserRoleAdmin},
	})
	if err != nil {
		t.Fatalf("Save(update): %v", err)
	}
	if updated.ID == nil || *updated.ID != *saved.ID {
		t.Fatalf("update changed id: %v", updated.ID)
	}
	got, err := repo.GetByID(ctx, *saved.ID)
	if err != nil || got == nil {
		t.Fatal(err)
	}
	if got.PasswordHash != "hash-1" {
		t.Fatalf("password_hash updated via save: %q", got.PasswordHash)
	}
	if got.FullName == nil || *got.FullName != "Bob B" {
		t.Fatalf("full_name = %v", got.FullName)
	}
	if got.Status != authEntities.UserStatusActive {
		t.Fatalf("status = %q", got.Status)
	}
	if len(got.Roles) != 1 || got.Roles[0] != authEntities.UserRoleAdmin {
		t.Fatalf("roles = %v", got.Roles)
	}
}

func TestAuthUserRepositoryDuplicateEmail(t *testing.T) {
	env := newAuthRepoEnv(t)
	repo, _ := NewUserRepository(env)
	ctx := context.Background()

	if _, err := repo.Save(ctx, authTestNewUser(t, "dup@example.com", "dup1")); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.Save(ctx, authTestNewUser(t, "dup@example.com", "dup2")); err == nil {
		t.Fatal("expected an integrity error for a duplicate email")
	}
}

func TestAuthUserRepositoryListAndSearch(t *testing.T) {
	env := newAuthRepoEnv(t)
	repo, _ := NewUserRepository(env)
	ctx := context.Background()

	for _, u := range []struct{ email, name string }{
		{"carol@example.com", "carol"},
		{"dave@work.com", "dave"},
		{"erin@example.com", "erin"},
	} {
		if _, err := repo.Save(ctx, authTestNewUser(t, u.email, u.name)); err != nil {
			t.Fatal(err)
		}
	}
	all, err := repo.ListAll(ctx, 100, 0, nil)
	if err != nil || len(all) != 3 {
		t.Fatalf("ListAll = %d, %v", len(all), err)
	}
	page, err := repo.ListAll(ctx, 1, 1, nil)
	if err != nil || len(page) != 1 {
		t.Fatalf("ListAll(limit=1,offset=1) = %d, %v", len(page), err)
	}
	// status filter applies the stored status (all are pending_verification).
	filtered, err := repo.ListAll(ctx, 100, 0, strPtr("pending_verification"))
	if err != nil || len(filtered) != 3 {
		t.Fatalf("ListAll(status) = %d, %v", len(filtered), err)
	}
	none, err := repo.ListAll(ctx, 100, 0, strPtr("active"))
	if err != nil || len(none) != 0 {
		t.Fatalf("ListAll(active) = %d, %v", len(none), err)
	}

	found, err := repo.Search(ctx, "EXAMPLE.COM", 50)
	if err != nil || len(found) != 2 {
		t.Fatalf("Search = %d, %v", len(found), err)
	}
	limited, err := repo.Search(ctx, "example", 1)
	if err != nil || len(limited) != 1 {
		t.Fatalf("Search(limit=1) = %d, %v", len(limited), err)
	}
	if empty, _ := repo.Search(ctx, "zzz", 50); len(empty) != 0 {
		t.Fatalf("Search(zzz) = %d", len(empty))
	}
}

func strPtr(s string) *string { return &s }

func orderedMetadata(key, value string) *tmentities.OrderedMap[any] {
	m := tmentities.NewOrderedMap[any]()
	m.Set(key, value)
	return m
}

func TestAuthUserRepositoryDeleteAndResetToken(t *testing.T) {
	env := newAuthRepoEnv(t)
	repo, _ := NewUserRepository(env)
	ctx := context.Background()

	token := "reset-token-1"
	u := authTestNewUser(t, "frank@example.com", "frank")
	u.PasswordResetToken = &token
	saved, err := repo.Save(ctx, u)
	if err != nil {
		t.Fatal(err)
	}
	// to_dict excludes password_reset_token, so create writes it but updates do not.
	byToken, err := repo.GetByResetToken(ctx, token)
	if err != nil || byToken == nil || byToken.Username != "frank" {
		t.Fatalf("GetByResetToken = %v, %v", byToken, err)
	}

	deleted, err := repo.Delete(ctx, *saved.ID)
	if err != nil || !deleted {
		t.Fatalf("Delete = %v, %v", deleted, err)
	}
	deleted, err = repo.Delete(ctx, *saved.ID)
	if err != nil || deleted {
		t.Fatalf("Delete(again) = %v, %v", deleted, err)
	}
}

func authTestCreateUser(t *testing.T, repo *UserRepository, ctx context.Context, email, username string) *authEntities.User {
	t.Helper()
	u, err := repo.Save(ctx, authTestNewUser(t, email, username))
	if err != nil {
		t.Fatalf("Save user: %v", err)
	}
	return u
}

func TestAuthTokenBalanceRepository(t *testing.T) {
	env := newAuthRepoEnv(t)
	users, _ := NewUserRepository(env)
	repo, err := NewTokenBalanceRepository(env)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	user := authTestCreateUser(t, users, ctx, "balance@example.com", "balance")
	uid := *user.ID

	if missing, err := repo.GetBalance(ctx, uid); err != nil || missing != nil {
		t.Fatalf("GetBalance(before) = %v, %v", missing, err)
	}
	created, err := repo.CreateBalance(ctx, uid, 10000, 10000)
	if err != nil {
		t.Fatalf("CreateBalance: %v", err)
	}
	if created["available_tokens"] != int64(10000) || created["monthly_quota"] != int64(10000) {
		t.Fatalf("CreateBalance = %v", created)
	}
	if _, err := repo.CreateBalance(ctx, uid, 1, 1); err == nil {
		t.Fatal("expected an integrity error for a duplicate balance")
	}

	ok, err := repo.ConsumeTokens(ctx, uid, 300)
	if err != nil || !ok {
		t.Fatalf("ConsumeTokens = %v, %v", ok, err)
	}
	if ok, _ := repo.ConsumeTokens(ctx, uid, 1000000); ok {
		t.Fatal("ConsumeTokens(insufficient) = true")
	}
	if _, err := repo.ConsumeTokens(ctx, uid, 0); err == nil {
		t.Fatal("ConsumeTokens(0) did not raise")
	}
	if _, err := repo.AddTokens(ctx, uid, -1); err == nil {
		t.Fatal("AddTokens(-1) did not raise")
	}
	if _, err := repo.UpdateQuota(ctx, uid, -5); err == nil {
		t.Fatal("UpdateQuota(-5) did not raise")
	}
	if ok, err := repo.AddTokens(ctx, uid, 50); err != nil || !ok {
		t.Fatalf("AddTokens = %v, %v", ok, err)
	}
	if ok, err := repo.UpdateQuota(ctx, uid, 20000); err != nil || !ok {
		t.Fatalf("UpdateQuota = %v, %v", ok, err)
	}
	balance, _ := repo.GetBalance(ctx, uid)
	if balance["available_tokens"] != int64(9750) || balance["monthly_quota"] != int64(20000) {
		t.Fatalf("balance after consume/add = %v", balance)
	}
	if balance["tokens_consumed_today"] != int64(300) || balance["total_tokens_consumed"] != int64(300) {
		t.Fatalf("counters = %v", balance)
	}

	stats, err := repo.GetUsageStats(ctx, uid)
	if err != nil || stats == nil {
		t.Fatalf("GetUsageStats = %v, %v", stats, err)
	}
	// consumed = 20000 - 9750 = 10250 -> 51.25%
	if stats["utilization_percentage"] != 51.25 {
		t.Fatalf("utilization = %v", stats["utilization_percentage"])
	}

	if ok, err := repo.ResetDailyConsumption(ctx, uid); err != nil || !ok {
		t.Fatalf("ResetDailyConsumption = %v, %v", ok, err)
	}
	balance, _ = repo.GetBalance(ctx, uid)
	if balance["tokens_consumed_today"] != int64(0) {
		t.Fatalf("tokens_consumed_today = %v", balance["tokens_consumed_today"])
	}

	if ok, err := repo.ResetMonthlyQuota(ctx, uid); err != nil || !ok {
		t.Fatalf("ResetMonthlyQuota = %v, %v", ok, err)
	}
	balance, _ = repo.GetBalance(ctx, uid)
	if balance["available_tokens"] != int64(20000) || balance["tokens_consumed_this_month"] != int64(0) {
		t.Fatalf("after reset = %v", balance)
	}

	// Auto reset: push next_reset_at into the past.
	if err := env.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, `UPDATE user_token_balances SET next_reset_at = now() - interval '1 day' WHERE user_id = $1`, uid)
		return err
	}); err != nil {
		t.Fatal(err)
	}
	reset, err := repo.CheckAndAutoReset(ctx, uid)
	if err != nil || !reset {
		t.Fatalf("CheckAndAutoReset = %v, %v", reset, err)
	}
	if again, _ := repo.CheckAndAutoReset(ctx, uid); again {
		t.Fatal("CheckAndAutoReset ran twice")
	}
	if missing, _ := repo.GetBalance(ctx, "00000000-0000-0000-0000-0000000000ff"); missing != nil {
		t.Fatalf("GetBalance(unknown) = %v", missing)
	}
	if ok, _ := repo.ConsumeTokens(ctx, "00000000-0000-0000-0000-0000000000ff", 1); ok {
		t.Fatal("ConsumeTokens(unknown) = true")
	}
	if ok, _ := repo.AddTokens(ctx, "00000000-0000-0000-0000-0000000000ff", 1); ok {
		t.Fatal("AddTokens(unknown) = true")
	}
	if ok, _ := repo.ResetMonthlyQuota(ctx, "00000000-0000-0000-0000-0000000000ff"); ok {
		t.Fatal("ResetMonthlyQuota(unknown) = true")
	}
	if ok, _ := repo.ResetDailyConsumption(ctx, "00000000-0000-0000-0000-0000000000ff"); ok {
		t.Fatal("ResetDailyConsumption(unknown) = true")
	}
	if stats, _ := repo.GetUsageStats(ctx, "00000000-0000-0000-0000-0000000000ff"); stats != nil {
		t.Fatalf("GetUsageStats(unknown) = %v", stats)
	}
}

func TestAuthEmailTokenRepository(t *testing.T) {
	env := newAuthRepoEnv(t)
	repo, err := NewEmailTokenRepository(env)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	now := time.Now().UTC()

	token := &EmailToken{
		Token: "tok-1", Email: "e@example.com", TokenType: "verification", TokenHash: "h1",
		ExpiresAt: now.Add(time.Hour), CreatedAt: now,
	}
	if ok, err := repo.SaveToken(ctx, token); err != nil || !ok {
		t.Fatalf("SaveToken = %v, %v", ok, err)
	}
	got, err := repo.GetToken(ctx, "tok-1")
	if err != nil || got == nil || got.Email != "e@example.com" || got.IsUsed {
		t.Fatalf("GetToken = %v, %v", got, err)
	}
	if missing, _ := repo.GetToken(ctx, "nope"); missing != nil {
		t.Fatalf("GetToken(unknown) = %v", missing)
	}
	// Duplicate primary key is swallowed into false.
	if ok, _ := repo.SaveToken(ctx, token); ok {
		t.Fatal("SaveToken(duplicate) = true")
	}

	used := &EmailToken{Token: "tok-2", Email: "e@example.com", TokenType: "password_reset", TokenHash: "h2",
		ExpiresAt: now.Add(time.Hour), CreatedAt: now, IsUsed: true}
	if ok, err := repo.SaveToken(ctx, used); err != nil || !ok {
		t.Fatalf("SaveToken(used) = %v, %v", ok, err)
	}
	unused, err := repo.GetTokensByEmail(ctx, "e@example.com", nil, false)
	if err != nil || len(unused) != 1 || unused[0].Token != "tok-1" {
		t.Fatalf("GetTokensByEmail(include_used=false) = %v, %v", unused, err)
	}
	all, err := repo.GetTokensByEmail(ctx, "e@example.com", nil, true)
	if err != nil || len(all) != 2 {
		t.Fatalf("GetTokensByEmail(include_used=true) = %d, %v", len(all), err)
	}
	verification := "verification"
	onlyVerification, err := repo.GetTokensByEmail(ctx, "e@example.com", &verification, true)
	if err != nil || len(onlyVerification) != 1 || onlyVerification[0].Token != "tok-1" {
		t.Fatalf("GetTokensByEmail(type) = %v, %v", onlyVerification, err)
	}

	if ok, err := repo.MarkTokenUsed(ctx, "tok-1", nil); err != nil || !ok {
		t.Fatalf("MarkTokenUsed = %v, %v", ok, err)
	}
	got, _ = repo.GetToken(ctx, "tok-1")
	if !got.IsUsed || got.UsedAt == nil {
		t.Fatalf("after MarkTokenUsed = %+v", got)
	}

	if ok, err := repo.DeleteToken(ctx, "tok-2"); err != nil || !ok {
		t.Fatalf("DeleteToken = %v, %v", ok, err)
	}
	if ok, _ := repo.DeleteToken(ctx, "tok-2"); ok {
		t.Fatal("DeleteToken(again) = true")
	}
	if ok, _ := repo.DeleteToken(ctx, "nope"); ok {
		t.Fatal("DeleteToken(unknown) = true")
	}
}

func TestAuthEmailTokenValidateAndStats(t *testing.T) {
	env := newAuthRepoEnv(t)
	repo, _ := NewEmailTokenRepository(env)
	ctx := context.Background()
	now := time.Now().UTC()

	valid := &EmailToken{Token: "v", Email: "v@example.com", TokenType: "verification", TokenHash: "h",
		ExpiresAt: now.Add(time.Hour), CreatedAt: now, Metadata: orderedMetadata("source", "test")}
	if _, err := repo.SaveToken(ctx, valid); err != nil {
		t.Fatal(err)
	}
	validated, err := repo.ValidateToken(ctx, "v", "v@example.com", "verification", true)
	if err != nil || validated == nil || !validated.IsUsed || validated.UsedAt == nil {
		t.Fatalf("ValidateToken = %v, %v", validated, err)
	}
	stored, _ := repo.GetToken(ctx, "v")
	if stored.Metadata == nil {
		t.Fatal("metadata was not persisted")
	} else if v, _ := stored.Metadata.Get("source"); v != "test" {
		t.Fatalf("metadata = %v", stored.Metadata)
	}
	if again, _ := repo.ValidateToken(ctx, "v", "v@example.com", "verification", true); again != nil {
		t.Fatal("ValidateToken(used) != nil")
	}

	expired := &EmailToken{Token: "exp", Email: "exp@example.com", TokenType: "verification", TokenHash: "h",
		ExpiresAt: now.Add(-time.Hour), CreatedAt: now}
	if _, err := repo.SaveToken(ctx, expired); err != nil {
		t.Fatal(err)
	}
	if obj, _ := repo.ValidateToken(ctx, "exp", "exp@example.com", "verification", true); obj != nil {
		t.Fatal("ValidateToken(expired) != nil")
	}
	if obj, _ := repo.ValidateToken(ctx, "v", "other@example.com", "verification", true); obj != nil {
		t.Fatal("ValidateToken(wrong email) != nil")
	}
	if obj, _ := repo.ValidateToken(ctx, "v", "v@example.com", "password_reset", true); obj != nil {
		t.Fatal("ValidateToken(wrong type) != nil")
	}

	// A fresh, unused token plus the expired one: total 3, used 1, expired 1.
	fresh := &EmailToken{Token: "fresh", Email: "fresh@example.com", TokenType: "password_reset", TokenHash: "h",
		ExpiresAt: now.Add(24 * time.Hour), CreatedAt: now}
	if _, err := repo.SaveToken(ctx, fresh); err != nil {
		t.Fatal(err)
	}
	stats, err := repo.GetTokenStats(ctx)
	if err != nil || stats == nil {
		t.Fatalf("GetTokenStats = %v, %v", stats, err)
	}
	if v, _ := stats.Get("total_tokens"); v != int64(3) {
		t.Fatalf("total_tokens = %v", v)
	}
	if v, _ := stats.Get("used_tokens"); v != int64(1) {
		t.Fatalf("used_tokens = %v", v)
	}
	if v, _ := stats.Get("expired_tokens"); v != int64(1) {
		t.Fatalf("expired_tokens = %v", v)
	}
	if v, _ := stats.Get("active_tokens"); v != int64(1) {
		t.Fatalf("active_tokens = %v", v)
	}
	if v, _ := stats.Get("verification_tokens"); v != int64(2) { // "v" and "exp"
		t.Fatalf("verification_tokens = %v", v)
	}
	if v, _ := stats.Get("reset_tokens"); v != int64(1) {
		t.Fatalf("reset_tokens = %v", v)
	}
	if v, _ := stats.Get("usage_rate"); v != float64(1)/float64(3)*100 {
		t.Fatalf("usage_rate = %v", v)
	}
}

func TestAuthEmailTokenCleanup(t *testing.T) {
	env := newAuthRepoEnv(t)
	repo, _ := NewEmailTokenRepository(env)
	ctx := context.Background()
	now := time.Now().UTC()

	if _, err := repo.SaveToken(ctx, &EmailToken{Token: "old", Email: "o@example.com", TokenType: "verification",
		TokenHash: "h", ExpiresAt: now.Add(-time.Hour), CreatedAt: now}); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.SaveToken(ctx, &EmailToken{Token: "keep", Email: "k@example.com", TokenType: "verification",
		TokenHash: "h", ExpiresAt: now.Add(time.Hour), CreatedAt: now}); err != nil {
		t.Fatal(err)
	}
	deleted, err := repo.CleanupExpiredTokens(ctx, 7)
	if err != nil || deleted != 1 {
		t.Fatalf("CleanupExpiredTokens = %d, %v", deleted, err)
	}
	if obj, _ := repo.GetToken(ctx, "old"); obj != nil {
		t.Fatal("expired token was not deleted")
	}
	if obj, _ := repo.GetToken(ctx, "keep"); obj == nil {
		t.Fatal("fresh token was deleted")
	}
}
