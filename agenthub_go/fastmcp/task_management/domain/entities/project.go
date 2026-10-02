package entities

import (
	"context"
	"fmt"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Project is the aggregate root for multi-agent task orchestration. All maps
// keep insertion order like Python dicts.
type Project struct {
	base.BaseTimestampEntity
	ID          *value_objects.ProjectId
	Name        string
	Description string

	GitBranchs            *OrderedMap[*GitBranch]
	RegisteredAgents      *OrderedMap[*Agent]
	AgentAssignments      *OrderedMap[string]     // git_branch_id -> agent_id
	CrossTreeDependencies *OrderedMap[*StringSet] // task_id -> prerequisite task ids
	ActiveWorkSessions    *OrderedMap[*WorkSession]
	ResourceLocks         *OrderedMap[string] // resource -> agent_id
}

// NewProject applies the defaults, initializes timestamps and validates.
func NewProject(p Project) (*Project, error) {
	s := p
	if s.GitBranchs == nil {
		s.GitBranchs = NewOrderedMap[*GitBranch]()
	}
	if s.RegisteredAgents == nil {
		s.RegisteredAgents = NewOrderedMap[*Agent]()
	}
	if s.AgentAssignments == nil {
		s.AgentAssignments = NewOrderedMap[string]()
	}
	if s.CrossTreeDependencies == nil {
		s.CrossTreeDependencies = NewOrderedMap[*StringSet]()
	}
	if s.ActiveWorkSessions == nil {
		s.ActiveWorkSessions = NewOrderedMap[*WorkSession]()
	}
	if s.ResourceLocks == nil {
		s.ResourceLocks = NewOrderedMap[string]()
	}
	if err := s.Init(&s); err != nil {
		return nil, err
	}
	return &s, nil
}

// CreateProject creates a project with a generated UUID.
func CreateProject(name, description string) (*Project, error) {
	id := value_objects.GenerateNewProjectId()
	return NewProject(Project{ID: &id, Name: name, Description: description})
}

func (p *Project) GetEntityID() string {
	if p.ID == nil {
		return "unknown"
	}
	return p.ID.Value
}

func (p *Project) ValidateEntity() error {
	if strings.TrimSpace(p.Name) == "" {
		return value_objects.ValueErrorf("Project name cannot be empty")
	}
	return nil
}

func (p *Project) idStr() string {
	if p.ID == nil {
		return ""
	}
	return p.ID.Value
}

func branchKey(b *GitBranch) string {
	if b.ID == nil {
		return ""
	}
	return b.ID.Value
}

// GitBranchCreator is what Project.create_git_branch_async needs from a git branch
// repository. Python duck-types these two methods (the ABC declares get_git_branch_by_name
// and create_git_branch instead; the ORM repository implements find_by_name/create_branch),
// so the contract is declared here on the consumer side.
type GitBranchCreator interface {
	FindByName(ctx context.Context, projectID, branchName string) (*GitBranch, error)
	CreateBranch(ctx context.Context, projectID, branchName, description string) (*GitBranch, error)
}

// CreateGitBranchAsync creates a git branch through the repository and caches it.
func (p *Project) CreateGitBranchAsync(ctx context.Context, repo GitBranchCreator, branchName, description string) (*GitBranch, error) {
	projectID := p.idStr()
	existing, err := repo.FindByName(ctx, projectID, branchName)
	if err != nil {
		return nil, err
	}
	if existing != nil {
		return nil, value_objects.ValueErrorf("Git branch %s already exists in project %s", branchName, p.idStr2())
	}
	branch, err := repo.CreateBranch(ctx, projectID, branchName, description)
	if err != nil {
		return nil, err
	}
	p.GitBranchs.Set(branchKey(branch), branch)
	return branch, p.Touch("git_branch_added")
}

// idStr2 is str(self.id) ("None" when unset), used in error text.
func (p *Project) idStr2() string {
	if p.ID == nil {
		return "None"
	}
	return p.ID.Value
}

// CreateGitBranch creates a task tree/branch within the project (legacy Python method).
func (p *Project) CreateGitBranch(gitBranchName, name, description string) (*GitBranch, error) {
	for _, b := range p.GitBranchs.Values() {
		if b.GitBranchName != nil && *b.GitBranchName == gitBranchName {
			return nil, value_objects.ValueErrorf("Git branch %s already exists", gitBranchName)
		}
	}
	id := value_objects.GenerateNewGitBranchId()
	branch, err := NewGitBranch(GitBranch{ID: &id, Name: name, Description: description,
		ProjectID: p.idStr(), GitBranchName: &gitBranchName})
	if err != nil {
		return nil, err
	}
	p.GitBranchs.Set(id.Value, branch)
	return branch, p.Touch("git_branch_created")
}

func (p *Project) AddGitBranch(b *GitBranch) error {
	p.GitBranchs.Set(branchKey(b), b)
	return p.Touch("git_branch_added")
}

// GetGitBranch finds a branch by its name.
func (p *Project) GetGitBranch(branchName string) *GitBranch {
	for _, b := range p.GitBranchs.Values() {
		if b.Name == branchName {
			return b
		}
	}
	return nil
}

func (p *Project) RegisterAgent(a *Agent) error {
	id := ""
	if a.ID != nil {
		id = a.ID.Value
	}
	p.RegisteredAgents.Set(id, a)
	return p.Touch("agent_registered")
}

func (p *Project) AssignAgentToTree(agentID, gitBranchID string) error {
	if !p.RegisteredAgents.Has(agentID) {
		return value_objects.ValueErrorf("Agent %s not registered", agentID)
	}
	if !p.GitBranchs.Has(gitBranchID) {
		return value_objects.ValueErrorf("Task tree %s not found", gitBranchID)
	}
	if current, ok := p.AgentAssignments.Get(gitBranchID); ok && current != agentID {
		return value_objects.ValueErrorf("Task tree %s already assigned to agent %s", gitBranchID, current)
	}
	p.AgentAssignments.Set(gitBranchID, agentID)
	return p.Touch("agent_assigned_to_tree")
}

func (p *Project) AddCrossTreeDependency(dependentTaskID, prerequisiteTaskID string) error {
	dependentTaskID = normalizeProjectTaskID(dependentTaskID)
	prerequisiteTaskID = normalizeProjectTaskID(prerequisiteTaskID)
	dep, pre := p.findGitBranch(dependentTaskID), p.findGitBranch(prerequisiteTaskID)
	if dep == nil || pre == nil {
		return value_objects.ValueErrorf("One or both tasks not found in project")
	}
	if branchKey(dep) == branchKey(pre) {
		return value_objects.ValueErrorf("Use regular task dependencies for tasks within the same tree")
	}
	set, ok := p.CrossTreeDependencies.Get(dependentTaskID)
	if !ok {
		set = &StringSet{}
		p.CrossTreeDependencies.Set(dependentTaskID, set)
	}
	set.Add(prerequisiteTaskID)
	return p.Touch("cross_tree_dependency_added")
}

func (p *Project) GetAvailableWorkForAgent(agentID string) ([]*Task, error) {
	if !p.RegisteredAgents.Has(agentID) {
		return nil, value_objects.ValueErrorf("Agent %s not registered", agentID)
	}
	available := []*Task{}
	for _, branchID := range p.AgentAssignments.Keys() {
		if assigned, _ := p.AgentAssignments.Get(branchID); assigned != agentID {
			continue
		}
		branch, _ := p.GitBranchs.Get(branchID)
		if branch == nil {
			return nil, &KeyError{branchID}
		}
		for _, task := range branch.GetAvailableTasks() {
			if p.isTaskReadyForWork(taskKey(task)) {
				available = append(available, task)
			}
		}
	}
	return available, nil
}

// StartWorkSession starts a session; maxDurationHours of 0 means no limit.
func (p *Project) StartWorkSession(agentID, taskID string, maxDurationHours float64) (*WorkSession, error) {
	if !p.RegisteredAgents.Has(agentID) {
		return nil, value_objects.ValueErrorf("Agent %s not registered", agentID)
	}
	branch := p.findGitBranch(taskID)
	if branch == nil {
		return nil, value_objects.ValueErrorf("Task %s not found", taskID)
	}
	key := branchKey(branch)
	if assigned, _ := p.AgentAssignments.Get(key); assigned != agentID || !p.AgentAssignments.Has(key) {
		return nil, value_objects.ValueErrorf("Agent %s not assigned to tree %s", agentID, key)
	}
	session, err := CreateWorkSession(agentID, taskID, key, maxDurationHours)
	if err != nil {
		return nil, err
	}
	p.ActiveWorkSessions.Set(session.ID, session)
	return session, p.Touch("work_session_started")
}

func (p *Project) findGitBranch(taskID string) *GitBranch {
	normalized := normalizeProjectTaskID(taskID)
	for _, b := range p.GitBranchs.Values() {
		if b.HasTask(normalized) {
			return b
		}
	}
	return nil
}

// FindGitBranch is Python's _find_git_branch, which other modules (orchestrator) call.
func (p *Project) FindGitBranch(taskID string) *GitBranch { return p.findGitBranch(taskID) }

// normalizeProjectTaskID converts a 32-char hex id to canonical UUID format.
func normalizeProjectTaskID(id string) string {
	if len([]rune(id)) == 32 && !strings.Contains(id, "-") {
		r := []rune(id)
		return string(r[:8]) + "-" + string(r[8:12]) + "-" + string(r[12:16]) + "-" + string(r[16:20]) + "-" + string(r[20:])
	}
	return id
}

func (p *Project) isTaskReadyForWork(taskID string) bool {
	deps, ok := p.CrossTreeDependencies.Get(normalizeProjectTaskID(taskID))
	if !ok {
		return true
	}
	for _, pre := range deps.Items() {
		tree := p.findGitBranch(pre)
		if tree == nil {
			return false
		}
		task := tree.GetTask(pre)
		if task == nil || task.Status.Value != "done" {
			return false
		}
	}
	return true
}

func (p *Project) totalCrossTreeDeps() int {
	n := 0
	for _, d := range p.CrossTreeDependencies.Values() {
		n += d.Len()
	}
	return n
}

func (p *Project) assignedTrees(agentID string) []string {
	out := []string{}
	for _, k := range p.AgentAssignments.Keys() {
		if a, _ := p.AgentAssignments.Get(k); a == agentID {
			out = append(out, k)
		}
	}
	return out
}

func (p *Project) distinctAssignedAgents() int {
	seen := map[string]struct{}{}
	for _, a := range p.AgentAssignments.Values() {
		seen[a] = struct{}{}
	}
	return len(seen)
}

// GetOrchestrationStatus returns the orchestration dashboard status.
func (p *Project) GetOrchestrationStatus() map[string]any {
	branches := map[string]any{}
	for _, k := range p.GitBranchs.Keys() {
		b, _ := p.GitBranchs.Get(k)
		var assigned any
		if a, ok := p.AgentAssignments.Get(k); ok {
			assigned = a
		}
		branches[k] = map[string]any{
			"name": b.Name, "assigned_agent": assigned, "total_tasks": b.GetTaskCount(),
			"completed_tasks": b.GetCompletedTaskCount(), "progress": b.GetProgressPercentage(),
		}
	}
	agents := map[string]any{}
	for _, k := range p.RegisteredAgents.Keys() {
		a, _ := p.RegisteredAgents.Get(k)
		caps := []string{}
		for _, c := range a.sortedCapabilities() {
			caps = append(caps, string(c))
		}
		sessions := []string{}
		for _, s := range p.ActiveWorkSessions.Values() {
			if s.AgentID == k {
				sessions = append(sessions, s.ID)
			}
		}
		agents[k] = map[string]any{
			"name": a.Name, "capabilities": caps, "assigned_trees": p.assignedTrees(k), "active_sessions": sessions,
		}
	}
	return map[string]any{
		"project_id": p.idStr(), "project_name": p.Name, "total_branches": p.GitBranchs.Len(),
		"registered_agents": p.RegisteredAgents.Len(), "active_assignments": p.AgentAssignments.Len(),
		"active_sessions": p.ActiveWorkSessions.Len(), "cross_tree_dependencies": p.totalCrossTreeDeps(),
		"resource_locks": p.ResourceLocks.Len(), "branches": branches, "agents": agents,
	}
}

// CoordinateCrossTreeDependencies validates the cross-tree dependencies.
func (p *Project) CoordinateCrossTreeDependencies() map[string]any {
	blocked, ready, missing := []string{}, []string{}, []map[string]any{}
	validated := 0
	for _, dependent := range p.CrossTreeDependencies.Keys() {
		if p.findGitBranch(dependent) == nil {
			missing = append(missing, map[string]any{"task_id": dependent, "issue": "Dependent task not found"})
			continue
		}
		deps, _ := p.CrossTreeDependencies.Get(dependent)
		allMet := true
		for _, pre := range deps.Items() {
			tree := p.findGitBranch(pre)
			if tree == nil {
				missing = append(missing, map[string]any{"task_id": pre, "issue": "Prerequisite task not found"})
				allMet = false
				continue
			}
			task := tree.GetTask(pre)
			if task == nil || task.Status.Value != "done" {
				allMet = false
			}
		}
		if allMet {
			ready = append(ready, dependent)
		} else {
			blocked = append(blocked, dependent)
		}
		validated++
	}
	return map[string]any{
		"total_dependencies": p.totalCrossTreeDeps(), "validated_dependencies": validated,
		"blocked_tasks": blocked, "ready_tasks": ready, "missing_prerequisites": missing,
	}
}

// ValidateAgentAssignment: agent registered, tree exists, and at most 3 concurrent tree assignments.
func (p *Project) ValidateAgentAssignment(agentID, taskTreeID string) bool {
	if !p.RegisteredAgents.Has(agentID) || !p.GitBranchs.Has(taskTreeID) {
		return false
	}
	current := 0
	for _, a := range p.AgentAssignments.Values() {
		if a == agentID {
			current++
		}
	}
	if !p.AgentAssignments.Has(taskTreeID) && current >= 3 {
		return false
	}
	return true
}

func (p *Project) totalTasks() int {
	n := 0
	for _, b := range p.GitBranchs.Values() {
		n += b.GetTaskCount()
	}
	return n
}

func (p *Project) completedBranches() int {
	n := 0
	for _, b := range p.GitBranchs.Values() {
		if b.GetProgressPercentage() == 100.0 {
			n++
		}
	}
	return n
}

// CalculateProjectHealth computes the weighted health score and metrics.
func (p *Project) CalculateProjectHealth() map[string]any {
	totalBranches := p.GitBranchs.Len()
	branchCompletion := 100.0
	if totalBranches != 0 {
		branchCompletion = float64(p.completedBranches()) / float64(totalBranches) * 100
	}
	totalAgents := p.RegisteredAgents.Len()
	agentUtil := 0.0
	if totalAgents != 0 {
		agentUtil = float64(p.distinctAssignedAgents()) / float64(totalAgents) * 100
	}
	totalTasks := p.totalTasks()
	blockedPct, activeRatio := 0.0, 0.0
	activeSessions := p.ActiveWorkSessions.Len()
	if totalTasks != 0 {
		blockedPct = float64(p.CrossTreeDependencies.Len()) / float64(totalTasks) * 100
		activeRatio = float64(activeSessions) / float64(totalTasks) * 100
	}
	capped := activeRatio
	if capped > 50 {
		capped = 50
	}
	score := branchCompletion*0.40 + agentUtil*0.20 + (100-blockedPct)*0.25 + capped*0.30
	var status string
	switch {
	case score >= 90:
		status = "excellent"
	case score >= 75:
		status = "good"
	case score >= 60:
		status = "fair"
	case score >= 40:
		status = "poor"
	default:
		status = "critical"
	}
	return map[string]any{
		"overall_health_score": value_objects.PyRound(score, 2), "health_status": status,
		"metrics": map[string]any{
			"branch_completion_rate":  value_objects.PyRound(branchCompletion, 2),
			"agent_utilization":       value_objects.PyRound(agentUtil, 2),
			"blocked_task_percentage": value_objects.PyRound(blockedPct, 2),
			"active_work_ratio":       value_objects.PyRound(activeRatio, 2),
		},
		"counts": map[string]any{
			"total_branches": totalBranches, "completed_branches": p.completedBranches(),
			"total_agents": totalAgents, "assigned_agents": p.distinctAssignedAgents(),
			"total_tasks": totalTasks, "blocked_tasks": p.CrossTreeDependencies.Len(), "active_sessions": activeSessions,
		},
	}
}

// CheckDeadlineRisk assesses the risk of missing deadlines.
func (p *Project) CheckDeadlineRisk() map[string]any {
	if p.GitBranchs.Len() == 0 {
		return map[string]any{"risk_level": "no_risk", "assessment": "No branches in project",
			"recommendation": "Create branches and tasks to begin work"}
	}
	totalTasks := p.totalTasks()
	if totalTasks == 0 {
		return map[string]any{"risk_level": "no_risk", "assessment": "No tasks defined yet",
			"recommendation": "Define tasks to track progress"}
	}
	completed := 0
	for _, b := range p.GitBranchs.Values() {
		completed += b.GetCompletedTaskCount()
	}
	completionRate := float64(completed) / float64(totalTasks) * 100
	activeSessions := p.ActiveWorkSessions.Len()
	hasActive := activeSessions > 0
	blockedRatio := float64(p.CrossTreeDependencies.Len()) / float64(totalTasks) * 100
	// Python yields the int 0 (not 0.0) when there are no registered agents.
	var agentUtil any = 0
	if n := p.RegisteredAgents.Len(); n > 0 {
		agentUtil = value_objects.PyRound(float64(p.distinctAssignedAgents())/float64(n)*100, 2)
	}
	result := func(level, assessment, recommendation string) map[string]any {
		return map[string]any{
			"risk_level": level, "assessment": assessment, "recommendation": recommendation,
			"metrics": map[string]any{
				"completion_rate": value_objects.PyRound(completionRate, 2), "active_sessions": activeSessions,
				"blocked_ratio": value_objects.PyRound(blockedRatio, 2), "agent_utilization": agentUtil,
			},
		}
	}
	switch {
	case completionRate < 10 && !hasActive:
		return result("critical_risk", fmt.Sprintf("Project is stalled with only %.1f%% completion and no active work", completionRate),
			"Immediately assign agents to tasks and resume development")
	case completionRate < 25 || (blockedRatio > 50 && !hasActive):
		return result("high_risk", fmt.Sprintf("Project at high risk with %.1f%% completion", completionRate),
			"Increase agent assignments, address blockers, and accelerate development")
	case completionRate < 50 || blockedRatio > 30:
		return result("medium_risk", fmt.Sprintf("Project shows moderate risk with %.1f%% completion", completionRate),
			"Review and resolve blockers, ensure adequate agent coverage")
	case completionRate < 75:
		return result("low_risk", fmt.Sprintf("Project on track with %.1f%% completion", completionRate),
			"Continue current pace, monitor for emerging blockers")
	}
	return result("no_risk", fmt.Sprintf("Project in excellent shape with %.1f%% completion", completionRate),
		"Maintain current trajectory to successful completion")
}
