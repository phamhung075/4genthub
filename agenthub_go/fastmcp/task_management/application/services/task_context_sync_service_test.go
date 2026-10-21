package services

import (
	"context"
	"errors"
	"strings"
	"testing"

	appexceptions "agenthub/fastmcp/task_management/application"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
)

type zpCtxSyncFakeContext struct {
	getResult *entities.OrderedMap[any]
	getErr    error
	created   *entities.OrderedMap[any]
	updated   *entities.OrderedMap[any]
	propagate bool
	updateErr error
}

func (f *zpCtxSyncFakeContext) GetContext(ctx context.Context, level, contextID string, includeInherited bool, userID *string) (*entities.OrderedMap[any], error) {
	return f.getResult, f.getErr
}

func (f *zpCtxSyncFakeContext) CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID *string) (*entities.OrderedMap[any], error) {
	f.created = data
	return entities.NewOrderedMap[any](), nil
}

func (f *zpCtxSyncFakeContext) UpdateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], propagateChanges bool) (*entities.OrderedMap[any], error) {
	f.updated = data
	f.propagate = propagateChanges
	if f.updateErr != nil {
		return entities.NewOrderedMap[any](), f.updateErr
	}
	return entities.NewOrderedMap[any](), nil
}

// zpCtxSyncContextWithContextData answers the shape the Go GetContext really answers with: the
// stored record under "context". (The Python port read "context_data", which nothing here
// produces, so the sync used to write onto an empty base and never saw the record.)
func zpCtxSyncContextWithContextData(data *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("context", data)
	return m
}

func TestTaskContextSyncService_ProviderUnwired(t *testing.T) {
	repoProviderInstance = nil
	repoProviderFactoryBackendProvider = nil
	_, err := NewTaskContextSyncService(nil, nil, nil, &zpCtxSyncFakeContext{})
	var rpe *appexceptions.RepositoryProviderError
	if !errors.As(err, &rpe) {
		t.Fatalf("want RepositoryProviderError, got %T %v", err, err)
	}
}

func TestTaskContextSyncService_AuthRequired(t *testing.T) {
	fake := &zpCtxSyncFakeContext{}
	svc := zpTaskCtxSyncNew(nil, nil, nil, fake, nil)
	_, err := svc.SyncContextAndGetTask(context.Background(), "t1", "", "", "main")
	var authErr *exceptions.UserAuthenticationRequiredError
	if !errors.As(err, &authErr) {
		t.Fatalf("want UserAuthenticationRequiredError, got %T %v", err, err)
	}
}

func TestTaskContextSyncService_SyncTaskMetadata_NoContext(t *testing.T) {
	fake := &zpCtxSyncFakeContext{getResult: nil}
	svc := zpTaskCtxSyncNew(nil, nil, nil, fake, nil)
	if err := svc.SyncTaskMetadata(context.Background(), "t1", &entities.Task{}); err == nil {
		t.Fatal("a read that returns no context must be reported")
	}
	if fake.updated != nil {
		t.Fatal("no context -> no update")
	}
}

// The three ways a sync can fail silently before: an unsuccessful read body, a read error and a
// refused update. Each must reach the caller.
func TestTaskContextSyncService_SyncFailuresAreReported(t *testing.T) {
	t.Run("unsuccessful read body", func(t *testing.T) {
		body := entities.NewOrderedMap[any]()
		body.Set("success", false)
		body.Set("error", "Context not found: t1")
		fake := &zpCtxSyncFakeContext{getResult: body}
		svc := zpTaskCtxSyncNew(nil, nil, nil, fake, nil)
		err := svc.SyncTaskMetadata(context.Background(), "t1", &entities.Task{})
		if err == nil || !strings.Contains(err.Error(), "Context not found") {
			t.Fatalf("err=%v", err)
		}
	})
	t.Run("read error", func(t *testing.T) {
		fake := &zpCtxSyncFakeContext{getErr: errors.New("the database is down")}
		svc := zpTaskCtxSyncNew(nil, nil, nil, fake, nil)
		err := svc.SyncTaskMetadata(context.Background(), "t1", &entities.Task{})
		if err == nil || !strings.Contains(err.Error(), "the database is down") {
			t.Fatalf("err=%v", err)
		}
	})
	t.Run("refused update", func(t *testing.T) {
		data := entities.NewOrderedMap[any]()
		fake := &zpCtxSyncFakeContext{
			getResult: zpCtxSyncContextWithContextData(data),
			updateErr: errors.New("the write was refused"),
		}
		svc := zpTaskCtxSyncNew(nil, nil, nil, fake, nil)
		err := svc.SyncTaskMetadata(context.Background(), "t1", &entities.Task{EstimatedEffort: "2d"})
		if err == nil || !strings.Contains(err.Error(), "the write was refused") {
			t.Fatalf("err=%v", err)
		}
	})
}

