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

func TestTaskContextSyncService_SyncTaskStatus(t *testing.T) {
	data := entities.NewOrderedMap[any]()
	data.Set("foo", "bar")
	fake := &zpCtxSyncFakeContext{getResult: zpCtxSyncContextWithContextData(data)}
	svc := zpTaskCtxSyncNew(nil, nil, nil, fake, nil)

	if err := svc.SyncTaskStatus(context.Background(), "t1", "in_progress"); err != nil {
		t.Fatal(err)
	}
	metadata, ok := fake.updated.Get("metadata")
	if !ok {
		t.Fatal("metadata missing")
	}
	md := metadata.(*entities.OrderedMap[any])
	if v, _ := md.Get("status"); v != "in_progress" {
		t.Fatalf("status=%v", v)
	}
	if fake.propagate {
		t.Fatal("propagate_changes should be false")
	}
}

// A read that answers with no context at all is reported now, not swallowed: silence is what let
// a done task keep resolving as todo.
func TestTaskContextSyncService_SyncTaskStatus_NoContext(t *testing.T) {
	fake := &zpCtxSyncFakeContext{getResult: nil}
	svc := zpTaskCtxSyncNew(nil, nil, nil, fake, nil)
	if err := svc.SyncTaskStatus(context.Background(), "t1", "done"); err == nil {
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
		err := svc.SyncTaskStatus(context.Background(), "t1", "done")
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

	if err := svc.SyncTaskStatus(context.Background(), "t1", "in_progress"); err != nil {
		t.Fatal(err)
	}
	if v, _ := fake.updated.Get("implementation_notes"); v != "keep me" {
		t.Fatalf("implementation_notes=%v: the sync dropped the record it read", v)
	}
	metadataAny, _ := fake.updated.Get("metadata")
	metadata, ok := metadataAny.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("metadata is %T", metadataAny)
	}
	if v, _ := metadata.Get("status"); v != "in_progress" {
		t.Fatalf("status=%v", v)
	}
	if v, _ := metadata.Get("version"); v != float64(3) {
		t.Fatalf("version=%v: the existing metadata did not survive", v)
	}
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
	metadataAny, _ := fake.updated.Get("metadata")
	metadata := metadataAny.(*entities.OrderedMap[any])
	assigneesAny, _ := metadata.Get("assignees")
	assignees := assigneesAny.([]string)
	if len(assignees) != 2 || assignees[0] != "@alice" || assignees[1] != "@bob" {
		t.Fatalf("assignees=%v", assignees)
	}
	objectiveAny, _ := fake.updated.Get("objective")
	objective := objectiveAny.(*entities.OrderedMap[any])
	if v, _ := objective.Get("estimated_effort"); v != "2d" {
		t.Fatalf("estimated_effort=%v", v)
	}
}
