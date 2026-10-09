// Package event_handlers ports task_management/application/event_handlers.
package event_handlers

import (
	"context"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/interfaces"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Deviation (MIGRATION.md, event_handlers decision 2026-10-02): 13 of 17 Python
// handlers read attributes the agent events do not define and raise
// AttributeError. The Go handlers work against the real event fields; invented
// values (from_agent "", nil agent lists, first outcome, workload placeholders)
// stand in for Python-only attributes.

// AgentCoordinationService is the minimal coordination dependency used by
// AgentEventHandlers (Python `coordination_service: Any | None`); the port is
// application/services/agent_coordination_service.go, and only the methods the
// Python actually calls are declared here.
type AgentCoordinationService interface {
	NotifyAgentAssigned(ctx context.Context, agentID, taskID, role string) error
	NotifyAgentFreed(ctx context.Context, agentID, taskID string) error
	TriggerWorkloadRebalancing(ctx context.Context, overloadedAgent string, workloadLevel float64) error
	ProcessHandoffRequest(ctx context.Context, fromAgent, toAgent, taskID, reason string, handoffContext map[string]any) error
	CompleteHandoff(ctx context.Context, fromAgent, toAgent, taskID string) error
	HandleHandoffRejection(ctx context.Context, fromAgent, rejectedBy, taskID, reason string) error
	InitiateConflictResolution(ctx context.Context, agents []string, conflictType, description string) error
	RecordConflictResolution(ctx context.Context, agents []string, conflictID, strategy, outcome string) error
	SetupCollaboration(ctx context.Context, agents []string, taskID, collaborationType string) error
	FinalizeCollaboration(ctx context.Context, agents []string, taskID string, outcome any) error
	RecordRebalancing(ctx context.Context, agents []string, strategy string, tasksMoved []string) error
	HandleEscalation(ctx context.Context, raisedBy string, taskID *string, reason, severity string) error
	RecordEscalationResolution(ctx context.Context, escalationID, resolution, resolvedBy string) error
}

// AgentEventHandlers handles agent-related domain events.
type AgentEventHandlers struct {
	// mu guards the four in-memory maps below (handlers run on concurrent event deliveries).
	mu                  sync.Mutex
	EventStore          interfaces.IEventStore
	AgentRepository     any
	CoordinationService AgentCoordinationService

	// AgentStats mirrors Python's defaultdict(lambda: {...}).
	AgentStats map[string]map[string]int
	// AgentWorkloads maps agent id -> workload record (nil = key absent).
	AgentWorkloads map[string]map[string]any
	// ActiveCollaborations maps collaboration id (task id) -> participating agents.
	ActiveCollaborations map[string][]string
	// PerformanceHistory maps agent id -> performance records.
	PerformanceHistory map[string][]map[string]any
}

// lock takes the state lock and returns an idempotent unlock.
func (h *AgentEventHandlers) lock() func() {
	h.mu.Lock()
	done := false
	return func() {
		if !done {
			done = true
			h.mu.Unlock()
		}
	}
}

// NewAgentEventHandlers builds the handler with the Python default dict state.
func NewAgentEventHandlers(eventStore interfaces.IEventStore, agentRepository any, coordinationService AgentCoordinationService) *AgentEventHandlers {
	return &AgentEventHandlers{
		EventStore:           eventStore,
		AgentRepository:      agentRepository,
		CoordinationService:  coordinationService,
		AgentStats:           map[string]map[string]int{},
		AgentWorkloads:       map[string]map[string]any{},
		ActiveCollaborations: map[string][]string{},
		PerformanceHistory:   map[string][]map[string]any{},
	}
}

func (h *AgentEventHandlers) stats(agentID string) map[string]int {
	s, ok := h.AgentStats[agentID]
	if !ok {
		s = map[string]int{
			"assignments": 0, "unassignments": 0, "handoffs_requested": 0,
			"handoffs_completed": 0, "conflicts": 0, "escalations": 0, "communications": 0,
		}
		h.AgentStats[agentID] = s
	}
	return s
}

// HandleAgentAssigned handles AgentAssigned.
func (h *AgentEventHandlers) HandleAgentAssigned(ctx context.Context, event events.AgentAssigned) {
	unlock := h.lock()
	defer unlock()
	h.stats(event.AgentID)["assignments"]++

	if _, ok := h.AgentWorkloads[event.AgentID]; !ok {
		h.AgentWorkloads[event.AgentID] = map[string]any{
			"active_tasks":      []string{},
			"total_assignments": 0,
			"last_updated":      time.Now().UTC(),
		}
	}
	w := h.AgentWorkloads[event.AgentID]
	w["active_tasks"] = append(w["active_tasks"].([]string), event.TaskID)
	w["total_assignments"] = w["total_assignments"].(int) + 1
	w["last_updated"] = event.OccurredAt

	if h.CoordinationService != nil {
		unlock() // never call the coordination service while holding the state lock
		_ = h.CoordinationService.NotifyAgentAssigned(ctx, event.AgentID, event.TaskID, event.Role)
	}
}

// HandleAgentUnassigned handles AgentUnassigned.
func (h *AgentEventHandlers) HandleAgentUnassigned(ctx context.Context, event events.AgentUnassigned) {
	unlock := h.lock()
	defer unlock()
	h.stats(event.AgentID)["unassignments"]++

	if w, ok := h.AgentWorkloads[event.AgentID]; ok {
		tasks := w["active_tasks"].([]string)
		for i, t := range tasks {
			if t == event.TaskID {
				tasks = append(tasks[:i], tasks[i+1:]...)
				break
			}
		}
		w["active_tasks"] = tasks
		w["last_updated"] = event.OccurredAt
	}
	if h.CoordinationService != nil {
		unlock() // never call the coordination service while holding the state lock
		_ = h.CoordinationService.NotifyAgentFreed(ctx, event.AgentID, event.TaskID)
	}
}

// HandleAgentWorkloadChanged handles AgentWorkloadChanged.
func (h *AgentEventHandlers) HandleAgentWorkloadChanged(ctx context.Context, event events.AgentWorkloadChanged) {
	unlock := h.lock()
	defer unlock()
	h.AgentWorkloads[event.AgentID] = map[string]any{
		"workload_level": event.NewWorkloadPercentage,
		"previous_level": event.OldWorkloadPercentage,
		"active_tasks":   []string{},
		"last_updated":   event.OccurredAt,
	}
	if event.NewWorkloadPercentage > 0.8 {
		if h.CoordinationService != nil {
			unlock() // never call the coordination service while holding the state lock
			_ = h.CoordinationService.TriggerWorkloadRebalancing(ctx, event.AgentID, event.NewWorkloadPercentage)
		}
	}
}

// HandleWorkHandoffRequested handles WorkHandoffRequested.
func (h *AgentEventHandlers) HandleWorkHandoffRequested(ctx context.Context, event events.WorkHandoffRequested) {
	unlock := h.lock()
	defer unlock()
	h.stats(event.FromAgentID)["handoffs_requested"]++
	if h.CoordinationService != nil {
		unlock() // never call the coordination service while holding the state lock
		_ = h.CoordinationService.ProcessHandoffRequest(ctx, event.FromAgentID, event.ToAgentID, event.TaskID, event.HandoffNotes, map[string]any{})
	}
}

// HandleWorkHandoffAccepted handles WorkHandoffAccepted.
func (h *AgentEventHandlers) HandleWorkHandoffAccepted(ctx context.Context, event events.WorkHandoffAccepted) {
	unlock := h.lock()
	defer unlock()
	if h.CoordinationService != nil {
		unlock() // never call the coordination service while holding the state lock
		_ = h.CoordinationService.CompleteHandoff(ctx, "", event.AcceptedBy, event.TaskID)
	}
}

// HandleWorkHandoffRejected handles WorkHandoffRejected.
func (h *AgentEventHandlers) HandleWorkHandoffRejected(ctx context.Context, event events.WorkHandoffRejected) {
	unlock := h.lock()
	defer unlock()
	if h.CoordinationService != nil {
		unlock() // never call the coordination service while holding the state lock
		_ = h.CoordinationService.HandleHandoffRejection(ctx, "", event.RejectedBy, event.TaskID, event.RejectionReason)
	}
}

// HandleWorkHandoffCompleted handles WorkHandoffCompleted.
func (h *AgentEventHandlers) HandleWorkHandoffCompleted(ctx context.Context, event events.WorkHandoffCompleted) {
	unlock := h.lock()
	defer unlock()
	h.stats(event.FromAgentID)["handoffs_completed"]++
}

// HandleConflictDetected handles ConflictDetected.
func (h *AgentEventHandlers) HandleConflictDetected(ctx context.Context, event events.ConflictDetected) {
	unlock := h.lock()
	defer unlock()
	for _, a := range event.InvolvedAgents {
		h.stats(a)["conflicts"]++
	}
	if h.CoordinationService != nil {
		unlock() // never call the coordination service while holding the state lock
		_ = h.CoordinationService.InitiateConflictResolution(ctx, event.InvolvedAgents, event.ConflictType, event.Description)
	}
}

// HandleConflictResolved handles ConflictResolved.
func (h *AgentEventHandlers) HandleConflictResolved(ctx context.Context, event events.ConflictResolved) {
	unlock := h.lock()
	defer unlock()
	if h.CoordinationService != nil {
		unlock() // never call the coordination service while holding the state lock
		_ = h.CoordinationService.RecordConflictResolution(ctx, nil, event.ConflictID, event.ResolutionStrategy, "resolved")
	}
}

// HandleAgentCollaborationStarted handles AgentCollaborationStarted.
func (h *AgentEventHandlers) HandleAgentCollaborationStarted(ctx context.Context, event events.AgentCollaborationStarted) {
	unlock := h.lock()
	defer unlock()
	h.ActiveCollaborations[event.TaskID] = append([]string{}, event.CollaboratingAgents...)
	if h.CoordinationService != nil {
		unlock() // never call the coordination service while holding the state lock
		_ = h.CoordinationService.SetupCollaboration(ctx, event.CollaboratingAgents, event.TaskID, event.CollaborationType)
	}
}

// HandleAgentCollaborationEnded handles AgentCollaborationEnded.
func (h *AgentEventHandlers) HandleAgentCollaborationEnded(ctx context.Context, event events.AgentCollaborationEnded) {
	unlock := h.lock()
	defer unlock()
	delete(h.ActiveCollaborations, event.TaskID)
	if h.CoordinationService != nil {
		unlock() // never call the coordination service while holding the state lock
		var outcome any
		if len(event.Outcomes) > 0 {
			outcome = event.Outcomes[0]
		}
		_ = h.CoordinationService.FinalizeCollaboration(ctx, nil, event.TaskID, outcome)
	}
}

// HandleAgentStatusBroadcast handles AgentStatusBroadcast.
func (h *AgentEventHandlers) HandleAgentStatusBroadcast(ctx context.Context, event events.AgentStatusBroadcast) {
	unlock := h.lock()
	defer unlock()
	if w, ok := h.AgentWorkloads[event.AgentID]; ok {
		w["status"] = event.Status
		w["last_broadcast"] = event.OccurredAt
	}
}

// HandleAgentWorkloadRebalanced handles AgentWorkloadRebalanced.
func (h *AgentEventHandlers) HandleAgentWorkloadRebalanced(ctx context.Context, event events.AgentWorkloadRebalanced) {
	unlock := h.lock()
	defer unlock()
	if h.CoordinationService != nil {
		unlock() // never call the coordination service while holding the state lock
		_ = h.CoordinationService.RecordRebalancing(ctx, event.AgentsAffected, event.Reason, []string{})
	}
}

// HandleAgentEscalationRaised handles AgentEscalationRaised.
func (h *AgentEventHandlers) HandleAgentEscalationRaised(ctx context.Context, event events.AgentEscalationRaised) {
	unlock := h.lock()
	defer unlock()
	h.stats(event.EscalatingAgent)["escalations"]++
	if h.CoordinationService != nil {
		unlock() // never call the coordination service while holding the state lock
		taskID := event.TaskID
		_ = h.CoordinationService.HandleEscalation(ctx, event.EscalatingAgent, &taskID, event.Reason, event.Severity)
	}
}

// HandleAgentEscalationResolved handles AgentEscalationResolved.
func (h *AgentEventHandlers) HandleAgentEscalationResolved(ctx context.Context, event events.AgentEscalationResolved) {
	unlock := h.lock()
	defer unlock()
	if h.CoordinationService != nil {
		unlock() // never call the coordination service while holding the state lock
		_ = h.CoordinationService.RecordEscalationResolution(ctx, event.EscalationID, event.Resolution, event.ResolvedBy)
	}
}

// HandleAgentCommunicationSent handles AgentCommunicationSent.
func (h *AgentEventHandlers) HandleAgentCommunicationSent(ctx context.Context, event events.AgentCommunicationSent) {
	unlock := h.lock()
	defer unlock()
	h.stats(event.FromAgentID)["communications"]++
}

// HandleAgentPerformanceEvaluated handles AgentPerformanceEvaluated.
func (h *AgentEventHandlers) HandleAgentPerformanceEvaluated(ctx context.Context, event events.AgentPerformanceEvaluated) {
	unlock := h.lock()
	defer unlock()
	record := map[string]any{
		"agent_id":  event.AgentID,
		"score":     event.OverallScore,
		"metrics":   event.Strengths,
		"period":    event.EvaluationID,
		"timestamp": isoOrEmpty(event.OccurredAt),
	}
	hist := append(h.PerformanceHistory[event.AgentID], record)
	if len(hist) > 30 {
		hist = hist[len(hist)-30:]
	}
	h.PerformanceHistory[event.AgentID] = hist
}

func isoOrEmpty(t time.Time) string {
	return value_objects.IsoFormat(t)
}

// GetAgentStatistics returns statistics for one agent or all agents.
func (h *AgentEventHandlers) GetAgentStatistics(ctx context.Context, agentID *string) map[string]any {
	unlock := h.lock()
	defer unlock()
	if agentID != nil {
		key := *agentID
		stats, _ := h.AgentStats[key]
		workload, _ := h.AgentWorkloads[key]
		performance := h.PerformanceHistory[key]
		out := map[string]any{
			"statistics":          map[string]int{},
			"workload":            workload,
			"performance_history": []map[string]any{},
		}
		if stats != nil {
			out["statistics"] = stats
		}
		if len(performance) > 5 {
			performance = performance[len(performance)-5:]
		}
		if len(performance) > 0 {
			out["performance_history"] = performance
		}
		return out
	}

	statisticsByAgent := map[string]map[string]int{}
	for k, v := range h.AgentStats {
		statisticsByAgent[k] = v
	}
	totalActiveTasks := 0
	workloadSum := 0.0
	for _, w := range h.AgentWorkloads {
		if tasks, ok := w["active_tasks"].([]string); ok {
			totalActiveTasks += len(tasks)
		}
		if level, ok := w["workload_level"].(float64); ok {
			workloadSum += level
		}
	}
	avg := 0.0
	if len(h.AgentWorkloads) > 0 {
		avg = workloadSum / float64(len(h.AgentWorkloads))
	}
	return map[string]any{
		"total_agents":          len(h.AgentStats),
		"active_collaborations": len(h.ActiveCollaborations),
		"statistics_by_agent":   statisticsByAgent,
		"workload_summary": map[string]any{
			"total_active_tasks": totalActiveTasks,
			"average_workload":   avg,
		},
	}
}

// ProcessEvent routes an event to the appropriate handler.
func (h *AgentEventHandlers) ProcessEvent(ctx context.Context, event events.Event) {
	switch event.EventType() {
	case "AgentAssigned":
		h.HandleAgentAssigned(ctx, event.(events.AgentAssigned))
	case "AgentUnassigned":
		h.HandleAgentUnassigned(ctx, event.(events.AgentUnassigned))
	case "AgentWorkloadChanged":
		h.HandleAgentWorkloadChanged(ctx, event.(events.AgentWorkloadChanged))
	case "WorkHandoffRequested":
		h.HandleWorkHandoffRequested(ctx, event.(events.WorkHandoffRequested))
	case "WorkHandoffAccepted":
		h.HandleWorkHandoffAccepted(ctx, event.(events.WorkHandoffAccepted))
	case "WorkHandoffRejected":
		h.HandleWorkHandoffRejected(ctx, event.(events.WorkHandoffRejected))
	case "WorkHandoffCompleted":
		h.HandleWorkHandoffCompleted(ctx, event.(events.WorkHandoffCompleted))
	case "ConflictDetected":
		h.HandleConflictDetected(ctx, event.(events.ConflictDetected))
	case "ConflictResolved":
		h.HandleConflictResolved(ctx, event.(events.ConflictResolved))
	case "AgentCollaborationStarted":
		h.HandleAgentCollaborationStarted(ctx, event.(events.AgentCollaborationStarted))
	case "AgentCollaborationEnded":
		h.HandleAgentCollaborationEnded(ctx, event.(events.AgentCollaborationEnded))
	case "AgentStatusBroadcast":
		h.HandleAgentStatusBroadcast(ctx, event.(events.AgentStatusBroadcast))
	case "AgentWorkloadRebalanced":
		h.HandleAgentWorkloadRebalanced(ctx, event.(events.AgentWorkloadRebalanced))
	case "AgentEscalationRaised":
		h.HandleAgentEscalationRaised(ctx, event.(events.AgentEscalationRaised))
	case "AgentEscalationResolved":
		h.HandleAgentEscalationResolved(ctx, event.(events.AgentEscalationResolved))
	case "AgentCommunicationSent":
		h.HandleAgentCommunicationSent(ctx, event.(events.AgentCommunicationSent))
	case "AgentPerformanceEvaluated":
		h.HandleAgentPerformanceEvaluated(ctx, event.(events.AgentPerformanceEvaluated))
	}
}
