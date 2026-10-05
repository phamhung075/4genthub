package orm

import (
	"context"
	"database/sql"
	"fmt"
	"net/url"
	"os"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// newMissedNotificationTestEnv creates a throwaway database (AGENTHUB_TEST_PG_URL, see
// tools/testpg) with all tables and returns a session manager over it.
func newMissedNotificationTestEnv(t *testing.T) *database.SessionManager {
	t.Helper()
	admin := os.Getenv("AGENTHUB_TEST_PG_URL")
	if admin == "" {
		t.Skip("AGENTHUB_TEST_PG_URL not set")
	}
	adm, err := sql.Open("pgx", admin)
	if err != nil {
		t.Fatal(err)
	}
	name := fmt.Sprintf("agenthub_missed_%d", time.Now().UnixNano())
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

func missedNotificationMessage(entityID, title string) *entities.OrderedMap[any] {
	message := entities.NewOrderedMap[any]()
	message.Set("id", "broadcast-notification-"+entityID)
	message.Set("version", "2.0")
	message.Set("type", "update")
	payload := entities.NewOrderedMap[any]()
	payload.Set("entity", "notification")
	payload.Set("action", "notification")
	data := entities.NewOrderedMap[any]()
	primary := entities.NewOrderedMap[any]()
	primary.Set("id", entityID)
	primary.Set("title", title)
	data.Set("primary", primary)
	payload.Set("data", data)
	message.Set("payload", payload)
	return message
}

func TestMissedNotificationRepositoryStoreFetchDeliverCleanup(t *testing.T) {
	sm := newMissedNotificationTestEnv(t)
	ctx := context.Background()
	repo, err := NewMissedNotificationRepository(sm)
	if err != nil {
		t.Fatal(err)
	}

	firstID, err := repo.Store(ctx, "user-a", missedNotificationMessage("notif-1", "first"))
	if err != nil {
		t.Fatal(err)
	}
	secondID, err := repo.Store(ctx, "user-a", missedNotificationMessage("notif-2", "second"))
	if err != nil {
		t.Fatal(err)
	}
	otherID, err := repo.Store(ctx, "user-b", missedNotificationMessage("notif-3", "other user"))
	if err != nil {
		t.Fatal(err)
	}

	// Pin created_at so the oldest-first ordering and the cleanup cutoff are deterministic, and
	// leave user-b's row old so CleanupExpired must remove exactly that one.
	mustExec := func(query string, args ...any) {
		t.Helper()
		if err := sm.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
			_, err := s.ExecContext(ctx, query, args...)
			return err
		}); err != nil {
			t.Fatal(err)
		}
	}
	now := time.Now().UTC()
	mustExec(`UPDATE "missed_notifications" SET "created_at" = $1 WHERE "id" = $2`, now.Add(-2*time.Second), firstID)
	mustExec(`UPDATE "missed_notifications" SET "created_at" = $1 WHERE "id" = $2`, now.Add(-1*time.Second), secondID)
	mustExec(`UPDATE "missed_notifications" SET "created_at" = $1 WHERE "id" = $2`, now.Add(-48*time.Hour), otherID)

	// The stored document is the Python-faithful JSON of the message, key order included.
	var raw string
	if err := sm.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT "message"::text FROM "missed_notifications" WHERE "id" = $1`, firstID).Scan(&raw)
	}); err != nil {
		t.Fatal(err)
	}
	// PyJSONDumpsCompact is the compact Python form (json.dumps with (",", ":") separators) and
	// keeps the message's key order; encoding/json on an OrderedMap would not.
	want := `{"id":"broadcast-notification-notif-1","version":"2.0","type":"update","payload":{"entity":"notification","action":"notification","data":{"primary":{"id":"notif-1","title":"first"}}}}`
	if raw != want {
		t.Fatalf("stored message = %s\nwant            = %s", raw, want)
	}

	// Fetch returns only user-a's undelivered rows, oldest first.
	rows, err := repo.Fetch(ctx, "user-a", false, 100)
	if err != nil {
		t.Fatal(err)
	}
	if len(rows) != 2 || rows[0].ID != firstID || rows[1].ID != secondID {
		t.Fatalf("Fetch(user-a) = %+v, want [%s %s] oldest first", rows, firstID, secondID)
	}
	if rows[0].Message == nil {
		t.Fatal("Fetch lost the decoded message")
	}
	if v, _ := rows[0].Message.Get("id"); v != "broadcast-notification-notif-1" {
		t.Fatalf("Fetch message id = %v", v)
	}

	// A different user never sees another user's missed notifications.
	if otherRows, err := repo.Fetch(ctx, "user-b", false, 100); err != nil || len(otherRows) != 1 || otherRows[0].ID != otherID {
		t.Fatalf("Fetch(user-b) = %+v err=%v", otherRows, err)
	}
	if none, err := repo.Fetch(ctx, "user-c", false, 100); err != nil || len(none) != 0 {
		t.Fatalf("Fetch(user-c) = %+v err=%v, want empty", none, err)
	}

	// limit caps the result and keeps the oldest first.
	if limited, err := repo.Fetch(ctx, "user-a", false, 1); err != nil || len(limited) != 1 || limited[0].ID != firstID {
		t.Fatalf("Fetch limit = %+v err=%v, want [%s]", limited, err, firstID)
	}

	// MarkDelivered moves the row out of the undelivered set and into the delivered set.
	if ok, err := repo.MarkDelivered(ctx, firstID); err != nil || !ok {
		t.Fatalf("MarkDelivered = %v err=%v", ok, err)
	}
	if missing, err := repo.MarkDelivered(ctx, "00000000-0000-4000-8000-000000000000"); err != nil || missing {
		t.Fatalf("MarkDelivered(missing) = %v err=%v, want false nil", missing, err)
	}
	if undelivered, err := repo.Fetch(ctx, "user-a", false, 100); err != nil || len(undelivered) != 1 || undelivered[0].ID != secondID {
		t.Fatalf("Fetch after MarkDelivered = %+v err=%v", undelivered, err)
	}
	if delivered, err := repo.Fetch(ctx, "user-a", true, 100); err != nil || len(delivered) != 1 || delivered[0].ID != firstID {
		t.Fatalf("Fetch(delivered=true) = %+v err=%v", delivered, err)
	}

	// IncrementDeliveryAttempts bumps the counter and stamps last_attempt_at.
	if ok, err := repo.IncrementDeliveryAttempts(ctx, secondID); err != nil || !ok {
		t.Fatalf("IncrementDeliveryAttempts = %v err=%v", ok, err)
	}
	var attempts int64
	var lastAttempt sql.NullTime
	if err := sm.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT "delivery_attempts", "last_attempt_at" FROM "missed_notifications" WHERE "id" = $1`, secondID).
			Scan(&attempts, &lastAttempt)
	}); err != nil {
		t.Fatal(err)
	}
	if attempts != 1 || !lastAttempt.Valid {
		t.Fatalf("after increment: attempts=%d last_attempt_at=%v, want 1 and set", attempts, lastAttempt)
	}

	// CleanupExpired removes only rows older than the retention window.
	if n, err := repo.CleanupExpired(ctx, 24); err != nil || n != 1 {
		t.Fatalf("CleanupExpired = %d err=%v, want 1 row (the 2019 row)", n, err)
	}
	var remaining int
	if err := sm.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT count(*) FROM "missed_notifications"`).Scan(&remaining)
	}); err != nil {
		t.Fatal(err)
	}
	if remaining != 2 {
		t.Fatalf("remaining rows = %d, want 2", remaining)
	}

	// The two windows are DISTINCT, which the single-window version of this method got wrong: a
	// DELIVERED row older than the undelivered window but younger than the delivered one must
	// survive. firstID is delivered and is now pinned 48h old.
	mustExec(`UPDATE "missed_notifications" SET "created_at" = $1 WHERE "id" = $2`, now.Add(-48*time.Hour), firstID)
	if n, err := repo.CleanupExpired(ctx, 24); err != nil || n != 0 {
		t.Fatalf("CleanupExpired with a 48h-old DELIVERED row = %d err=%v, want 0 (delivered history is kept 7 days)", n, err)
	}
	var survived int
	if err := sm.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT count(*) FROM "missed_notifications" WHERE "id" = $1`, firstID).Scan(&survived)
	}); err != nil {
		t.Fatal(err)
	}
	if survived != 1 {
		t.Fatal("a delivered row 48h old was deleted on the undelivered window; the two cutoffs are not distinct")
	}
}
