package api_controllers

import (
	"context"
	"fmt"
	"strconv"
	"time"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/types"
)

// brACFacadeProvider is the consumer-side view of FacadeService.get_branch_facade.
type brACFacadeProvider interface {
	GetBranchFacade(projectID, userID *string) (*facades.GitBranchApplicationFacade, error)
}

// brACRepoProvider is the consumer-side view of the RepositoryProviderService
// getters the controller calls.
type brACRepoProvider interface {
	GetGitBranchRepository(session any, userID *string) (repositories.GitBranchRepository, error)
	GetProjectRepository(session any, userID *string) (repositories.ProjectRepository, error)
}

// brACRow is one result row.
type brACRow []any

// brACResult mirrors SQLAlchemy's Result for the bulk query (fetchall and iteration).
type brACResult interface {
	FetchAll() []brACRow
	Iterate() []brACRow
}

// brACQueryer is the session boundary for the raw SQL bulk-summary queries.
type brACQueryer interface {
	Execute(ctx context.Context, query string, params map[string]any) (brACResult, error)
}

// BranchAPIController mirrors branch_api_controller.BranchAPIController.
type BranchAPIController struct {
	facadeService brACFacadeProvider
	repoProvider  brACRepoProvider
}

// NewBranchAPIController builds the controller.
func NewBranchAPIController(facadeService brACFacadeProvider, repoProvider brACRepoProvider) *BranchAPIController {
	return &BranchAPIController{facadeService: facadeService, repoProvider: repoProvider}
}

func brACNow() *string {
	s := value_objects.IsoFormat(time.Now().UTC())
	return &s
}

func brACGet(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

func brACGetDefault(m *entities.OrderedMap[any], key string, def any) any {
	if m != nil {
		if v, ok := m.Get(key); ok {
			return v
		}
	}
	return def
}

func brACTruthy(m *entities.OrderedMap[any], key string) bool {
	return value_objects.PyTruthy(brACGet(m, key))
}

func brACOptStr(v any) *string {
	if v == nil {
		return nil
	}
	s := value_objects.PyStr(v)
	return &s
}

func brACOptInt(v any) *int {
	if v == nil {
		return nil
	}
	f, ok := value_objects.PyFloat(v)
	if !ok {
		return nil
	}
	i := int(f)
	return &i
}

func brACOptBool(v any) *bool {
	if b, ok := v.(bool); ok {
		return &b
	}
	return nil
}

// brACAsMap coerces a dict value to OrderedMap.
func brACAsMap(v any) *entities.OrderedMap[any] {
	if m, ok := v.(*entities.OrderedMap[any]); ok {
		return m
	}
	return nil
}

// brACBranchDTOBase builds the BranchDTO fields except task_count.
func brACBranchDTOBase(data *entities.OrderedMap[any]) *types.BranchDTO {
	return &types.BranchDTO{
		ID:             value_objects.PyStr(brACGet(data, "id")),
		ProjectID:      value_objects.PyStr(brACGet(data, "project_id")),
		Name:           value_objects.PyStr(brACGetDefault(data, "name", "")),
		GitBranchName:  value_objects.PyStr(brACGetDefault(data, "git_branch_name", brACGetDefault(data, "name", ""))),
		Description:    brACOptStr(brACGet(data, "description")),
		Status:         brACOptStr(brACGet(data, "status")),
		IsActive:       brACOptBool(brACGet(data, "is_active")),
		CreatedAt:      brACOptStr(brACGet(data, "created_at")),
		UpdatedAt:      brACOptStr(brACGet(data, "updated_at")),
		CompletedTasks: brACOptInt(brACGetDefault(data, "completed_tasks", 0)),
	}
}

// brACBranchDTOFromDict builds a BranchDTO the way the controller's inline
// constructor does, with the task_count source selected per call site.
func brACBranchDTOFromDict(data *entities.OrderedMap[any], taskCount any) *types.BranchDTO {
	dto := brACBranchDTOBase(data)
	dto.TaskCount = brACOptInt(taskCount)
	return dto
}

func brACListOf(v any) []any {
	if s, ok := v.([]any); ok {
		return s
	}
	return []any{}
}

// --- methods ---

// GetBranchesWithTaskCounts mirrors get_branches_with_task_counts.
func (c *BranchAPIController) GetBranchesWithTaskCounts(ctx context.Context, projectID, userID string, session any) (resp *types.BranchesResponse) {
	resp = &types.BranchesResponse{Success: false, Timestamp: brACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Error = brACPtr(value_objects.PyStr(r))
			resp.Message = brACPtr("Failed to get branches with task counts")
			resp.Branches = []*types.BranchDTO{}
			resp.Total = brACIntPtr(0)
			resp.Timestamp = brACNow()
		}
	}()
	facade, err := c.facadeService.GetBranchFacade(&projectID, &userID)
	if err != nil {
		return brACBranchesError(err, "Failed to get branches with task counts")
	}
	result := facade.GetBranchesWithTaskCounts(ctx, projectID)
	if !brACTruthy(result, "success") {
		errMsg := value_objects.PyStr(brACGetDefault(result, "error", "Failed to fetch branches"))
		return &types.BranchesResponse{
			Success:   false,
			Error:     &errMsg,
			Message:   brACPtr("Failed to fetch branches"),
			Branches:  []*types.BranchDTO{},
			Total:     brACIntPtr(0),
			Timestamp: brACNow(),
		}
	}
	branchesData := brACListOf(brACGetDefault(result, "branches", []any{}))
	dtos := make([]*types.BranchDTO, 0, len(branchesData))
	for _, b := range branchesData {
		data := brACAsMap(b)
		dto := brACBranchDTOBase(data)
		dto.TaskCount = brACOptInt(brACGetDefault(data, "total_tasks", brACGetDefault(data, "task_count", 0)))
		dtos = append(dtos, dto)
	}
	total := len(dtos)
	return &types.BranchesResponse{
		Success:   true,
		Branches:  dtos,
		Total:     &total,
		Timestamp: brACNow(),
	}
}

