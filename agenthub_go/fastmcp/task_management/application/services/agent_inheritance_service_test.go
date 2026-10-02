package services

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// zpAInheritTaskRepo is a fake TaskRepository exposing only FindByID.
type zpAInheritTaskRepo struct {
	repositories.TaskRepository
	task *entities.Task
	err  error
}

func (r *zpAInheritTaskRepo) FindByID(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
	if r.err != nil {
		return nil, r.err
	}
	return r.task, nil
}

// zpAInheritSubtaskRepo is a fake SubtaskRepository exposing FindByParentTaskID and Save.
type zpAInheritSubtaskRepo struct {
	repositories.SubtaskRepository
	subtasks []*entities.Subtask
	saved    []*entities.Subtask
	findErr  error
	saveErr  error
}

func (r *zpAInheritSubtaskRepo) FindByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) ([]*entities.Subtask, error) {
	if r.findErr != nil {
		return nil, r.findErr
	}
	return r.subtasks, nil
}

func (r *zpAInheritSubtaskRepo) Save(ctx context.Context, subtask *entities.Subtask) (bool, error) {
	if r.saveErr != nil {
		return false, r.saveErr
	}
	r.saved = append(r.saved, subtask)
	return true, nil
}

func zpAInheritanceMustTaskID(t *testing.T, value string) value_objects.TaskId {
	t.Helper()
	id, err := value_objects.NewTaskId(value)
	if err != nil {
		t.Fatalf("NewTaskId(%q) failed: %v", value, err)
	}
	return id
}

func zpAInheritanceNewTask(t *testing.T, title string, assignees []string) *entities.Task {
	t.Helper()
	task, err := entities.NewTask(entities.Task{Title: title, Description: "d", Assignees: assignees})
	if err != nil {
		t.Fatalf("NewTask(%q) failed: %v", title, err)
	}
	return task
}

func zpAInheritanceNewSubtask(t *testing.T, id *value_objects.TaskId, title string, parentID value_objects.TaskId, assignees []string) *entities.Subtask {
	t.Helper()
	subtask, err := entities.NewSubtask(entities.Subtask{ID: id, Title: title, ParentTaskID: &parentID, Assignees: assignees})
	if err != nil {
		t.Fatalf("NewSubtask(%q) failed: %v", title, err)
	}
	return subtask
}

func zpAInheritanceExpectKeys(t *testing.T, m *entities.OrderedMap[any], want []string) {
	t.Helper()
	got := m.Keys()
	if len(got) != len(want) {
		t.Fatalf("keys = %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("keys = %v, want %v", got, want)
		}
	}
}

func TestAgentInheritanceService_ApplyAgentInheritance_Inherits(t *testing.T) {
	taskID := zpAInheritanceMustTaskID(t, "task-1")
	parent := zpAInheritanceNewTask(t, "parent", []string{"@coding-agent"})
	subtask := zpAInheritanceNewSubtask(t, nil, "s1", taskID, nil)

	svc := NewAgentInheritanceService(&zpAInheritTaskRepo{task: parent}, &zpAInheritSubtaskRepo{})
	got, err := svc.ApplyAgentInheritance(context.Background(), subtask, nil)
	if err != nil {
		t.Fatalf("ApplyAgentInheritance error: %v", err)
	}
	if !zpAInheritanceStringSlicesEqual(got.Assignees, []string{"@coding-agent"}) {
		t.Fatalf("Assignees = %v, want [@coding-agent]", got.Assignees)
	}
}

func TestAgentInheritanceService_ApplyAgentInheritance_KeepsExistingAssignees(t *testing.T) {
	taskID := zpAInheritanceMustTaskID(t, "task-1")
	parent := zpAInheritanceNewTask(t, "parent", []string{"@coding-agent"})
	subtask := zpAInheritanceNewSubtask(t, nil, "s1", taskID, []string{"@existing"})

	svc := NewAgentInheritanceService(&zpAInheritTaskRepo{task: parent}, &zpAInheritSubtaskRepo{})
	got, err := svc.ApplyAgentInheritance(context.Background(), subtask, nil)
	if err != nil {
		t.Fatalf("ApplyAgentInheritance error: %v", err)
	}
	if !zpAInheritanceStringSlicesEqual(got.Assignees, []string{"@existing"}) {
		t.Fatalf("Assignees = %v, want [@existing]", got.Assignees)
	}
}

