// work_distribution_service.go ports
// task_management/application/services/work_distribution_service.py.
//
// Mapping notes:
//   - Python's Task.metadata does not exist on the Go entities.Task either; the
//     Python TaskRequirements.from_task would raise AttributeError on `task.metadata`
//     (Task has no metadata field), so the Go port reads an empty metadata map and
//     keeps every metadata-derived field at its default. This preserves the observable
//     shape without inventing a field.
//   - AgentRepository and AgentCoordinationService are ported in
//     domain/repositories/agent_repository.go and
//     application/services/agent_coordination_service.go. The minimal
//     interfaces needed are declared in this file (WorkDistributionAgentRepository,
//     WorkDistributionCoordinationService).
//   - Python asynchronous methods become plain methods with ctx first.
//   - Logging calls are dropped.
package services

import (
	"context"
	"sort"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// DistributionStrategy is work_distribution_service.DistributionStrategy.
type DistributionStrategy string

const (
	DistributionRoundRobin   DistributionStrategy = "round_robin"
	DistributionLoadBalanced DistributionStrategy = "load_balanced"
	DistributionSkillMatched DistributionStrategy = "skill_matched"
	DistributionPriorityBase DistributionStrategy = "priority_based"
	DistributionHybrid       DistributionStrategy = "hybrid"
)

// WorkDistributionException is work_distribution_service.WorkDistributionException.
type WorkDistributionException struct {
	exceptions.DomainException
}

// NewWorkDistributionException builds the exception.
func NewWorkDistributionException(msg string) *WorkDistributionException {
	return &WorkDistributionException{DomainException: exceptions.DomainException{Msg: msg}}
}

// TaskRequirements is work_distribution_service.TaskRequirements.
type TaskRequirements struct {
	TaskID              string
	RequiredRole        *value_objects.AgentsAgentRole
	RequiredExpertise   map[value_objects.AgentExpertise]struct{}
	RequiredSkills      map[string]float64
	PreferredAgents     []string
	ExcludedAgents      []string
	CollaborationNeeded bool
	EstimatedHours      float64
	Deadline            *string
}

// TaskRequirementsFromTask is TaskRequirements.from_task. The Go Task exposes no
// metadata field, so metadata is empty (see the file header).
func TaskRequirementsFromTask(task *entities.Task) TaskRequirements {
	metadata := map[string]any{}

	var requiredRole *value_objects.AgentsAgentRole
	if raw, ok := metadata["required_role"]; ok {
		role := value_objects.AgentsAgentRole(value_objects.PyStr(raw))
		if wdKnownAgentRole(role) {
			requiredRole = &role
		}
	}

	requiredExpertise := map[value_objects.AgentExpertise]struct{}{}
	if raw, ok := metadata["required_expertise"]; ok {
		if list, ok := raw.([]any); ok {
			for _, exp := range list {
				e := value_objects.AgentExpertise(value_objects.PyStr(exp))
				if wdKnownAgentExpertise(e) {
					requiredExpertise[e] = struct{}{}
				}
			}
		}
	}

	return TaskRequirements{
		TaskID:              wdTaskIDString(task),
		RequiredRole:        requiredRole,
		RequiredExpertise:   requiredExpertise,
		RequiredSkills:      wdMetadataStringFloatMap(metadata, "required_skills"),
		PreferredAgents:     wdMetadataStringSlice(metadata, "preferred_agents"),
		ExcludedAgents:      wdMetadataStringSlice(metadata, "excluded_agents"),
		CollaborationNeeded: wdMetadataBool(metadata, "collaboration_needed"),
		EstimatedHours:      wdMetadataFloat(metadata, "estimated_hours"),
		Deadline:            task.DueDate,
	}
}

var workDistributionKnownRoles = map[value_objects.AgentsAgentRole]struct{}{
	value_objects.AgentsAgentRoleArchitect:  {},
	value_objects.AgentsAgentRoleDeveloper:  {},
	value_objects.AgentsAgentRoleTester:     {},
	value_objects.AgentsAgentRoleReviewer:   {},
	value_objects.AgentsAgentRoleManager:    {},
	value_objects.AgentsAgentRoleAnalyst:    {},
	value_objects.AgentsAgentRoleDesigner:   {},
	value_objects.AgentsAgentRoleDevops:     {},
	value_objects.AgentsAgentRoleSecurity:   {},
	value_objects.AgentsAgentRoleDocumenter: {},
}

var workDistributionKnownExpertise = map[value_objects.AgentExpertise]struct{}{
	value_objects.AgentExpertiseFrontend:          {},
	value_objects.AgentExpertiseBackend:           {},
	value_objects.AgentExpertiseDatabase:          {},
	value_objects.AgentExpertiseCloud:             {},
	value_objects.AgentExpertiseMobile:            {},
	value_objects.AgentExpertiseAiMl:              {},
	value_objects.AgentExpertiseSecurity:          {},
	value_objects.AgentExpertisePerformance:       {},
	value_objects.AgentExpertiseTesting:           {},
	value_objects.AgentExpertiseDocumentation:     {},
	value_objects.AgentExpertiseArchitecture:      {},
	value_objects.AgentExpertiseProjectManagement: {},
}

func wdKnownAgentRole(r value_objects.AgentsAgentRole) bool {
	_, ok := workDistributionKnownRoles[r]
	return ok
}

func wdKnownAgentExpertise(e value_objects.AgentExpertise) bool {
	_, ok := workDistributionKnownExpertise[e]
	return ok
}

func wdMetadataStringSlice(metadata map[string]any, key string) []string {
	raw, ok := metadata[key]
	if !ok {
		return []string{}
	}
	list, ok := raw.([]any)
	if !ok {
		if ss, ok := raw.([]string); ok {
			return ss
		}
		return []string{}
	}
	out := make([]string, 0, len(list))
	for _, v := range list {
		out = append(out, value_objects.PyStr(v))
	}
	return out
}

func wdMetadataStringFloatMap(metadata map[string]any, key string) map[string]float64 {
	raw, ok := metadata[key]
	if !ok {
		return map[string]float64{}
	}
	out := map[string]float64{}
	switch m := raw.(type) {
	case map[string]float64:
		return m
	case map[string]any:
		for k, v := range m {
			if f, ok := wdToFloat(v); ok {
				out[k] = f
			}
		}
	}
	return out
}

func wdMetadataBool(metadata map[string]any, key string) bool {
	v, ok := metadata[key]
	if !ok {
		return false
	}
	return value_objects.PyTruthy(v)
}

func wdMetadataFloat(metadata map[string]any, key string) float64 {
	v, ok := metadata[key]
	if !ok {
		return 0.0
	}
	f, _ := wdToFloat(v)
	return f
}

func wdToFloat(v any) (float64, bool) {
	switch n := v.(type) {
	case float64:
		return n, true
	case float32:
		return float64(n), true
	case int:
		return float64(n), true
	case int64:
		return float64(n), true
	}
	return 0, false
}

// wdTaskIDString mirrors `task.id.value if hasattr(task.id, "value") else task.id`.
func wdTaskIDString(task *entities.Task) string {
	if task == nil || task.ID == nil {
		return ""
	}
	return task.ID.String()
}

// wdAgentIDString is `agent.id`.
func wdAgentIDString(agent *entities.Agent) string {
	if agent == nil || agent.ID == nil {
		return ""
	}
	return agent.ID.String()
}

// DistributionPlan is work_distribution_service.DistributionPlan.
type DistributionPlan struct {
	PlanID          string
	CreatedAt       time.Time
	Assignments     [][3]string // (task_id, agent_id, role)
	UnassignableRaw []string
	Recommendations map[string]string
}

// NewDistributionPlan mirrors DistributionPlan defaults.
func NewDistributionPlan() *DistributionPlan {
	return &DistributionPlan{
		PlanID:          value_objects.NewUUIDv4(),
		CreatedAt:       time.Now(),
		Assignments:     [][3]string{},
		UnassignableRaw: []string{},
		Recommendations: map[string]string{},
	}
}

// AddAssignment is add_assignment.
func (p *DistributionPlan) AddAssignment(taskID, agentID, role string) {
	p.Assignments = append(p.Assignments, [3]string{taskID, agentID, role})
}

// MarkUnassignable is mark_unassignable.
func (p *DistributionPlan) MarkUnassignable(taskID, reason string) {
	p.UnassignableRaw = append(p.UnassignableRaw, taskID)
	p.Recommendations[taskID] = reason
}

// WorkDistributionAgentRepository is the minimal interface for the Python Any-typed
// AgentRepository (infrastructure.repositories.agent_repository).
type WorkDistributionAgentRepository interface {
	GetByProject(ctx context.Context, projectID string) ([]*entities.Agent, error)
	GetAll(ctx context.Context) ([]*entities.Agent, error)
}

// WorkDistributionCoordinationService is the minimal interface for
// agent_coordination_service.AgentCoordinationService.
type WorkDistributionCoordinationService interface {
	FindBestAgentForTask(ctx context.Context, taskID string, requiredRole *value_objects.AgentsAgentRole, requiredExpertise map[value_objects.AgentExpertise]struct{}, requiredSkills map[string]float64) (*entities.Agent, error)
	AssignAgentToTask(ctx context.Context, taskID, agentID, role, assignedBy string) error
}

// distributionRecord is one entry of distribution_history.
type distributionRecord struct {
	PlanID            string
	Timestamp         time.Time
	Strategy          string
	TotalTasks        int
	AssignedTasks     int
	UnassignableTasks int
	Assignments       [][3]string
	Recommendations   map[string]string
}

// WorkDistributionService is work_distribution_service.WorkDistributionService.
type WorkDistributionService struct {
	TaskRepository      repositories.TaskRepository
	AgentRepository     WorkDistributionAgentRepository
	CoordinationService WorkDistributionCoordinationService
	EventBus            any

	DistributionHistory   []distributionRecord
	AgentPerformanceCache map[string]float64
	userID                *string
}

// NewWorkDistributionService mirrors WorkDistributionService.__init__.
func NewWorkDistributionService(taskRepository repositories.TaskRepository, agentRepository WorkDistributionAgentRepository, coordinationService WorkDistributionCoordinationService, eventBus any, userID *string) *WorkDistributionService {
	return &WorkDistributionService{
		TaskRepository:        taskRepository,
		AgentRepository:       agentRepository,
		CoordinationService:   coordinationService,
		EventBus:              eventBus,
		DistributionHistory:   []distributionRecord{},
		AgentPerformanceCache: map[string]float64{},
		userID:                userID,
	}
}

// WithUser is with_user.
func (s *WorkDistributionService) WithUser(userID string) *WorkDistributionService {
	return NewWorkDistributionService(s.TaskRepository, s.AgentRepository, s.CoordinationService, s.EventBus, &userID)
}

// DistributeTasks is distribute_tasks.
func (s *WorkDistributionService) DistributeTasks(ctx context.Context, taskIDs []string, strategy DistributionStrategy, projectID *string) (*DistributionPlan, error) {
	plan := NewDistributionPlan()

	taskRepo := s.scopedTaskRepository()
	tasks := []*entities.Task{}
	for _, taskID := range taskIDs {
		tid, err := value_objects.NewTaskId(taskID)
		if err != nil {
			continue
		}
		task, err := taskRepo.FindByID(ctx, tid)
		if err != nil {
			return nil, err
		}
		if task != nil && task.Status != nil && (task.Status.IsTodo() || task.Status.IsInProgress()) {
			tasks = append(tasks, task)
		}
	}

	if len(tasks) == 0 {
		return plan, nil
	}

	var agents []*entities.Agent
	if projectID != nil {
		if s.AgentRepository != nil {
			var err error
			agents, err = s.AgentRepository.GetByProject(ctx, *projectID)
			if err != nil {
				return nil, err
			}
		}
	} else if s.AgentRepository != nil {
		var err error
		agents, err = s.AgentRepository.GetAll(ctx)
		if err != nil {
			return nil, err
		}
	}

	availableAgents := []*entities.Agent{}
	for _, a := range agents {
		if a.IsAvailable() {
			availableAgents = append(availableAgents, a)
		}
	}

	if len(availableAgents) == 0 {
		for _, task := range tasks {
			plan.MarkUnassignable(wdTaskIDString(task), "No available agents")
		}
		return plan, nil
	}

	switch strategy {
	case DistributionRoundRobin:
		s.distributeRoundRobin(tasks, availableAgents, plan)
	case DistributionLoadBalanced:
		s.distributeLoadBalanced(tasks, availableAgents, plan)
	case DistributionSkillMatched:
		if err := s.distributeSkillMatched(ctx, tasks, plan); err != nil {
			return nil, err
		}
	case DistributionPriorityBase:
		s.distributePriorityBased(tasks, availableAgents, plan)
	default: // HYBRID
		s.distributeHybrid(tasks, availableAgents, plan)
	}

	if err := s.executeDistributionPlan(ctx, plan); err != nil {
		return nil, err
	}

	s.recordDistribution(plan, strategy)
	return plan, nil
}

// scopedTaskRepository mirrors _get_user_scoped_repository for the task repository.
// The Go repositories.TaskRepository interface does not expose with_user, so the
// repository is returned unchanged.
func (s *WorkDistributionService) scopedTaskRepository() repositories.TaskRepository {
	return s.TaskRepository
}

// wdMaxConcurrentTasks is agent.max_concurrent_tasks (Go nil means the Python default 1).
func wdMaxConcurrentTasks(agent *entities.Agent) int {
	if agent == nil || agent.MaxConcurrentTasks == nil {
		return 1
	}
	return *agent.MaxConcurrentTasks
}

func (s *WorkDistributionService) distributeRoundRobin(tasks []*entities.Task, agents []*entities.Agent, plan *DistributionPlan) {
	agentIndex := 0
	for _, task := range tasks {
		if len(agents) > 0 {
			agent := agents[agentIndex%len(agents)]
			plan.AddAssignment(wdTaskIDString(task), wdAgentIDString(agent), "assignee")
			agentIndex++
		} else {
			plan.MarkUnassignable(wdTaskIDString(task), "No agents available")
		}
	}
}

func (s *WorkDistributionService) distributeLoadBalanced(tasks []*entities.Task, agents []*entities.Agent, plan *DistributionPlan) {
	agentsByWorkload := append([]*entities.Agent{}, agents...)
	sort.SliceStable(agentsByWorkload, func(i, j int) bool {
		return agentsByWorkload[i].GetWorkloadPercentage() < agentsByWorkload[j].GetWorkloadPercentage()
	})

	for _, task := range tasks {
		assigned := false
		for _, agent := range agentsByWorkload {
			if agent.IsAvailable() {
				plan.AddAssignment(wdTaskIDString(task), wdAgentIDString(agent), "assignee")
				agent.CurrentWorkload++
				assigned = true
				break
			}
		}
		if !assigned {
			plan.MarkUnassignable(wdTaskIDString(task), "All agents at capacity")
		}
	}
}

func (s *WorkDistributionService) distributeSkillMatched(ctx context.Context, tasks []*entities.Task, plan *DistributionPlan) error {
	for _, task := range tasks {
		requirements := TaskRequirementsFromTask(task)
		if s.CoordinationService == nil {
			plan.MarkUnassignable(wdTaskIDString(task), "No agent with required skills: any")
			continue
		}
		bestAgent, err := s.CoordinationService.FindBestAgentForTask(ctx, wdTaskIDString(task), requirements.RequiredRole, requirements.RequiredExpertise, requirements.RequiredSkills)
		if err != nil {
			return err
		}
		if bestAgent != nil {
			plan.AddAssignment(wdTaskIDString(task), wdAgentIDString(bestAgent), "specialist")
		} else {
			role := "any"
			if requirements.RequiredRole != nil {
				role = string(*requirements.RequiredRole)
			}
			plan.MarkUnassignable(wdTaskIDString(task), "No agent with required skills: "+role)
		}
	}
	return nil
}

func (s *WorkDistributionService) distributePriorityBased(tasks []*entities.Task, agents []*entities.Agent, plan *DistributionPlan) {
	priorityOrder := map[string]int{
		"critical": 5, "urgent": 4, "high": 3, "medium": 2, "low": 1, "none": 1,
	}
	sortedTasks := append([]*entities.Task{}, tasks...)
	sort.SliceStable(sortedTasks, func(i, j int) bool {
		return priorityOrder[wdTaskPriorityValue(sortedTasks[i])] > priorityOrder[wdTaskPriorityValue(sortedTasks[j])]
	})

	sortedAgents := append([]*entities.Agent{}, agents...)
	sort.SliceStable(sortedAgents, func(i, j int) bool {
		return s.agentPerformanceScore(sortedAgents[i]) > s.agentPerformanceScore(sortedAgents[j])
	})

	agentAssignments := map[string]int{}
	for _, task := range sortedTasks {
		assigned := false
		for _, agent := range sortedAgents {
			aid := wdAgentIDString(agent)
			if agent.IsAvailable() && agentAssignments[aid] < wdMaxConcurrentTasks(agent) {
				plan.AddAssignment(wdTaskIDString(task), aid, "priority_assignee")
				agentAssignments[aid]++
				assigned = true
				break
			}
		}
		if !assigned {
			plan.MarkUnassignable(wdTaskIDString(task), "No suitable agent for priority task")
		}
	}
}

func (s *WorkDistributionService) distributeHybrid(tasks []*entities.Task, agents []*entities.Agent, plan *DistributionPlan) {
	priorityTasks := []*entities.Task{}
	skilledTasks := []*entities.Task{}
	regularTasks := []*entities.Task{}

	for _, task := range tasks {
		requirements := TaskRequirementsFromTask(task)
		wdTaskPriorityValue := wdTaskPriorityValue(task)
		if wdTaskPriorityValue == "critical" || wdTaskPriorityValue == "high" {
			priorityTasks = append(priorityTasks, task)
		} else if requirements.RequiredRole != nil || len(requirements.RequiredExpertise) > 0 {
			skilledTasks = append(skilledTasks, task)
		} else {
			regularTasks = append(regularTasks, task)
		}
	}

	agentUtilization := map[string]int{}
	for _, agent := range agents {
		agentUtilization[wdAgentIDString(agent)] = 0
	}

	bestAgents := append([]*entities.Agent{}, agents...)
	sort.SliceStable(bestAgents, func(i, j int) bool {
		return s.agentPerformanceScore(bestAgents[i]) > s.agentPerformanceScore(bestAgents[j])
	})

	for _, task := range priorityTasks {
		for _, agent := range bestAgents {
			aid := wdAgentIDString(agent)
			if agent.IsAvailable() && agentUtilization[aid] < wdMaxConcurrentTasks(agent) {
				plan.AddAssignment(wdTaskIDString(task), aid, "priority_specialist")
				agentUtilization[aid]++
				break
			}
		}
	}

	for _, task := range skilledTasks {
		requirements := TaskRequirementsFromTask(task)
		matchingAgents := []*entities.Agent{}
		for _, agent := range agents {
			aid := wdAgentIDString(agent)
			if agentUtilization[aid] >= wdMaxConcurrentTasks(agent) {
				continue
			}
			if s.agentMatchesRequirements(agent, requirements) {
				matchingAgents = append(matchingAgents, agent)
			}
		}
		if len(matchingAgents) > 0 {
			bestMatch := matchingAgents[0]
			for _, agent := range matchingAgents[1:] {
				if agentUtilization[wdAgentIDString(agent)] < agentUtilization[wdAgentIDString(bestMatch)] {
					bestMatch = agent
				}
			}
			plan.AddAssignment(wdTaskIDString(task), wdAgentIDString(bestMatch), "skill_matched")
			agentUtilization[wdAgentIDString(bestMatch)]++
		} else {
			plan.MarkUnassignable(wdTaskIDString(task), "No agent with required skills available")
		}
	}

	for _, task := range regularTasks {
		availableAgents := []*entities.Agent{}
		for _, a := range agents {
			if agentUtilization[wdAgentIDString(a)] < wdMaxConcurrentTasks(a) {
				availableAgents = append(availableAgents, a)
			}
		}
		if len(availableAgents) > 0 {
			leastLoaded := availableAgents[0]
			for _, a := range availableAgents[1:] {
				if agentUtilization[wdAgentIDString(a)] < agentUtilization[wdAgentIDString(leastLoaded)] {
					leastLoaded = a
				}
			}
			plan.AddAssignment(wdTaskIDString(task), wdAgentIDString(leastLoaded), "load_balanced")
			agentUtilization[wdAgentIDString(leastLoaded)]++
		} else {
			plan.MarkUnassignable(wdTaskIDString(task), "All agents at capacity")
		}
	}
}

// agentPerformanceScore is _get_agent_performance_score.
func (s *WorkDistributionService) agentPerformanceScore(agent *entities.Agent) float64 {
	aid := wdAgentIDString(agent)
	if score, ok := s.AgentPerformanceCache[aid]; ok {
		return score
	}
	successRate := 100.0
	if agent.SuccessRate != nil {
		successRate = *agent.SuccessRate
	}
	score := successRate / 100.0
	if agent.AverageTaskDuration != nil && *agent.AverageTaskDuration != 0 {
		durationFactor := 8.0 / *agent.AverageTaskDuration
		if durationFactor > 1.0 {
			durationFactor = 1.0
		}
		score = (score * 0.7) + (durationFactor * 0.3)
	}
	s.AgentPerformanceCache[aid] = score
	return score
}

// agentMatchesRequirements is _agent_matches_requirements.
func (s *WorkDistributionService) agentMatchesRequirements(agent *entities.Agent, requirements TaskRequirements) bool {
	aid := wdAgentIDString(agent)
	for _, excluded := range requirements.ExcludedAgents {
		if excluded == aid {
			return false
		}
	}
	for _, preferred := range requirements.PreferredAgents {
		if preferred == aid {
			return true
		}
	}
	if requirements.RequiredRole != nil {
		switch *requirements.RequiredRole {
		case value_objects.AgentsAgentRoleDeveloper:
			return agent.HasCapability(entities.CapabilityBackendDevelopment)
		case value_objects.AgentsAgentRoleTester:
			return agent.HasCapability(entities.CapabilityTesting)
		}
	}
	return true
}

// executeDistributionPlan is _execute_distribution_plan.
func (s *WorkDistributionService) executeDistributionPlan(ctx context.Context, plan *DistributionPlan) error {
	for _, assignment := range plan.Assignments {
		taskID, agentID, role := assignment[0], assignment[1], assignment[2]
		if err := s.assignAgentSafely(ctx, taskID, agentID, role); err != nil {
			plan.MarkUnassignable(taskID, err.Error())
		}
	}
	return nil
}

// assignAgentSafely mirrors the Python except Exception around assign_agent_to_task;
// a panic is converted to an error so the caller can mark the task unassignable.
func (s *WorkDistributionService) assignAgentSafely(ctx context.Context, taskID, agentID, role string) (err error) {
	defer func() {
		if r := recover(); r != nil {
			err = wdRuntimeError(r)
		}
	}()
	if s.CoordinationService == nil {
		return nil
	}
	return s.CoordinationService.AssignAgentToTask(ctx, taskID, agentID, role, "work_distribution_service")
}

func wdRuntimeError(r any) error {
	switch v := r.(type) {
	case error:
		return v
	case string:
		return NewWorkDistributionException(v)
	}
	return NewWorkDistributionException(value_objects.PyStr(r))
}

// recordDistribution is _record_distribution.
func (s *WorkDistributionService) recordDistribution(plan *DistributionPlan, strategy DistributionStrategy) {
	record := distributionRecord{
		PlanID:            plan.PlanID,
		Timestamp:         plan.CreatedAt,
		Strategy:          string(strategy),
		TotalTasks:        len(plan.Assignments) + len(plan.UnassignableRaw),
		AssignedTasks:     len(plan.Assignments),
		UnassignableTasks: len(plan.UnassignableRaw),
		Assignments:       plan.Assignments,
		Recommendations:   plan.Recommendations,
	}
	s.DistributionHistory = append(s.DistributionHistory, record)
	if len(s.DistributionHistory) > 100 {
		s.DistributionHistory = s.DistributionHistory[len(s.DistributionHistory)-100:]
	}
}

// GetDistributionAnalytics is get_distribution_analytics.
func (s *WorkDistributionService) GetDistributionAnalytics() (*entities.OrderedMap[any], error) {
	if len(s.DistributionHistory) == 0 {
		out := entities.NewOrderedMap[any]()
		out.Set("message", "No distribution history available")
		return out, nil
	}

	totalDistributions := len(s.DistributionHistory)
	totalTasks := 0
	totalAssigned := 0
	strategyUsage := map[string]int{}
	strategySuccess := map[string][2]int{}
	for _, d := range s.DistributionHistory {
		totalTasks += d.TotalTasks
		totalAssigned += d.AssignedTasks
		strategyUsage[d.Strategy]++
		cur := strategySuccess[d.Strategy]
		cur[0] += d.AssignedTasks
		cur[1] += d.TotalTasks
		strategySuccess[d.Strategy] = cur
	}

	usageOrder := wdOrderKeysInt(strategyUsage)
	usageMap := entities.NewOrderedMap[any]()
	for _, k := range usageOrder {
		usageMap.Set(k, strategyUsage[k])
	}
	successMap := entities.NewOrderedMap[any]()
	for _, k := range wdOrderKeysPair(strategySuccess) {
		data := strategySuccess[k]
		rate := 0
		if data[1] > 0 {
			rate = int(float64(data[0]) / float64(data[1]) * 100)
		}
		successMap.Set(k, rate)
	}

	recentReasons := []string{}
	for i := len(s.DistributionHistory) - 10; i < len(s.DistributionHistory); i++ {
		if i < 0 {
			continue
		}
		for _, reason := range s.DistributionHistory[i].Recommendations {
			recentReasons = append(recentReasons, reason)
		}
	}

	out := entities.NewOrderedMap[any]()
	out.Set("total_distributions", totalDistributions)
	out.Set("total_tasks_distributed", totalTasks)
	out.Set("total_tasks_assigned", totalAssigned)
	out.Set("overall_assignment_rate", wdAssignmentRate(totalAssigned, totalTasks))
	out.Set("strategy_usage", usageMap)
	out.Set("strategy_success_rates", successMap)
	out.Set("recent_unassignable_reasons", recentReasons)
	return out, nil
}

func wdAssignmentRate(assigned, total int) any {
	if total > 0 {
		return float64(assigned) / float64(total) * 100
	}
	return 0
}

func wdOrderKeysInt(m map[string]int) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

func wdOrderKeysPair(m map[string][2]int) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

func wdTaskPriorityValue(task *entities.Task) string {
	if task == nil || task.Priority == nil {
		return "none"
	}
	if task.Priority.Value == "" {
		return "none"
	}
	return task.Priority.Value
}