// GetBranch mirrors the async wrapper; it delegates to GetSingleBranchSummary.
func (c *BranchAPIController) GetBranch(ctx context.Context, branchID, userID string, session any) *types.BranchResponse {
	return c.GetSingleBranchSummary(ctx, branchID, userID, session)
}

// GetSingleBranchSummary mirrors get_single_branch_summary.
func (c *BranchAPIController) GetSingleBranchSummary(ctx context.Context, branchID, userID string, session any) (resp *types.BranchResponse) {
	resp = &types.BranchResponse{Success: false, Timestamp: brACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Error = brACPtr(value_objects.PyStr(r))
			resp.Message = brACPtr("Failed to get branch summary")
			resp.Branch = nil
			resp.Timestamp = brACNow()
		}
	}()
	repo, err := c.repoProvider.GetGitBranchRepository(session, &userID)
	if err != nil {
		return brACBranchError(err, "Failed to get branch summary")
	}
	gitBranch, err := repo.FindByID(ctx, branchID, nil)
	if err != nil {
		return brACBranchError(err, "Failed to get branch summary")
	}
	if gitBranch == nil {
		return &types.BranchResponse{
			Success:   false,
			Error:     brACPtr("Branch " + branchID + " not found"),
			Message:   brACPtr("Branch not found"),
			Branch:    nil,
			Timestamp: brACNow(),
		}
	}
	facade, err := c.facadeService.GetBranchFacade(&gitBranch.ProjectID, &userID)
	if err != nil {
		return brACBranchError(err, "Failed to get branch summary")
	}
	result := facade.GetBranchSummary(ctx, branchID)
	if !brACTruthy(result, "success") {
		errMsg := value_objects.PyStr(brACGetDefault(result, "error", "Branch "+branchID+" not found"))
		return &types.BranchResponse{
			Success:   false,
			Error:     &errMsg,
			Message:   brACPtr("Failed to get branch summary"),
			Branch:    nil,
			Timestamp: brACNow(),
		}
	}
	branchData := brACAsMap(brACGet(result, "branch"))
	if branchData == nil {
		return &types.BranchResponse{
			Success:   false,
			Error:     brACPtr("Branch " + branchID + " not found"),
			Message:   brACPtr("Branch not found"),
			Branch:    nil,
			Timestamp: brACNow(),
		}
	}
	dto := brACBranchDTOBase(branchData)
	dto.TaskCount = brACOptInt(brACGetDefault(branchData, "total_tasks", 0))
	return &types.BranchResponse{
		Success:   true,
		Branch:    dto,
		Timestamp: brACNow(),
	}
}

