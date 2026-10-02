// Package orchestration ports
// task_management/application/orchestration/*.py.
package orchestration

import (
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// OrchestrationStrategy mirrors the Python ABC's assign_work contract.
//
// Python defect preserved: CapabilityBasedStrategy stores Agent.id (an AgentId
// value object) even though the annotation says dict[str, str].
type OrchestrationStrategy interface {
	AssignWork(project *entities.Project, availableAgents []*entities.Agent) *entities.OrderedMap[*value_objects.AgentId]
}

// CapabilityBasedStrategy assigns each unassigned git branch to the best-scoring
// available agent (Python CapabilityBasedStrategy).
type CapabilityBasedStrategy struct{}

// AssignWork iterates project.git_branchs in insertion order and skips branches
// already present in agent_assignments.
func (CapabilityBasedStrategy) AssignWork(project *entities.Project, availableAgents []*entities.Agent) *entities.OrderedMap[*value_objects.AgentId] {
	assignments := entities.NewOrderedMap[*value_objects.AgentId]()
	for _, name := range project.GitBranchs.Keys() {
		if project.AgentAssignments.Has(name) {
			continue // Already assigned
		}
		tree, _ := project.GitBranchs.Get(name)
		if best := projectOrchestratorFindBestAgentForTree(tree, availableAgents); best != nil {
			assignments.Set(name, best.ID)
		}
	}
	return assignments
}

// projectOrchestratorFindBestAgentForTree scores the agent-available subset and
// returns the highest scorer when its score is positive.
func projectOrchestratorFindBestAgentForTree(tree *entities.GitBranch, agents []*entities.Agent) *entities.Agent {
	type scored struct {
		agent *entities.Agent
		score float64
	}
	var scores []scored
	for _, a := range agents {
		if a.IsAvailable() {
			scores = append(scores, scored{a, projectOrchestratorCalculateAgentTreeScore(a, tree)})
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

// projectOrchestratorCalculateAgentTreeScore mirrors _calculate_agent_tree_score.
func projectOrchestratorCalculateAgentTreeScore(agent *entities.Agent, tree *entities.GitBranch) float64 {
	const baseScore = 50.0
	caps, langs := projectOrchestratorAnalyzeTreeRequirements(tree)
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
	workloadScore := (1.0 - agent.GetWorkloadPercentage()/100.0) * 10.0
	return baseScore + capScore + langScore + workloadScore
}

// projectOrchestratorAnyKeyword is Python's any(keyword in text for keyword in ...).
func projectOrchestratorAnyKeyword(text string, keywords ...string) bool {
	for _, k := range keywords {
		if strings.Contains(text, k) {
			return true
		}
	}
	return false
}

// projectOrchestratorAnalyzeTreeRequirements mirrors _analyze_tree_requirements.
// Python builds sets; this keeps first-seen insertion order (Python set order is
// unspecified).
func projectOrchestratorAnalyzeTreeRequirements(tree *entities.GitBranch) ([]entities.AgentCapability, []string) {
	var caps entities.StringSet
	var langs entities.StringSet
	for _, task := range tree.AllTasks.Values() {
		text := value_objects.PyLower(task.Title + " " + task.Description)

		if projectOrchestratorAnyKeyword(text, "frontend", "ui", "react", "vue", "angular") {
			caps.Add(string(entities.CapabilityFrontendDevelopment))
			for _, l := range []string{"javascript", "typescript", "html", "css"} {
				langs.Add(l)
			}
		}
		if projectOrchestratorAnyKeyword(text, "backend", "api", "server", "database") {
			caps.Add(string(entities.CapabilityBackendDevelopment))
			for _, l := range []string{"python", "java", "node.js"} {
				langs.Add(l)
			}
		}
		if projectOrchestratorAnyKeyword(text, "deploy", "docker", "kubernetes", "ci/cd") {
			caps.Add(string(entities.CapabilityDevops))
		}
		if projectOrchestratorAnyKeyword(text, "test", "testing", "qa", "quality") {
			caps.Add(string(entities.CapabilityTesting))
		}
	}
	out := make([]entities.AgentCapability, 0, caps.Len())
	for _, c := range caps.Items() {
		out = append(out, entities.AgentCapability(c))
	}
	return out, langs.Items()
}

// ProjectOrchestrator is the application service for orchestrating multi-agent
// work across projects.
type ProjectOrchestrator struct {
	Strategy OrchestrationStrategy
}

// NewProjectOrchestrator builds an orchestrator; a nil strategy means
// CapabilityBasedStrategy (Python `strategy or CapabilityBasedStrategy()`).
func NewProjectOrchestrator(strategy OrchestrationStrategy) *ProjectOrchestrator {
	if strategy == nil {
		strategy = CapabilityBasedStrategy{}
	}
	return &ProjectOrchestrator{Strategy: strategy}
}

// projectOrchestratorAgentIDString is str(agent.id).
func projectOrchestratorAgentIDString(id *value_objects.AgentId) string {
	if id == nil {
		return "None"
	}
	return id.Value
}

// projectOrchestratorAgentIDRepr is repr(agent.id) for the frozen AgentId dataclass.
func projectOrchestratorAgentIDRepr(id *value_objects.AgentId) string {
	if id == nil {
		return "None"
	}
	return "AgentId(value=" + value_objects.PyRepr(id.Value) + ")"
}

// projectOrchestratorObjectKeyError is a Python KeyError with an arbitrary object key.
type projectOrchestratorObjectKeyError struct{ Msg string }

func (e *projectOrchestratorObjectKeyError) Error() string { return e.Msg }

// projectOrchestratorRegisteredAgentByObject reproduces Python's
// `registered_agents[agent_id_object]`: hash(AgentId) == hash(str) but
// AgentId.__eq__ returns NotImplemented for a str, so the lookup always misses.
func projectOrchestratorRegisteredAgentByObject(_ *entities.Project, id *value_objects.AgentId) (*entities.Agent, error) {
	return nil, &projectOrchestratorObjectKeyError{Msg: projectOrchestratorAgentIDRepr(id)}
}

// projectOrchestratorTaskIDValue is `task.id.value if task else None`.
func projectOrchestratorTaskIDValue(t *entities.Task) any {
	if t == nil || t.ID == nil {
		return nil
	}
	return t.ID.Value
}

// OrchestrateProject distributes work for a project
// (Python ProjectOrchestrator.orchestrate_project).
//
// Python defect preserved: assign_work returns Agent.id (an AgentId object) while
// registered_agents is str-keyed; an AgentId never equals a str, so
// Project.assign_agent_to_tree raises ValueError("Agent <id> not registered") for
// EVERY assignment the strategy produces. orchestrate_project therefore fails
// whenever an unassigned branch meets an available agent, after the
// timeout/conflict handling has already mutated the project.
func (o *ProjectOrchestrator) OrchestrateProject(project *entities.Project) (map[string]any, error) {
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
	newAssignments := o.Strategy.AssignWork(project, available)
	for _, name := range newAssignments.Keys() {
		id, _ := newAssignments.Get(name)
		if _, err := projectOrchestratorRegisteredAgentByObject(project, id); err != nil {
			return nil, value_objects.ValueErrorf("Agent %s not registered", projectOrchestratorAgentIDString(id))
		}
		// unreachable: an AgentId object never matches the str keys
	}
	recommendations := entities.NewOrderedMap[any]()
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
			if rec := projectOrchestratorPrioritizeTasksForAgent(agent, next); rec != nil {
				recommendations.Set(agentID, projectOrchestratorTaskIDValue(rec))
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
		"orchestrator_layer":      "application",
	}, nil
}

// CoordinateCrossTreeDependencies reports prerequisites whose tree cannot be
// found (Python ProjectOrchestrator.coordinate_cross_tree_dependencies).
//
// Python defect preserved: the "prerequisite_not_active" branch looks up
// agent_assignments with `prerequisite_tree.id` (a GitBranchId object) in a
// str-keyed dict, which never matches, so that issue type is never produced. The
// branch is therefore intentionally omitted here (a Go string lookup would
// wrongly match). Prerequisite iteration follows insertion order (Python iterates
// a set in arbitrary order).
func (o *ProjectOrchestrator) CoordinateCrossTreeDependencies(project *entities.Project) []map[string]any {
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

// BalanceWorkload analyses agent workloads
// (Python ProjectOrchestrator.balance_workload).
//
// Python defect preserved: the overloaded list holds AgentId objects, so
// `registered_agents[overloaded_agent_id]` raises KeyError for any overloaded
// agent. Unlike the domain orchestrator, an empty agent list yields
// average_workload 0 instead of ZeroDivisionError.
func (o *ProjectOrchestrator) BalanceWorkload(project *entities.Project) (map[string]any, error) {
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
		if _, err := projectOrchestratorRegisteredAgentByObject(project, id); err != nil {
			return nil, err
		}
	}
	var average any
	if len(workloads) > 0 {
		loads := make([]float64, 0, len(workloads))
		for _, w := range workloads {
			loads = append(loads, w.Workload)
		}
		average = value_objects.PySum(loads) / float64(len(workloads))
	} else {
		average = 0
	}
	if overloaded == nil {
		overloaded = []*value_objects.AgentId{}
	}
	if underloaded == nil {
		underloaded = []*value_objects.AgentId{}
	}
	return map[string]any{
		"workload_analysis": map[string]any{
			"overloaded_agents": overloaded, "underloaded_agents": underloaded,
			"average_workload": average, "workload_distribution": workloads,
		},
		"rebalancing_recommendations": []map[string]any{},
		"orchestrator_layer":          "application",
	}, nil
}

// handleTimeoutSessions mirrors _handle_timeout_sessions (the datetime.now()
// call in the Python body has no effect).
func (o *ProjectOrchestrator) handleTimeoutSessions(project *entities.Project) error {
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

// detectConflicts mirrors _detect_conflicts.
func (o *ProjectOrchestrator) detectConflicts(project *entities.Project) []map[string]any {
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

// resolveConflicts mirrors _resolve_conflicts.
func (o *ProjectOrchestrator) resolveConflicts(project *entities.Project, conflicts []map[string]any) error {
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

// projectOrchestratorDaysBetween is timedelta.days of (a - b): whole days,
// floored toward -infinity.
func projectOrchestratorDaysBetween(a, b time.Time) int {
	d := a.Sub(b)
	q := d / (24 * time.Hour)
	if d%(24*time.Hour) < 0 {
		q--
	}
	return int(q)
}

// projectOrchestratorPrioritizeTasksForAgent picks the highest-scoring task
// (Python _prioritize_tasks_for_agent). The task age compares a naive local
// `datetime.now()` (reinterpreted as UTC because created_at is timezone-aware)
// with created_at.
func projectOrchestratorPrioritizeTasksForAgent(agent *entities.Agent, tasks []*entities.Task) *entities.Task {
	if len(tasks) == 0 {
		return nil
	}
	type scored struct {
		task  *entities.Task
		score float64
	}
	priorityScores := map[string]float64{"critical": 5, "urgent": 4, "high": 3, "medium": 2, "low": 1}
	var scores []scored
	n := time.Now()
	nowAsUTC := time.Date(n.Year(), n.Month(), n.Day(), n.Hour(), n.Minute(), n.Second(), n.Nanosecond(), time.UTC)
	for _, t := range tasks {
		score := 0.0
		taskPriorityScore := 1.0
		if s, ok := priorityScores[t.Priority.Value]; ok {
			taskPriorityScore = s
		}
		if t.Priority.Value == agent.PriorityPreference {
			score += taskPriorityScore * 2
		} else {
			score += taskPriorityScore
		}
		if t.CreatedAt != nil {
			age := projectOrchestratorDaysBetween(nowAsUTC, *t.CreatedAt)
			score += min(float64(age)*0.1, 1.0)
		}
		scores = append(scores, scored{t, score})
	}
	sort.SliceStable(scores, func(i, j int) bool { return scores[i].score > scores[j].score })
	return scores[0].task
}

// canAgentHandleTask mirrors _can_agent_handle_task.
func (o *ProjectOrchestrator) canAgentHandleTask(agent *entities.Agent, task *entities.Task) bool {
	taskText := value_objects.PyLower(task.Title + " " + task.Description)

	if projectOrchestratorAnyKeyword(taskText, "frontend", "ui", "react") {
		return agent.HasCapability(entities.CapabilityFrontendDevelopment)
	}
	if projectOrchestratorAnyKeyword(taskText, "backend", "api", "server") {
		return agent.HasCapability(entities.CapabilityBackendDevelopment)
	}
	return true
}