// The sync reads the record it was handed (the key the Go GetContext answers with), so an update
// carries it forward instead of writing onto an empty base. Before the key was fixed this lost
// implementation_notes and the existing metadata.
func TestTaskContextSyncService_SyncKeepsTheExistingRecord(t *testing.T) {
	data := entities.NewOrderedMap[any]()
	data.Set("implementation_notes", "keep me")
	data.Set("metadata", map[string]any{"version": float64(3)})
	fake := &zpCtxSyncFakeContext{getResult: zpCtxSyncContextWithContextData(data)}
	svc := zpTaskCtxSyncNew(nil, nil, nil, fake, nil)

	if err := svc.SyncTaskMetadata(context.Background(), "t1", &entities.Task{EstimatedEffort: "2d"}); err != nil {
		t.Fatal(err)
	}
	if v, _ := fake.updated.Get("implementation_notes"); v != "keep me" {
		t.Fatalf("implementation_notes=%v: the sync dropped the record it read", v)
	}
	metadataAny, _ := fake.updated.Get("metadata")
	// The map travels untouched now - the sync reads the record and writes only the objective - so it is
	// whatever shape the record carried, not the OrderedMap the old status write re-Set it into.
	metadata := zpCtxSyncMetadataMap(t, metadataAny)
	// The completion used to write the task's status into this map through SyncTaskStatus; no column
	// keeps it, so the write was dropped by the repository and every completion reported
	// `add metadata.status`. The status is the task row's, and a context read serves it from there.
	if v, ok := metadata["status"]; ok {
		t.Fatalf("status=%v: the context metadata carried a task-owned field", v)
	}
	if v, _ := metadata["version"]; v != float64(3) {
		t.Fatalf("version=%v: the existing metadata did not survive", v)
	}
}

// zpCtxSyncMetadataMap flattens either shape a record's metadata can arrive in.
func zpCtxSyncMetadataMap(t *testing.T, v any) map[string]any {
	t.Helper()
	switch m := v.(type) {
	case nil:
		return map[string]any{}
	case map[string]any:
		return m
	case *entities.OrderedMap[any]:
		out := map[string]any{}
		for _, k := range m.Keys() {
			val, _ := m.Get(k)
			out[k] = val
		}
		return out
	}
	t.Fatalf("metadata is %T", v)
	return nil
}

func TestTaskContextSyncService_SyncSubtaskCountsNilRepo(t *testing.T) {
	fake := &zpCtxSyncFakeContext{}
	svc := zpTaskCtxSyncNew(nil, nil, nil, fake, nil)
	if err := svc.SyncSubtaskCounts(context.Background(), "11111111-1111-1111-1111-111111111111", nil); err != nil {
		t.Fatal(err)
	}
}

func TestTaskContextSyncService_SyncTaskMetadata(t *testing.T) {
	data := entities.NewOrderedMap[any]()
	fake := &zpCtxSyncFakeContext{getResult: zpCtxSyncContextWithContextData(data)}
	svc := zpTaskCtxSyncNew(nil, nil, nil, fake, nil)

	task := &entities.Task{Assignees: []string{"@alice", "bob"}, Labels: []string{"x"}, EstimatedEffort: "2d"}
	if err := svc.SyncTaskMetadata(context.Background(), "t1", task); err != nil {
		t.Fatal(err)
	}
	objectiveAny, _ := fake.updated.Get("objective")
	objective := objectiveAny.(*entities.OrderedMap[any])
	if v, _ := objective.Get("estimated_effort"); v != "2d" {
		t.Fatalf("estimated_effort=%v", v)
	}
	// The context row stores no column for the task's own fields, and it does not have to: a context read
	// serves them from the task row. Writing them into this metadata was the phantom add the ledger repeated
	// on every task update (hub row f6328d5a), so the write is asserted ABSENT, field by field.
	metadataAny, hasMetadata := fake.updated.Get("metadata")
	if hasMetadata {
		metadata, _ := metadataAny.(*entities.OrderedMap[any])
		for _, key := range []string{"status", "priority", "labels", "assignees", "created_at", "updated_at"} {
			if v, ok := metadata.Get(key); ok {
				t.Fatalf("metadata.%s written to a context that cannot store it: %v", key, v)
			}
		}
	}
}

func TestTaskContextSyncService_SyncTaskMetadataSkipsAnUnchangedObjective(t *testing.T) {
	data := entities.NewOrderedMap[any]()
	objective := entities.NewOrderedMap[any]()
	objective.Set("estimated_effort", "2d")
	data.Set("objective", objective)
	fake := &zpCtxSyncFakeContext{getResult: zpCtxSyncContextWithContextData(data)}
	svc := zpTaskCtxSyncNew(nil, nil, nil, fake, nil)

	if err := svc.SyncTaskMetadata(context.Background(), "t1", &entities.Task{EstimatedEffort: "2d"}); err != nil {
		t.Fatal(err)
	}
	// The context owns nothing that changed, so nothing is written: an update here bumps the version and
	// appends an empty change set, which is the same phantom history in a quieter shape.
	if fake.updated != nil {
		t.Fatal("an unchanged objective must not write the context")
	}
}
