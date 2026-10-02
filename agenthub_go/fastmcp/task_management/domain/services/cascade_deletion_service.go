package services

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// DeleteScope is the scope of a cascade deletion.
type DeleteScope string

const (
	DeleteScopeTaskOnly         DeleteScope = "task_only"
	DeleteScopeTaskWithSubtasks DeleteScope = "task_with_subtasks"
	DeleteScopeTaskFull         DeleteScope = "task_full"    // Task + Subtasks + Contexts
	DeleteScopeBranchFull       DeleteScope = "branch_full"  // Branch + All Tasks/Subtasks/Contexts
	DeleteScopeProjectFull      DeleteScope = "project_full" // Project + All Branches/Tasks/Subtasks/Contexts
)

// DeleteScopeValues lists the scopes in declaration order.
var DeleteScopeValues = []DeleteScope{DeleteScopeTaskOnly, DeleteScopeTaskWithSubtasks, DeleteScopeTaskFull, DeleteScopeBranchFull, DeleteScopeProjectFull}

// The service is duck-typed in Python (repositories have no declared type), and it
// calls methods the domain repository ABCs do not declare (branch find_by_project_id,
// delete, task find_by_git_branch_id). The narrow consumer-side interfaces below list
// exactly the methods it uses.

// CascadeTaskRepository is the task repository surface used by the service.
type CascadeTaskRepository interface {
	FindByID(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error)
	FindByGitBranchID(ctx context.Context, branchID string) ([]*entities.Task, error)
	Delete(ctx context.Context, taskID value_objects.TaskId) (bool, error)
}

// CascadeSubtaskRepository is the subtask repository surface used by the service.
type CascadeSubtaskRepository interface {
	CountByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) (int, error)
	DeleteByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) (bool, error)
}

// CascadeBranchRepository is the branch repository surface used by the service.
type CascadeBranchRepository interface {
	FindByID(ctx context.Context, branchID string) (*entities.GitBranch, error)
	FindByProjectID(ctx context.Context, projectID string) ([]*entities.GitBranch, error)
	Delete(ctx context.Context, branchID string) (bool, error)
}

// CascadeProjectRepository is the project repository surface used by the service.
type CascadeProjectRepository interface {
	FindByID(ctx context.Context, projectID string) (*entities.Project, error)
	Delete(ctx context.Context, projectID string) (bool, error)
}

// CascadeContextRepository deletes a context by ID.
type CascadeContextRepository interface {
	Delete(ctx context.Context, contextID string) error
}

// CascadeDeletionService deletes an entity together with everything beneath it.
// Only task entities carry a context_id, so branch and project context deletion
// (guarded by hasattr(..., "context_id") in Python) never runs for the current
// GitBranch and Project entities.
//
// Known Python defect preserved: the three _dispatch_*_deleted_event helpers always
// fail (TaskDeletedEvent/ProjectDeletedEvent have no `create`, and
// branch_lifecycle_events.py cannot be imported), the exception is swallowed, and no
// event is ever dispatched - yet "task_deleted"/"branch_deleted"/"project_deleted"
// are still listed in stats["events_dispatched"]. The Go port reproduces exactly that.
type CascadeDeletionService struct {
	taskRepository    CascadeTaskRepository
	subtaskRepository CascadeSubtaskRepository
	branchRepository  CascadeBranchRepository
	projectRepository CascadeProjectRepository
	contextRepository CascadeContextRepository // may be nil
}

// NewCascadeDeletionService builds the service; contextRepository may be nil.
func NewCascadeDeletionService(t CascadeTaskRepository, s CascadeSubtaskRepository, b CascadeBranchRepository,
	p CascadeProjectRepository, c CascadeContextRepository) *CascadeDeletionService {
	return &CascadeDeletionService{t, s, b, p, c}
}

