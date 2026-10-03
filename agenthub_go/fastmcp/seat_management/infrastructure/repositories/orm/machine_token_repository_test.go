package orm

import (
	"context"
	"database/sql/driver"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgconn"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
)

var machineTokenCols = []string{"id", "user_id", "machine_id", "token_hash", "created_at", "revoked_at"}

const (
	testMachineTokenID   = "66666666-6666-4666-8666-666666666666"
	testMachineIDHome    = "pc-home"
	testMachineTokenHash = "sha256-hex-of-the-bearer-token"
)

func TestMachineTokenCreateStoresOnlyTheHashAndMapsUniqueViolation(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC()

	var insertArgs []driver.Value
	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		if strings.Contains(q, `INSERT INTO "machine_tokens"`) {
			insertArgs = args
			return machineTokenCols, [][]driver.Value{
				fakeRow(testMachineTokenID, testUser, testMachineIDHome, testMachineTokenHash, now, nil),
			}, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMMachineTokenRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatalf("NewORMMachineTokenRepository: %v", err)
	}

	got, err := repo.Create(ctx, testUser, testMachineIDHome, testMachineTokenHash)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if got == nil {
		t.Fatal("Create returned a nil token")
	}
	if got.ID != testMachineTokenID || got.UserID != testUser || got.MachineID != testMachineIDHome || got.TokenHash != testMachineTokenHash {
		t.Fatalf("Create = %+v", got)
	}
	if !got.CreatedAt.Equal(now) {
		t.Fatalf("Create CreatedAt = %v, want %v", got.CreatedAt, now)
	}
	if got.RevokedAt != nil {
		t.Fatalf("Create RevokedAt = %v, want nil", got.RevokedAt)
	}

	inserted := false
	for _, q := range f.recorded() {
		if strings.Contains(q, `INSERT INTO "machine_tokens"`) {
			inserted = true
			if !strings.Contains(q, `"token_hash"`) {
				t.Fatalf("insert does not store the hash: %s", q)
			}
		}
	}
	if !inserted {
		t.Fatalf("no insert recorded: %v", f.recorded())
	}
	sawHash := false
	for _, a := range insertArgs {
		if s, ok := a.(string); ok && s == testMachineTokenHash {
			sawHash = true
		}
	}
	if !sawHash {
		t.Fatalf("insert did not bind the token hash: %v", insertArgs)
	}

	// The partial unique index uq_machine_tokens_active rejects a second active token.
	f2 := &fakeDriver{}
	f2.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		if strings.Contains(q, `INSERT INTO "machine_tokens"`) {
			return nil, nil, &pgconn.PgError{Code: "23505", Message: "duplicate key value violates unique constraint"}
		}
		return nil, nil, nil
	}
	repo2, err := NewORMMachineTokenRepository(newFakeManager(t, f2))
	if err != nil {
		t.Fatalf("NewORMMachineTokenRepository: %v", err)
	}
	if _, err := repo2.Create(ctx, testUser, testMachineIDHome, testMachineTokenHash); !errors.Is(err, domainrepo.ErrMachineTokenExists) {
		t.Fatalf("Create(unique violation) = %v, want ErrMachineTokenExists", err)
	}
}

func TestMachineTokenRevokeIsScopedToUserAndMachine(t *testing.T) {
	ctx := context.Background()
	f := &fakeDriver{}
	repo, err := NewORMMachineTokenRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatalf("NewORMMachineTokenRepository: %v", err)
	}

	if _, err := repo.Revoke(ctx, testUser, testMachineIDHome); err != nil {
		t.Fatalf("Revoke: %v", err)
	}

	// The fake driver always reports RowsAffected(1), so the boolean cannot be exercised for
	// 0 vs 1 here; only the statement scoping and the absence of an error are asserted.
	found := false
	for _, q := range f.recorded() {
		if strings.Contains(q, `UPDATE "machine_tokens" SET "revoked_at"`) {
			if !strings.Contains(q, `"user_id" = $2 AND "machine_id" = $3 AND "revoked_at" IS NULL`) {
				t.Fatalf("revoke is not user and machine scoped: %s", q)
			}
			found = true
		}
	}
	if !found {
		t.Fatalf("no revoke statement recorded: %v", f.recorded())
	}
}

func TestMachineTokenFindActive(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC()

	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		if strings.Contains(q, `FROM "machine_tokens"`) {
			return machineTokenCols, [][]driver.Value{
				fakeRow(testMachineTokenID, testUser, testMachineIDHome, testMachineTokenHash, now, nil),
			}, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMMachineTokenRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatalf("NewORMMachineTokenRepository: %v", err)
	}

	got, err := repo.FindActive(ctx, testMachineTokenHash)
	if err != nil {
		t.Fatalf("FindActive: %v", err)
	}
	if got == nil {
		t.Fatal("FindActive returned nil for an existing token")
	}
	if got.ID != testMachineTokenID || got.UserID != testUser || got.MachineID != testMachineIDHome || got.TokenHash != testMachineTokenHash {
		t.Fatalf("FindActive = %+v", got)
	}
	if !got.CreatedAt.Equal(now) {
		t.Fatalf("FindActive CreatedAt = %v, want %v", got.CreatedAt, now)
	}
	if got.RevokedAt != nil {
		t.Fatalf("FindActive RevokedAt = %v, want nil", got.RevokedAt)
	}

	scoped := false
	for _, q := range f.recorded() {
		if strings.Contains(q, `FROM "machine_tokens"`) && strings.Contains(q, `"token_hash" = $1 AND "revoked_at" IS NULL`) {
			scoped = true
		}
	}
	if !scoped {
		t.Fatalf("FindActive query is not hash and active scoped: %v", f.recorded())
	}

	// No row means no active token; that is not an error.
	f2 := &fakeDriver{}
	f2.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		if strings.Contains(q, `FROM "machine_tokens"`) {
			return machineTokenCols, nil, nil
		}
		return nil, nil, nil
	}
	repo2, err := NewORMMachineTokenRepository(newFakeManager(t, f2))
	if err != nil {
		t.Fatalf("NewORMMachineTokenRepository: %v", err)
	}
	got2, err := repo2.FindActive(ctx, testMachineTokenHash)
	if err != nil {
		t.Fatalf("FindActive(no row): %v", err)
	}
	if got2 != nil {
		t.Fatalf("FindActive(no row) = %+v, want nil", got2)
	}
}
