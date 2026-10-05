package facades

import (
	"context"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	domainservices "agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// gbGitBranchService is the consumer-side port of the GitBranchService methods the
// facade calls. Signatures match application/services.GitBranchService.
type gbGitBranchService interface {
	CreateGitBranch(ctx context.Context, projectID, branchName, description string) (*entities.OrderedMap[any], error)
	GetGitBranch(ctx context.Context, projectID, branchName string) (*entities.OrderedMap[any], error)
	ListGitBranchs(ctx context.Context, projectID string) (*entities.OrderedMap[any], error)
	DeleteGitBranch(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error)
}

// gbBranchRepository extends the domain GitBranchRepository with FindAllByProject,
// which GitBranchNameValidator needs.
type gbBranchRepository interface {
	repositories.GitBranchRepository
	FindAllByProject(ctx context.Context, projectID string) ([]*entities.GitBranch, error)
}

// gbTaskRepository extends the domain TaskRepository with the concrete ORM method used
// for statistics.
type gbTaskRepository interface {
	repositories.TaskRepository
	GetTasksByGitBranchID(ctx context.Context, gitBranchID string) ([]*entities.OrderedMap[any], error)
}

// gbRepositoryProvider is the consumer-side port of RepositoryProviderService's
// get_git_branch_repository/get_task_repository.
type gbRepositoryProvider interface {
	GetGitBranchRepository(userID *string) (gbBranchRepository, error)
	GetTaskRepository(projectID *string, userID *string) (gbTaskRepository, error)
}

// gbTaskRepositoryFactory is the consumer-side port of
// TaskRepositoryFactory.create_repository (unported).
type gbTaskRepositoryFactory interface {
	CreateRepository(ctx context.Context, projectID, gitBranchName string, userID *string) (gbTaskRepository, error)
}

// gbWebSocketNotifier is the consumer-side port of
// WebSocketNotificationService.sync_broadcast_branch_event (unported). It swallows its
// own errors in Python.
type gbWebSocketNotifier interface {
	SyncBroadcastBranchEvent(eventType, branchID, projectID string, userID *string, branchData *entities.OrderedMap[any])
}

// gbAgentFacade is the consumer-side port of the agent facade obtained from
// FacadeService.get_agent_facade.
type gbAgentFacade interface {
	AssignAgent(ctx context.Context, projectID, agentID, gitBranchID *string) (*entities.OrderedMap[any], error)
	UnassignAgent(ctx context.Context, projectID, agentID, gitBranchID *string) (*entities.OrderedMap[any], error)
}

// GitBranchApplicationFacade mirrors git_branch_application_facade.GitBranchApplicationFacade.
// Python reads RepositoryProviderService/TaskRepositoryFactory/FacadeService singletons
// inside methods; those are injected here because they are unported or global.
type GitBranchApplicationFacade struct {
	gitBranchService gbGitBranchService
	projectID        *string
	userID           *string
	repoProvider     gbRepositoryProvider
	taskRepoFactory  gbTaskRepositoryFactory
	notifier         gbWebSocketNotifier
	agentFacade      gbAgentFacade
}

// NewGitBranchApplicationFacade mirrors __init__(git_branch_service=None,
// project_repo=None, project_id=None, user_id=None). Python builds GitBranchService from
// project_repo when no service is given; there is no exported Go constructor, so a ready
// service is required. repoProvider/taskRepoFactory/notifier/agentFacade replace the
// Python singletons.
func NewGitBranchApplicationFacade(gitBranchService gbGitBranchService, repoProvider gbRepositoryProvider, taskRepoFactory gbTaskRepositoryFactory, notifier gbWebSocketNotifier, agentFacade gbAgentFacade, projectID, userID *string) *GitBranchApplicationFacade {
	return &GitBranchApplicationFacade{
		gitBranchService: gitBranchService,
		projectID:        projectID,
		userID:           userID,
		repoProvider:     repoProvider,
		taskRepoFactory:  taskRepoFactory,
		notifier:         notifier,
		agentFacade:      agentFacade,
	}
}

func gbTruthy(s *string) bool { return s != nil && *s != "" }

func gbFail(msg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", msg)
	return m
}

func gbFailCode(code, msg string) *entities.OrderedMap[any] {
	m := gbFail(msg)
	m.Set("error_code", code)
	return m
}

func gbValue(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

func gbString(v any) string {
	if v == nil {
		return ""
	}
	return value_objects.PyStr(v)
}

// gbListOf normalises OrderedMap list values (Python lists) to []any.
func gbListOf(v any) []any {
	switch t := v.(type) {
	case nil:
		return nil
	case []any:
		return t
	case []*entities.OrderedMap[any]:
		out := make([]any, len(t))
		for i, e := range t {
			out[i] = e
		}
		return out
	}
	return nil
}

func gbAsMap(v any) *entities.OrderedMap[any] {
	if m, ok := v.(*entities.OrderedMap[any]); ok {
		return m
	}
	return nil
}

// CreateTree mirrors create_tree(project_id, tree_name, description="").
func (f *GitBranchApplicationFacade) CreateTree(ctx context.Context, projectID, treeName, description string) (*entities.OrderedMap[any], error) {
	if !gbTruthy(f.userID) {
		return gbFail("User authentication required"), nil
	}
	if f.repoProvider == nil {
		return gbFail("Repository provider not configured"), nil
	}
	repo, err := f.repoProvider.GetGitBranchRepository(f.userID)
	if err != nil {
		return gbFail(err.Error()), nil
	}
	validator := domainservices.NewGitBranchNameValidator(repo)
	if err := validator.ValidateBranchName(ctx, treeName, projectID, nil); err != nil {
		return gbFail(err.Error()), nil
	}
	return f.gitBranchService.CreateGitBranch(ctx, projectID, treeName, description)
}

// gbBroadcastCreate mirrors the inner WebSocket notification block shared by the two
// asyncio branches of create_git_branch.
func (f *GitBranchApplicationFacade) gbBroadcastCreate(projectID, gitBranchName, gitBranchDescription string, result *entities.OrderedMap[any]) {
	if f.notifier == nil {
		return
	}
	if v, _ := result.Get("success"); !value_objects.PyTruthy(v) {
		return
	}
	branchData := gbAsMap(gbValue(result, "git_branch"))
	if branchData == nil {
		return
	}
	data := entities.NewOrderedMap[any]()
	data.Set("id", gbString(gbValue(branchData, "id")))
	gbn := gbValue(branchData, "git_branch_name")
	if gbn == nil || !value_objects.PyTruthy(gbn) {
		gbn = gbValue(branchData, "name")
	}
	if gbn == nil || !value_objects.PyTruthy(gbn) {
		gbn = gitBranchName
	}
	data.Set("git_branch_name", gbn)
	data.Set("name", gbValue(branchData, "name"))
	desc := gbValue(branchData, "description")
	if desc == nil {
		desc = gitBranchDescription
	}
	data.Set("description", desc)
	data.Set("project_id", projectID)
	userID := f.userID
	if !gbTruthy(userID) {
		system := "system"
		userID = &system
	}
	f.notifier.SyncBroadcastBranchEvent("created", gbString(gbValue(branchData, "id")), projectID, userID, data)
}

// CreateGitBranch mirrors create_git_branch(project_id, git_branch_name,
// git_branch_description="").
func (f *GitBranchApplicationFacade) CreateGitBranch(ctx context.Context, projectID, gitBranchName, gitBranchDescription string) *entities.OrderedMap[any] {
	result, err := f.CreateTree(ctx, projectID, gitBranchName, gitBranchDescription)
	if err != nil {
		return gbFailCode("CREATION_FAILED", "Failed to create git branch: "+err.Error())
	}
	f.gbBroadcastCreate(projectID, gitBranchName, gitBranchDescription, result)
	return result
}

// UpdateGitBranch mirrors update_git_branch(git_branch_id, git_branch_name=None,
// git_branch_description=None, project_id=None).
func (f *GitBranchApplicationFacade) UpdateGitBranch(ctx context.Context, gitBranchID string, gitBranchName, gitBranchDescription, projectID *string) *entities.OrderedMap[any] {
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("message", "Git branch "+gitBranchID+" updated successfully")
	result.Set("git_branch_id", gitBranchID)

	branchResult := f.GetGitBranchByID(ctx, gitBranchID)
	if v, _ := branchResult.Get("success"); value_objects.PyTruthy(v) {
		branchData := gbAsMap(gbValue(branchResult, "git_branch"))
		var actualProjectID any
		if branchData != nil {
			if pv, ok := branchData.Get("project_id"); ok {
				actualProjectID = pv
			}
		}
		if actualProjectID == nil {
			actualProjectID = projectID
		}
		if f.notifier != nil {
			data := entities.NewOrderedMap[any]()
			data.Set("id", gitBranchID)
			gbn := gbValue(branchData, "git_branch_name")
			if gitBranchName != nil && *gitBranchName != "" {
				gbn = *gitBranchName
			}
			if gbn == nil || !value_objects.PyTruthy(gbn) {
				gbn = gbValue(branchData, "name")
			}
			if gbn == nil || !value_objects.PyTruthy(gbn) {
				gbn = ""
			}
			data.Set("git_branch_name", gbn)
			data.Set("name", gbValue(branchData, "name"))
			desc := gbValue(branchData, "description")
			if gitBranchDescription != nil && *gitBranchDescription != "" {
				desc = *gitBranchDescription
			}
			if desc == nil {
				desc = ""
			}
			data.Set("description", desc)
			data.Set("project_id", gbString(actualProjectID))
			userID := f.userID
			if !gbTruthy(userID) {
				system := "system"
				userID = &system
			}
			f.notifier.SyncBroadcastBranchEvent("updated", gitBranchID, gbString(actualProjectID), userID, data)
		}
	}
	return result
}

// GetGitBranch mirrors get_git_branch(project_id, git_branch_id).
func (f *GitBranchApplicationFacade) GetGitBranch(ctx context.Context, projectID, gitBranchID string) *entities.OrderedMap[any] {
	result := f.GetGitBranchByID(ctx, gitBranchID)
	// Python only logs a warning on project id mismatch; result is unchanged.
	return result
}

// GetGitBranchByID mirrors get_git_branch_by_id(git_branch_id).
func (f *GitBranchApplicationFacade) GetGitBranchByID(ctx context.Context, gitBranchID string) *entities.OrderedMap[any] {
	return f.findGitBranchByID(ctx, gitBranchID)
}

// findGitBranchByID mirrors _find_git_branch_by_id.
func (f *GitBranchApplicationFacade) findGitBranchByID(ctx context.Context, gitBranchID string) *entities.OrderedMap[any] {
	if !gbTruthy(f.userID) {
		return gbFailCode("GET_FAILED", "Failed to get git branch: User authentication required. No user ID provided.")
	}
	if f.repoProvider == nil {
		return gbFailCode("GET_FAILED", "Failed to get git branch: Repository provider not configured")
	}
	repo, err := f.repoProvider.GetGitBranchRepository(f.userID)
	if err != nil {
		return gbFailCode("GET_FAILED", "Failed to get git branch: "+err.Error())
	}
	gitBranch, err := repo.FindByID(ctx, gitBranchID, nil)
	if err != nil {
		return gbFailCode("GET_FAILED", "Failed to get git branch: "+err.Error())
	}
	if gitBranch == nil {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("error", "Git branch not found: "+gitBranchID)
		m.Set("error_code", "NOT_FOUND")
		return m
	}
	var createdAt, updatedAt any
	if gitBranch.CreatedAt != nil {
		createdAt = value_objects.IsoFormat(*gitBranch.CreatedAt)
	}
	if gitBranch.UpdatedAt != nil {
		updatedAt = value_objects.IsoFormat(*gitBranch.UpdatedAt)
	}
	branch := entities.NewOrderedMap[any]()
	branch.Set("id", gitBranch.GetEntityID())
	branch.Set("name", gitBranch.Name)
	branch.Set("description", gitBranch.Description)
	branch.Set("project_id", gitBranch.ProjectID)
	branch.Set("created_at", createdAt)
	branch.Set("updated_at", updatedAt)
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("git_branch", branch)
	return m
}

// getBranchEntity mirrors _get_branch_entity.
func (f *GitBranchApplicationFacade) getBranchEntity(ctx context.Context, gitBranchID string, repo gbBranchRepository) *entities.GitBranch {
	if repo == nil {
		return nil
	}
	branch, err := repo.FindByID(ctx, gitBranchID, nil)
	if err != nil {
		return nil
	}
	return branch
}

// DeleteGitBranch mirrors delete_git_branch(git_branch_id, project_id=None).
func (f *GitBranchApplicationFacade) DeleteGitBranch(ctx context.Context, gitBranchID string, projectID *string) *entities.OrderedMap[any] {
	targetProjectID := projectID
	if !gbTruthy(targetProjectID) {
		targetProjectID = f.projectID
	}
	result, err := f.gitBranchService.DeleteGitBranch(ctx, gbString(targetProjectID), gitBranchID)
	if err != nil {
		return gbFailCode("DELETE_FAILED", "Failed to delete git branch: "+err.Error())
	}
	return result
}

// gbTransformTrees mirrors the list transformation duplicated in both branches of
// list_git_branchs.
func gbTransformTrees(result *entities.OrderedMap[any], projectID string) *entities.OrderedMap[any] {
	gitBranchs := []any{}
	for _, treeAny := range gbListOf(gbValue(result, "git_branchs")) {
		tree := gbAsMap(treeAny)
		if tree == nil {
			continue
		}
		desc := gbValue(tree, "description")
		if desc == nil {
			desc = ""
		}
		taskCount := gbValue(tree, "task_count")
		if taskCount == nil {
			taskCount = 0
		}
		completed := gbValue(tree, "completed_tasks")
		if completed == nil {
			completed = 0
		}
		progress := gbValue(tree, "progress")
		if progress == nil {
			progress = 0.0
		}
		entry := entities.NewOrderedMap[any]()
		entry.Set("id", gbValue(tree, "id"))
		entry.Set("name", gbValue(tree, "name"))
		entry.Set("description", desc)
		entry.Set("created_at", gbValue(tree, "created_at"))
		entry.Set("task_count", taskCount)
		entry.Set("completed_tasks", completed)
		entry.Set("progress", progress)
		gitBranchs = append(gitBranchs, entry)
	}
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("git_branchs", gitBranchs)
	m.Set("total_count", len(gitBranchs))
	m.Set("message", "Listed git branches for project "+projectID)
	return m
}

// ListGitBranchs mirrors list_git_branchs(project_id).
func (f *GitBranchApplicationFacade) ListGitBranchs(ctx context.Context, projectID string) *entities.OrderedMap[any] {
	result, err := f.ListTrees(ctx, projectID)
	if err != nil {
		return gbFailCode("LIST_FAILED", "Failed to list git branches: "+err.Error())
	}
	if v, _ := result.Get("success"); value_objects.PyTruthy(v) {
		return gbTransformTrees(result, projectID)
	}
	return result
}

// GetTree mirrors get_tree(project_id, tree_name).
func (f *GitBranchApplicationFacade) GetTree(ctx context.Context, projectID, treeName string) (*entities.OrderedMap[any], error) {
	return f.gitBranchService.GetGitBranch(ctx, projectID, treeName)
}

// ListTrees mirrors list_trees(project_id).
func (f *GitBranchApplicationFacade) ListTrees(ctx context.Context, projectID string) (*entities.OrderedMap[any], error) {
	return f.gitBranchService.ListGitBranchs(ctx, projectID)
}

// AssignAgent mirrors assign_agent(git_branch_id, agent_id, project_id=None).
func (f *GitBranchApplicationFacade) AssignAgent(ctx context.Context, gitBranchID, agentID string, projectID *string) *entities.OrderedMap[any] {
	if !gbTruthy(f.userID) {
		return gbFailCode("AUTHENTICATION_REQUIRED", "Agent assignment requires user authentication. No user ID was provided.")
	}
	if f.agentFacade == nil {
		return gbFailCode("ASSIGNMENT_FAILED", "Failed to assign agent: Agent facade not configured")
	}
	targetProjectID := projectID
	if !gbTruthy(targetProjectID) {
		targetProjectID = f.projectID
	}
	result, err := f.agentFacade.AssignAgent(ctx, targetProjectID, &agentID, &gitBranchID)
	if err != nil {
		return gbFailCode("ASSIGNMENT_FAILED", "Failed to assign agent: "+err.Error())
	}
	return result
}

// UnassignAgent mirrors unassign_agent(git_branch_id, agent_id, project_id=None).
func (f *GitBranchApplicationFacade) UnassignAgent(ctx context.Context, gitBranchID, agentID string, projectID *string) *entities.OrderedMap[any] {
	if !gbTruthy(f.userID) {
		return gbFailCode("AUTHENTICATION_REQUIRED", "Agent unassignment requires user authentication. No user ID was provided.")
	}
	if f.agentFacade == nil {
		return gbFailCode("UNASSIGNMENT_FAILED", "Failed to unassign agent: Agent facade not configured")
	}
	targetProjectID := projectID
	if !gbTruthy(targetProjectID) {
		targetProjectID = f.projectID
	}
	result, err := f.agentFacade.UnassignAgent(ctx, targetProjectID, &agentID, &gitBranchID)
	if err != nil {
		return gbFailCode("UNASSIGNMENT_FAILED", "Failed to unassign agent: "+err.Error())
	}
	return result
}

func gbTaskStatus(task *entities.OrderedMap[any]) any {
	if task == nil {
		return nil
	}
	v, _ := task.Get("status")
	return v
}

func gbProgressPercent(task *entities.OrderedMap[any]) float64 {
	if task == nil {
		return 0
	}
	v, _ := task.Get("progress_percentage")
	if v == nil {
		return 0
	}
	f, ok := value_objects.PyFloat(v)
	if !ok {
		return 0
	}
	return f
}

// gbStatusCounts mirrors the repeated in_progress/todo/blocked counting.
func gbStatusCounts(tasks []*entities.OrderedMap[any]) (int, int, int) {
	inProgress, todo, blocked := 0, 0, 0
	for _, task := range tasks {
		switch s := gbTaskStatus(task).(type) {
		case string:
			switch s {
			case "in_progress":
				inProgress++
			case "todo":
				todo++
			case "blocked":
				blocked++
			}
		}
	}
	return inProgress, todo, blocked
}

func gbSumProgress(tasks []*entities.OrderedMap[any]) float64 {
	total := 0.0
	for _, task := range tasks {
		total += gbProgressPercent(task)
	}
	return total
}

func gbLastActivity(tasks []*entities.OrderedMap[any]) any {
	var maxVal any
	for _, task := range tasks {
		v, ok := task.Get("updated_at")
		if !ok || v == nil {
			continue
		}
		if maxVal == nil || gbString(v) > gbString(maxVal) {
			maxVal = v
		}
	}
	return maxVal
}

// GetStatistics mirrors get_statistics(project_id, git_branch_id).
func (f *GitBranchApplicationFacade) GetStatistics(ctx context.Context, projectID, gitBranchID string) *entities.OrderedMap[any] {
	if f.repoProvider == nil {
		return gbFailCode("STATISTICS_FAILED", "Failed to get git branch statistics: Repository provider not configured")
	}
	taskRepo, err := f.repoProvider.GetTaskRepository(&projectID, f.userID)
	if err != nil {
		return gbFailCode("STATISTICS_FAILED", "Failed to get git branch statistics: "+err.Error())
	}
	tasks := []*entities.OrderedMap[any]{}
	if taskRepo != nil {
		taskObjs, terr := taskRepo.GetTasksByGitBranchID(ctx, gitBranchID)
		if terr != nil {
			return gbFailCode("STATISTICS_FAILED", "Failed to get git branch statistics: "+terr.Error())
		}
		tasks = taskObjs
	}
	branchRepo, berr := f.repoProvider.GetGitBranchRepository(f.userID)
	if berr != nil {
		return gbFailCode("STATISTICS_FAILED", "Failed to get git branch statistics: "+berr.Error())
	}
	branch := f.getBranchEntity(ctx, gitBranchID, branchRepo)
	if branch == nil {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("error", "Branch "+gitBranchID+" not found")
		m.Set("error_code", "BRANCH_NOT_FOUND")
		return m
	}

	// Python uses getattr(branch, "task_count", 0); GitBranch has no such attribute
	// (only get_task_count()), so both denormalized counts are always 0. Kept as-is.
	totalTasks := 0
	completedTasks := 0
	inProgress, todo, blocked := gbStatusCounts(tasks)
	totalProgress := gbSumProgress(tasks)
	progressPercentage := 0.0
	if totalTasks > 0 {
		progressPercentage = totalProgress / float64(totalTasks)
	}

	statistics := entities.NewOrderedMap[any]()
	statistics.Set("task_count", totalTasks)
	statistics.Set("completed_tasks", completedTasks)
	statistics.Set("in_progress_tasks", inProgress)
	statistics.Set("todo_tasks", todo)
	statistics.Set("blocked_tasks", blocked)
	statistics.Set("progress_percentage", value_objects.PyRound(progressPercentage, 2))
	statistics.Set("last_activity", gbLastActivity(tasks))
	statistics.Set("assigned_agents", []any{})
	statistics.Set("git_branch_id", gitBranchID)
	statistics.Set("project_id", projectID)
	statistics.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))

	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("statistics", statistics)
	m.Set("message", "Statistics retrieved for git branch "+gitBranchID)
	return m
}

