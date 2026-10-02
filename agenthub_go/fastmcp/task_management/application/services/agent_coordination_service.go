package services

import (
	"context"
	"fmt"
	"sort"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AgentCoordinationException is agent_coordination_service.AgentCoordinationException.
type AgentCoordinationException struct{ exceptions.DomainException }

func coordErrorf(format string, a ...any) error {
	return &AgentCoordinationException{exceptions.DomainException{Msg: fmt.Sprintf(format, a...)}}
}

// CoordinationTaskRepository is the `get(task_id)` surface the Python service
// calls on its task repository.
type CoordinationTaskRepository interface {
	Get(ctx context.Context, taskID string) (*entities.Task, error)
}

// CoordinationAgentRepository is the Python `agent_repository: Any` surface.
type CoordinationAgentRepository interface {
	Get(ctx context.Context, agentID string) (*entities.Agent, error)
	Save(ctx context.Context, agent *entities.Agent) error
	GetByProject(ctx context.Context, projectID string) ([]*entities.Agent, error)
	GetAll(ctx context.Context) ([]*entities.Agent, error)
}

// CoordinationEventBus is the Python `event_bus: Any` surface.
type CoordinationEventBus interface {
	Publish(ctx context.Context, event events.Event) error
}

// coordinationUserScopedTasks / Agents are the optional `with_user` hooks.
type coordinationUserScopedTasks interface {
	WithUser(userID string) CoordinationTaskRepository
}
type coordinationUserScopedAgents interface {
	WithUser(userID string) CoordinationAgentRepository
}

// CoordinationContext is the context for coordination decisions.
type CoordinationContext struct {
	Task               *entities.Task
	AvailableAgents    []*entities.Agent
	CurrentAssignments map[string][]string
	WorkloadMetrics    map[string]float64
}

// GetAgentWorkload returns the agent workload percentage (0.0 when unknown).
func (c CoordinationContext) GetAgentWorkload(agentID string) float64 {
	return c.WorkloadMetrics[agentID]
}

// IsAgentOverloaded: workload strictly above the threshold (Python default 80.0).
func (c CoordinationContext) IsAgentOverloaded(agentID string, threshold float64) bool {
	return c.GetAgentWorkload(agentID) > threshold
}

// AgentCoordinationService coordinates multi-agent workflows. The in-memory
// maps are guarded by mu; Python is single-threaded.
type AgentCoordinationService struct {
	TaskRepository         CoordinationTaskRepository
	AgentRepository        CoordinationAgentRepository
	EventBus               CoordinationEventBus
	CoordinationRepository any
	userID                 *string

	mu                   sync.Mutex
	CoordinationRequests map[string]value_objects.CoordinationRequest
	WorkAssignments      map[string]value_objects.WorkAssignment
	Handoffs             map[string]*value_objects.WorkHandoff
	Conflicts            map[string]*value_objects.CoordinationConflictResolution
	Communications       []value_objects.AgentCommunication
}

// NewAgentCoordinationService builds the service with empty in-memory state.
func NewAgentCoordinationService(taskRepository CoordinationTaskRepository, agentRepository CoordinationAgentRepository, eventBus CoordinationEventBus, coordinationRepository any, userID *string) *AgentCoordinationService {
	return &AgentCoordinationService{
		TaskRepository: taskRepository, AgentRepository: agentRepository, EventBus: eventBus,
		CoordinationRepository: coordinationRepository, userID: userID,
		CoordinationRequests: map[string]value_objects.CoordinationRequest{},
		WorkAssignments:      map[string]value_objects.WorkAssignment{},
		Handoffs:             map[string]*value_objects.WorkHandoff{},
		Conflicts:            map[string]*value_objects.CoordinationConflictResolution{},
	}
}

// WithUser creates a new service instance scoped to a specific user.
func (s *AgentCoordinationService) WithUser(userID string) *AgentCoordinationService {
	return NewAgentCoordinationService(s.TaskRepository, s.AgentRepository, s.EventBus, s.CoordinationRepository, &userID)
}

func (s *AgentCoordinationService) scopedTasks() CoordinationTaskRepository {
	if r, ok := s.TaskRepository.(coordinationUserScopedTasks); ok && s.userID != nil && *s.userID != "" {
		return r.WithUser(*s.userID)
	}
	return s.TaskRepository
}

func (s *AgentCoordinationService) scopedAgents() CoordinationAgentRepository {
	if r, ok := s.AgentRepository.(coordinationUserScopedAgents); ok && s.userID != nil && *s.userID != "" {
		return r.WithUser(*s.userID)
	}
	return s.AgentRepository
}

// publish mirrors `await self.event_bus.publish(event)`; a missing bus is
// Python's AttributeError on None.
func (s *AgentCoordinationService) publish(ctx context.Context, event events.Event) error {
	if s.EventBus == nil {
		return fmt.Errorf("AttributeError: 'NoneType' object has no attribute 'publish'")
	}
	return s.EventBus.Publish(ctx, event)
}

func agentIDString(a *entities.Agent) string {
	if a.ID == nil {
		return "None"
	}
	return a.ID.String()
}

func orEmpty(l []string) []string {
	if l == nil {
		return []string{}
	}
	return l
}

// AssignAgentToTask assigns an agent to a task.
func (s *AgentCoordinationService) AssignAgentToTask(ctx context.Context, taskID, agentID, role, assignedBy string, responsibilities []string, estimatedHours *float64, dueDate *time.Time) (value_objects.WorkAssignment, error) {
	var zero value_objects.WorkAssignment
	task, err := s.scopedTasks().Get(ctx, taskID)
	if err != nil {
		return zero, err
	}
	if task == nil {
		return zero, coordErrorf("Task %s not found", taskID)
	}
	agent, err := s.scopedAgents().Get(ctx, agentID)
	if err != nil {
		return zero, err
	}
	if agent == nil {
		return zero, coordErrorf("Agent %s not found", agentID)
	}
	if !agent.IsAvailable() {
		return zero, coordErrorf("Agent %s is not available for new assignments", agentID)
	}
	roleCopy := role
	assignment := value_objects.WorkAssignment{
		AssignmentID: value_objects.NewUUIDv4(), TaskID: taskID, AssignedAgentID: agentID,
		AssignedByAgentID: assignedBy, AssignedAt: time.Now(), Role: &roleCopy,
		Responsibilities: orEmpty(responsibilities), EstimatedHours: estimatedHours, DueDate: dueDate,
	}
	if err := agent.StartTask(taskID); err != nil {
		return zero, err
	}
	if err := s.AgentRepository.Save(ctx, agent); err != nil {
		return zero, err
	}
	s.mu.Lock()
	s.WorkAssignments[assignment.AssignmentID] = assignment
	s.mu.Unlock()

	event := events.NewAgentAssigned()
	event.AgentID, event.TaskID, event.Role, event.AssignedBy = agentID, taskID, role, assignedBy
	event.Responsibilities, event.EstimatedHours, event.DueDate = orEmpty(responsibilities), estimatedHours, dueDate
	if err := s.publish(ctx, event); err != nil {
		return zero, err
	}
	return assignment, nil
}

// RequestWorkHandoff requests handoff of work from one agent to another.
func (s *AgentCoordinationService) RequestWorkHandoff(ctx context.Context, fromAgentID, toAgentID, taskID, workSummary string, completedItems, remainingItems []string, handoffNotes string) (*value_objects.WorkHandoff, error) {
	from, err := s.AgentRepository.Get(ctx, fromAgentID)
	if err != nil {
		return nil, err
	}
	to, err := s.AgentRepository.Get(ctx, toAgentID)
	if err != nil {
		return nil, err
	}
	if from == nil || to == nil {
		return nil, coordErrorf("Invalid agent IDs for handoff")
	}
	handoff := value_objects.NewWorkHandoff(value_objects.NewUUIDv4(), fromAgentID, toAgentID, taskID, time.Now())
	handoff.WorkSummary, handoff.CompletedItems, handoff.RemainingItems, handoff.HandoffNotes = workSummary, completedItems, remainingItems, handoffNotes
	s.mu.Lock()
	s.Handoffs[handoff.HandoffID] = handoff
	s.mu.Unlock()

	event := events.NewWorkHandoffRequested()
	event.HandoffID, event.FromAgentID, event.ToAgentID, event.TaskID = handoff.HandoffID, fromAgentID, toAgentID, taskID
	event.WorkSummary, event.CompletedItems, event.RemainingItems, event.HandoffNotes = workSummary, completedItems, remainingItems, handoffNotes
	if err := s.publish(ctx, event); err != nil {
		return nil, err
	}
	return handoff, nil
}

func (s *AgentCoordinationService) targetHandoff(handoffID, agentID string) (*value_objects.WorkHandoff, error) {
	s.mu.Lock()
	handoff := s.Handoffs[handoffID]
	s.mu.Unlock()
	if handoff == nil {
		return nil, coordErrorf("Handoff %s not found", handoffID)
	}
	if handoff.ToAgentID != agentID {
		return nil, coordErrorf("Agent %s is not the target of this handoff", agentID)
	}
	return handoff, nil
}

// AcceptHandoff accepts a work handoff and reassigns the task.
func (s *AgentCoordinationService) AcceptHandoff(ctx context.Context, handoffID, agentID string, notes *string) error {
	handoff, err := s.targetHandoff(handoffID, agentID)
	if err != nil {
		return err
	}
	if err := handoff.Accept(); err != nil {
		return err
	}
	if _, err := s.AssignAgentToTask(ctx, handoff.TaskID, agentID, "continued_work", handoff.FromAgentID, nil, nil, nil); err != nil {
		return err
	}
	event := events.NewWorkHandoffAccepted()
	event.HandoffID, event.AcceptedBy, event.TaskID, event.AcceptanceNotes = handoffID, agentID, handoff.TaskID, notes
	return s.publish(ctx, event)
}

// RejectHandoff rejects a work handoff.
func (s *AgentCoordinationService) RejectHandoff(ctx context.Context, handoffID, agentID, reason string) error {
	handoff, err := s.targetHandoff(handoffID, agentID)
	if err != nil {
		return err
	}
	if err := handoff.Reject(reason); err != nil {
		return err
	}
	event := events.NewWorkHandoffRejected()
	event.HandoffID, event.RejectedBy, event.TaskID, event.RejectionReason = handoffID, agentID, handoff.TaskID, reason
	return s.publish(ctx, event)
}

// DetectAndResolveConflict creates a conflict and optionally auto-resolves it.
func (s *AgentCoordinationService) DetectAndResolveConflict(ctx context.Context, taskID string, conflictType value_objects.ConflictType, involvedAgents []string, description string, strategy *value_objects.ResolutionStrategy) (*value_objects.CoordinationConflictResolution, error) {
	conflict := &value_objects.CoordinationConflictResolution{
		ConflictID: value_objects.NewUUIDv4(), ConflictType: conflictType, InvolvedAgents: involvedAgents,
		TaskID: taskID, DetectedAt: time.Now(), Description: description,
		ConflictingElements: map[string]any{}, ImpactAssessment: "low", Votes: map[string]string{},
	}
	s.mu.Lock()
	s.Conflicts[conflict.ConflictID] = conflict
	s.mu.Unlock()

	detect := events.NewConflictDetected()
	detect.ConflictID, detect.ConflictType, detect.InvolvedAgents = conflict.ConflictID, string(conflictType), orEmpty(involvedAgents)
	detect.TaskID, detect.Description = taskID, description
	if err := s.publish(ctx, detect); err != nil {
		return nil, err
	}
	if strategy != nil {
		if err := s.ResolveConflict(ctx, conflict.ConflictID, *strategy, "agent_coordination_service", "Auto-resolved using "+string(*strategy)+" strategy"); err != nil {
			return nil, err
		}
	}
	return conflict, nil
}

// ResolveConflict resolves a conflict.
func (s *AgentCoordinationService) ResolveConflict(ctx context.Context, conflictID string, strategy value_objects.ResolutionStrategy, resolvedBy, details string) error {
	s.mu.Lock()
	conflict := s.Conflicts[conflictID]
	s.mu.Unlock()
	if conflict == nil {
		return coordErrorf("Conflict %s not found", conflictID)
	}
	if err := conflict.Resolve(strategy, resolvedBy, details); err != nil {
		return err
	}
	event := events.NewConflictResolved()
	event.ConflictID, event.ResolutionStrategy, event.ResolvedBy = conflictID, string(strategy), resolvedBy
	event.TaskID, event.ResolutionDetails = conflict.TaskID, details
	return s.publish(ctx, event)
}

// BroadcastAgentStatus broadcasts agent status to the coordination system.
func (s *AgentCoordinationService) BroadcastAgentStatus(ctx context.Context, agentID, status string, currentTaskID, currentActivity, blockerDescription *string) error {
	agent, err := s.AgentRepository.Get(ctx, agentID)
	if err != nil {
		return err
	}
	if agent == nil {
		return coordErrorf("Agent %s not found", agentID)
	}
	event := events.NewAgentStatusBroadcast()
	event.AgentID, event.Status = agentID, status
	event.CurrentTaskID, event.CurrentActivity, event.BlockerDescription = currentTaskID, currentActivity, blockerDescription
	event.WorkloadPercentage = agent.GetWorkloadPercentage()
	return s.publish(ctx, event)
}

func workloads(agents []*entities.Agent) map[string]int {
	out := make(map[string]int, len(agents))
	for _, a := range agents {
		out[agentIDString(a)] = len(a.ActiveTasks)
	}
	return out
}

func sortedTaskIDs(m map[string]struct{}) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

// RebalanceResult is the dict returned by rebalance_workload.
type RebalanceResult struct {
	TasksReassigned map[string]string
	WorkloadBefore  map[string]int
	WorkloadAfter   map[string]int
}

// RebalanceWorkload rebalances workload across the agents of a project.
func (s *AgentCoordinationService) RebalanceWorkload(ctx context.Context, projectID, initiatedBy, reason string) (*RebalanceResult, error) {
	agents, err := s.AgentRepository.GetByProject(ctx, projectID)
	if err != nil {
		return nil, err
	}
	before := workloads(agents)
	var overloaded, under []*entities.Agent
	for _, a := range agents {
		if a.GetWorkloadPercentage() > 80 {
			overloaded = append(overloaded, a)
		}
	}
	for _, a := range agents {
		if a.GetWorkloadPercentage() < 40 && a.IsAvailable() {
			under = append(under, a)
		}
	}
	reassigned := map[string]string{}
	for _, over := range overloaded {
		if len(under) == 0 {
			break
		}
		tasks := sortedTaskIDs(over.ActiveTasks)
		if len(tasks) > 1 {
			tasks = tasks[:1] // one task at a time
		}
		for _, taskID := range tasks {
			if len(under) == 0 {
				continue
			}
			target := under[0]
			if _, err := s.RequestWorkHandoff(ctx, agentIDString(over), agentIDString(target), taskID,
				"Workload rebalancing", []string{}, []string{"Continue current work"},
				"Rebalancing workload: "+reason); err != nil {
				return nil, err
			}
			reassigned[taskID] = agentIDString(target)
			if target.GetWorkloadPercentage() >= 40 {
				under = under[1:]
			}
		}
	}
	agentsAfter, err := s.AgentRepository.GetByProject(ctx, projectID)
	if err != nil {
		return nil, err
	}
	after := workloads(agentsAfter)

	seen := map[string]struct{}{}
	var affected []string
	add := func(id string) {
		if _, ok := seen[id]; !ok {
			seen[id] = struct{}{}
			affected = append(affected, id)
		}
	}
	keys := make([]string, 0, len(before))
	for k := range before {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		add(k)
	}
	for _, id := range sortedValues(reassigned) {
		add(id)
	}
	event := events.NewAgentWorkloadRebalanced()
	event.RebalanceID, event.InitiatedBy, event.AgentsAffected = value_objects.NewUUIDv4(), initiatedBy, affected
	event.TasksReassigned, event.Reason, event.WorkloadBefore, event.WorkloadAfter = reassigned, reason, before, after
	if err := s.publish(ctx, event); err != nil {
		return nil, err
	}
	return &RebalanceResult{TasksReassigned: reassigned, WorkloadBefore: before, WorkloadAfter: after}, nil
}

func sortedValues(m map[string]string) []string {
	out := make([]string, 0, len(m))
	for _, v := range m {
		out = append(out, v)
	}
	sort.Strings(out)
	return out
}

// GetAgentWorkload returns detailed workload information for an agent.
func (s *AgentCoordinationService) GetAgentWorkload(ctx context.Context, agentID string) (*entities.OrderedMap[any], error) {
	agent, err := s.AgentRepository.Get(ctx, agentID)
	if err != nil {
		return nil, err
	}
	if agent == nil {
		return nil, coordErrorf("Agent %s not found", agentID)
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	var active []any
	for _, a := range s.sortedAssignments() {
		if _, ok := agent.ActiveTasks[a.TaskID]; ok && a.AssignedAgentID == agentID {
			var role, due any
			if a.Role != nil {
				role = *a.Role
			}
			if a.DueDate != nil {
				due = *a.DueDate
			}
			item := entities.NewOrderedMap[any]()
			item.Set("task_id", a.TaskID)
			item.Set("role", role)
			item.Set("assigned_at", value_objects.IsoFormat(a.AssignedAt))
			item.Set("due_date", due)
			active = append(active, item)
		}
	}
	if active == nil {
		active = []any{}
	}
	toRecv, toGive := 0, 0
	for _, h := range s.Handoffs {
		if h.Status != value_objects.HandoffStatusPending {
			continue
		}
		if h.ToAgentID == agentID {
			toRecv++
		}
		if h.FromAgentID == agentID {
			toGive++
		}
	}
	out := entities.NewOrderedMap[any]()
	out.Set("agent_id", agentID)
	out.Set("status", string(agent.Status))
	out.Set("workload_percentage", agent.GetWorkloadPercentage())
	out.Set("current_tasks", len(agent.ActiveTasks))
	out.Set("max_tasks", *agent.MaxConcurrentTasks)
	out.Set("active_assignments", active)
	out.Set("pending_handoffs_to_receive", toRecv)
	out.Set("pending_handoffs_to_give", toGive)
	out.Set("can_accept_work", agent.IsAvailable())
	return out, nil
}

// sortedAssignments returns assignments in assigned_at order (Python dict
// insertion order). Caller holds mu.
func (s *AgentCoordinationService) sortedAssignments() []value_objects.WorkAssignment {
	out := make([]value_objects.WorkAssignment, 0, len(s.WorkAssignments))
	for _, a := range s.WorkAssignments {
		out = append(out, a)
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].AssignedAt.Before(out[j].AssignedAt) })
	return out
}