// GetProjectBranchStats mirrors get_project_branch_stats.
func (c *BranchAPIController) GetProjectBranchStats(ctx context.Context, projectID, userID string, session any) (resp *types.ApiResponse) {
	resp = &types.ApiResponse{Success: false, Timestamp: brACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Error = brACPtr(value_objects.PyStr(r))
			resp.Message = brACPtr("Failed to get project branch stats")
			resp.Data = brACStatsData(nil)
			resp.Timestamp = brACNow()
		}
	}()
	facade, err := c.facadeService.GetBranchFacade(&projectID, &userID)
	if err != nil {
		return brACAPIError(err, "Failed to get project branch stats", brACStatsData(nil))
	}
	result := facade.GetProjectBranchSummary(ctx, projectID)
	if !brACTruthy(result, "success") {
		errMsg := value_objects.PyStr(brACGetDefault(result, "error", "Failed to fetch branch statistics"))
		return &types.ApiResponse{
			Success:   false,
			Error:     &errMsg,
			Message:   brACPtr("Failed to fetch branch statistics"),
			Data:      brACStatsData(nil),
			Timestamp: brACNow(),
		}
	}
	return &types.ApiResponse{
		Success:   true,
		Data:      brACStatsData(brACGet(result, "summary")),
		Timestamp: brACNow(),
	}
}

func brACStatsData(summary any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	if summary == nil {
		m.Set("stats", entities.NewOrderedMap[any]())
	} else {
		m.Set("stats", summary)
	}
	return m
}

// GetBranchPerformanceMetrics mirrors get_branch_performance_metrics.
func (c *BranchAPIController) GetBranchPerformanceMetrics(ctx context.Context, userID string, session any) (resp *types.ApiResponse) {
	resp = &types.ApiResponse{Success: false, Timestamp: brACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Error = brACPtr(value_objects.PyStr(r))
			resp.Message = brACPtr("Failed to get branch performance metrics")
			resp.Data = brACMetricsErrorData()
			resp.Timestamp = brACNow()
		}
	}()
	return &types.ApiResponse{
		Success:   true,
		Data:      brACMetricsData(),
		Timestamp: brACNow(),
	}
}

func brACMetricsData() *entities.OrderedMap[any] {
	before := entities.NewOrderedMap[any]()
	before.Set("queries_per_request", "100+ (N+1 problem)")
	before.Set("average_response_time", "2000-3000ms")
	before.Set("database_round_trips", "20+")
	after := entities.NewOrderedMap[any]()
	after.Set("queries_per_request", "1-3")
	after.Set("average_response_time", "50-150ms")
	after.Set("database_round_trips", "1-3")
	expected := entities.NewOrderedMap[any]()
	expected.Set("before", before)
	expected.Set("after", after)
	expected.Set("improvement", "~95% reduction in response time")
	cache := entities.NewOrderedMap[any]()
	cache.Set("enabled", "via_redis_decorator")
	cache.Set("ttl", "300 seconds (5 minutes)")
	cache.Set("invalidation", "automatic_on_changes")
	m := entities.NewOrderedMap[any]()
	m.Set("optimization_status", "enabled")
	m.Set("query_strategy", "facade_with_optimized_repositories")
	m.Set("expected_performance", expected)
	m.Set("cache_status", cache)
	m.Set("recommendations", []any{
		"Use /api/branches/summaries endpoint for sidebar loading",
		"Cache invalidates automatically on branch/task changes",
		"Monitor this endpoint for performance tracking",
		"DDD architecture ensures proper separation of concerns",
	})
	return m
}

func brACMetricsErrorData() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("metrics", entities.NewOrderedMap[any]())
	return m
}

// CreateBranch mirrors create_branch.
func (c *BranchAPIController) CreateBranch(ctx context.Context, projectID, name, description, userID string, session any) (resp *types.BranchResponse) {
	resp = &types.BranchResponse{Success: false, Timestamp: brACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Error = brACPtr(value_objects.PyStr(r))
			resp.Message = brACPtr("Failed to create branch")
			resp.Branch = nil
			resp.Timestamp = brACNow()
		}
	}()
	facade, err := c.facadeService.GetBranchFacade(&projectID, &userID)
	if err != nil {
		return brACBranchError(err, "Failed to create branch")
	}
	result := facade.CreateGitBranch(ctx, projectID, name, description)
	if brACTruthy(result, "success") {
		branchData := brACAsMap(brACGetDefault(result, "git_branch", entities.NewOrderedMap[any]()))
		dto := brACBranchDTOFromDict(branchData, 0)
		return &types.BranchResponse{
			Success:   true,
			Branch:    dto,
			Message:   brACPtr("Branch created successfully"),
			Timestamp: brACNow(),
		}
	}
	errMsg := value_objects.PyStr(brACGetDefault(result, "error", "Failed to create branch"))
	return &types.BranchResponse{
		Success:   false,
		Error:     &errMsg,
		Message:   brACPtr("Failed to create branch"),
		Branch:    nil,
		Timestamp: brACNow(),
	}
}