// GetBranchesWithTaskCounts mirrors get_branches_with_task_counts(project_id).
func (f *GitBranchApplicationFacade) GetBranchesWithTaskCounts(ctx context.Context, projectID string) *entities.OrderedMap[any] {
	branchesResult := f.ListGitBranchs(ctx, projectID)
	if v, _ := branchesResult.Get("success"); !value_objects.PyTruthy(v) {
		return branchesResult
	}
	branches := gbListOf(gbValue(branchesResult, "git_branchs"))

	enhancedBranches := []any{}
	for _, branchAny := range branches {
		branch := gbAsMap(branchAny)
		if branch == nil {
			continue
		}
		branchID := gbString(gbValue(branch, "id"))
		tasks := []*entities.OrderedMap[any]{}
		if f.taskRepoFactory != nil {
			branchName := gbString(gbValue(branch, "name"))
			if branchName == "" {
				branchName = "main"
			}
			taskRepo, err := f.taskRepoFactory.CreateRepository(ctx, projectID, branchName, f.userID)
			if err != nil {
				return gbBranchesCountsFailure(err)
			}
			if taskRepo != nil {
				taskObjs, terr := taskRepo.GetTasksByGitBranchID(ctx, branchID)
				if terr != nil {
					return gbBranchesCountsFailure(terr)
				}
				tasks = taskObjs
			}
		}
		totalTasks := 0
		if v := gbValue(branch, "task_count"); v != nil && value_objects.PyTruthy(v) {
			if n, ok := value_objects.PyFloat(v); ok {
				totalTasks = int(n)
			}
		}
		completedTasks := 0
		if v := gbValue(branch, "completed_task_count"); v != nil && value_objects.PyTruthy(v) {
			if n, ok := value_objects.PyFloat(v); ok {
				completedTasks = int(n)
			}
		}
		inProgress, todo, blocked := gbStatusCounts(tasks)
		totalProgress := gbSumProgress(tasks)
		progressPercentage := 0.0
		if totalTasks > 0 {
			progressPercentage = totalProgress / float64(totalTasks)
		}
		enhanced := entities.NewOrderedMap[any]()
		enhanced.Set("id", branchID)
		enhanced.Set("name", gbValue(branch, "name"))
		gbn := gbValue(branch, "git_branch_name")
		if gbn == nil || !value_objects.PyTruthy(gbn) {
			gbn = gbValue(branch, "name")
		}
		enhanced.Set("git_branch_name", gbn)
		desc := gbValue(branch, "description")
		if desc == nil {
			desc = ""
		}
		enhanced.Set("description", desc)
		enhanced.Set("project_id", projectID)
		enhanced.Set("task_count", totalTasks)
		enhanced.Set("completed_tasks", completedTasks)
		enhanced.Set("in_progress_tasks", inProgress)
		enhanced.Set("todo_tasks", todo)
		enhanced.Set("blocked_tasks", blocked)
		enhanced.Set("progress_percentage", value_objects.PyRound(progressPercentage, 2))
		enhanced.Set("created_at", gbValue(branch, "created_at"))
		enhanced.Set("updated_at", gbValue(branch, "updated_at"))
		enhancedBranches = append(enhancedBranches, enhanced)
	}

	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("branches", enhancedBranches)
	m.Set("total_count", len(enhancedBranches))
	return m
}

