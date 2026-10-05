package database

import (
	"context"
	"errors"
	"testing"
	"time"
)

func newTestManager(t *testing.T) (*SessionManager, *fakeDB) {
	ResetInstance()
	t.Cleanup(ResetInstance)
	f := newFakeDB()
	env := map[string]string{"DATABASE_TYPE": "postgresql", "DATABASE_HOST": "h", "DATABASE_PASSWORD": "p"}
	cfg, err := GetInstance(context.Background(), Deps{Getenv: envFrom(env), Sleep: func(time.Duration) {}, Open: f.open})
	if err != nil {
		t.Fatal(err)
	}
	f.statements = nil
	return NewSessionManager(cfg), f
}

func TestWithSessionCommitsAndRollsBack(t *testing.T) {
	m, f := newTestManager(t)
	ctx := context.Background()
	if err := m.WithSession(ctx, func(ctx context.Context, s DBTX) error {
		_, err := s.ExecContext(ctx, "UPDATE x SET y = 1")
		return err
	}); err != nil {
		t.Fatal(err)
	}
	boom := &OperationalError{Msg: "boom"}
	if err := m.WithSession(ctx, func(context.Context, DBTX) error { return boom }); !errors.Is(err, boom) {
		t.Fatal(err)
	}
	app := errors.New("application error")
	_ = m.WithSession(ctx, func(context.Context, DBTX) error { return app })
	st := m.stats
	if st.TransactionsCommitted != 1 || st.TransactionsRolledBack != 1 || st.SessionErrors != 1 || st.SessionsClosed != 3 || st.SessionsCreated != 3 {
		t.Fatalf("stats %+v", st)
	}
	var commits, rollbacks int
	for _, s := range f.statements {
		switch s {
		case "COMMIT":
			commits++
		case "ROLLBACK":
			rollbacks++
		}
	}
	if commits != 1 || rollbacks != 2 {
		t.Fatalf("commits=%d rollbacks=%d %v", commits, rollbacks, f.statements)
	}
}

func TestTransactionSharesOneSession(t *testing.T) {
	m, f := newTestManager(t)
	ctx := context.Background()
	err := m.Transaction(ctx, func(ctx context.Context) error {
		for i := 0; i < 2; i++ {
			if err := m.WithSession(ctx, func(ctx context.Context, s DBTX) error {
				_, err := s.ExecContext(ctx, "INSERT INTO t VALUES (1)")
				return err
			}); err != nil {
				return err
			}
		}
		return m.Transaction(ctx, func(context.Context) error { return nil }) // nested reuses
	})
	if err != nil {
		t.Fatal(err)
	}
	begins, commits := 0, 0
	for _, s := range f.statements {
		switch s {
		case "BEGIN":
			begins++
		case "COMMIT":
			commits++
		}
	}
	if begins != 1 || commits != 1 || m.stats.TransactionsCommitted != 1 {
		t.Fatalf("begins=%d commits=%d %+v", begins, commits, m.stats)
	}
}
