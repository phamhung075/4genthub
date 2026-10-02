package services

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/events"
	domainServices "agenthub/fastmcp/task_management/domain/services"
)

type bsiSvcFakeTaskRepo struct {
	tasks []domainServices.StatusedTask
}

func (f *bsiSvcFakeTaskRepo) FindByGitBranchID(branchID string) ([]domainServices.StatusedTask, error) {
	return f.tasks, nil
}

type bsiSvcFakeTask struct{ status any }

func (t *bsiSvcFakeTask) StatusValue() any { return t.status }

type bsiSvcFakeBranchRepo struct {
	branchExists bool
	updates      map[string]map[string]any
}

func (f *bsiSvcFakeBranchRepo) Get(branchID string) (any, error) {
	if !f.branchExists {
		return nil, nil
	}
	return struct{}{}, nil
}

func (f *bsiSvcFakeBranchRepo) Update(branchID string, updates map[string]any) (bool, error) {
	if f.updates == nil {
		f.updates = map[string]map[string]any{}
	}
	f.updates[branchID] = updates
	return true, nil
}

func (f *bsiSvcFakeBranchRepo) FindByProjectID(projectID string) ([]domainServices.IdentifiedBranch, error) {
	return nil, nil
}

func (f *bsiSvcFakeBranchRepo) GetAll() ([]domainServices.IdentifiedBranch, error) {
	return nil, nil
}

var _ domainServices.TaskRepositoryProtocol = (*bsiSvcFakeTaskRepo)(nil)
var _ domainServices.GitBranchRepositoryProtocol = (*bsiSvcFakeBranchRepo)(nil)

func bsiSvcClearHandlers() {
	d := domainServices.GetEventDispatcher()
	for _, eventType := range []string{"task_created", "task_updated", "task_deleted", "task_status_changed", "task_moved_to_branch"} {
		d.ClearHandlers(eventType)
	}
}

func TestBsiSvcRegisterEventHandlersOnce(t *testing.T) {
	bsiSvcClearHandlers()
	defer bsiSvcClearHandlers()

	svc := NewBranchStatisticsIntegrationService(&bsiSvcFakeTaskRepo{}, &bsiSvcFakeBranchRepo{})
	svc.RegisterEventHandlers()
	svc.RegisterEventHandlers()

	if got := domainServices.GetEventDispatcher().GetHandlerCount("task_created"); got != 1 {
		t.Fatalf("task_created handler count = %d, want 1", got)
	}
	if got := domainServices.GetEventDispatcher().GetHandlerCount("task_moved_to_branch"); got != 1 {
		t.Fatalf("task_moved_to_branch handler count = %d, want 1", got)
	}
}

func TestBsiSvcTaskCreatedRecalculatesBranch(t *testing.T) {
	bsiSvcClearHandlers()
	defer bsiSvcClearHandlers()

	taskRepo := &bsiSvcFakeTaskRepo{tasks: []domainServices.StatusedTask{&bsiSvcFakeTask{status: "done"}}}
	branchRepo := &bsiSvcFakeBranchRepo{branchExists: true}
	svc := NewBranchStatisticsIntegrationService(taskRepo, branchRepo)
	svc.RegisterEventHandlers()

	event := events.NewTaskCreatedEvent()
	event.TaskID = "t1"
	event.BranchID = "b1"
	event.Status = "todo"
	domainServices.DispatchDomainEvent("task_created", event)

	updates, ok := branchRepo.updates["b1"]
	if !ok {
		t.Fatalf("branch b1 was not recalculated")
	}
	if got := updates["task_count"]; got != 1 {
		t.Fatalf("task_count = %v, want 1", got)
	}
	if got := updates["completed_task_count"]; got != 1 {
		t.Fatalf("completed_task_count = %v, want 1", got)
	}
	if got := updates["progress_percentage"]; got != 100.0 {
		t.Fatalf("progress_percentage = %v, want 100.0", got)
	}
}

func TestBsiSvcTaskUpdatedUsesNewBranchFallback(t *testing.T) {
	bsiSvcClearHandlers()
	defer bsiSvcClearHandlers()

	taskRepo := &bsiSvcFakeTaskRepo{tasks: []domainServices.StatusedTask{}}
	branchRepo := &bsiSvcFakeBranchRepo{branchExists: true}
	svc := NewBranchStatisticsIntegrationService(taskRepo, branchRepo)
	svc.RegisterEventHandlers()

	event := events.NewTaskUpdatedEvent()
	event.TaskID = "t1"
	event.BranchID = "fallback"
	domainServices.DispatchDomainEvent("task_updated", event)

	if _, ok := branchRepo.updates["fallback"]; !ok {
		t.Fatalf("fallback branch was not recalculated: %v", branchRepo.updates)
	}
}

func TestBsiSvcGetBranchStatisticsIntegrationServiceSingleton(t *testing.T) {
	bsiSvcClearHandlers()
	bsiSvcIntegrationService = nil
	defer func() {
		bsiSvcClearHandlers()
		bsiSvcIntegrationService = nil
	}()

	taskRepo := &bsiSvcFakeTaskRepo{}
	branchRepo := &bsiSvcFakeBranchRepo{}
	first := GetBranchStatisticsIntegrationService(taskRepo, branchRepo)
	second := GetBranchStatisticsIntegrationService(&bsiSvcFakeTaskRepo{}, &bsiSvcFakeBranchRepo{})
	if first != second {
		t.Fatalf("singleton getter returned different instances")
	}
	if got := domainServices.GetEventDispatcher().GetHandlerCount("task_created"); got != 1 {
		t.Fatalf("task_created handler count = %d, want 1", got)
	}
}