// ListBranches mirrors list_branches.
func (c *BranchAPIController) ListBranches(ctx context.Context, projectID, userID string, session any) (resp *types.BranchesResponse) {
	resp = &types.BranchesResponse{Success: false, Timestamp: brACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Error = brACPtr(value_objects.PyStr(r))
			resp.Message = brACPtr("Failed to list branches")
			resp.Branches = []*types.BranchDTO{}
			resp.Total = brACIntPtr(0)
			resp.Timestamp = brACNow()
		}
	}()
	facade, err := c.facadeService.GetBranchFacade(&projectID, &userID)
	if err != nil {
		return brACBranchesError(err, "Failed to list branches")
	}
	result := facade.ListGitBranchs(ctx, projectID)
	if brACTruthy(result, "success") {
		branchesData := brACListOf(brACGetDefault(result, "git_branchs", []any{}))
		dtos := make([]*types.BranchDTO, 0, len(branchesData))
		for _, b := range branchesData {
			data := brACAsMap(b)
			dtos = append(dtos, brACBranchDTOFromDict(data, brACGetDefault(data, "task_count", 0)))
		}
		total := len(dtos)
		return &types.BranchesResponse{
			Success:   true,
			Branches:  dtos,
			Total:     &total,
			Timestamp: brACNow(),
		}
	}
	errMsg := value_objects.PyStr(brACGetDefault(result, "error", "Failed to list branches"))
	return &types.BranchesResponse{
		Success:   false,
		Error:     &errMsg,
		Message:   brACPtr("Failed to list branches"),
		Branches:  []*types.BranchDTO{},
		Total:     brACIntPtr(0),
		Timestamp: brACNow(),
	}
}

// UpdateBranch mirrors update_branch.
func (c *BranchAPIController) UpdateBranch(ctx context.Context, branchID string, name, description *string, userID string, session any) (resp *types.BranchResponse) {
	resp = &types.BranchResponse{Success: false, Timestamp: brACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Error = brACPtr(value_objects.PyStr(r))
			resp.Message = brACPtr("Failed to update branch")
			resp.Branch = nil
			resp.Timestamp = brACNow()
		}
	}()
	repo, err := c.repoProvider.GetGitBranchRepository(session, &userID)
	if err != nil {
		return brACBranchError(err, "Failed to update branch")
	}
	gitBranch, err := repo.FindByID(ctx, branchID, nil)
	if err != nil {
		return brACBranchError(err, "Failed to update branch")
	}
	if gitBranch == nil {
		return &types.BranchResponse{
			Success:   false,
			Error:     brACPtr("Branch " + branchID + " not found"),
			Message:   brACPtr("Branch not found"),
			Branch:    nil,
			Timestamp: brACNow(),
		}
	}
	facade, err := c.facadeService.GetBranchFacade(&gitBranch.ProjectID, &userID)
	if err != nil {
		return brACBranchError(err, "Failed to update branch")
	}
	result := facade.UpdateGitBranch(ctx, branchID, name, description, &gitBranch.ProjectID)
	if brACTruthy(result, "success") {
		branchData := brACAsMap(brACGetDefault(result, "git_branch", entities.NewOrderedMap[any]()))
		if brACGet(branchData, "id") == nil {
			// BranchDTO(id=None) fails pydantic validation (the facade's update wrapper has no id).
			panic("1 validation error for BranchDTO\nid\n  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]")
		}
		dto := brACBranchDTOFromDict(branchData, brACGetDefault(branchData, "task_count", 0))
		return &types.BranchResponse{
			Success:   true,
			Branch:    dto,
			Message:   brACPtr("Branch updated successfully"),
			Timestamp: brACNow(),
		}
	}
	errMsg := value_objects.PyStr(brACGetDefault(result, "error", "Failed to update branch"))
	return &types.BranchResponse{
		Success:   false,
		Error:     &errMsg,
		Message:   brACPtr("Failed to update branch"),
		Branch:    nil,
		Timestamp: brACNow(),
	}
}