// GetProjectBranchSummary mirrors get_project_branch_summary(project_id).
func (f *GitBranchApplicationFacade) GetProjectBranchSummary(ctx context.Context, projectID string) *entities.OrderedMap[any] {
	branchesResult := f.GetBranchesWithTaskCounts(ctx, projectID)
	if v, _ := branchesResult.Get("success"); !value_objects.PyTruthy(v) {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("summary", entities.NewOrderedMap[any]())
		m.Set("error", gbValue(branchesResult, "error"))
		return m
	}
	branches := gbListOf(gbValue(branchesResult, "branches"))

	totalBranches := len(branches)
	totalTasks, totalCompleted, totalInProgress, totalTodo, totalBlocked := 0, 0, 0, 0, 0
	for _, branchAny := range branches {
		branch := gbAsMap(branchAny)
		if branch == nil {
			continue
		}
		totalTasks += gbIntDefault(branch, "task_count")
		totalCompleted += gbIntDefault(branch, "completed_tasks")
		totalInProgress += gbIntDefault(branch, "in_progress_tasks")
		totalTodo += gbIntDefault(branch, "todo_tasks")
		totalBlocked += gbIntDefault(branch, "blocked_tasks")
	}
	overallProgress := 0.0
	if totalTasks > 0 {
		overallProgress = float64(totalCompleted) / float64(totalTasks) * 100
	}
	var mostActiveBranch any
	if len(branches) > 0 {
		mostActive := gbAsMap(branches[0])
		for _, branchAny := range branches[1:] {
			branch := gbAsMap(branchAny)
			if branch != nil && gbIntDefault(branch, "task_count") > gbIntDefault(mostActive, "task_count") {
				mostActive = branch
			}
		}
		if gbIntDefault(mostActive, "task_count") > 0 {
			entry := entities.NewOrderedMap[any]()
			entry.Set("id", gbValue(mostActive, "id"))
			entry.Set("name", gbValue(mostActive, "name"))
			entry.Set("task_count", gbValue(mostActive, "task_count"))
			mostActiveBranch = entry
		}
	}

	summary := entities.NewOrderedMap[any]()
	summary.Set("total_branches", totalBranches)
	summary.Set("task_count", totalTasks)
	summary.Set("completed_tasks", totalCompleted)
	summary.Set("in_progress_tasks", totalInProgress)
	summary.Set("todo_tasks", totalTodo)
	summary.Set("blocked_tasks", totalBlocked)
	summary.Set("overall_progress", value_objects.PyRound(overallProgress, 2))
	summary.Set("most_active_branch", mostActiveBranch)
	summary.Set("project_id", projectID)

	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("summary", summary)
	return m
}

