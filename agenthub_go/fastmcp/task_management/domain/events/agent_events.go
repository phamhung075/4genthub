package events

import "time"

// AgentAssigned: Event raised when an agent is assigned to a task
type AgentAssigned struct {
	BaseDomainEvent
	AgentID          string     `dict:"agent_id"`
	TaskID           string     `dict:"task_id"`
	Role             string     `dict:"role"`
	AssignedBy       string     `dict:"assigned_by"`
	Responsibilities []string   `dict:"responsibilities"`
	EstimatedHours   *float64   `dict:"estimated_hours"`
	DueDate          *time.Time `dict:"due_date"`
}

// NewAgentAssigned applies the Python field defaults.
func NewAgentAssigned() AgentAssigned {
	e := AgentAssigned{BaseDomainEvent: NewBaseDomainEvent()}
	e.Responsibilities = []string{}
	return e
}

func (e AgentAssigned) EventType() string { return "AgentAssigned" }

func (e AgentAssigned) ToDict() map[string]any { return EventToDict(e, "AgentAssigned") }

// AgentUnassigned: Event raised when an agent is unassigned from a task
type AgentUnassigned struct {
	BaseDomainEvent
	AgentID        string  `dict:"agent_id"`
	TaskID         string  `dict:"task_id"`
	UnassignedBy   string  `dict:"unassigned_by"`
	Reason         string  `dict:"reason"`
	HandoffToAgent *string `dict:"handoff_to_agent"`
	HandoffNotes   *string `dict:"handoff_notes"`
}

// NewAgentUnassigned applies the Python field defaults.
func NewAgentUnassigned() AgentUnassigned {
	e := AgentUnassigned{BaseDomainEvent: NewBaseDomainEvent()}
	return e
}

func (e AgentUnassigned) EventType() string { return "AgentUnassigned" }

func (e AgentUnassigned) ToDict() map[string]any { return EventToDict(e, "AgentUnassigned") }

// WorkHandoffRequested: Event raised when work handoff is requested
type WorkHandoffRequested struct {
	BaseDomainEvent
	HandoffID      string   `dict:"handoff_id"`
	FromAgentID    string   `dict:"from_agent_id"`
	ToAgentID      string   `dict:"to_agent_id"`
	TaskID         string   `dict:"task_id"`
	WorkSummary    string   `dict:"work_summary"`
	CompletedItems []string `dict:"completed_items"`
	RemainingItems []string `dict:"remaining_items"`
	HandoffNotes   string   `dict:"handoff_notes"`
}

// NewWorkHandoffRequested applies the Python field defaults.
func NewWorkHandoffRequested() WorkHandoffRequested {
	e := WorkHandoffRequested{BaseDomainEvent: NewBaseDomainEvent()}
	e.CompletedItems = []string{}
	e.RemainingItems = []string{}
	e.CompletedItems = []string{}
	e.RemainingItems = []string{}
	return e
}

func (e WorkHandoffRequested) EventType() string { return "WorkHandoffRequested" }

func (e WorkHandoffRequested) ToDict() map[string]any { return EventToDict(e, "WorkHandoffRequested") }

// WorkHandoffAccepted: Event raised when work handoff is accepted
type WorkHandoffAccepted struct {
	BaseDomainEvent
	HandoffID       string  `dict:"handoff_id"`
	AcceptedBy      string  `dict:"accepted_by"`
	TaskID          string  `dict:"task_id"`
	AcceptanceNotes *string `dict:"acceptance_notes"`
}

// NewWorkHandoffAccepted applies the Python field defaults.
func NewWorkHandoffAccepted() WorkHandoffAccepted {
	e := WorkHandoffAccepted{BaseDomainEvent: NewBaseDomainEvent()}
	return e
}

func (e WorkHandoffAccepted) EventType() string { return "WorkHandoffAccepted" }

func (e WorkHandoffAccepted) ToDict() map[string]any { return EventToDict(e, "WorkHandoffAccepted") }

// WorkHandoffRejected: Event raised when work handoff is rejected
type WorkHandoffRejected struct {
	BaseDomainEvent
	HandoffID       string `dict:"handoff_id"`
	RejectedBy      string `dict:"rejected_by"`
	TaskID          string `dict:"task_id"`
	RejectionReason string `dict:"rejection_reason"`
}

// NewWorkHandoffRejected applies the Python field defaults.
func NewWorkHandoffRejected() WorkHandoffRejected {
	e := WorkHandoffRejected{BaseDomainEvent: NewBaseDomainEvent()}
	return e
}

func (e WorkHandoffRejected) EventType() string { return "WorkHandoffRejected" }

