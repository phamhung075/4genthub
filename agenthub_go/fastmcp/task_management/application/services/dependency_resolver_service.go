package services

import (
	"context"
	"fmt"
	"strings"

	"agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// DependencyResolverService ports dependency_resolver_service.DependencyResolverService.
type DependencyResolverService struct {
	taskRepository repositories.TaskRepository
	userID         *string
}

// NewDependencyResolverService builds the service. userID nil mirrors Python None.
func NewDependencyResolverService(taskRepository repositories.TaskRepository, userID *string) *DependencyResolverService {
	return &DependencyResolverService{taskRepository: taskRepository, userID: userID}
}

// WithUser mirrors with_user(user_id): a new service sharing the repository.
func (s *DependencyResolverService) WithUser(userID string) *DependencyResolverService {
	return NewDependencyResolverService(s.taskRepository, &userID)
}

// userScopedRepository mirrors _get_user_scoped_repository: the Go repository
// interfaces expose no with_user/user_id/session attributes, so the repository
// is returned unchanged.
func (s *DependencyResolverService) userScopedRepository() repositories.TaskRepository {
	return s.taskRepository
}

// ResolveDependencies ports resolve_dependencies. TaskNotFoundError propagates;
// any other lookup/parse error yields the empty fallback relationships.
func (s *DependencyResolverService) ResolveDependencies(ctx context.Context, taskID string) (*task.DependencyRelationships, error) {
	repo := s.userScopedRepository()

	id, err := value_objects.NewTaskId(taskID)
	if err != nil {
		return depResolveEmptyRelationships(taskID), nil
	}

	mainTask, err := repo.FindByID(ctx, id)
	if err != nil {
		return depResolveEmptyRelationships(taskID), nil
	}
	if mainTask == nil {
		return nil, exceptions.NewTaskNotFoundError(fmt.Sprintf("Task %s not found", taskID))
	}

	dependencyGraph := s.buildDependencyGraph(ctx, taskID)

	dependsOn := s.resolveDirectDependencies(ctx, repo, mainTask.GetDependencyIDs())
	blocks := s.resolveBlockingTasks(ctx, repo, taskID)

	upstreamChains := s.buildUpstreamChains(ctx, repo, taskID, dependencyGraph)
	downstreamChains := s.buildDownstreamChains(ctx, repo, taskID, dependencyGraph)

	totalDependencies := len(dependsOn)
	completedDependencies := 0
	blockedDependencies := 0
	for _, dep := range dependsOn {
		if dep.Status == "done" {
			completedDependencies++
		}
		if dep.Status == "blocked" {
			blockedDependencies++
		}
	}

	canStart := depResolveCanTaskStart(dependsOn)
	isBlocked := depResolveIsTaskBlocked(dependsOn)
	isBlockingOthers := len(blocks) > 0

	rels := task.DependencyRelationships{
		TaskID:                taskID,
		DependsOn:             dependsOn,
		Blocks:                blocks,
		UpstreamChains:        upstreamChains,
		DownstreamChains:      downstreamChains,
		TotalDependencies:     totalDependencies,
		CompletedDependencies: completedDependencies,
		BlockedDependencies:   blockedDependencies,
		CanStart:              canStart,
		IsBlocked:             isBlocked,
		IsBlockingOthers:      isBlockingOthers,
		DependencySummary:     depResolveGenerateDependencySummary(dependsOn, blocks),
		NextActions:           depResolveGenerateNextActions(dependsOn, blocks, canStart),
		BlockingReasons:       depResolveGenerateBlockingReasons(dependsOn),
	}
	return task.NewDependencyRelationships(rels), nil
}

func depResolveEmptyRelationships(taskID string) *task.DependencyRelationships {
	return task.NewDependencyRelationships(task.DependencyRelationships{
		TaskID:            taskID,
		CanStart:          true,
		DependencySummary: "Unable to resolve dependencies",
		NextActions:       []string{"Check task dependencies manually"},
	})
}

// dependencyInfoFor builds a DependencyInfo from a Task.
func depResolveDependencyInfo(ctx context.Context, repo repositories.TaskRepository, t *entities.Task, isBlocking bool) *task.DependencyInfo {
	effort := t.EstimatedEffort
	assignees := []string{}
	if len(t.Assignees) > 0 {
		assignees = append([]string{}, t.Assignees...)
	}
	return task.NewDependencyInfo(task.DependencyInfo{
		TaskID:               t.ID.Value,
		Title:                t.Title,
		Status:               t.Status.Value,
		Priority:             t.Priority.Value,
		CompletionPercentage: t.OverallProgress,
		IsBlocking:           isBlocking,
		IsBlocked:            depResolveIsTaskBlockedByDependencies(ctx, repo, t),
		EstimatedEffort:      &effort,
		Assignees:            assignees,
		UpdatedAt:            t.UpdatedAt,
	})
}

// buildDependencyGraph ports _build_dependency_graph.
func (s *DependencyResolverService) buildDependencyGraph(ctx context.Context, rootTaskID string) *entities.OrderedMap[[]string] {
	graph := entities.NewOrderedMap[[]string]()
	visited := map[string]bool{}

	var traverse func(taskID string, depth int)
	traverse = func(taskID string, depth int) {
		if visited[taskID] || depth > 10 {
			return
		}
		visited[taskID] = true

		id, err := value_objects.NewTaskId(taskID)
		if err != nil {
			return
		}
		t, err := s.taskRepository.FindByID(ctx, id)
		if err != nil {
			return
		}
		if t != nil {
			dependencies := t.GetDependencyIDs()
			graph.Set(taskID, dependencies)
			for _, depID := range dependencies {
				traverse(depID, depth+1)
			}
		}
	}

	traverse(rootTaskID, 0)
	return graph
}

// resolveDirectDependencies ports _resolve_direct_dependencies.
func (s *DependencyResolverService) resolveDirectDependencies(ctx context.Context, repo repositories.TaskRepository, dependencyIDs []string) []task.DependencyInfo {
	dependencies := []task.DependencyInfo{}
	for _, depID := range dependencyIDs {
		id, err := value_objects.NewTaskId(depID)
		if err != nil {
			continue
		}
		t, err := repo.FindByID(ctx, id)
		if err != nil || t == nil {
			continue
		}
		dependencies = append(dependencies, *depResolveDependencyInfo(ctx, repo, t, false))
	}
	return dependencies
}

// resolveBlockingTasks ports _resolve_blocking_tasks.
func (s *DependencyResolverService) resolveBlockingTasks(ctx context.Context, repo repositories.TaskRepository, taskID string) []task.DependencyInfo {
	blockingTasks := []task.DependencyInfo{}
	allTasks, err := repo.FindAll(ctx)
	if err != nil {
		return blockingTasks
	}
	for _, t := range allTasks {
		for _, depID := range t.GetDependencyIDs() {
			if depID == taskID {
				blockingTasks = append(blockingTasks, *depResolveDependencyInfo(ctx, repo, t, true))
				break
			}
		}
	}
	return blockingTasks
}

// buildUpstreamChains ports _build_upstream_chains.
func (s *DependencyResolverService) buildUpstreamChains(ctx context.Context, repo repositories.TaskRepository, taskID string, graph *entities.OrderedMap[[]string]) []task.DependencyChain {
	chains := []task.DependencyChain{}

	buildChain := func(startTask string, visited map[string]bool) *task.DependencyChain {
		if visited[startTask] {
			return nil
		}
		visited[startTask] = true
		chainTasks := []task.DependencyInfo{}

		queue := []string{startTask}
		for len(queue) > 0 {
			currentTask := queue[0]
			queue = queue[1:]

			id, err := value_objects.NewTaskId(currentTask)
			if err != nil {
				continue
			}
			t, err := repo.FindByID(ctx, id)
			if err == nil && t != nil {
				chainTasks = append(chainTasks, *depResolveDependencyInfo(ctx, repo, t, false))
				deps, _ := graph.Get(currentTask)
				for _, depID := range deps {
					if !visited[depID] {
						queue = append(queue, depID)
						visited[depID] = true
					}
				}
			}
		}

		if len(chainTasks) == 0 {
			return nil
		}

		completedTasks := 0
		blockedTasks := 0
		hasInProgress := false
		for _, t := range chainTasks {
			if t.Status == "done" {
				completedTasks++
			}
			if t.Status == "blocked" {
				blockedTasks++
			}
			if t.Status == "in_progress" {
				hasInProgress = true
			}
		}

		chainStatus := "not_started"
		if completedTasks == len(chainTasks) {
			chainStatus = "completed"
		} else if blockedTasks > 0 {
			chainStatus = "blocked"
		} else if hasInProgress {
			chainStatus = "in_progress"
		}

		return &task.DependencyChain{
			ChainID:        fmt.Sprintf("upstream_%s", startTask),
			Tasks:          chainTasks,
			TotalTasks:     len(chainTasks),
			CompletedTasks: completedTasks,
			BlockedTasks:   blockedTasks,
			ChainStatus:    chainStatus,
		}
	}

	visited := map[string]bool{}
	directDeps, _ := graph.Get(taskID)
	for _, depID := range directDeps {
		if chain := buildChain(depID, visited); chain != nil {
			chains = append(chains, *chain)
		}
	}
	return chains
}

// buildDownstreamChains ports _build_downstream_chains.
func (s *DependencyResolverService) buildDownstreamChains(ctx context.Context, repo repositories.TaskRepository, taskID string, graph *entities.OrderedMap[[]string]) []task.DependencyChain {
	chains := []task.DependencyChain{}

	dependentTasks := []string{}
	for _, tid := range graph.Keys() {
		deps, _ := graph.Get(tid)
		for _, d := range deps {
			if d == taskID {
				dependentTasks = append(dependentTasks, tid)
				break
			}
		}
	}

	for _, depTask := range dependentTasks {
		chainTasks := []task.DependencyInfo{}

		id, err := value_objects.NewTaskId(depTask)
		if err != nil {
			continue
		}
		t, err := repo.FindByID(ctx, id)
		if err == nil && t != nil {
			chainTasks = append(chainTasks, *depResolveDependencyInfo(ctx, repo, t, true))

			completedTasks := 0
			blockedTasks := 0
			for _, ct := range chainTasks {
				if ct.Status == "done" {
					completedTasks++
				}
				if ct.Status == "blocked" {
					blockedTasks++
				}
			}
			chainStatus := "in_progress"
			if completedTasks == len(chainTasks) {
				chainStatus = "completed"
			}
			chains = append(chains, task.DependencyChain{
				ChainID:        fmt.Sprintf("downstream_%s", depTask),
				Tasks:          chainTasks,
				TotalTasks:     len(chainTasks),
				CompletedTasks: completedTasks,
				BlockedTasks:   blockedTasks,
				ChainStatus:    chainStatus,
			})
		}
	}
	return chains
}

func depResolveCanTaskStart(dependencies []task.DependencyInfo) bool {
	for _, dep := range dependencies {
		if dep.Status != "done" {
			return false
		}
	}
	return true
}

func depResolveIsTaskBlocked(dependencies []task.DependencyInfo) bool {
	for _, dep := range dependencies {
		if dep.Status == "blocked" {
			return true
		}
	}
	return false
}

func depResolveIsTaskBlockedByDependencies(ctx context.Context, repo repositories.TaskRepository, t *entities.Task) bool {
	for _, depID := range t.GetDependencyIDs() {
		id, err := value_objects.NewTaskId(depID)
		if err != nil {
			continue
		}
		depTask, err := repo.FindByID(ctx, id)
		if err != nil || depTask == nil {
			continue
		}
		if depTask.Status.Value != "done" && depTask.Status.Value != "cancelled" {
			return true
		}
	}
	return false
}

func depResolveGenerateDependencySummary(dependsOn, blocks []task.DependencyInfo) string {
	if len(dependsOn) == 0 && len(blocks) == 0 {
		return "No dependencies"
	}
	summaryParts := []string{}
	if len(dependsOn) > 0 {
		completed := 0
		for _, dep := range dependsOn {
			if dep.Status == "done" {
				completed++
			}
		}
		total := len(dependsOn)
		summaryParts = append(summaryParts, fmt.Sprintf("Depends on %d task(s) (%d/%d completed)", total, completed, total))
	}
	if len(blocks) > 0 {
		summaryParts = append(summaryParts, fmt.Sprintf("Blocks %d task(s)", len(blocks)))
	}
	return strings.Join(summaryParts, " | ")
}

func depResolveGenerateNextActions(dependsOn, blocks []task.DependencyInfo, canStart bool) []string {
	actions := []string{}
	if canStart {
		actions = append(actions, "✅ Ready to start - no blocking dependencies")
	} else {
		incompleteDeps := []task.DependencyInfo{}
		for _, dep := range dependsOn {
			if dep.Status != "done" {
				incompleteDeps = append(incompleteDeps, dep)
			}
		}
		if len(incompleteDeps) > 0 {
			actions = append(actions, fmt.Sprintf("⏳ Wait for %d dependencies to complete", len(incompleteDeps)))
			todoDeps := 0
			for _, dep := range incompleteDeps {
				if dep.Status == "todo" {
					todoDeps++
				}
			}
			if todoDeps > 0 {
				actions = append(actions, fmt.Sprintf("💡 Consider working on %d unstarted dependencies", todoDeps))
			}
		}
	}
	if len(blocks) > 0 {
		actions = append(actions, fmt.Sprintf("🚧 Completing this task will unblock %d other task(s)", len(blocks)))
	}
	return actions
}

func depResolveGenerateBlockingReasons(dependsOn []task.DependencyInfo) []string {
	reasons := []string{}
	for _, dep := range dependsOn {
		if dep.Status != "done" {
			reasons = append(reasons, fmt.Sprintf("'%s' (%s)", dep.Title, dep.Status))
		}
	}
	return reasons
}
