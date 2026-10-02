package use_cases

import (
	"context"
	"errors"
	"testing"

	ctxdto "agenthub/fastmcp/task_management/application/dtos/context"
	"agenthub/fastmcp/task_management/application/dtos/dependency"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// useCasesGroup1TaskRepo is a fake repositories.TaskRepository. The embedded
// interface satisfies the methods the tests never call.
type useCasesGroup1TaskRepo struct {
	repositories.TaskRepository
	byID        map[string]*entities.Task
	allStates   map[string]*entities.Task
	across      map[string]*entities.Task
	findByIDErr error
	saveErr     error
	saved       []*entities.Task
	searchTasks []*entities.Task
	searchQuery string
	searchLimit int
}

func (f *useCasesGroup1TaskRepo) FindByID(_ context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
	if f.findByIDErr != nil {
		return nil, f.findByIDErr
	}
	return f.byID[taskID.Value], nil
}

func (f *useCasesGroup1TaskRepo) FindByIDAllStates(_ context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
	return f.allStates[taskID.Value], nil
}

// FindByIDAcrossContexts makes the fake also satisfy the optional
// addDependencyAcrossContextsFinder probe.
func (f *useCasesGroup1TaskRepo) FindByIDAcrossContexts(_ context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
	return f.across[taskID.Value], nil
}

func (f *useCasesGroup1TaskRepo) Save(_ context.Context, task *entities.Task) (*entities.Task, error) {
	if f.saveErr != nil {
		return nil, f.saveErr
	}
	f.saved = append(f.saved, task)
	return task, nil
}

func (f *useCasesGroup1TaskRepo) Search(_ context.Context, query string, limit int) ([]*entities.Task, error) {
	f.searchQuery, f.searchLimit = query, limit
	return f.searchTasks, nil
}

// useCasesGroup1ContextRepo is a fake repositories.ContextRepository.
type useCasesGroup1ContextRepo struct {
	repositories.ContextRepository
	exists       bool
	existsErr    error
	taskContext  *entities.TaskContext
	getErr       error
	updateResult map[string]any
	updateErr    error
	updated      *entities.TaskContext
}

func (f *useCasesGroup1ContextRepo) ContextExists(_ context.Context, _ string) (bool, error) {
	return f.exists, f.existsErr
}

func (f *useCasesGroup1ContextRepo) GetContext(_ context.Context, _ string) (*entities.TaskContext, error) {
	return f.taskContext, f.getErr
}

func (f *useCasesGroup1ContextRepo) UpdateContext(_ context.Context, c *entities.TaskContext) (map[string]any, error) {
	f.updated = c
	return f.updateResult, f.updateErr
}

// useCasesGroup1AgentRepo is a fake repositories.AgentRepository.
type useCasesGroup1AgentRepo struct {
	repositories.AgentRepository
	data map[string]any
	err  error
}

func (f *useCasesGroup1AgentRepo) GetAgent(_ context.Context, _, _ string) (map[string]any, error) {
	return f.data, f.err
}

func useCasesGroup1MustTaskID(t *testing.T, raw string) value_objects.TaskId {
	t.Helper()
	id, err := value_objects.NewTaskId(raw)
	if err != nil {
		t.Fatalf("NewTaskId(%q): %v", raw, err)
	}
	return id
}

func useCasesGroup1NewTask(t *testing.T, id string) *entities.Task {
	t.Helper()
	taskID := useCasesGroup1MustTaskID(t, id)
	task, err := entities.NewTask(entities.Task{ID: &taskID, Title: "title", Description: "description"})
	if err != nil {
		t.Fatalf("NewTask(%q): %v", id, err)
	}
	return task
}

func useCasesGroup1NewTaskWithStatus(t *testing.T, id, status string) *entities.Task {
	t.Helper()
	task := useCasesGroup1NewTask(t, id)
	st, err := value_objects.NewTaskStatus(status)
	if err != nil {
		t.Fatalf("NewTaskStatus(%q): %v", status, err)
	}
	task.Status = &st
	return task
}

func useCasesGroup1WantMessage(t *testing.T, got *string, want string) {
	t.Helper()
	if got == nil {
		t.Fatalf("message = nil, want %q", want)
	}
	if *got != want {
		t.Errorf("message = %q, want %q", *got, want)
	}
}

func TestAddDependencySuccess(t *testing.T) {
	task := useCasesGroup1NewTask(t, "task-1")
	dependencyTask := useCasesGroup1NewTaskWithStatus(t, "task-2", "done")
	repo := &useCasesGroup1TaskRepo{
		byID:      map[string]*entities.Task{"task-1": task},
		allStates: map[string]*entities.Task{"task-2": dependencyTask},
	}
	uc := NewAddDependencyUseCase(repo)

	resp, err := uc.Execute(context.Background(), dependency.NewAddDependencyRequest("task-1", "task-2", nil))
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if !resp.Success {
		t.Errorf("Success = false, want true")
	}
	useCasesGroup1WantMessage(t, resp.Message,
		"Dependency task-2 added successfully (dependency is completed - task can proceed immediately)")
	if resp.TaskID != "task-1" {
		t.Errorf("TaskID = %v, want task-1", resp.TaskID)
	}
	if resp.DependsOnTaskID != "task-2" {
		t.Errorf("DependsOnTaskID = %v, want task-2", resp.DependsOnTaskID)
	}
	if resp.DependencyType == nil || *resp.DependencyType != "blocks" {
		t.Errorf("DependencyType = %v, want blocks", resp.DependencyType)
	}
	if resp.Errors != nil {
		t.Errorf("Errors = %v, want nil", resp.Errors)
	}
	if !task.HasDependency(useCasesGroup1MustTaskID(t, "task-2")) {
		t.Errorf("task dependency was not added")
	}
	if len(repo.saved) != 1 || repo.saved[0] != task {
		t.Errorf("Save calls = %d, want 1 with the task", len(repo.saved))
	}
}

func TestAddDependencyAlreadyExists(t *testing.T) {
	task := useCasesGroup1NewTask(t, "task-1")
	if err := task.AddDependency(useCasesGroup1MustTaskID(t, "task-2")); err != nil {
		t.Fatalf("AddDependency: %v", err)
	}
	repo := &useCasesGroup1TaskRepo{
		byID:      map[string]*entities.Task{"task-1": task},
		allStates: map[string]*entities.Task{"task-2": useCasesGroup1NewTask(t, "task-2")},
	}
	uc := NewAddDependencyUseCase(repo)

	resp, err := uc.Execute(context.Background(), dependency.NewAddDependencyRequest("task-1", "task-2", nil))
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if resp.Success {
		t.Errorf("Success = true, want false")
	}
	useCasesGroup1WantMessage(t, resp.Message, "Dependency task-2 already exists")
	if resp.TaskID != "task-1" || resp.DependsOnTaskID != "task-2" {
		t.Errorf("ids = (%v, %v), want (task-1, task-2)", resp.TaskID, resp.DependsOnTaskID)
	}
	if resp.DependencyType != nil {
		t.Errorf("DependencyType = %v, want nil", resp.DependencyType)
	}
	if len(repo.saved) != 0 {
		t.Errorf("Save calls = %d, want 0", len(repo.saved))
	}
}

func TestAddDependencyCircular(t *testing.T) {
	task := useCasesGroup1NewTask(t, "task-1")
	repo := &useCasesGroup1TaskRepo{
		byID:      map[string]*entities.Task{"task-1": task},
		allStates: map[string]*entities.Task{"task-1": task},
	}
	uc := NewAddDependencyUseCase(repo)

	resp, err := uc.Execute(context.Background(), dependency.NewAddDependencyRequest("task-1", "task-1", nil))
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if resp.Success {
		t.Errorf("Success = true, want false")
	}
	useCasesGroup1WantMessage(t, resp.Message, "Cannot add dependency: would create circular reference")
	if resp.TaskID != "task-1" || resp.DependsOnTaskID != "task-1" {
		t.Errorf("ids = (%v, %v), want (task-1, task-1)", resp.TaskID, resp.DependsOnTaskID)
	}
	if len(repo.saved) != 0 {
		t.Errorf("Save calls = %d, want 0", len(repo.saved))
	}
}

func TestAddDependencyTaskNotFound(t *testing.T) {
	repo := &useCasesGroup1TaskRepo{byID: map[string]*entities.Task{}}
	uc := NewAddDependencyUseCase(repo)

	_, err := uc.Execute(context.Background(), dependency.NewAddDependencyRequest("task-1", "task-2", nil))
	if err == nil {
		t.Fatalf("Execute error = nil, want TaskNotFoundError")
	}
	var notFound *exceptions.TaskNotFoundError
	if !errors.As(err, &notFound) {
		t.Fatalf("error type = %T, want *exceptions.TaskNotFoundError", err)
	}
	if err.Error() != "Task task-1 not found" {
		t.Errorf("error = %q, want %q", err.Error(), "Task task-1 not found")
	}
}

func TestAddDependencyDependencyNotFound(t *testing.T) {
	task := useCasesGroup1NewTask(t, "task-1")
	repo := &useCasesGroup1TaskRepo{byID: map[string]*entities.Task{"task-1": task}}
	uc := NewAddDependencyUseCase(repo)

	_, err := uc.Execute(context.Background(), dependency.NewAddDependencyRequest("task-1", "task-2", nil))
	if err == nil {
		t.Fatalf("Execute error = nil, want TaskNotFoundError")
	}
	var notFound *exceptions.TaskNotFoundError
	if !errors.As(err, &notFound) {
		t.Fatalf("error type = %T, want *exceptions.TaskNotFoundError", err)
	}
	want := "Dependency task task-2 not found in active, completed, or archived tasks"
	if err.Error() != want {
		t.Errorf("error = %q, want %q", err.Error(), want)
	}
}

func TestClearDependencies(t *testing.T) {
	task := useCasesGroup1NewTask(t, "task-1")
	if err := task.AddDependency(useCasesGroup1MustTaskID(t, "task-2")); err != nil {
		t.Fatalf("AddDependency: %v", err)
	}
	if err := task.AddDependency(useCasesGroup1MustTaskID(t, "task-3")); err != nil {
		t.Fatalf("AddDependency: %v", err)
	}
	repo := &useCasesGroup1TaskRepo{byID: map[string]*entities.Task{"task-1": task}}
	uc := NewClearDependenciesUseCase(repo)

	// Python raises TypeError (unexpected keyword 'dependencies') after clearing and saving.
	if _, err := uc.Execute(context.Background(), "task-1"); err == nil {
		t.Fatalf("Execute: want TypeError, got nil")
	}
	if len(task.Dependencies) != 0 {
		t.Errorf("Dependencies = %v, want empty", task.GetDependencyIDs())
	}
	if len(repo.saved) != 1 || repo.saved[0] != task {
		t.Errorf("Save calls = %d, want 1 with the task", len(repo.saved))
	}
}

func TestClearDependenciesTaskNotFound(t *testing.T) {
	repo := &useCasesGroup1TaskRepo{byID: map[string]*entities.Task{}}
	uc := NewClearDependenciesUseCase(repo)

	_, err := uc.Execute(context.Background(), "task-1")
	if err == nil {
		t.Fatalf("Execute error = nil, want TaskNotFoundError")
	}
	var notFound *exceptions.TaskNotFoundError
	if !errors.As(err, &notFound) {
		t.Fatalf("error type = %T, want *exceptions.TaskNotFoundError", err)
	}
	if err.Error() != "Task task-1 not found" {
		t.Errorf("error = %q, want %q", err.Error(), "Task task-1 not found")
	}
}

func TestUpdateContextNotFound(t *testing.T) {
	repo := &useCasesGroup1ContextRepo{exists: false}
	uc := NewUpdateContextUseCase(repo)

	resp, err := uc.Execute(context.Background(), &ctxdto.UpdateContextRequest{TaskID: "task-1"})
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if resp.Success {
		t.Errorf("Success = true, want false")
	}
	if resp.Message != "Operation failed" {
		t.Errorf("Message = %q, want %q", resp.Message, "Operation failed")
	}
	if resp.Error == nil || *resp.Error != "Context not found for task task-1" {
		t.Errorf("Error = %v, want Context not found for task task-1", resp.Error)
	}
	if resp.Data != nil {
		t.Errorf("Data = %v, want nil", resp.Data)
	}
	if resp.Context != nil {
		t.Errorf("Context = %v, want nil", resp.Context)
	}
}

func TestUpdateContextSuccess(t *testing.T) {
	metadata, err := entities.NewContextMetadata(entities.ContextMetadata{TaskID: "task-1"})
	if err != nil {
		t.Fatalf("NewContextMetadata: %v", err)
	}
	taskContext := entities.NewTaskContext(metadata, entities.ContextObjective{Title: "objective"})

	repo := &useCasesGroup1ContextRepo{
		exists:       true,
		taskContext:  taskContext,
		updateResult: map[string]any{"status": "updated"},
	}
	uc := NewUpdateContextUseCase(repo)

	data := entities.NewOrderedMap[any]()
	data.Set("custom_key", "custom_value")
	resp, err := uc.Execute(context.Background(), &ctxdto.UpdateContextRequest{TaskID: "task-1", Data: data})
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if !resp.Success {
		t.Errorf("Success = false, want true")
	}
	if resp.Message != "Context updated successfully" {
		t.Errorf("Message = %q, want %q", resp.Message, "Context updated successfully")
	}
	if resp.Error != nil {
		t.Errorf("Error = %v, want nil", resp.Error)
	}
	if resp.Context == nil || resp.Context.Metadata == nil || resp.Context.Metadata.TaskID != "task-1" {
		t.Fatalf("Context = %v, want task-1 context", resp.Context)
	}
	if repo.updated != resp.Context {
		t.Errorf("UpdateContext received a different context pointer")
	}
	if resp.Data == nil || resp.Data.Len() != 1 {
		t.Fatalf("Data = %v, want one entry", resp.Data)
	}
	if got, _ := resp.Data.Get("status"); got != "updated" {
		t.Errorf("Data[status] = %v, want updated", got)
	}
	foundCustom := false
	for _, section := range resp.Context.CustomSections {
		if section.Name != "root_level_custom_fields" {
			continue
		}
		if got, _ := section.Data["custom_key"]; got == "custom_value" {
			foundCustom = true
		}
	}
	if !foundCustom {
		t.Errorf("merged custom_key not found in root_level_custom_fields")
	}
}

func TestUpdateContextSuccessWithoutData(t *testing.T) {
	metadata, err := entities.NewContextMetadata(entities.ContextMetadata{TaskID: "task-1"})
	if err != nil {
		t.Fatalf("NewContextMetadata: %v", err)
	}
	taskContext := entities.NewTaskContext(metadata, entities.ContextObjective{Title: "objective"})

	repo := &useCasesGroup1ContextRepo{
		exists:       true,
		taskContext:  taskContext,
		updateResult: map[string]any{},
	}
	uc := NewUpdateContextUseCase(repo)

	resp, err := uc.Execute(context.Background(), &ctxdto.UpdateContextRequest{TaskID: "task-1"})
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if !resp.Success {
		t.Errorf("Success = false, want true")
	}
	if resp.Message != "Context updated successfully" {
		t.Errorf("Message = %q, want %q", resp.Message, "Context updated successfully")
	}
	if repo.updated != taskContext {
		t.Errorf("UpdateContext did not receive the fetched context")
	}
}

func TestGetAgentNotFound(t *testing.T) {
	repo := &useCasesGroup1AgentRepo{err: exceptions.NewAgentNotFoundError("Agent not found")}
	uc := NewGetAgentUseCase(repo)

	resp := uc.Execute(context.Background(), &GetAgentRequest{ProjectID: "project-1", AgentID: "agent-1"})
	if resp.Success {
		t.Errorf("Success = true, want false")
	}
	if resp.Error == nil || *resp.Error != "Agent not found" {
		t.Errorf("Error = %v, want Agent not found", resp.Error)
	}
	if resp.Agent != nil {
		t.Errorf("Agent = %v, want nil", resp.Agent)
	}
	if resp.WorkloadStatus != nil {
		t.Errorf("WorkloadStatus = %v, want nil", resp.WorkloadStatus)
	}
}

func TestGetAgentSuccess(t *testing.T) {
	repo := &useCasesGroup1AgentRepo{data: map[string]any{
		"id":          "agent-1",
		"name":        "Agent One",
		"call_agent":  "coding-agent",
		"assignments": []any{"project-1"},
	}}
	uc := NewGetAgentUseCase(repo)

	resp := uc.Execute(context.Background(), &GetAgentRequest{ProjectID: "project-1", AgentID: "agent-1"})
	if !resp.Success {
		t.Fatalf("Success = false, want true")
	}
	if resp.Error != nil {
		t.Errorf("Error = %v, want nil", resp.Error)
	}
	if resp.Agent == nil {
		t.Fatalf("Agent = nil, want value")
	}
	if resp.Agent.ID != "agent-1" || resp.Agent.Name != "Agent One" || resp.Agent.CallAgent != "coding-agent" {
		t.Errorf("Agent = %+v", *resp.Agent)
	}
	if len(resp.Agent.Assignments) != 1 || resp.Agent.Assignments[0] != "project-1" {
		t.Errorf("Assignments = %v, want [project-1]", resp.Agent.Assignments)
	}
	if resp.WorkloadStatus == nil || *resp.WorkloadStatus != "Available for assignment analysis" {
		t.Errorf("WorkloadStatus = %v, want Available for assignment analysis", resp.WorkloadStatus)
	}
}