func (e WorkHandoffRejected) ToDict() map[string]any { return EventToDict(e, "WorkHandoffRejected") }

// WorkHandoffCompleted: Event raised when work handoff is completed
type WorkHandoffCompleted struct {
	BaseDomainEvent
	HandoffID                 string  `dict:"handoff_id"`
	FromAgentID               string  `dict:"from_agent_id"`
	ToAgentID                 string  `dict:"to_agent_id"`
	TaskID                    string  `dict:"task_id"`
	HandoffDurationHours      float64 `dict:"handoff_duration_hours"`
	KnowledgeTransferComplete bool    `dict:"knowledge_transfer_complete"`
}

// NewWorkHandoffCompleted applies the Python field defaults.
func NewWorkHandoffCompleted() WorkHandoffCompleted {
	e := WorkHandoffCompleted{BaseDomainEvent: NewBaseDomainEvent()}
	e.KnowledgeTransferComplete = true
	return e
}

func (e WorkHandoffCompleted) EventType() string { return "WorkHandoffCompleted" }

func (e WorkHandoffCompleted) ToDict() map[string]any { return EventToDict(e, "WorkHandoffCompleted") }

// ConflictDetected: Event raised when a conflict is detected
type ConflictDetected struct {
	BaseDomainEvent
	ConflictID          string         `dict:"conflict_id"`
	ConflictType        string         `dict:"conflict_type"`
	InvolvedAgents      []string       `dict:"involved_agents"`
	TaskID              string         `dict:"task_id"`
	Description         string         `dict:"description"`
	ConflictingElements map[string]any `dict:"conflicting_elements"`
	ImpactAssessment    string         `dict:"impact_assessment"`
	SuggestedResolution *string        `dict:"suggested_resolution"`
}

// NewConflictDetected applies the Python field defaults.
func NewConflictDetected() ConflictDetected {
	e := ConflictDetected{BaseDomainEvent: NewBaseDomainEvent()}
	e.InvolvedAgents = []string{}
	e.ConflictingElements = map[string]any{}
	e.ImpactAssessment = "low"
	e.InvolvedAgents = []string{}
	e.ConflictingElements = map[string]any{}
	return e
}

func (e ConflictDetected) EventType() string { return "ConflictDetected" }

func (e ConflictDetected) ToDict() map[string]any { return EventToDict(e, "ConflictDetected") }

// ConflictResolved: Event raised when a conflict is resolved
type ConflictResolved struct {
	BaseDomainEvent
	ConflictID         string         `dict:"conflict_id"`
	ResolutionStrategy string         `dict:"resolution_strategy"`
	ResolvedBy         string         `dict:"resolved_by"`
	TaskID             string         `dict:"task_id"`
	ResolutionDetails  string         `dict:"resolution_details"`
	WinningAgent       *string        `dict:"winning_agent"`
	CompromiseDetails  map[string]any `dict:"compromise_details"`
}

// NewConflictResolved applies the Python field defaults.
func NewConflictResolved() ConflictResolved {
	e := ConflictResolved{BaseDomainEvent: NewBaseDomainEvent()}
	return e
}

func (e ConflictResolved) EventType() string { return "ConflictResolved" }

func (e ConflictResolved) ToDict() map[string]any { return EventToDict(e, "ConflictResolved") }

// AgentCollaborationStarted: Event raised when agents start collaborating
type AgentCollaborationStarted struct {
	BaseDomainEvent
	CollaborationID       string   `dict:"collaboration_id"`
	InitiatingAgent       string   `dict:"initiating_agent"`
	CollaboratingAgents   []string `dict:"collaborating_agents"`
	TaskID                string   `dict:"task_id"`
	CollaborationType     string   `dict:"collaboration_type"`
	Objectives            []string `dict:"objectives"`
	ExpectedDurationHours *float64 `dict:"expected_duration_hours"`
}

// NewAgentCollaborationStarted applies the Python field defaults.
func NewAgentCollaborationStarted() AgentCollaborationStarted {
	e := AgentCollaborationStarted{BaseDomainEvent: NewBaseDomainEvent()}
	e.CollaboratingAgents = []string{}
	e.CollaborationType = "general"
	e.Objectives = []string{}
	e.CollaboratingAgents = []string{}
	e.Objectives = []string{}
	return e
}

func (e AgentCollaborationStarted) EventType() string { return "AgentCollaborationStarted" }

func (e AgentCollaborationStarted) ToDict() map[string]any {
	return EventToDict(e, "AgentCollaborationStarted")
}