// DeleteBranch mirrors delete_branch.
func (c *BranchAPIController) DeleteBranch(ctx context.Context, branchID, userID string, session any) (resp *types.DeleteResponse) {
	resp = &types.DeleteResponse{Success: false, Timestamp: brACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Deleted = brACBoolPtr(false)
			resp.Error = brACPtr(value_objects.PyStr(r))
			resp.Message = brACPtr("Failed to delete branch")
			resp.Timestamp = brACNow()
		}
	}()
	repo, err := c.repoProvider.GetGitBranchRepository(session, &userID)
	if err != nil {
		return brACDeleteError(err, "Failed to delete branch")
	}
	branch, err := repo.FindByID(ctx, branchID, nil)
	if err != nil {
		return brACDeleteError(err, "Failed to delete branch")
	}
	if branch == nil {
		return &types.DeleteResponse{
			Success:   false,
			Deleted:   brACBoolPtr(false),
			Error:     brACPtr("Branch " + branchID + " not found"),
			Message:   brACPtr("Branch not found"),
			Timestamp: brACNow(),
		}
	}
	projectID := branch.ProjectID
	projectRepo, err := c.repoProvider.GetProjectRepository(session, &userID)
	if err != nil {
		return brACDeleteError(err, "Failed to delete branch")
	}
	project, err := projectRepo.FindByID(ctx, projectID)
	if err != nil {
		return brACDeleteError(err, "Failed to delete branch")
	}
	if project == nil {
		return &types.DeleteResponse{
			Success:   false,
			Deleted:   brACBoolPtr(false),
			Error:     brACPtr("You don't have permission to delete this branch"),
			Message:   brACPtr("Permission denied"),
			Timestamp: brACNow(),
		}
	}
	facade, err := c.facadeService.GetBranchFacade(&projectID, &userID)
	if err != nil {
		return brACDeleteError(err, "Failed to delete branch")
	}
	result := facade.DeleteGitBranch(ctx, branchID, nil)
	if brACTruthy(result, "success") {
		return &types.DeleteResponse{
			Success:   true,
			Deleted:   brACBoolPtr(true),
			ID:        &branchID,
			Message:   brACPtr("Branch deleted successfully"),
			Timestamp: brACNow(),
		}
	}
	errMsg := value_objects.PyStr(brACGetDefault(result, "error", "Failed to delete branch"))
	return &types.DeleteResponse{
		Success:   false,
		Deleted:   brACBoolPtr(false),
		Error:     &errMsg,
		Message:   brACPtr("Failed to delete branch"),
		Timestamp: brACNow(),
	}
}

// AssignAgent mirrors assign_agent.
func (c *BranchAPIController) AssignAgent(ctx context.Context, branchID, agentID, userID string, session any) (resp *types.ApiResponse) {
	resp = &types.ApiResponse{Success: false, Timestamp: brACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Error = brACPtr(value_objects.PyStr(r))
			resp.Message = brACPtr("Failed to assign agent")
			resp.Timestamp = brACNow()
		}
	}()
	repo, err := c.repoProvider.GetGitBranchRepository(session, &userID)
	if err != nil {
		return brACAPIError(err, "Failed to assign agent", nil)
	}
	gitBranch, err := repo.FindByID(ctx, branchID, nil)
	if err != nil {
		return brACAPIError(err, "Failed to assign agent", nil)
	}
	if gitBranch == nil {
		return &types.ApiResponse{
			Success:   false,
			Error:     brACPtr("Branch " + branchID + " not found"),
			Message:   brACPtr("Branch not found"),
			Timestamp: brACNow(),
		}
	}
	facade, err := c.facadeService.GetBranchFacade(&gitBranch.ProjectID, &userID)
	if err != nil {
		return brACAPIError(err, "Failed to assign agent", nil)
	}
	result := facade.AssignAgent(ctx, branchID, agentID, &gitBranch.ProjectID)
	if brACTruthy(result, "success") {
		return &types.ApiResponse{
			Success:   true,
			Data:      result,
			Message:   brACPtr("Agent assigned successfully"),
			Timestamp: brACNow(),
		}
	}
	errMsg := value_objects.PyStr(brACGetDefault(result, "error", "Failed to assign agent"))
	return &types.ApiResponse{
		Success:   false,
		Error:     &errMsg,
		Message:   brACPtr("Failed to assign agent"),
		Timestamp: brACNow(),
	}
}

