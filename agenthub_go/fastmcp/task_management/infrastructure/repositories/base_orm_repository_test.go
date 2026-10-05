package repositories

import (
	"context"
	"encoding/json"
	"errors"
	"testing"

	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

const (
	uidA = "11111111-1111-4111-8111-111111111111"
	uidB = "22222222-2222-4222-8222-222222222222"
)

func TestBaseRepositoryCRUDOnRealPostgres(t *testing.T) {
	sm := newTestRepoEnv(t)
	ctx := context.Background()
	repo, err := NewORMRepository[database.Project]("projects", sm)
	if err != nil {
		t.Fatal(err)
	}

	p, err := repo.Create(ctx, NewKwargs("id", uidA, "name", "alpha", "user_id", "u1"))
	if err != nil {
		t.Fatal(err)
	}
	if p.ID != uidA || p.Description != "" || p.Status != "active" || string(p.Metadata) != "{}" || p.CreatedAt.IsZero() || p.UpdatedAt.IsZero() {
		t.Fatalf("defaults/timestamps not applied: %+v", p)
	}
	// unknown attribute on create is a TypeError, like model_class(**kwargs)
	if _, err := repo.Create(ctx, NewKwargs("id", uidB, "bogus", 1)); err == nil {
		t.Fatal("expected TypeError")
	}
	// model_metadata maps to the "metadata" column
	q, err := repo.Create(ctx, NewKwargs("id", uidB, "name", "beta", "user_id", "u2", "model_metadata", map[string]any{"k": []any{int64(1), "x"}}))
	if err != nil {
		t.Fatal(err)
	}
	var meta map[string]any
	_ = json.Unmarshal(q.Metadata, &meta)
	if meta["k"] == nil || string(q.Metadata) != `{"k": [1, "x"]}` {
		t.Fatalf("metadata %s", q.Metadata)
	}

	got, err := repo.GetByID(ctx, uidA)
	if err != nil || got == nil || got.Name != "alpha" {
		t.Fatalf("GetByID: %v %+v", err, got)
	}
	if none, _ := repo.GetByID(ctx, "33333333-3333-4333-8333-333333333333"); none != nil {
		t.Fatal("expected nil for a missing id")
	}

	n, _ := repo.Count(ctx, nil)
	if n != 2 {
		t.Fatalf("count %d", n)
	}
	if ex, _ := repo.Exists(ctx, NewKwargs("user_id", "u2")); !ex {
		t.Fatal("exists")
	}
	if rows, _ := repo.FindBy(ctx, NewKwargs("user_id", "u1", "ignored_attr", 5)); len(rows) != 1 {
		t.Fatalf("FindBy %d", len(rows))
	}
	if one, _ := repo.FindOneBy(ctx, NewKwargs("name", "beta")); one == nil || one.ID != uidB {
		t.Fatalf("FindOneBy %+v", one)
	}
	limit, off := 1, 1
	if rows, _ := repo.GetAll(ctx, &limit, &off); len(rows) != 1 {
		t.Fatalf("GetAll %d", len(rows))
	}

	before := p.UpdatedAt
	up, err := repo.Update(ctx, uidA, NewKwargs("name", "alpha2", "unknown", 1))
	if err != nil || up.Name != "alpha2" || !up.UpdatedAt.After(before) {
		t.Fatalf("Update: %v %+v", err, up)
	}
	// before_update fires for any assigned known attribute, even with an unchanged value
	same, _ := repo.Update(ctx, uidA, NewKwargs("name", "alpha2"))
	if !same.UpdatedAt.After(up.UpdatedAt) {
		t.Fatal("assigning an attribute must refresh updated_at")
	}
	// ...but not when nothing known is assigned
	untouched, _ := repo.Update(ctx, uidA, NewKwargs("unknown", 1))
	if !untouched.UpdatedAt.Equal(same.UpdatedAt) {
		t.Fatal("unknown-only update must not touch updated_at")
	}
	if missing, _ := repo.Update(ctx, "33333333-3333-4333-8333-333333333333", NewKwargs("name", "x")); missing != nil {
		t.Fatal("expected nil")
	}

	// unique (id, user_id) is on the pk so duplicate id => integrity exception
	_, err = repo.Create(ctx, NewKwargs("id", uidA, "name", "dup", "user_id", "u1"))
	var ie *exceptions.DatabaseIntegrityException
	if !errors.As(err, &ie) {
		t.Fatalf("want DatabaseIntegrityException, got %T %v", err, err)
	}

	if ok, _ := repo.Delete(ctx, uidB); !ok {
		t.Fatal("delete")
	}
	if ok, _ := repo.Delete(ctx, uidB); ok {
		t.Fatal("second delete must report false")
	}

	// transaction: rollback on error leaves nothing behind
	errBoom := errors.New("boom")
	err = repo.Transaction(ctx, func(ctx context.Context) error {
		if _, err := repo.Create(ctx, NewKwargs("id", uidB, "name", "tx", "user_id", "u3")); err != nil {
			return err
		}
		return errBoom
	})
	if err != errBoom {
		t.Fatalf("callback errors must propagate unchanged, got %T %v", err, err)
	}
	if ex, _ := repo.Exists(ctx, NewKwargs("name", "tx")); ex {
		t.Fatal("rolled back transaction leaked a row")
	}
	// transaction commit
	_ = repo.Transaction(ctx, func(ctx context.Context) error {
		_, err := repo.BulkCreate(ctx, []Kwargs{NewKwargs("id", uidB, "name", "b1", "user_id", "u3")})
		return err
	})
	if ex, _ := repo.Exists(ctx, NewKwargs("name", "b1")); !ex {
		t.Fatal("committed transaction row missing")
	}
}

func TestUserScopedRepositoryIsolation(t *testing.T) {
	sm := newTestRepoEnv(t)
	ctx := context.Background()
	u1, u2 := "user-1", "user-2"
	r1, err := NewUserScopedORMRepository[database.Project]("projects", sm, &u1)
	if err != nil {
		t.Fatal(err)
	}
	r2, _ := NewUserScopedORMRepository[database.Project]("projects", sm, &u2)
	sys, _ := NewUserScopedORMRepository[database.Project]("projects", sm, nil)

	if _, err := sys.Create(ctx, NewKwargs("id", uidA, "name", "x")); err == nil {
		t.Fatal("system mode create must fail (user authentication required)")
	}
	p, err := r1.Create(ctx, NewKwargs("id", uidA, "name", "mine", "user_id", "ignored-user"))
	if err != nil || p.UserID != u1 {
		t.Fatalf("user id must be injected: %v %+v", err, p)
	}
	if got, _ := r2.GetByID(ctx, uidA); got != nil {
		t.Fatal("user 2 must not see user 1 data")
	}
	if n, _ := r2.Count(ctx, nil); n != 0 {
		t.Fatalf("count %d", n)
	}
	up, err := r1.Update(ctx, uidA, NewKwargs("name", "renamed", "user_id", "hijack"))
	if err != nil || up.Name != "renamed" || up.UserID != u1 {
		t.Fatalf("update: %v %+v", err, up)
	}
	if none, _ := r2.Update(ctx, uidA, NewKwargs("name", "evil")); none != nil {
		t.Fatal("cross-user update must not find the row")
	}
	if ok, _ := r2.Delete(ctx, uidA); ok {
		t.Fatal("cross-user delete must be a no-op")
	}
	if _, err := r1.BulkCreate(ctx, []Kwargs{NewKwargs("id", uidB, "name", "b")}); err != nil {
		t.Fatal(err)
	}
	n, err := r1.BulkUpdate(ctx, []any{uidA, uidB}, NewKwargs("status", "archived", "user_id", "nope"))
	if err != nil || n != 2 {
		t.Fatalf("bulk update %d %v", n, err)
	}
	if n, _ := r2.BulkDelete(ctx, []any{uidA}); n != 0 {
		t.Fatalf("cross-user bulk delete count %d", n)
	}
	if n, _ := r1.BulkDelete(ctx, []any{uidA, uidB}); n != 2 {
		t.Fatalf("bulk delete %d", n)
	}
	// system mode reads everything
	if all, _ := sys.GetAll(ctx, nil, nil); len(all) != 0 {
		t.Fatalf("expected empty, got %d", len(all))
	}
}

func TestBaseRepositoryUUIDNormalisationAndErrorWrapping(t *testing.T) {
	sm := newTestRepoEnv(t)
	ctx := context.Background()
	repo, _ := NewORMRepository[database.Project]("projects", sm)

	// a non-UUID id becomes the deterministic uuid5 on every path (UnifiedUUID)
	p, err := repo.Create(ctx, NewKwargs("id", "not-a-uuid", "name", "n", "user_id", "u"))
	if err != nil {
		t.Fatal(err)
	}
	if got, _ := repo.GetByID(ctx, "not-a-uuid"); got == nil || got.ID != p.ID {
		t.Fatal("GetByID must normalise the id the same way")
	}
	if rows, _ := repo.FindBy(ctx, NewKwargs("id", "not-a-uuid")); len(rows) != 1 {
		t.Fatalf("FindBy by normalised id: %d", len(rows))
	}
	if ok, _ := repo.Delete(ctx, "not-a-uuid"); !ok {
		t.Fatal("Delete by non-uuid id")
	}

	// bulk_create does not convert IntegrityError (only create does)
	_, err = repo.Create(ctx, NewKwargs("id", uidA, "name", "a", "user_id", "u"))
	if err != nil {
		t.Fatal(err)
	}
	_, err = repo.BulkCreate(ctx, []Kwargs{NewKwargs("id", uidA, "name", "dup", "user_id", "u")})
	var de *exceptions.DatabaseException
	var ie *exceptions.DatabaseIntegrityException
	if !errors.As(err, &de) || errors.As(err, &ie) {
		t.Fatalf("BulkCreate duplicate must be DatabaseException, got %T %v", err, err)
	}

	// driver-side encoding failures are DatabaseException as well
	_, err = repo.FindBy(ctx, NewKwargs("name", 5))
	if !errors.As(err, &de) {
		t.Fatalf("encode error must be DatabaseException, got %T %v", err, err)
	}
}
