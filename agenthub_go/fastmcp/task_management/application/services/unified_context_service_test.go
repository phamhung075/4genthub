package services

import (
	"context"
	"errors"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type zucsFakeRepo struct {
	store    map[string]any
	created  []any
	deleted  []string
	listVals []any
}

func newZucsFakeRepo() *zucsFakeRepo { return &zucsFakeRepo{store: map[string]any{}} }

func (f *zucsFakeRepo) Get(ctx context.Context, id string) (any, error) {
	v, ok := f.store[id]
	if !ok {
		return nil, nil
	}
	return v, nil
}

func (f *zucsFakeRepo) Create(ctx context.Context, entity any) (any, error) {
	id := zpUCSEntityID(entity)
	f.store[id] = entity
	f.created = append(f.created, entity)
	return entity, nil
}

func (f *zucsFakeRepo) Update(ctx context.Context, id string, entity any) (any, error) {
	f.store[id] = entity
	return entity, nil
}

func (f *zucsFakeRepo) Delete(ctx context.Context, id string) (bool, error) {
	if _, ok := f.store[id]; !ok {
		return false, errors.New("not found")
	}
	delete(f.store, id)
	f.deleted = append(f.deleted, id)
	return true, nil
}

func (f *zucsFakeRepo) List(ctx context.Context, filters map[string]any) ([]any, error) {
	return f.listVals, nil
}

func newZucsService(t *testing.T) (*UnifiedContextService, *zucsFakeRepo, *zucsFakeRepo) {
	t.Helper()
	global := newZucsFakeRepo()
	project := newZucsFakeRepo()
	branch := newZucsFakeRepo()
	task := newZucsFakeRepo()
	user := "user-1"
	s := NewUnifiedContextService(global, project, branch, task, nil, nil, nil, nil, &user)
	return s, global, project
}

func zucsOM(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}

func TestZucsCreateGlobalContextNormalizesID(t *testing.T) {
	s, global, _ := newZucsService(t)
	ctx := context.Background()
	res, _ := s.CreateContext(ctx, "global", "global", entities.NewOrderedMap[any](), nil, nil, true)
	if v, _ := res.Get("success"); v != true {
		t.Fatalf("success=%v res=%v", v, res.Keys())
	}
	id, _ := res.Get("context_id")
	if id == nil || id == "" || id == "global" {
		t.Fatalf("context_id=%v", id)
	}
	if len(global.created) != 1 {
		t.Fatalf("created=%d", len(global.created))
	}
	// The constructor puts global_settings, then metadata; the ID is preserved.
	globalEntity, _ := global.store[id.(string)].(*entities.GlobalContext)
	if globalEntity == nil {
		t.Fatalf("stored entity type %T", global.store[id.(string)])
	}
	if globalEntity.Metadata["user_id"] != "user-1" {
		t.Fatalf("user_id=%v", globalEntity.Metadata["user_id"])
	}
}

func TestZucsGetContextAndNotFound(t *testing.T) {
	s, global, _ := newZucsService(t)
	ctx := context.Background()
	global.store["abc"] = entities.NewGlobalContext("abc", "Org", map[string]any{}, map[string]any{"user_id": "user-1"})

	res, _ := s.GetContext(ctx, "global", "abc", false, false, nil)
	if v, _ := res.Get("success"); v != true {
		t.Fatalf("success=%v", v)
	}
	if v, _ := res.Get("context_id"); v != "abc" {
		t.Fatalf("context_id=%v", v)
	}
	// Order: success, context, level, context_id, inherited
	wantKeys := []string{"success", "context", "level", "context_id", "inherited"}
	gotKeys := res.Keys()
	if len(gotKeys) != len(wantKeys) {
		t.Fatalf("keys=%v", gotKeys)
	}
	for i, k := range wantKeys {
		if gotKeys[i] != k {
			t.Fatalf("keys=%v want %v", gotKeys, wantKeys)
		}
	}

	missing, _ := s.GetContext(ctx, "global", "nope", false, false, nil)
	if v, _ := missing.Get("success"); v != false {
		t.Fatalf("expected failure")
	}
	if v, _ := missing.Get("error"); v != "Context not found: nope" {
		t.Fatalf("error=%v", v)
	}
}

func TestZucsMergeContextDataListSemantics(t *testing.T) {
	s, _, _ := newZucsService(t)
	existing := zucsOM("insights", []any{"a"}, "next_steps", []any{"s"}, "labels", []any{"x"}, "nested", zucsOM("a", 1))
	incoming := zucsOM("insights", []any{"b"}, "next_steps", []any{"t"}, "labels", []any{"y"}, "nested", zucsOM("b", 2))
	merged := s.mergeContextData(existing, incoming)

	if v, _ := merged.Get("insights"); len(v.([]any)) != 1 || v.([]any)[0] != "b" {
		t.Fatalf("insights=%v", v)
	}
	if v, _ := merged.Get("next_steps"); len(v.([]any)) != 1 || v.([]any)[0] != "t" {
		t.Fatalf("next_steps=%v", v)
	}
	if v, _ := merged.Get("labels"); len(v.([]any)) != 2 || v.([]any)[0] != "x" || v.([]any)[1] != "y" {
		t.Fatalf("labels=%v", v)
	}
	nested, _ := merged.Get("nested")
	nestedOM := nested.(*entities.OrderedMap[any])
	if a, _ := nestedOM.Get("a"); a != 1 {
		t.Fatalf("nested.a=%v", a)
	}
	if b, _ := nestedOM.Get("b"); b != 2 {
		t.Fatalf("nested.b=%v", b)
	}
}

func TestZucsShouldAllowOrphanedCreation(t *testing.T) {
	s, _, _ := newZucsService(t)
	if !s.shouldAllowOrphanedCreation(value_objects.ContextLevelGlobal, "g", entities.NewOrderedMap[any]()) {
		t.Fatal("global should be allowed")
	}
	if !s.shouldAllowOrphanedCreation(value_objects.ContextLevelProject, "p", zucsOM("auto_created", true)) {
		t.Fatal("auto_created project should be allowed")
	}
	if !s.shouldAllowOrphanedCreation(value_objects.ContextLevelProject, "p", zucsOM("project_name", "Test Thing")) {
		t.Fatal("Test project should be allowed")
	}
	if s.shouldAllowOrphanedCreation(value_objects.ContextLevelProject, "p", zucsOM("project_name", "Real")) {
		t.Fatal("real project should not be allowed")
	}
}
