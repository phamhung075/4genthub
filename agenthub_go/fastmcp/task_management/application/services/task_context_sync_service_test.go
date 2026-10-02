package services

import (
	"context"
	"errors"
	"testing"

	appexceptions "agenthub/fastmcp/task_management/application"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
)

type zpCtxSyncFakeContext struct {
	getResult *entities.OrderedMap[any]
	created   *entities.OrderedMap[any]
	updated   *entities.OrderedMap[any]
	propagate bool
}

func (f *zpCtxSyncFakeContext) GetContext(ctx context.Context, level, contextID string, includeInherited, forceRefresh bool, userID *string) (*entities.OrderedMap[any], error) {
	return f.getResult, nil
}

func (f *zpCtxSyncFakeContext) CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID *string) (*entities.OrderedMap[any], error) {
	f.created = data
	return entities.NewOrderedMap[any](), nil
}

func (f *zpCtxSyncFakeContext) UpdateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], propagateChanges bool) (*entities.OrderedMap[any], error) {
	f.updated = data
	f.propagate = propagateChanges
	return entities.NewOrderedMap[any](), nil
}

func zpCtxSyncContextWithContextData(data *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("context_data", data)
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

func TestTaskContextSyncService_SyncTaskStatus_NoContext(t *testing.T) {
	fake := &zpCtxSyncFakeContext{getResult: nil}
	svc := zpTaskCtxSyncNew(nil, nil, nil, fake, nil)
	if err := svc.SyncTaskStatus(context.Background(), "t1", "done"); err != nil {
		t.Fatal(err)
	}
	if fake.updated != nil {
		t.Fatal("no context -> no update")
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