// AgentCollaborationEnded: Event raised when collaboration ends
type AgentCollaborationEnded struct {
	BaseDomainEvent
	CollaborationID string            `dict:"collaboration_id"`
	TaskID          string            `dict:"task_id"`
	Outcomes        []string          `dict:"outcomes"`
	DecisionsMade   map[string]string `dict:"decisions_made"`
	FollowUpActions []map[string]any  `dict:"follow_up_actions"`
	DurationHours   float64           `dict:"duration_hours"`
}

// NewAgentCollaborationEnded applies the Python field defaults.
func NewAgentCollaborationEnded() AgentCollaborationEnded {
	e := AgentCollaborationEnded{BaseDomainEvent: NewBaseDomainEvent()}
	e.Outcomes = []string{}
	e.DecisionsMade = map[string]string{}
	e.FollowUpActions = []map[string]any{}
	e.Outcomes = []string{}
	e.DecisionsMade = map[string]string{}
	e.FollowUpActions = []map[string]any{}
	return e
}

func (e AgentCollaborationEnded) EventType() string { return "AgentCollaborationEnded" }

func (e AgentCollaborationEnded) ToDict() map[string]any {
	return EventToDict(e, "AgentCollaborationEnded")
}

// AgentStatusBroadcast: Event raised when agent broadcasts status
type AgentStatusBroadcast struct {
	BaseDomainEvent
	AgentID               string     `dict:"agent_id"`
	Status                string     `dict:"status"`
	CurrentTaskID         *string    `dict:"current_task_id"`
	CurrentActivity       *string    `dict:"current_activity"`
	BlockerDescription    *string    `dict:"blocker_description"`
	EstimatedAvailability *time.Time `dict:"estimated_availability"`
	WorkloadPercentage    float64    `dict:"workload_percentage"`
}

// NewAgentStatusBroadcast applies the Python field defaults.
func NewAgentStatusBroadcast() AgentStatusBroadcast {
	e := AgentStatusBroadcast{BaseDomainEvent: NewBaseDomainEvent()}
	return e
}

func (e AgentStatusBroadcast) EventType() string { return "AgentStatusBroadcast" }

func (e AgentStatusBroadcast) ToDict() map[string]any { return EventToDict(e, "AgentStatusBroadcast") }

// AgentWorkloadRebalanced: Event raised when workload is rebalanced
type AgentWorkloadRebalanced struct {
	BaseDomainEvent
	RebalanceID     string            `dict:"rebalance_id"`
	InitiatedBy     string            `dict:"initiated_by"`
	AgentsAffected  []string          `dict:"agents_affected"`
	TasksReassigned map[string]string `dict:"tasks_reassigned"`
	Reason          string            `dict:"reason"`
	WorkloadBefore  map[string]int    `dict:"workload_before"`
	WorkloadAfter   map[string]int    `dict:"workload_after"`
}

// NewAgentWorkloadRebalanced applies the Python field defaults.
func NewAgentWorkloadRebalanced() AgentWorkloadRebalanced {
	e := AgentWorkloadRebalanced{BaseDomainEvent: NewBaseDomainEvent()}
	e.AgentsAffected = []string{}
	e.TasksReassigned = map[string]string{}
	e.WorkloadBefore = map[string]int{}
	e.WorkloadAfter = map[string]int{}
	e.AgentsAffected = []string{}
	e.TasksReassigned = map[string]string{}
	e.WorkloadBefore = map[string]int{}
	e.WorkloadAfter = map[string]int{}
	return e
}

func (e AgentWorkloadRebalanced) EventType() string { return "AgentWorkloadRebalanced" }

func (e AgentWorkloadRebalanced) ToDict() map[string]any {
	return EventToDict(e, "AgentWorkloadRebalanced")
}

// AgentWorkloadChanged: Event raised when an agent's workload changes.
type AgentWorkloadChanged struct {
	BaseDomainEvent
	AgentID               string  `dict:"agent_id"`
	OldTaskCount          int     `dict:"old_task_count"`
	NewTaskCount          int     `dict:"new_task_count"`
	OldWorkloadPercentage float64 `dict:"old_workload_percentage"`
	NewWorkloadPercentage float64 `dict:"new_workload_percentage"`
	Reason                string  `dict:"reason"`
}

// NewAgentWorkloadChanged applies the Python field defaults.
func NewAgentWorkloadChanged() AgentWorkloadChanged {
	e := AgentWorkloadChanged{BaseDomainEvent: NewBaseDomainEvent()}
	return e
}

func (e AgentWorkloadChanged) EventType() string { return "AgentWorkloadChanged" }

func (e AgentWorkloadChanged) ToDict() map[string]any { return EventToDict(e, "AgentWorkloadChanged") }