// GetBranchTaskCounts mirrors get_branch_task_counts.
func (c *BranchAPIController) GetBranchTaskCounts(ctx context.Context, branchID, userID string, session any) (resp *types.ApiResponse) {
	resp = &types.ApiResponse{Success: false, Timestamp: brACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Error = brACPtr(value_objects.PyStr(r))
			resp.Message = brACPtr("Failed to get branch task counts")
			resp.Data = brACTaskCountsErrorData(brACPtr(value_objects.PyStr(r)))
			resp.Timestamp = brACNow()
		}
	}()
	repo, err := c.repoProvider.GetGitBranchRepository(session, &userID)
	if err != nil {
		return brACAPIError(err, "Failed to get branch task counts", brACTaskCountsEmptyData())
	}
	gitBranch, err := repo.FindByID(ctx, branchID, nil)
	if err != nil {
		return brACAPIError(err, "Failed to get branch task counts", brACTaskCountsEmptyData())
	}
	if gitBranch == nil {
		return &types.ApiResponse{
			Success:   false,
			Error:     brACPtr("Branch " + branchID + " not found"),
			Message:   brACPtr("Branch not found"),
			Timestamp: brACNow(),
		}
	}
	facade, err := c.facadeService.GetBranchFacade(&gitBranch.ProjectID, &userID)
	if err != nil {
		return brACAPIError(err, "Failed to get branch task counts", brACTaskCountsEmptyData())
	}
	result := facade.GetBranchSummary(ctx, branchID)
	if !brACTruthy(result, "success") {
		errMsg := value_objects.PyStr(brACGetDefault(result, "error", "Failed to get branch summary"))
		return &types.ApiResponse{
			Success:   false,
			Error:     &errMsg,
			Message:   brACPtr("Failed to get branch summary"),
			Timestamp: brACNow(),
		}
	}
	branch := brACAsMap(brACGetDefault(result, "branch", entities.NewOrderedMap[any]()))
	taskCounts := entities.NewOrderedMap[any]()
	taskCounts.Set("total", brACIntDefault(branch, "total_tasks", 0))
	taskCounts.Set("todo", brACIntDefault(branch, "todo_tasks", 0))
	taskCounts.Set("in_progress", brACIntDefault(branch, "in_progress_tasks", 0))
	taskCounts.Set("done", brACIntDefault(branch, "completed_tasks", 0))
	taskCounts.Set("blocked", brACIntDefault(branch, "blocked_tasks", 0))
	taskCounts.Set("progress_percentage", brACFloatDefault(branch, "progress_percentage", 0.0))
	data := entities.NewOrderedMap[any]()
	data.Set("task_counts", taskCounts)
	data.Set("branch_id", branchID)
	return &types.ApiResponse{
		Success:   true,
		Data:      data,
		Timestamp: brACNow(),
	}
}

func brACIntDefault(m *entities.OrderedMap[any], key string, def int) int {
	if f, ok := value_objects.PyFloat(brACGet(m, key)); ok {
		return int(f)
	}
	return def
}

func brACFloatDefault(m *entities.OrderedMap[any], key string, def float64) float64 {
	if f, ok := value_objects.PyFloat(brACGet(m, key)); ok {
		return f
	}
	return def
}

func brACTaskCountsEmptyData() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("task_counts", entities.NewOrderedMap[any]())
	return m
}

func brACTaskCountsErrorData(_ *string) *entities.OrderedMap[any] {
	return brACTaskCountsEmptyData()
}