// FindBestAgentForTask finds the best available agent (score > 0.5) or nil.
func (s *AgentCoordinationService) FindBestAgentForTask(ctx context.Context, taskID string, requiredRole *value_objects.AgentsAgentRole, requiredExpertise map[value_objects.AgentExpertise]struct{}, requiredSkills map[string]float64) (*entities.Agent, error) {
	task, err := s.TaskRepository.Get(ctx, taskID)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, coordErrorf("Task %s not found", taskID)
	}
	all, err := s.AgentRepository.GetAll(ctx)
	if err != nil {
		return nil, err
	}
	var available []*entities.Agent
	for _, a := range all {
		if a.IsAvailable() {
			available = append(available, a)
		}
	}
	if len(available) == 0 {
		return nil, nil
	}
	expertise := make([]value_objects.AgentExpertise, 0, len(requiredExpertise))
	for e := range requiredExpertise {
		expertise = append(expertise, e)
	}
	sort.Slice(expertise, func(i, j int) bool { return expertise[i] < expertise[j] })
	skillNames := make([]string, 0, len(requiredSkills))
	for k := range requiredSkills {
		skillNames = append(skillNames, k)
	}
	sort.Strings(skillNames)
	skills := make([]value_objects.SkillRequirement, 0, len(skillNames))
	for _, k := range skillNames {
		skills = append(skills, value_objects.SkillRequirement{Skill: k, Level: requiredSkills[k]})
	}
	req := value_objects.TaskRequirements{Role: requiredRole, Expertise: expertise, Skills: skills}

	var best *entities.Agent
	bestScore := 0.0
	for i, a := range available {
		caps := value_objects.NewAgentCapabilities(value_objects.AgentsAgentRoleDeveloper)
		for e := range requiredExpertise {
			caps.ExpertiseAreas[e] = struct{}{}
		}
		for k, v := range requiredSkills {
			caps.SkillLevels[k] = v
		}
		profile := value_objects.NewAgentProfile(agentIDString(a), a.Name, caps)
		profile.AvailabilityScore = 1.0 - (a.GetWorkloadPercentage() / 100.0)
		successRate := 100.0 // Python default when unset
		if a.SuccessRate != nil {
			successRate = *a.SuccessRate
		}
		profile.PerformanceScore = successRate / 100.0
		score := profile.OverallSuitabilityScore(req)
		if i == 0 || score > bestScore { // stable: first of equal scores wins, like sort(reverse=True)
			best, bestScore = a, score
		}
	}
	if best != nil && bestScore > 0.5 {
		return best, nil
	}
	return nil, nil
}