// DeleteTaskCascade deletes a task and, per scope, its subtasks and context. A
// malformed task ID or a repository failure while finding/deleting the task is
// returned as an error (uncaught in Python).
func (s *CascadeDeletionService) DeleteTaskCascade(ctx context.Context, taskID string, scope DeleteScope) (map[string]any, error) {
	stats := map[string]any{"task_deleted": false, "subtasks_deleted": 0, "contexts_deleted": 0, "events_dispatched": []string{}}
	id, err := value_objects.NewTaskId(taskID)
	if err != nil {
		return nil, err
	}
	task, err := s.taskRepository.FindByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return stats, nil
	}
	if scope == DeleteScopeTaskWithSubtasks || scope == DeleteScopeTaskFull {
		stats["subtasks_deleted"] = s.deleteTaskSubtasks(ctx, id)
	}
	if scope == DeleteScopeTaskFull && s.contextRepository != nil && task.ContextID != nil && *task.ContextID != "" {
		if err := s.contextRepository.Delete(ctx, *task.ContextID); err == nil {
			stats["contexts_deleted"] = stats["contexts_deleted"].(int) + 1
		}
	}
	success, err := s.taskRepository.Delete(ctx, id)
	if err != nil {
		return nil, err
	}
	stats["task_deleted"] = success
	if success {
		// _dispatch_task_deleted_event always fails in Python (see type comment).
		stats["events_dispatched"] = append(stats["events_dispatched"].([]string), "task_deleted")
	}
	return stats, nil
}

// DeleteBranchCascade deletes every task in the branch, then the branch.
func (s *CascadeDeletionService) DeleteBranchCascade(ctx context.Context, branchID string) (map[string]any, error) {
	stats := map[string]any{"branch_deleted": false, "tasks_deleted": 0, "subtasks_deleted": 0, "contexts_deleted": 0, "events_dispatched": []string{}}
	branch, err := s.branchRepository.FindByID(ctx, branchID)
	if err != nil {
		return nil, err
	}
	if branch == nil {
		return stats, nil
	}
	tasks, err := s.taskRepository.FindByGitBranchID(ctx, branchID)
	if err != nil {
		return nil, err
	}
	for _, task := range tasks {
		id := "None"
		if task.ID != nil {
			id = task.ID.Value
		}
		ts, err := s.DeleteTaskCascade(ctx, id, DeleteScopeTaskFull)
		if err != nil {
			return nil, err
		}
		if ts["task_deleted"] == true {
			stats["tasks_deleted"] = stats["tasks_deleted"].(int) + 1
			stats["subtasks_deleted"] = stats["subtasks_deleted"].(int) + ts["subtasks_deleted"].(int)
			stats["contexts_deleted"] = stats["contexts_deleted"].(int) + ts["contexts_deleted"].(int)
		}
	}
	success, err := s.branchRepository.Delete(ctx, branchID)
	if err != nil {
		return nil, err
	}
	stats["branch_deleted"] = success
	if success {
		stats["events_dispatched"] = append(stats["events_dispatched"].([]string), "branch_deleted")
	}
	return stats, nil
}

// DeleteProjectCascade deletes every branch in the project, then the project.
func (s *CascadeDeletionService) DeleteProjectCascade(ctx context.Context, projectID string) (map[string]any, error) {
	stats := map[string]any{"project_deleted": false, "branches_deleted": 0, "tasks_deleted": 0, "subtasks_deleted": 0,
		"contexts_deleted": 0, "events_dispatched": []string{}}
	project, err := s.projectRepository.FindByID(ctx, projectID)
	if err != nil {
		return nil, err
	}
	if project == nil {
		return stats, nil
	}
	branches, err := s.branchRepository.FindByProjectID(ctx, projectID)
	if err != nil {
		return nil, err
	}
	for _, b := range branches {
		id := "None"
		if b.ID != nil {
			id = b.ID.Value
		}
		bs, err := s.DeleteBranchCascade(ctx, id)
		if err != nil {
			return nil, err
		}
		if bs["branch_deleted"] == true {
			stats["branches_deleted"] = stats["branches_deleted"].(int) + 1
			for _, k := range []string{"tasks_deleted", "subtasks_deleted", "contexts_deleted"} {
				stats[k] = stats[k].(int) + bs[k].(int)
			}
		}
	}
	success, err := s.projectRepository.Delete(ctx, projectID)
	if err != nil {
		return nil, err
	}
	stats["project_deleted"] = success
	if success {
		stats["events_dispatched"] = append(stats["events_dispatched"].([]string), "project_deleted")
	}
	return stats, nil
}

// deleteTaskSubtasks returns the number of deleted subtasks; any failure yields 0.
func (s *CascadeDeletionService) deleteTaskSubtasks(ctx context.Context, taskID value_objects.TaskId) int {
	count, err := s.subtaskRepository.CountByParentTaskID(ctx, taskID)
	if err != nil {
		return 0
	}
	ok, err := s.subtaskRepository.DeleteByParentTaskID(ctx, taskID)
	if err != nil || !ok {
		return 0
	}
	return count
}
