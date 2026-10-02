package services

import (
	"context"

	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ContextDerivationService derives context (project, branch name, user) from
// tasks and git branches. Both repositories are optional (nil = absent). Like
// Python, derivation failures (including repository errors) fall back to the
// default context instead of surfacing.
type ContextDerivationService struct {
	taskRepository      repositories.TaskRepository
	gitBranchRepository repositories.GitBranchRepository
}

// NewContextDerivationService builds the service; either repository may be nil.
func NewContextDerivationService(t repositories.TaskRepository, g repositories.GitBranchRepository) *ContextDerivationService {
	return &ContextDerivationService{t, g}
}

// DeriveContextFromTask resolves the task's git branch context, else the default.
func (s *ContextDerivationService) DeriveContextFromTask(ctx context.Context, taskID string, defaultUserID string) map[string]string {
	if s.taskRepository != nil {
		if id, err := value_objects.NewTaskId(taskID); err == nil {
			if task, err := s.taskRepository.FindByID(ctx, id); err == nil && task != nil && task.GitBranchID != nil && *task.GitBranchID != "" {
				return s.DeriveContextFromGitBranch(ctx, *task.GitBranchID, defaultUserID)
			}
		}
	}
	return s.getDefaultContext(defaultUserID)
}

// DeriveContextFromGitBranch returns project_id, git_branch_name and user_id for the
// branch. Python also looks for `git_branch.project.user_id`, but the GitBranch
// entity has no `project` attribute, so the user is always default_user_id (or the
// resolved fallback).
func (s *ContextDerivationService) DeriveContextFromGitBranch(ctx context.Context, gitBranchID string, defaultUserID string) map[string]string {
	if s.gitBranchRepository != nil {
		if b, err := s.gitBranchRepository.FindByID(ctx, gitBranchID, nil); err == nil && b != nil {
			user := defaultUserID
			if user == "" {
				user = s.resolveUserID(defaultUserID)
			}
			return map[string]string{"project_id": b.ProjectID, "git_branch_name": b.Name, "user_id": user}
		}
	}
	return s.getDefaultContext(defaultUserID)
}

// DeriveContextHierarchy builds the global/project/branch/task hierarchy from the
// identifiers provided (empty string = None).
func (s *ContextDerivationService) DeriveContextHierarchy(ctx context.Context, taskID, gitBranchID, projectID, userID string) map[string]any {
	global := map[string]any{}
	project := map[string]any{}
	branch := map[string]any{}
	task := map[string]any{}
	if userID != "" {
		global["user_id"] = userID
	}
	if projectID != "" {
		project["project_id"] = projectID
	}
	if gitBranchID != "" {
		bc := s.DeriveContextFromGitBranch(ctx, gitBranchID, userID)
		branch = toAnyMap(bc)
		if p, _ := project["project_id"].(string); p == "" {
			project["project_id"] = bc["project_id"]
		}
	}
	if taskID != "" {
		tc := s.DeriveContextFromTask(ctx, taskID, userID)
		task = toAnyMap(tc)
		if len(branch) == 0 {
			branch = map[string]any{"git_branch_name": tc["git_branch_name"], "project_id": tc["project_id"]}
		}
		if p, _ := project["project_id"].(string); p == "" {
			project["project_id"] = tc["project_id"]
		}
	}
	return map[string]any{"global": global, "project": project, "branch": branch, "task": task}
}

func toAnyMap(m map[string]string) map[string]any {
	out := make(map[string]any, len(m))
	for k, v := range m {
		out[k] = v
	}
	return out
}

func (s *ContextDerivationService) getDefaultContext(defaultUserID string) map[string]string {
	return map[string]string{"project_id": "default_project", "git_branch_name": "main", "user_id": s.resolveUserID(defaultUserID)}
}

func (s *ContextDerivationService) resolveUserID(defaultUserID string) string {
	if defaultUserID != "" {
		return defaultUserID
	}
	return "system"
}

// DetermineContextLevel returns "task", "branch", "project" or "global".
func (s *ContextDerivationService) DetermineContextLevel(taskID, gitBranchID, projectID string) string {
	switch {
	case taskID != "":
		return "task"
	case gitBranchID != "":
		return "branch"
	case projectID != "":
		return "project"
	}
	return "global"
}