func gbIntDefault(m *entities.OrderedMap[any], key string) int {
	v := gbValue(m, key)
	if v == nil {
		return 0
	}
	f, ok := value_objects.PyFloat(v)
	if !ok {
		return 0
	}
	return int(f)
}

// GetBranchSummary mirrors get_branch_summary(branch_id).
func (f *GitBranchApplicationFacade) GetBranchSummary(ctx context.Context, branchID string) *entities.OrderedMap[any] {
	branchResult := f.GetGitBranchByID(ctx, branchID)
	if v, _ := branchResult.Get("success"); !value_objects.PyTruthy(v) {
		errVal := gbValue(branchResult, "error")
		if errVal == nil {
			errVal = "Branch " + branchID + " not found"
		}
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("branch", nil)
		m.Set("error", errVal)
		return m
	}
	branch := gbAsMap(gbValue(branchResult, "git_branch"))

	tasks := []*entities.OrderedMap[any]{}
	if f.repoProvider != nil {
		taskRepo, err := f.repoProvider.GetTaskRepository(nil, nil)
		if err != nil {
			return gbBranchSummaryFailure(err)
		}
		if taskRepo != nil {
			taskObjs, terr := taskRepo.GetTasksByGitBranchID(ctx, branchID)
			if terr != nil {
				return gbBranchSummaryFailure(terr)
			}
			tasks = taskObjs
		}
	}
	// Python getattr(branch, "task_count"/"completed_task_count") on a plain dict
	// returns the 0 default (the git_branch dict has neither key).
	totalTasks := 0
	completedTasks := 0
	inProgress, todo, blocked := gbStatusCounts(tasks)
	totalProgress := gbSumProgress(tasks)
	progressPercentage := 0.0
	if totalTasks > 0 {
		progressPercentage = totalProgress / float64(totalTasks)
	}

	desc := gbValue(branch, "description")
	if desc == nil {
		desc = ""
	}
	gbn := gbValue(branch, "git_branch_name")
	if gbn == nil || !value_objects.PyTruthy(gbn) {
		gbn = gbValue(branch, "name")
	}
	branchSummary := entities.NewOrderedMap[any]()
	branchSummary.Set("id", branchID)
	branchSummary.Set("name", gbValue(branch, "name"))
	branchSummary.Set("git_branch_name", gbn)
	branchSummary.Set("description", desc)
	branchSummary.Set("project_id", gbValue(branch, "project_id"))
	branchSummary.Set("task_count", totalTasks)
	branchSummary.Set("completed_tasks", completedTasks)
	branchSummary.Set("in_progress_tasks", inProgress)
	branchSummary.Set("todo_tasks", todo)
	branchSummary.Set("blocked_tasks", blocked)
	branchSummary.Set("progress_percentage", value_objects.PyRound(progressPercentage, 2))
	branchSummary.Set("created_at", gbValue(branch, "created_at"))
	branchSummary.Set("updated_at", gbValue(branch, "updated_at"))

	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("branch", branchSummary)
	return m
}

// Exported names for the consumer-side ports so the composition root can implement them.
type (
	GitBranchFacadeService      = gbGitBranchService
	GitBranchFacadeBranchRepo   = gbBranchRepository
	GitBranchFacadeTaskRepo     = gbTaskRepository
	GitBranchFacadeRepoProvider = gbRepositoryProvider
	GitBranchFacadeTaskFactory  = gbTaskRepositoryFactory
	GitBranchFacadeNotifier     = gbWebSocketNotifier
	GitBranchFacadeAgentFacade  = gbAgentFacade
)

// gbBranchesCountsFailure is the outer-except response of get_branches_with_task_counts.
func gbBranchesCountsFailure(err error) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", "Failed to get branches with task counts: "+err.Error())
	m.Set("branches", []any{})
	return m
}

// gbBranchSummaryFailure is the outer-except response of get_branch_summary.
func gbBranchSummaryFailure(err error) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("branch", nil)
	m.Set("error", "Failed to get branch summary: "+err.Error())
	return m
}