// GetBulkSummaries mirrors get_bulk_summaries.
func (c *BranchAPIController) GetBulkSummaries(ctx context.Context, projectIDs []string, userID string, includeArchived bool, session brACQueryer) (resp *types.BulkSummaryResponse) {
	startTime := time.Now()
	defer func() {
		if r := recover(); r != nil {
			msg := "Failed to get bulk summaries: " + value_objects.PyStr(r)
			resp = &types.BulkSummaryResponse{
				Success:   false,
				Summaries: entities.NewOrderedMap[any](),
				Projects:  entities.NewOrderedMap[any](),
				Metadata:  &types.BulkSummaryMetadata{Count: 0, QueryTimeMs: 0, FromCache: false},
				Message:   &msg,
				Timestamp: *brACNow(),
			}
		}
	}()
	query := `
            SELECT
                b.id as branch_id,
                b.project_id,
                b.name as branch_name,
                b.status as branch_status,
                b.priority as branch_priority,
                COUNT(DISTINCT t.id) as task_count,
                COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END) as completed_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'in_progress' THEN t.id END) as in_progress_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'blocked' THEN t.id END) as blocked_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'todo' THEN t.id END) as todo_tasks,
                CASE
                    WHEN COUNT(DISTINCT t.id) = 0 THEN 0
                    ELSE ROUND((COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END)::numeric / COUNT(DISTINCT t.id)::numeric) * 100, 2)
                END as progress_percentage,
                b.updated_at as last_task_activity
            FROM project_git_branchs b
            LEFT JOIN tasks t ON b.id = t.git_branch_id AND t.user_id = :user_id
            WHERE 1=1
            `
	params := map[string]any{"user_id": userID}

	if len(projectIDs) > 0 {
		placeholders := ""
		for i := range projectIDs {
			if i > 0 {
				placeholders += ", "
			}
			placeholders += ":p" + strconv.Itoa(i)
		}
		query += " AND b.project_id IN (" + placeholders + ")"
		for i, pid := range projectIDs {
			params["p"+strconv.Itoa(i)] = pid
		}
	} else if userID != "" {
		userProjectsResult, err := session.Execute(ctx, `
                    SELECT DISTINCT project_id
                    FROM project_git_branchs b
                    WHERE b.user_id = :user_id
                `, map[string]any{"user_id": userID})
		if err != nil {
			return brACBulkError(err)
		}
		userProjectIDs := []string{}
		for _, row := range userProjectsResult.Iterate() {
			if len(row) > 0 && row[0] != nil {
				userProjectIDs = append(userProjectIDs, value_objects.PyStr(row[0]))
			}
		}
		if len(userProjectIDs) > 0 {
			placeholders := ""
			for i := range userProjectIDs {
				if i > 0 {
					placeholders += ", "
				}
				placeholders += ":p" + strconv.Itoa(i)
			}
			query += " AND b.project_id IN (" + placeholders + ")"
			for i, pid := range userProjectIDs {
				params["p"+strconv.Itoa(i)] = pid
			}
		} else {
			return &types.BulkSummaryResponse{
				Success:   true,
				Summaries: entities.NewOrderedMap[any](),
				Projects:  entities.NewOrderedMap[any](),
				Metadata:  &types.BulkSummaryMetadata{Count: 0, QueryTimeMs: 0, FromCache: false},
				Message:   brACPtr("No projects found for user"),
				Timestamp: *brACNow(),
			}
		}
	}

	if !includeArchived {
		query += " AND b.status != 'archived'"
	}
	query += `
            GROUP BY b.id, b.project_id, b.name, b.status, b.priority, b.updated_at
            ORDER BY b.name
            `

	result, err := session.Execute(ctx, query, params)
	if err != nil {
		return brACBulkError(err)
	}
	rows := result.FetchAll()

	summaries := entities.NewOrderedMap[any]()
	projectIDsFound := []string{}
	foundSet := map[string]bool{}
	for _, row := range rows {
		branchSummary := entities.NewOrderedMap[any]()
		branchSummary.Set("id", value_objects.PyStr(at(row, 0)))
		branchSummary.Set("project_id", value_objects.PyStr(at(row, 1)))
		branchSummary.Set("name", at(row, 2))
		branchSummary.Set("status", at(row, 3))
		branchSummary.Set("priority", at(row, 4))
		branchSummary.Set("task_count", brACOrZero(at(row, 5)))
		branchSummary.Set("completed_tasks", brACOrZero(at(row, 6)))
		branchSummary.Set("in_progress_tasks", brACOrZero(at(row, 7)))
		branchSummary.Set("blocked_tasks", brACOrZero(at(row, 8)))
		branchSummary.Set("todo_tasks", brACOrZero(at(row, 9)))
		branchSummary.Set("progress_percentage", brACFloatOrZero(at(row, 10)))
		branchSummary.Set("last_activity", brACIso(at(row, 11)))
		key := value_objects.PyStr(at(row, 0))
		summaries.Set(key, branchSummary)
		pid := value_objects.PyStr(at(row, 1))
		if !foundSet[pid] {
			foundSet[pid] = true
			projectIDsFound = append(projectIDsFound, pid)
		}
	}

	projects := entities.NewOrderedMap[any]()
	if len(projectIDsFound) > 0 {
		projectQuery := `
                    SELECT
                        p.id as project_id,
                        p.name as project_name,
                        p.description as project_description,
                        COUNT(DISTINCT b.id) as total_branches,
                        COUNT(DISTINCT CASE WHEN b.status != 'archived' THEN b.id END) as active_branches,
                        COUNT(DISTINCT t.id) as total_tasks,
                        COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END) as completed_tasks,
                        CASE
                            WHEN COUNT(DISTINCT t.id) = 0 THEN 0
                            ELSE ROUND((COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END)::numeric / COUNT(DISTINCT t.id)::numeric) * 100, 2)
                        END as overall_progress_percentage
                    FROM projects p
                    LEFT JOIN project_git_branchs b ON p.id = b.project_id
                    LEFT JOIN tasks t ON b.id = t.git_branch_id AND t.user_id = :user_id
                    WHERE p.id IN (%s)
                    GROUP BY p.id, p.name, p.description
                `
		placeholders := ""
		for i := range projectIDsFound {
			if i > 0 {
				placeholders += ", "
			}
			placeholders += ":proj" + strconv.Itoa(i)
		}
		projectQuery = fmt.Sprintf(projectQuery, placeholders)
		projectParams := map[string]any{"user_id": userID}
		for i, pid := range projectIDsFound {
			projectParams["proj"+strconv.Itoa(i)] = pid
		}
		projectResult, err := session.Execute(ctx, projectQuery, projectParams)
		if err != nil {
			return brACBulkError(err)
		}
		for _, row := range projectResult.Iterate() {
			entry := entities.NewOrderedMap[any]()
			entry.Set("id", value_objects.PyStr(at(row, 0)))
			entry.Set("name", at(row, 1))
			entry.Set("description", at(row, 2))
			entry.Set("total_branches", brACOrZero(at(row, 3)))
			entry.Set("active_branches", brACOrZero(at(row, 4)))
			entry.Set("total_tasks", brACOrZero(at(row, 5)))
			entry.Set("completed_tasks", brACOrZero(at(row, 6)))
			entry.Set("progress_percentage", brACFloatOrZero(at(row, 7)))
			projects.Set(value_objects.PyStr(at(row, 0)), entry)
		}
	}

	queryTime := float64(time.Since(startTime).Nanoseconds()) / 1e6
	return &types.BulkSummaryResponse{
		Success:   true,
		Summaries: summaries,
		Projects:  projects,
		Metadata: &types.BulkSummaryMetadata{
			Count:       summaries.Len(),
			QueryTimeMs: queryTime,
			FromCache:   false,
		},
		Timestamp: *brACNow(),
	}
}