func TestAgentInheritanceService_ApplyAgentInheritance_ParentMissing(t *testing.T) {
	taskID := zpAInheritanceMustTaskID(t, "task-1")
	subtask := zpAInheritanceNewSubtask(t, nil, "s1", taskID, nil)

	svc := NewAgentInheritanceService(&zpAInheritTaskRepo{task: nil}, &zpAInheritSubtaskRepo{})
	got, err := svc.ApplyAgentInheritance(context.Background(), subtask, nil)
	if err != nil {
		t.Fatalf("ApplyAgentInheritance error: %v", err)
	}
	if len(got.Assignees) != 0 {
		t.Fatalf("Assignees = %v, want empty", got.Assignees)
	}
}

func TestAgentInheritanceService_ApplyInheritanceToAllSubtasks(t *testing.T) {
	taskID := zpAInheritanceMustTaskID(t, "task-1")
	parent := zpAInheritanceNewTask(t, "parent", []string{"@coding-agent"})
	inheriting := zpAInheritanceNewSubtask(t, nil, "s1", taskID, nil)
	explicit := zpAInheritanceNewSubtask(t, nil, "s2", taskID, []string{"@existing"})
	subtaskRepo := &zpAInheritSubtaskRepo{subtasks: []*entities.Subtask{inheriting, explicit}}

	svc := NewAgentInheritanceService(&zpAInheritTaskRepo{task: parent}, subtaskRepo)
	updated, err := svc.ApplyInheritanceToAllSubtasks(context.Background(), taskID)
	if err != nil {
		t.Fatalf("ApplyInheritanceToAllSubtasks error: %v", err)
	}
	if len(updated) != 1 || updated[0] != inheriting {
		t.Fatalf("updated = %v, want [s1]", updated)
	}
	if len(subtaskRepo.saved) != 1 || subtaskRepo.saved[0] != inheriting {
		t.Fatalf("saved = %v, want [s1]", subtaskRepo.saved)
	}
	if !zpAInheritanceStringSlicesEqual(inheriting.Assignees, []string{"@coding-agent"}) {
		t.Fatalf("inheriting.Assignees = %v, want [@coding-agent]", inheriting.Assignees)
	}
	if !zpAInheritanceStringSlicesEqual(explicit.Assignees, []string{"@existing"}) {
		t.Fatalf("explicit.Assignees = %v, want [@existing]", explicit.Assignees)
	}
}

func TestAgentInheritanceService_ApplyInheritanceToAllSubtasks_ParentMissing(t *testing.T) {
	taskID := zpAInheritanceMustTaskID(t, "task-1")
	subtaskRepo := &zpAInheritSubtaskRepo{subtasks: []*entities.Subtask{zpAInheritanceNewSubtask(t, nil, "s1", taskID, nil)}}

	svc := NewAgentInheritanceService(&zpAInheritTaskRepo{task: nil}, subtaskRepo)
	updated, err := svc.ApplyInheritanceToAllSubtasks(context.Background(), taskID)
	if err != nil {
		t.Fatalf("ApplyInheritanceToAllSubtasks error: %v", err)
	}
	if len(updated) != 0 {
		t.Fatalf("updated = %v, want empty", updated)
	}
	if len(subtaskRepo.saved) != 0 {
		t.Fatalf("saved = %v, want empty", subtaskRepo.saved)
	}
}

func TestAgentInheritanceService_ValidateAgentAssignments(t *testing.T) {
	svc := NewAgentInheritanceService(&zpAInheritTaskRepo{}, &zpAInheritSubtaskRepo{})

	empty, err := svc.ValidateAgentAssignments([]string{})
	if err != nil || len(empty) != 0 {
		t.Fatalf("empty = %v, %v; want [] and nil", empty, err)
	}

	valid, err := svc.ValidateAgentAssignments([]string{"coding-agent"})
	if err != nil {
		t.Fatalf("valid error: %v", err)
	}
	if !zpAInheritanceStringSlicesEqual(valid, []string{"@coding-agent"}) {
		t.Fatalf("valid = %v, want [@coding-agent]", valid)
	}

	if _, err := svc.ValidateAgentAssignments([]string{"nonexistent-agent-xyz"}); err == nil {
		t.Fatalf("expected ValueError for invalid assignee")
	}
}

