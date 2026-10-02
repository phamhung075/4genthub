package services

import (
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// OrchestrationStrategy assigns work to agents. Like Python, the returned agent IDs are
// AgentId value objects (Agent.id), not the plain strings that Project.registered_agents is
// keyed by.
type OrchestrationStrategy interface {
	AssignWork(project *entities.Project, availableAgents []*entities.Agent) (*entities.OrderedMap[*value_objects.AgentId], error)
}

// CapabilityBasedStrategy assigns each unassigned git branch to the best-scoring available agent.
type CapabilityBasedStrategy struct{}

func (CapabilityBasedStrategy) AssignWork(project *entities.Project, availableAgents []*entities.Agent) (*entities.OrderedMap[*value_objects.AgentId], error) {
	assignments := entities.NewOrderedMap[*value_objects.AgentId]()
	for _, name := range project.GitBranchs.Keys() {
		if project.AgentAssignments.Has(name) {
			continue // already assigned
		}
		tree, _ := project.GitBranchs.Get(name)
		if best := findBestAgentForTree(tree, availableAgents); best != nil {
			assignments.Set(name, best.ID)
		}
	}
	return assignments, nil
}

func findBestAgentForTree(tree *entities.GitBranch, agents []*entities.Agent) *entities.Agent {
	type scored struct {
		agent *entities.Agent
		score float64
	}
	var scores []scored
	for _, a := range agents {
		if a.IsAvailable() {
			scores = append(scores, scored{a, calculateAgentTreeScore(a, tree)})
		}
	}
	if len(scores) == 0 {
		return nil
	}
	sort.SliceStable(scores, func(i, j int) bool { return scores[i].score > scores[j].score })
	if scores[0].score > 0 {
		return scores[0].agent
	}
	return nil
}

func calculateAgentTreeScore(agent *entities.Agent, tree *entities.GitBranch) float64 {
	const baseScore = 50.0
	caps, langs := analyzeTreeRequirements(tree)
	capMatch := 0
	for _, c := range caps {
		if agent.HasCapability(c) {
			capMatch++
		}
	}
	capScore := float64(capMatch) / float64(max(len(caps), 1)) * 30.0
	langMatch := 0
	for _, l := range langs {
		for _, p := range agent.PreferredLanguages {
			if p == l {
				langMatch++
				break
			}
		}
	}
	langScore := float64(langMatch) / float64(max(len(langs), 1)) * 10.0
	workload := (1.0 - agent.GetWorkloadPercentage()/100.0) * 10.0
	return float64(float64(baseScore+capScore)+langScore) + workload
}

func anyKeyword(text string, keywords ...string) bool {
	for _, k := range keywords {
		if strings.Contains(text, k) {
			return true
		}
	}
	return false
}

// analyzeTreeRequirements derives required capabilities and languages from task text
// (Python builds sets; only their sizes and membership matter).
func analyzeTreeRequirements(tree *entities.GitBranch) ([]entities.AgentCapability, []string) {
	var caps entities.StringSet
	var langs entities.StringSet
	for _, task := range tree.AllTasks.Values() {
		text := value_objects.PyLower(task.Title + " " + task.Description)
		if anyKeyword(text, "frontend", "ui", "react", "vue", "angular") {
			caps.Add(string(entities.CapabilityFrontendDevelopment))
			for _, l := range []string{"javascript", "typescript", "html", "css"} {
				langs.Add(l)
			}
		}
		if anyKeyword(text, "backend", "api", "server", "database") {
			caps.Add(string(entities.CapabilityBackendDevelopment))
			for _, l := range []string{"python", "java", "node.js"} {
				langs.Add(l)
			}
		}
		if anyKeyword(text, "deploy", "docker", "kubernetes", "ci/cd") {
			caps.Add(string(entities.CapabilityDevops))
		}
		if anyKeyword(text, "test", "testing", "qa", "quality") {
			caps.Add(string(entities.CapabilityTesting))
		}
	}
	out := make([]entities.AgentCapability, 0, caps.Len())
	for _, c := range caps.Items() {
		out = append(out, entities.AgentCapability(c))
	}
	return out, langs.Items()
}

// Orchestrator is the domain service for orchestrating multi-agent work.
type Orchestrator struct {
	Strategy OrchestrationStrategy
}

// NewOrchestrator builds an orchestrator; a nil strategy means CapabilityBasedStrategy.
func NewOrchestrator(strategy OrchestrationStrategy) *Orchestrator {
	if strategy == nil {
		strategy = CapabilityBasedStrategy{}
	}
	return &Orchestrator{Strategy: strategy}
}

// ObjectKeyError is a Python KeyError whose key is an arbitrary object; Msg is repr(key).
type ObjectKeyError struct{ Msg string }

func (e *ObjectKeyError) Error() string { return e.Msg }

func agentIDRepr(id *value_objects.AgentId) string {
	if id == nil {
		return "None"
	}
	return "AgentId(value=" + value_objects.PyRepr(id.Value) + ")"
}

func agentIDString(id *value_objects.AgentId) string {
	if id == nil {
		return "None"
	}
	return id.Value
}

// OrchestrateProject distributes work for a project.
//
// Python defect preserved: assign_work returns Agent.id (an AgentId object) while
// registered_agents is keyed by str; an AgentId never equals a str, so
// Project.assign_agent_to_tree raises ValueError("Agent <id> not registered") for EVERY
// assignment the strategy produces. orchestrate_project therefore fails whenever an
// unassigned branch meets an available agent, after the timeout/conflict handling has
// already mutated the project.
func (o *Orchestrator) OrchestrateProject(project *entities.Project) (map[string]any, error) {
	var available []*entities.Agent
	for _, a := range project.RegisteredAgents.Values() {
		if a.Status != entities.AgentStatusOffline {
			available = append(available, a)
		}
	}
	if err := o.handleTimeoutSessions(project); err != nil {
		return nil, err
	}
	conflicts := o.detectConflicts(project)
	if len(conflicts) > 0 {
		if err := o.resolveConflicts(project, conflicts); err != nil {
			return nil, err
		}
	}
	newAssignments, err := o.Strategy.AssignWork(project, available)
	if err != nil {
		return nil, err
	}
	for _, name := range newAssignments.Keys() {
		id, _ := newAssignments.Get(name)
		if _, err := registeredAgentByObject(project, id); err != nil {
			return nil, value_objects.ValueErrorf("Agent %s not registered", agentIDString(id))
		}
		// unreachable: an AgentId object never matches the str keys
	}
	recommendations := entities.NewOrderedMap[string]()
	for _, agentID := range project.RegisteredAgents.Keys() {
		agent, _ := project.RegisteredAgents.Get(agentID)
		if !agent.IsAvailable() {
			continue
		}
		next, err := project.GetAvailableWorkForAgent(agentID)
		if err != nil {
			return nil, err
		}
		if len(next) > 0 {
			if rec := prioritizeTasksForAgent(agent, next); rec != nil {
				recommendations.Set(agentID, taskIDStr(rec))
			}
		}
	}
	availableCount := 0
	for _, a := range available {
		if a.IsAvailable() {
			availableCount++
		}
	}
	var projectID any
	if project.ID != nil {
		projectID = *project.ID
	}
	return map[string]any{
		"orchestration_timestamp": value_objects.IsoFormatNaive(time.Now()),
		"project_id":              projectID,
		"new_assignments":         newAssignments,
		"agent_recommendations":   recommendations,
		"conflicts_detected":      len(conflicts),
		"conflicts_resolved":      len(conflicts),
		"active_sessions":         project.ActiveWorkSessions.Len(),
		"available_agents":        availableCount,
	}, nil
}

// registeredAgentByObject looks an Agent.id object up in the str-keyed registered_agents:
// hash(AgentId) == hash(str) but AgentId.__eq__ returns NotImplemented for a str, so the
// lookup always misses.
func registeredAgentByObject(_ *entities.Project, id *value_objects.AgentId) (*entities.Agent, error) {
	return nil, &ObjectKeyError{agentIDRepr(id)}
}

// CoordinateCrossTreeDependencies reports prerequisites whose tree cannot be found. Python's
// "prerequisite_not_active" branch looks up agent_assignments by a GitBranchId object
// (str-keyed), which never matches, so that issue type is never produced. Prerequisite
// iteration follows insertion order (Python iterates a set in arbitrary order).
func (o *Orchestrator) CoordinateCrossTreeDependencies(project *entities.Project) []map[string]any {
	issues := []map[string]any{}
	for _, dependent := range project.CrossTreeDependencies.Keys() {
		if project.FindGitBranch(dependent) == nil {
			continue
		}
		prereqs, _ := project.CrossTreeDependencies.Get(dependent)
		for _, pre := range prereqs.Items() {
			if project.FindGitBranch(pre) == nil {
				issues = append(issues, map[string]any{"type": "missing_prerequisite", "dependent_task": dependent,
					"missing_prerequisite": pre})
			}
		}
	}
	return issues
}

// WorkloadEntry mirrors the (agent.id, workload) tuple of workload_distribution.
type WorkloadEntry struct {
	AgentID  *value_objects.AgentId
	Workload float64
}

// BalanceWorkload analyses agent workloads. Python defects preserved: the agent lists hold
// AgentId objects, so `registered_agents[overloaded_agent_id]` raises KeyError for any
// overloaded agent, and averaging zero agents raises ZeroDivisionError.
func (o *Orchestrator) BalanceWorkload(project *entities.Project) (map[string]any, error) {
	var workloads []WorkloadEntry
	for _, a := range project.RegisteredAgents.Values() {
		workloads = append(workloads, WorkloadEntry{a.ID, a.GetWorkloadPercentage()})
	}
	sort.SliceStable(workloads, func(i, j int) bool { return workloads[i].Workload < workloads[j].Workload })
	var overloaded, underloaded []*value_objects.AgentId
	for _, w := range workloads {
		if w.Workload > 80.0 {
			overloaded = append(overloaded, w.AgentID)
		}
	}
	for _, w := range workloads {
		if w.Workload < 50.0 {
			underloaded = append(underloaded, w.AgentID)
		}
	}
	for _, id := range overloaded {
		if _, err := registeredAgentByObject(project, id); err != nil {
			return nil, err
		}
	}
	if len(workloads) == 0 {
		return nil, entities.ErrZeroDivision
	}
	loads := make([]float64, 0, len(workloads))
	for _, w := range workloads {
		loads = append(loads, w.Workload)
	}
	sum := value_objects.PySum(loads)
	if overloaded == nil {
		overloaded = []*value_objects.AgentId{}
	}
	if underloaded == nil {
		underloaded = []*value_objects.AgentId{}
	}
	return map[string]any{
		"workload_analysis": map[string]any{
			"overloaded_agents": overloaded, "underloaded_agents": underloaded,
			"average_workload": sum / float64(len(workloads)), "workload_distribution": workloads,
		},
		"rebalancing_recommendations": []map[string]any{},
	}, nil
}

func (o *Orchestrator) handleTimeoutSessions(project *entities.Project) error {
	for _, id := range project.ActiveWorkSessions.Keys() {
		session, _ := project.ActiveWorkSessions.Get(id)
		if !session.IsTimeoutDue() {
			continue
		}
		if err := session.TimeoutSession(); err != nil {
			return err
		}
		project.ActiveWorkSessions.Delete(id)
		if agent, ok := project.RegisteredAgents.Get(session.AgentID); ok {
			if err := agent.CompleteTask(session.TaskID, false); err != nil {
				return err
			}
		}
	}
	return nil
}

func (o *Orchestrator) detectConflicts(project *entities.Project) []map[string]any {
	conflicts := []map[string]any{}
	usage := map[string]string{}
	for _, session := range project.ActiveWorkSessions.Values() {
		for _, resource := range session.ResourcesLocked {
			if first, ok := usage[resource]; ok {
				conflicts = append(conflicts, map[string]any{"type": "resource_conflict", "resource": resource,
					"conflicting_sessions": []string{first, session.ID}})
			} else {
				usage[resource] = session.ID
			}
		}
	}
	return conflicts
}

func (o *Orchestrator) resolveConflicts(project *entities.Project, conflicts []map[string]any) error {
	for _, c := range conflicts {
		if c["type"] != "resource_conflict" {
			continue
		}
		sessions := c["conflicting_sessions"].([]string)
		if len(sessions) >= 2 {
			if older, ok := project.ActiveWorkSessions.Get(sessions[0]); ok {
				if err := older.UnlockResource(c["resource"].(string)); err != nil {
					return err
				}
			}
		}
	}
	return nil
}

// prioritizeTasksForAgent picks the highest-scoring task. The task age compares a naive local
// `datetime.now()` (reinterpreted as UTC, because created_at is timezone-aware) with created_at.
func prioritizeTasksForAgent(agent *entities.Agent, tasks []*entities.Task) *entities.Task {
	if len(tasks) == 0 {
		return nil
	}
	type scored struct {
		task  *entities.Task
		score float64
	}
	var scores []scored
	n := time.Now()
	nowAsUTC := time.Date(n.Year(), n.Month(), n.Day(), n.Hour(), n.Minute(), n.Second(), n.Nanosecond(), time.UTC)
	for _, t := range tasks {
		score := 0.0
		var ts float64
		switch priorityStr(t) {
		case "critical":
			ts = 5
		case "urgent":
			ts = 4
		case "high":
			ts = 3
		case "medium":
			ts = 2
		default:
			ts = 1
		}
		if priorityStr(t) == agent.PriorityPreference {
			score += ts * 2
		} else {
			score += ts
		}
		if t.CreatedAt != nil {
			age := daysBetween(nowAsUTC, *t.CreatedAt)
			score += min(float64(age)*0.1, 1.0)
		}
		scores = append(scores, scored{t, score})
	}
	sort.SliceStable(scores, func(i, j int) bool { return scores[i].score > scores[j].score })
	return scores[0].task
}