// AgentEscalationRaised: Event raised when escalation is needed
type AgentEscalationRaised struct {
	BaseDomainEvent
	EscalationID    string         `dict:"escalation_id"`
	EscalatingAgent string         `dict:"escalating_agent"`
	EscalatedTo     string         `dict:"escalated_to"`
	TaskID          string         `dict:"task_id"`
	Reason          string         `dict:"reason"`
	Severity        string         `dict:"severity"`
	Context         map[string]any `dict:"context"`
	RequestedAction string         `dict:"requested_action"`
	Deadline        *time.Time     `dict:"deadline"`
}

// NewAgentEscalationRaised applies the Python field defaults.
func NewAgentEscalationRaised() AgentEscalationRaised {
	e := AgentEscalationRaised{BaseDomainEvent: NewBaseDomainEvent()}
	e.Severity = "medium"
	e.Context = map[string]any{}
	return e
}

func (e AgentEscalationRaised) EventType() string { return "AgentEscalationRaised" }

func (e AgentEscalationRaised) ToDict() map[string]any {
	return EventToDict(e, "AgentEscalationRaised")
}

// AgentEscalationResolved: Event raised when escalation is resolved
type AgentEscalationResolved struct {
	BaseDomainEvent
	EscalationID     string   `dict:"escalation_id"`
	ResolvedBy       string   `dict:"resolved_by"`
	TaskID           string   `dict:"task_id"`
	Resolution       string   `dict:"resolution"`
	ActionsTaken     []string `dict:"actions_taken"`
	GuidanceProvided *string  `dict:"guidance_provided"`
}

// NewAgentEscalationResolved applies the Python field defaults.
func NewAgentEscalationResolved() AgentEscalationResolved {
	e := AgentEscalationResolved{BaseDomainEvent: NewBaseDomainEvent()}
	e.ActionsTaken = []string{}
	return e
}

func (e AgentEscalationResolved) EventType() string { return "AgentEscalationResolved" }

func (e AgentEscalationResolved) ToDict() map[string]any {
	return EventToDict(e, "AgentEscalationResolved")
}

// AgentCommunicationSent: Event raised when agent sends communication
type AgentCommunicationSent struct {
	BaseDomainEvent
	MessageID        string   `dict:"message_id"`
	FromAgentID      string   `dict:"from_agent_id"`
	ToAgentIds       []string `dict:"to_agent_ids"`
	MessageType      string   `dict:"message_type"`
	Subject          string   `dict:"subject"`
	Priority         string   `dict:"priority"`
	TaskID           *string  `dict:"task_id"`
	RequiresResponse bool     `dict:"requires_response"`
}

// NewAgentCommunicationSent applies the Python field defaults.
func NewAgentCommunicationSent() AgentCommunicationSent {
	e := AgentCommunicationSent{BaseDomainEvent: NewBaseDomainEvent()}
	e.ToAgentIds = []string{}
	e.MessageType = "status_update"
	e.Priority = "normal"
	e.ToAgentIds = []string{}
	return e
}

func (e AgentCommunicationSent) EventType() string { return "AgentCommunicationSent" }

func (e AgentCommunicationSent) ToDict() map[string]any {
	return EventToDict(e, "AgentCommunicationSent")
}

// AgentPerformanceEvaluated: Event raised when agent performance is evaluated
type AgentPerformanceEvaluated struct {
	BaseDomainEvent
	AgentID             string   `dict:"agent_id"`
	EvaluationID        string   `dict:"evaluation_id"`
	EvaluatedBy         *string  `dict:"evaluated_by"`
	TaskID              *string  `dict:"task_id"`
	QualityScore        float64  `dict:"quality_score"`
	TimelinessScore     float64  `dict:"timeliness_score"`
	CollaborationScore  float64  `dict:"collaboration_score"`
	OverallScore        float64  `dict:"overall_score"`
	Strengths           []string `dict:"strengths"`
	AreasForImprovement []string `dict:"areas_for_improvement"`
}

// NewAgentPerformanceEvaluated applies the Python field defaults.
func NewAgentPerformanceEvaluated() AgentPerformanceEvaluated {
	e := AgentPerformanceEvaluated{BaseDomainEvent: NewBaseDomainEvent()}
	e.Strengths = []string{}
	e.AreasForImprovement = []string{}
	e.Strengths = []string{}
	e.AreasForImprovement = []string{}
	return e
}

func (e AgentPerformanceEvaluated) EventType() string { return "AgentPerformanceEvaluated" }

func (e AgentPerformanceEvaluated) ToDict() map[string]any {
	return EventToDict(e, "AgentPerformanceEvaluated")
}