// --- branch file helpers ---

func brACPtr(s string) *string { return &s }
func brACBoolPtr(b bool) *bool { return &b }
func brACIntPtr(i int) *int    { return &i }

func at(row brACRow, i int) any {
	if i < len(row) {
		return row[i]
	}
	return nil
}

func brACOrZero(v any) any {
	if v == nil {
		return 0
	}
	return v
}

func brACFloatOrZero(v any) float64 {
	if f, ok := value_objects.PyFloat(v); ok {
		return f
	}
	return 0
}

func brACIso(v any) any {
	switch x := v.(type) {
	case nil:
		return nil
	case time.Time:
		return value_objects.IsoFormat(x)
	case *time.Time:
		if x == nil {
			return nil
		}
		return value_objects.IsoFormat(*x)
	case string:
		return x
	case *string:
		if x == nil {
			return nil
		}
		return *x
	}
	return nil
}

func brACBranchesError(err error, message string) *types.BranchesResponse {
	msg := err.Error()
	return &types.BranchesResponse{
		Success:   false,
		Error:     &msg,
		Message:   &message,
		Branches:  []*types.BranchDTO{},
		Total:     brACIntPtr(0),
		Timestamp: brACNow(),
	}
}

func brACBranchError(err error, message string) *types.BranchResponse {
	msg := err.Error()
	return &types.BranchResponse{
		Success:   false,
		Error:     &msg,
		Message:   &message,
		Branch:    nil,
		Timestamp: brACNow(),
	}
}

func brACDeleteError(err error, message string) *types.DeleteResponse {
	msg := err.Error()
	return &types.DeleteResponse{
		Success:   false,
		Deleted:   brACBoolPtr(false),
		Error:     &msg,
		Message:   &message,
		Timestamp: brACNow(),
	}
}

func brACAPIError(err error, message string, data any) *types.ApiResponse {
	msg := err.Error()
	return &types.ApiResponse{
		Success:   false,
		Error:     &msg,
		Message:   &message,
		Data:      data,
		Timestamp: brACNow(),
	}
}

func brACBulkError(err error) *types.BulkSummaryResponse {
	msg := "Failed to get bulk summaries: " + err.Error()
	return &types.BulkSummaryResponse{
		Success:   false,
		Summaries: entities.NewOrderedMap[any](),
		Projects:  entities.NewOrderedMap[any](),
		Metadata:  &types.BulkSummaryMetadata{Count: 0, QueryTimeMs: 0, FromCache: false},
		Message:   &msg,
		Timestamp: *brACNow(),
	}
}

// Exported names for the bulk-summary session boundary so the composition root can
// implement it.
type (
	BulkRow     = brACRow
	BulkResult  = brACResult
	BulkQueryer = brACQueryer

	BranchFacadeProvider = brACFacadeProvider
	BranchRepoProvider   = brACRepoProvider
)
