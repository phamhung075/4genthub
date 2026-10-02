package entities

import (
	"errors"
	"sort"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AgentStatus is the agent status enumeration.
type AgentStatus string

const (
	AgentStatusAvailable AgentStatus = "available"
	AgentStatusBusy      AgentStatus = "busy"
	AgentStatusOffline   AgentStatus = "offline"
	AgentStatusPaused    AgentStatus = "paused"
)

// AgentCapability is the agent capability enumeration.
type AgentCapability string

const (
	CapabilityFrontendDevelopment AgentCapability = "frontend_development"
	CapabilityBackendDevelopment  AgentCapability = "backend_development"
	CapabilityDevops              AgentCapability = "devops"
	CapabilityTesting             AgentCapability = "testing"
	CapabilitySecurity            AgentCapability = "security"
	CapabilityDocumentation       AgentCapability = "documentation"
	CapabilityArchitecture        AgentCapability = "architecture"
	CapabilityCodeReview          AgentCapability = "code_review"
	CapabilityProjectManagement   AgentCapability = "project_management"
	CapabilityDataAnalysis        AgentCapability = "data_analysis"
)

// AgentCapabilityValues lists every capability in declaration order.
var AgentCapabilityValues = []AgentCapability{
	CapabilityFrontendDevelopment, CapabilityBackendDevelopment, CapabilityDevops, CapabilityTesting,
	CapabilitySecurity, CapabilityDocumentation, CapabilityArchitecture, CapabilityCodeReview,
	CapabilityProjectManagement, CapabilityDataAnalysis,
}

// ErrZeroDivision stands in for Python's ZeroDivisionError.
var ErrZeroDivision = errors.New("division by zero")

// TaskRequirements is the dict Agent.can_handle_task reads ("capabilities",
// "languages", "frameworks", "priority"). Priority "" means the key is absent
// (Python default "medium").
type TaskRequirements struct {
	Capabilities []string
	Languages    []string
	Frameworks   []string
	Priority     string
}

// Agent represents an AI agent that can work on tasks. Python sets are
// stored as maps; output lists are sorted (capabilities in declaration order)
// because Python set order is unspecified.
type Agent struct {
	base.BaseTimestampEntity
	ID                  *value_objects.AgentId
	Name                string
	Description         string
	Capabilities        map[AgentCapability]struct{}
	Specializations     []string
	PreferredLanguages  []string
	PreferredFrameworks []string
	Status              AgentStatus // "" → AVAILABLE
	MaxConcurrentTasks  *int        // nil → 1
	CurrentWorkload     int
	WorkHours           map[string]string
	Timezone            string // "" → "UTC"
	PriorityPreference  string // "" → "high"
	CompletedTasks      int
	AverageTaskDuration *float64
	SuccessRate         *float64 // nil → 100.0
	AssignedProjects    map[string]struct{}
	AssignedTrees       map[string]struct{}
	ActiveTasks         map[string]struct{}
}

// NewAgent applies the Python dataclass defaults, initializes timestamps and validates.
func NewAgent(a Agent) (*Agent, error) {
	s := a
	if s.Status == "" {
		s.Status = AgentStatusAvailable
	}
	if s.MaxConcurrentTasks == nil {
		one := 1
		s.MaxConcurrentTasks = &one
	}
	if s.Timezone == "" {
		s.Timezone = "UTC"
	}
	if s.PriorityPreference == "" {
		s.PriorityPreference = "high"
	}
	if s.SuccessRate == nil {
		hundred := 100.0
		s.SuccessRate = &hundred
	}
	if s.Capabilities == nil {
		s.Capabilities = map[AgentCapability]struct{}{}
	}
	if s.Specializations == nil {
		s.Specializations = []string{}
	}
	if s.PreferredLanguages == nil {
		s.PreferredLanguages = []string{}
	}
	if s.PreferredFrameworks == nil {
		s.PreferredFrameworks = []string{}
	}
	if s.AssignedProjects == nil {
		s.AssignedProjects = map[string]struct{}{}
	}
	if s.AssignedTrees == nil {
		s.AssignedTrees = map[string]struct{}{}
	}
	if s.ActiveTasks == nil {
		s.ActiveTasks = map[string]struct{}{}
	}
	if err := s.Init(&s); err != nil {
		return nil, err
	}
	return &s, nil
}

func (a *Agent) idStr() string {
	if a.ID == nil {
		return "None"
	}
	return a.ID.String()
}

func (a *Agent) GetEntityID() string {
	if a.ID == nil {
		return "unknown"
	}
	return a.ID.String()
}

func (a *Agent) ValidateEntity() error {
	if a.ID == nil {
		return value_objects.ValueErrorf("Agent id cannot be empty")
	}
	if strings.TrimSpace(a.Name) == "" {
		return value_objects.ValueErrorf("Agent name cannot be empty")
	}
	return nil
}

func (a *Agent) maxTasks() int { return *a.MaxConcurrentTasks }

func sortedKeys(m map[string]struct{}) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func (a *Agent) sortedCapabilities() []AgentCapability {
	out := []AgentCapability{}
	for _, c := range AgentCapabilityValues {
		if _, ok := a.Capabilities[c]; ok {
			out = append(out, c)
		}
	}
	return out
}

func (a *Agent) AddCapability(c AgentCapability) error {
	a.Capabilities[c] = struct{}{}
	return a.Touch("capability_added")
}

func (a *Agent) RemoveCapability(c AgentCapability) error {
	delete(a.Capabilities, c)
	return a.Touch("capability_removed")
}

func (a *Agent) HasCapability(c AgentCapability) bool {
	_, ok := a.Capabilities[c]
	return ok
}

func anyIn(wanted, have []string) bool {
	for _, w := range wanted {
		for _, h := range have {
			if w == h {
				return true
			}
		}
	}
	return false
}

// CanHandleTask checks capabilities, languages and frameworks; unknown capability strings are skipped.
func (a *Agent) CanHandleTask(r TaskRequirements) bool {
	for _, req := range r.Capabilities {
		known := false
		for _, c := range AgentCapabilityValues {
			if string(c) == req {
				known = true
				break
			}
		}
		if !known {
			continue
		}
		if !a.HasCapability(AgentCapability(req)) {
			return false
		}
	}
	if len(r.Languages) > 0 && !anyIn(r.Languages, a.PreferredLanguages) {
		return false
	}
	if len(r.Frameworks) > 0 && !anyIn(r.Frameworks, a.PreferredFrameworks) {
		return false
	}
	return true
}

func (a *Agent) IsAvailable() bool {
	return a.Status == AgentStatusAvailable && a.CurrentWorkload < a.maxTasks()
}

func (a *Agent) AssignToProject(projectID string) error {
	a.AssignedProjects[projectID] = struct{}{}
	return a.Touch("project_assignment_added")
}

func (a *Agent) AssignToTree(gitBranchName string) error {
	a.AssignedTrees[gitBranchName] = struct{}{}
	return a.Touch("tree_assignment_added")
}

func (a *Agent) UnassignFromTree(gitBranchName string) error {
	if _, ok := a.AssignedTrees[gitBranchName]; ok {
		delete(a.AssignedTrees, gitBranchName)
		return a.Touch("tree_assignment_removed")
	}
	return nil
}

func (a *Agent) UnassignFromAllTrees() error {
	if len(a.AssignedTrees) > 0 {
		a.AssignedTrees = map[string]struct{}{}
		return a.Touch("all_tree_assignments_removed")
	}
	return nil
}

func (a *Agent) StartTask(taskID string) error {
	if !a.IsAvailable() {
		return value_objects.ValueErrorf("Agent %s is not available for new tasks", a.idStr())
	}
	a.ActiveTasks[taskID] = struct{}{}
	a.CurrentWorkload++
	if a.CurrentWorkload >= a.maxTasks() {
		a.Status = AgentStatusBusy
	}
	return a.Touch("task_started")
}

func (a *Agent) CompleteTask(taskID string, success bool) error {
	if _, ok := a.ActiveTasks[taskID]; !ok {
		return value_objects.ValueErrorf("Task %s not assigned to agent %s", taskID, a.idStr())
	}
	delete(a.ActiveTasks, taskID)
	if a.CurrentWorkload-1 > 0 {
		a.CurrentWorkload--
	} else {
		a.CurrentWorkload = 0
	}
	a.CompletedTasks++
	if success {
		*a.SuccessRate = (*a.SuccessRate * 0.9) + (100.0 * 0.1)
	} else {
		*a.SuccessRate = (*a.SuccessRate * 0.9) + (0.0 * 0.1)
	}
	if a.CurrentWorkload < a.maxTasks() && a.Status == AgentStatusBusy {
		a.Status = AgentStatusAvailable
	}
	return a.Touch("task_completed")
}

func (a *Agent) PauseWork() error {
	a.Status = AgentStatusPaused
	return a.Touch("agent_paused")
}

func (a *Agent) ResumeWork() error {
	if a.CurrentWorkload >= a.maxTasks() {
		a.Status = AgentStatusBusy
	} else {
		a.Status = AgentStatusAvailable
	}
	return a.Touch("agent_resumed")
}

func (a *Agent) GoOffline() error {
	a.Status = AgentStatusOffline
	return a.Touch("agent_offline")
}

func (a *Agent) GoOnline() error {
	a.Status = AgentStatusAvailable
	return a.Touch("agent_online")
}

func (a *Agent) GetWorkloadPercentage() float64 {
	if a.maxTasks() == 0 {
		return 100.0
	}
	return (float64(a.CurrentWorkload) / float64(a.maxTasks())) * 100.0
}

// GetAgentProfile returns the comprehensive profile dict.
func (a *Agent) GetAgentProfile() map[string]any {
	id := ""
	if a.ID != nil {
		id = a.ID.String()
	}
	caps := []string{}
	for _, c := range a.sortedCapabilities() {
		caps = append(caps, string(c))
	}
	var workHours any
	if a.WorkHours != nil {
		workHours = a.WorkHours
	}
	var avg any
	if a.AverageTaskDuration != nil {
		avg = *a.AverageTaskDuration
	}
	return map[string]any{
		"id": id, "name": a.Name, "description": a.Description, "status": string(a.Status),
		"capabilities": caps, "specializations": a.Specializations,
		"preferred_languages": a.PreferredLanguages, "preferred_frameworks": a.PreferredFrameworks,
		"workload": map[string]any{
			"current": a.CurrentWorkload, "max": a.maxTasks(),
			"percentage": a.GetWorkloadPercentage(), "available": a.IsAvailable(),
		},
		"performance": map[string]any{
			"completed_tasks": a.CompletedTasks, "success_rate": *a.SuccessRate, "average_duration": avg,
		},
		"assignments": map[string]any{
			"projects": sortedKeys(a.AssignedProjects), "trees": sortedKeys(a.AssignedTrees),
			"active_tasks": sortedKeys(a.ActiveTasks),
		},
		"preferences": map[string]any{
			"work_hours": workHours, "timezone": a.Timezone, "priority_preference": a.PriorityPreference,
		},
		"created_at": value_objects.IsoFormat(*a.CreatedAt),
		"updated_at": value_objects.IsoFormat(*a.UpdatedAt),
	}
}

// CalculateTaskSuitabilityScore scores the agent for a task (0-100). Python raises
// ZeroDivisionError when max_concurrent_tasks is 0 and the agent can handle the task.
func (a *Agent) CalculateTaskSuitabilityScore(r TaskRequirements) (float64, error) {
	if !a.CanHandleTask(r) {
		return 0.0, nil
	}
	score := 50.0
	if a.IsAvailable() {
		score += 20.0
	}
	if a.maxTasks() == 0 {
		return 0, ErrZeroDivision
	}
	score += (1.0 - (float64(a.CurrentWorkload) / float64(a.maxTasks()))) * 10.0
	score += (*a.SuccessRate / 100.0) * 10.0
	priority := r.Priority
	if priority == "" {
		priority = "medium"
	}
	if priority == a.PriorityPreference {
		score += 10.0
	}
	if score > 100.0 {
		score = 100.0
	}
	return score, nil
}

// ValidateCapabilityMatch reports whether every requirement matches a capability or specialization.
func (a *Agent) ValidateCapabilityMatch(requirements []string) bool {
	if len(requirements) == 0 {
		return true
	}
	for _, req := range requirements {
		reqLower := strings.ReplaceAll(strings.ToLower(req), " ", "_")
		matched := false
		for c := range a.Capabilities {
			if strings.ToLower(string(c)) == reqLower {
				matched = true
				break
			}
		}
		if !matched {
			for _, spec := range a.Specializations {
				if strings.ToLower(spec) == reqLower {
					matched = true
					break
				}
			}
		}
		if !matched {
			return false
		}
	}
	return true
}

// CalculateWorkloadScore returns current_workload / max_concurrent_tasks with status special cases.
func (a *Agent) CalculateWorkloadScore() float64 {
	if a.Status == AgentStatusOffline || a.maxTasks() == 0 {
		return 1.0
	}
	return float64(a.CurrentWorkload) / float64(a.maxTasks())
}

// CheckAvailability returns detailed availability information.
func (a *Agent) CheckAvailability() map[string]any {
	blocking := []string{}
	available := true
	switch a.Status {
	case AgentStatusOffline:
		available = false
		blocking = append(blocking, "Agent is offline")
	case AgentStatusPaused:
		available = false
		blocking = append(blocking, "Agent is paused")
	case AgentStatusBusy:
		if a.CurrentWorkload >= a.maxTasks() {
			available = false
			blocking = append(blocking, "Agent is at maximum capacity")
		}
	case AgentStatusAvailable:
		if a.CurrentWorkload >= a.maxTasks() {
			available = false
			blocking = append(blocking, "Agent workload at maximum capacity")
		}
	}
	capacity := 0
	if available && a.maxTasks()-a.CurrentWorkload > 0 {
		capacity = a.maxTasks() - a.CurrentWorkload
	}
	var avg any
	if a.AverageTaskDuration != nil {
		avg = *a.AverageTaskDuration
	}
	return map[string]any{
		"available": available, "status": string(a.Status),
		"workload_score": value_objects.PyRound(a.CalculateWorkloadScore(), 3),
		"current_tasks":  a.CurrentWorkload, "capacity": a.maxTasks(),
		"blocking_reasons": blocking, "estimated_capacity": capacity,
		"active_task_ids": sortedKeys(a.ActiveTasks),
		"performance_metrics": map[string]any{
			"completed_tasks": a.CompletedTasks, "success_rate": value_objects.PyRound(*a.SuccessRate, 2),
			"average_duration_hours": avg,
		},
	}
}

// CreateAgent is the factory method (agent_id is validated as an AgentId).
func CreateAgent(agentID, name, description string, capabilities []AgentCapability, specializations, preferredLanguages []string) (*Agent, error) {
	id, err := value_objects.NewAgentId(agentID)
	if err != nil {
		return nil, err
	}
	caps := map[AgentCapability]struct{}{}
	for _, c := range capabilities {
		caps[c] = struct{}{}
	}
	return NewAgent(Agent{
		ID: &id, Name: name, Description: description, Capabilities: caps,
		Specializations: specializations, PreferredLanguages: preferredLanguages,
	})
}