func TestAgentInheritanceService_GetInheritanceSummary_Missing(t *testing.T) {
	taskID := zpAInheritanceMustTaskID(t, "task-1")
	svc := NewAgentInheritanceService(&zpAInheritTaskRepo{task: nil}, &zpAInheritSubtaskRepo{})

	summary, err := svc.GetInheritanceSummary(context.Background(), taskID)
	if err != nil {
		t.Fatalf("GetInheritanceSummary error: %v", err)
	}
	zpAInheritanceExpectKeys(t, summary, []string{"error"})
	value, _ := summary.Get("error")
	if value != "Task task-1 not found" {
		t.Fatalf("error = %v", value)
	}
}

func TestAgentInheritanceService_GetInheritanceSummary(t *testing.T) {
	taskID := zpAInheritanceMustTaskID(t, "task-1")
	subtaskID1 := zpAInheritanceMustTaskID(t, "sub-1")
	subtaskID2 := zpAInheritanceMustTaskID(t, "sub-2")
	parent := zpAInheritanceNewTask(t, "parent", []string{"@coding-agent", "@review-agent"})
	s1 := zpAInheritanceNewSubtask(t, &subtaskID1, "s1", taskID, nil)
	s2 := zpAInheritanceNewSubtask(t, &subtaskID2, "s2", taskID, []string{"@x"})
	svc := NewAgentInheritanceService(&zpAInheritTaskRepo{task: parent}, &zpAInheritSubtaskRepo{subtasks: []*entities.Subtask{s1, s2}})

	summary, err := svc.GetInheritanceSummary(context.Background(), taskID)
	if err != nil {
		t.Fatalf("GetInheritanceSummary error: %v", err)
	}
	zpAInheritanceExpectKeys(t, summary, []string{
		"task_id", "parent_assignees", "parent_assignee_count", "total_subtasks",
		"subtasks_with_assignees", "subtasks_inheriting", "subtask_details",
	})
	if v, _ := summary.Get("task_id"); v != "task-1" {
		t.Fatalf("task_id = %v", v)
	}
	if v, _ := summary.Get("parent_assignee_count"); v != 2 {
		t.Fatalf("parent_assignee_count = %v", v)
	}
	if v, _ := summary.Get("total_subtasks"); v != 2 {
		t.Fatalf("total_subtasks = %v", v)
	}
	if v, _ := summary.Get("subtasks_with_assignees"); v != 1 {
		t.Fatalf("subtasks_with_assignees = %v", v)
	}
	if v, _ := summary.Get("subtasks_inheriting"); v != 1 {
		t.Fatalf("subtasks_inheriting = %v", v)
	}
	detailsAny, _ := summary.Get("subtask_details")
	details, ok := detailsAny.([]*entities.OrderedMap[any])
	if !ok || len(details) != 2 {
		t.Fatalf("subtask_details = %v", detailsAny)
	}
	zpAInheritanceExpectKeys(t, details[0], []string{"id", "title", "has_assignees", "should_inherit", "current_assignees", "assignee_count"})
	if v, _ := details[0].Get("id"); v != "sub-1" {
		t.Fatalf("details[0].id = %v", v)
	}
	if v, _ := details[0].Get("has_assignees"); v != false {
		t.Fatalf("details[0].has_assignees = %v", v)
	}
	if v, _ := details[0].Get("should_inherit"); v != true {
		t.Fatalf("details[0].should_inherit = %v", v)
	}
	if v, _ := details[0].Get("assignee_count"); v != 0 {
		t.Fatalf("details[0].assignee_count = %v", v)
	}
	if v, _ := details[1].Get("assignee_count"); v != 1 {
		t.Fatalf("details[1].assignee_count = %v", v)
	}
}
