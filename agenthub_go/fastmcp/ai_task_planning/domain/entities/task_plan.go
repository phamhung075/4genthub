package entities

import (
	"fmt"
	"strings"
	"time"

	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskType is the type of a task in the plan.
type TaskType string

const (
	TaskTypeEpic          TaskType = "epic"
	TaskTypeFeature       TaskType = "feature"
	TaskTypeStory         TaskType = "story"
	TaskTypeTask          TaskType = "task"
	TaskTypeSubtask       TaskType = "subtask"
	TaskTypeBug           TaskType = "bug"
	TaskTypeSpike         TaskType = "spike"
	TaskTypeDocumentation TaskType = "documentation"
	TaskTypeTesting       TaskType = "testing"
	TaskTypeReview        TaskType = "review"
)

// ExecutionPhase is a phase of execution.
type ExecutionPhase string

const (
	PhasePlanning       ExecutionPhase = "planning"
	PhaseArchitecture   ExecutionPhase = "architecture"
	PhaseImplementation ExecutionPhase = "implementation"
	PhaseTesting        ExecutionPhase = "testing"
	PhaseReview         ExecutionPhase = "review"
	PhaseDeployment     ExecutionPhase = "deployment"
	PhaseMonitoring     ExecutionPhase = "monitoring"
)

// TaskDependency is a dependency between tasks.
type TaskDependency struct {
	DependentTaskID    string
	PrerequisiteTaskID string
	DependencyType     string // finish_to_start, start_to_start, ...
	LagTime            int    // hours
}

// AgentAssignment is the assignment of agents to tasks.
type AgentAssignment struct {
	PrimaryAgent     string
	SupportingAgents []string
	EffortPercentage *tmentities.OrderedMap[float64]
}

// NewAgentAssignment applies `supporting or []` and `effort or {primary: 100.0}`.
func NewAgentAssignment(primary string, supporting []string, effort *tmentities.OrderedMap[float64]) *AgentAssignment {
	if supporting == nil {
		supporting = []string{}
	}
	if effort == nil || effort.Len() == 0 {
		effort = tmentities.NewOrderedMap[float64]()
		effort.Set(primary, 100.0)
	}
	return &AgentAssignment{PrimaryAgent: primary, SupportingAgents: supporting, EffortPercentage: effort}
}

func floatMap(m *tmentities.OrderedMap[float64]) *tmentities.OrderedMap[any] {
	out := tmentities.NewOrderedMap[any]()
	for _, k := range m.Keys() {
		v, _ := m.Get(k)
		out.Set(k, v)
	}
	return out
}

func (a *AgentAssignment) ToDict() *tmentities.OrderedMap[any] {
	d := tmentities.NewOrderedMap[any]()
	d.Set("primary_agent", a.PrimaryAgent)
	d.Set("supporting_agents", strs(a.SupportingAgents))
	d.Set("effort_percentage", floatMap(a.EffortPercentage))
	return d
}

// PlannedTask is a single task in the AI-generated plan.
type PlannedTask struct {
	ID          string
	Title       string
	Description string
	TaskType    TaskType
	Phase       ExecutionPhase

	ParentTaskID *string
	SubtaskIDs   []string

	AgentAssignment     *AgentAssignment
	EstimatedHours      float64
	EstimatedComplexity string

	AcceptanceCriteria    []string
	TechnicalRequirements []string
	FileReferences        []string
	CodeReferences        *tmentities.OrderedMap[[]string]

	Priority    string
	Tags        []string
	Risks       []string
	Assumptions []string

	Status    string
	MCPTaskID *string
	CreatedAt time.Time
}

// NewPlannedTask applies the Python defaults.
func NewPlannedTask(id, title, description string, taskType TaskType, phase ExecutionPhase) *PlannedTask {
	return &PlannedTask{ID: id, Title: title, Description: description, TaskType: taskType, Phase: phase,
		SubtaskIDs: []string{}, EstimatedComplexity: "medium", AcceptanceCriteria: []string{},
		TechnicalRequirements: []string{}, FileReferences: []string{},
		CodeReferences: tmentities.NewOrderedMap[[]string](), Priority: "medium", Tags: []string{},
		Risks: []string{}, Assumptions: []string{}, Status: "planned", CreatedAt: time.Now().UTC()}
}

// AddSubtask links a subtask to this task.
func (t *PlannedTask) AddSubtask(sub *PlannedTask) {
	for _, id := range t.SubtaskIDs {
		if id == sub.ID {
			sub.ParentTaskID = &t.ID
			return
		}
	}
	t.SubtaskIDs = append(t.SubtaskIDs, sub.ID)
	sub.ParentTaskID = &t.ID
}

// CanRunInParallel: no shared primary agent, no shared files, no incompatible phases.
func (t *PlannedTask) CanRunInParallel(other *PlannedTask) bool {
	if t.AgentAssignment != nil && other.AgentAssignment != nil &&
		t.AgentAssignment.PrimaryAgent == other.AgentAssignment.PrimaryAgent {
		return false
	}
	files := map[string]struct{}{}
	for _, f := range t.FileReferences {
		files[f] = struct{}{}
	}
	for _, f := range other.FileReferences {
		if _, ok := files[f]; ok {
			return false
		}
	}
	incompatible := func(a, b ExecutionPhase) bool {
		return (a == PhasePlanning && b == PhaseImplementation) || (a == PhaseArchitecture && b == PhaseTesting)
	}
	return !incompatible(t.Phase, other.Phase) && !incompatible(other.Phase, t.Phase)
}

func bulletLines(items []string, format string) string {
	lines := make([]string, len(items))
	for i, it := range items {
		lines[i] = fmt.Sprintf(format, it)
	}
	return strings.Join(lines, "\n")
}

// ToMCPTaskRequest converts to the MCP task creation request.
func (t *PlannedTask) ToMCPTaskRequest() *tmentities.OrderedMap[any] {
	assignees := []string{}
	if t.AgentAssignment != nil {
		assignees = append(assignees, t.AgentAssignment.PrimaryAgent)
		assignees = append(assignees, t.AgentAssignment.SupportingAgents...)
	}
	var refs []string
	if t.CodeReferences != nil {
		for _, k := range t.CodeReferences.Keys() {
			ranges, _ := t.CodeReferences.Get(k)
			refs = append(refs, "- "+k+": "+strings.Join(ranges, ", "))
		}
	}
	const pad = "        "
	details := tmvo.PyStrip("\n" +
		pad + "**Task Type**: " + string(t.TaskType) + "\n" +
		pad + "**Phase**: " + string(t.Phase) + "\n" +
		pad + "**Estimated Hours**: " + tmvo.PyStr(t.EstimatedHours) + "\n" +
		pad + "**Complexity**: " + t.EstimatedComplexity + "\n" +
		pad + "\n" +
		pad + "**Acceptance Criteria**:\n" + pad + bulletLines(t.AcceptanceCriteria, "- %s") + "\n" +
		pad + "\n" +
		pad + "**Technical Requirements**:\n" + pad + bulletLines(t.TechnicalRequirements, "- %s") + "\n" +
		pad + "\n" +
		pad + "**File References**:\n" + pad + bulletLines(t.FileReferences, "- %s") + "\n" +
		pad + "\n" +
		pad + "**Code References**:\n" + pad + strings.Join(refs, "\n") + "\n" +
		pad + "\n" +
		pad + "**Risks**:\n" + pad + bulletLines(t.Risks, "- %s") + "\n" +
		pad + "\n" +
		pad + "**Assumptions**:\n" + pad + bulletLines(t.Assumptions, "- %s") + "\n" +
		pad)
	d := tmentities.NewOrderedMap[any]()
	d.Set("title", t.Title)
	d.Set("description", t.Description)
	d.Set("assignees", assignees)
	d.Set("details", details)
	d.Set("priority", t.Priority)
	d.Set("estimated_effort", tmvo.PyStr(t.EstimatedHours)+"h")
	d.Set("labels", strs(t.Tags))
	return d
}

func codeRefsDict(m *tmentities.OrderedMap[[]string]) *tmentities.OrderedMap[any] {
	out := tmentities.NewOrderedMap[any]()
	if m != nil {
		for _, k := range m.Keys() {
			v, _ := m.Get(k)
			out.Set(k, strs(v))
		}
	}
	return out
}

func (t *PlannedTask) ToDict() *tmentities.OrderedMap[any] {
	var assignment any
	if t.AgentAssignment != nil {
		assignment = t.AgentAssignment.ToDict()
	}
	d := tmentities.NewOrderedMap[any]()
	d.Set("id", t.ID)
	d.Set("title", t.Title)
	d.Set("description", t.Description)
	d.Set("task_type", string(t.TaskType))
	d.Set("phase", string(t.Phase))
	d.Set("parent_task_id", optStr(t.ParentTaskID))
	d.Set("subtask_ids", strs(t.SubtaskIDs))
	d.Set("agent_assignment", assignment)
	d.Set("estimated_hours", t.EstimatedHours)
	d.Set("estimated_complexity", t.EstimatedComplexity)
	d.Set("acceptance_criteria", strs(t.AcceptanceCriteria))
	d.Set("technical_requirements", strs(t.TechnicalRequirements))
	d.Set("file_references", strs(t.FileReferences))
	d.Set("code_references", codeRefsDict(t.CodeReferences))
	d.Set("priority", t.Priority)
	d.Set("tags", strs(t.Tags))
	d.Set("risks", strs(t.Risks))
	d.Set("assumptions", strs(t.Assumptions))
	d.Set("status", t.Status)
	d.Set("mcp_task_id", optStr(t.MCPTaskID))
	d.Set("created_at", tmvo.IsoFormat(t.CreatedAt))
	return d
}

// TaskPlan is a complete AI-generated task plan.
type TaskPlan struct {
	ID                string
	PlanningRequestID string
	Title             string
	Description       string

	Tasks        []*PlannedTask
	Dependencies []TaskDependency

	TotalEstimatedHours   float64
	EstimatedDurationDays float64
	ConfidenceScore       float64
	RiskLevel             string

	ExecutionPhases         []ExecutionPhase
	ParallelExecutionGroups [][]string
	CriticalPath            []string

	AgentWorkload  *tmentities.OrderedMap[float64]
	RequiredAgents tmentities.StringSet

	CreatedAt time.Time
	CreatedBy string
	Version   string
}

// NewTaskPlan applies the Python defaults.
func NewTaskPlan(id, planningRequestID, title, description string) *TaskPlan {
	return &TaskPlan{ID: id, PlanningRequestID: planningRequestID, Title: title, Description: description,
		RiskLevel: "medium", AgentWorkload: tmentities.NewOrderedMap[float64](),
		CreatedAt: time.Now().UTC(), CreatedBy: "ai_task_planning_engine", Version: "1.0"}
}

// AddTask adds a task unless its id is present, updating workload, totals and phases.
func (p *TaskPlan) AddTask(task *PlannedTask) {
	for _, t := range p.Tasks {
		if t.ID == task.ID {
			return
		}
	}
	p.Tasks = append(p.Tasks, task)
	if a := task.AgentAssignment; a != nil {
		cur, _ := p.AgentWorkload.Get(a.PrimaryAgent)
		p.AgentWorkload.Set(a.PrimaryAgent, cur+task.EstimatedHours)
		p.RequiredAgents.Add(a.PrimaryAgent)
		for _, sup := range a.SupportingAgents {
			pct, ok := a.EffortPercentage.Get(sup)
			if !ok {
				pct = 10
			}
			hours := float64(task.EstimatedHours*pct) / 100
			cur, _ := p.AgentWorkload.Get(sup)
			p.AgentWorkload.Set(sup, cur+hours)
			p.RequiredAgents.Add(sup)
		}
	}
	p.TotalEstimatedHours += task.EstimatedHours
	for _, ph := range p.ExecutionPhases {
		if ph == task.Phase {
			return
		}
	}
	p.ExecutionPhases = append(p.ExecutionPhases, task.Phase)
}

// AddDependency adds a dependency between tasks.
func (p *TaskPlan) AddDependency(dependent, prerequisite, dependencyType string, lagTime int) {
	p.Dependencies = append(p.Dependencies, TaskDependency{dependent, prerequisite, dependencyType, lagTime})
}

func (p *TaskPlan) GetTaskByID(id string) *PlannedTask {
	for _, t := range p.Tasks {
		if t.ID == id {
			return t
		}
	}
	return nil
}

func (p *TaskPlan) GetRootTasks() []*PlannedTask {
	out := []*PlannedTask{}
	for _, t := range p.Tasks {
		if t.ParentTaskID == nil {
			out = append(out, t)
		}
	}
	return out
}

func (p *TaskPlan) GetSubtasks(parentID string) []*PlannedTask {
	out := []*PlannedTask{}
	for _, t := range p.Tasks {
		if t.ParentTaskID != nil && *t.ParentTaskID == parentID {
			out = append(out, t)
		}
	}
	return out
}

// CalculateCriticalPath stores the root task with the longest path. A dependency that
// names an unknown task is an error (Python KeyError).
func (p *TaskPlan) CalculateCriticalPath() ([]string, error) {
	duration := map[string]float64{}
	successors := map[string][]string{}
	for _, t := range p.Tasks {
		duration[t.ID] = t.EstimatedHours
		successors[t.ID] = []string{}
	}
	for _, dep := range p.Dependencies {
		if _, ok := successors[dep.DependentTaskID]; !ok {
			return nil, fmt.Errorf("KeyError: %s", tmvo.PyRepr(dep.DependentTaskID))
		}
		if _, ok := successors[dep.PrerequisiteTaskID]; !ok {
			return nil, fmt.Errorf("KeyError: %s", tmvo.PyRepr(dep.PrerequisiteTaskID))
		}
		successors[dep.PrerequisiteTaskID] = append(successors[dep.PrerequisiteTaskID], dep.DependentTaskID)
	}
	var longest func(id string, visited map[string]struct{}) (float64, error)
	longest = func(id string, visited map[string]struct{}) (float64, error) {
		if _, ok := visited[id]; ok {
			return 0, nil
		}
		visited[id] = struct{}{}
		if len(successors[id]) == 0 {
			return duration[id], nil
		}
		best, first := 0.0, true
		for _, s := range successors[id] {
			cp := make(map[string]struct{}, len(visited))
			for k := range visited {
				cp[k] = struct{}{}
			}
			v, err := longest(s, cp)
			if err != nil {
				return 0, err
			}
			if first || v > best {
				best, first = v, false
			}
		}
		return duration[id] + best, nil
	}
	critical := []string{}
	maxLen := 0.0
	for _, root := range p.GetRootTasks() {
		l, err := longest(root.ID, map[string]struct{}{})
		if err != nil {
			return nil, err
		}
		if l > maxLen {
			maxLen = l
			critical = []string{root.ID}
		}
	}
	p.CriticalPath = critical
	return critical, nil
}

// FindParallelExecutionGroups groups tasks that can run in parallel.
func (p *TaskPlan) FindParallelExecutionGroups() [][]string {
	groups := [][]string{}
	remaining := append([]*PlannedTask{}, p.Tasks...)
	for len(remaining) > 0 {
		group := []string{}
		for _, task := range append([]*PlannedTask{}, remaining...) {
			canAdd := true
			for _, gid := range group {
				if g := p.GetTaskByID(gid); g != nil && !task.CanRunInParallel(g) {
					canAdd = false
					break
				}
			}
			if canAdd {
				group = append(group, task.ID)
				for i, r := range remaining {
					if r == task {
						remaining = append(remaining[:i], remaining[i+1:]...)
						break
					}
				}
			}
		}
		if len(group) > 0 {
			groups = append(groups, group)
		} else if len(remaining) > 0 {
			groups = append(groups, []string{remaining[0].ID})
			remaining = remaining[1:]
		}
	}
	p.ParallelExecutionGroups = groups
	return groups
}

// ValidatePlan checks for cycles, unknown task references and unassigned tasks.
func (p *TaskPlan) ValidatePlan() (bool, []string) {
	errs := []string{}
	var cyclic func(id string, visited, stack map[string]struct{}) bool
	cyclic = func(id string, visited, stack map[string]struct{}) bool {
		visited[id] = struct{}{}
		stack[id] = struct{}{}
		for _, dep := range p.Dependencies {
			if dep.PrerequisiteTaskID != id {
				continue
			}
			d := dep.DependentTaskID
			if _, seen := visited[d]; !seen {
				if cyclic(d, visited, stack) {
					return true
				}
			} else if _, on := stack[d]; on {
				return true
			}
		}
		delete(stack, id)
		return false
	}
	visited := map[string]struct{}{}
	for _, t := range p.Tasks {
		if _, seen := visited[t.ID]; !seen && cyclic(t.ID, visited, map[string]struct{}{}) {
			errs = append(errs, "Circular dependency detected involving task "+t.ID)
		}
	}
	ids := map[string]struct{}{}
	for _, t := range p.Tasks {
		ids[t.ID] = struct{}{}
	}
	for _, dep := range p.Dependencies {
		for _, id := range []string{dep.DependentTaskID, dep.PrerequisiteTaskID} {
			if _, ok := ids[id]; !ok {
				errs = append(errs, "Dependency references non-existent task: "+id)
			}
		}
	}
	unassigned := []string{}
	for _, t := range p.Tasks {
		if t.AgentAssignment == nil {
			unassigned = append(unassigned, t.ID)
		}
	}
	if len(unassigned) > 0 {
		errs = append(errs, "Tasks without agent assignments: "+tmvo.PyRepr(unassigned))
	}
	return len(errs) == 0, errs
}

// ToDict converts to the serialisable dictionary (required_agents in insertion order;
// Python's set order is unspecified).
func (p *TaskPlan) ToDict() *tmentities.OrderedMap[any] {
	tasks := make([]any, 0, len(p.Tasks))
	for _, t := range p.Tasks {
		tasks = append(tasks, t.ToDict())
	}
	deps := make([]any, 0, len(p.Dependencies))
	for _, dep := range p.Dependencies {
		m := tmentities.NewOrderedMap[any]()
		m.Set("dependent_task_id", dep.DependentTaskID)
		m.Set("prerequisite_task_id", dep.PrerequisiteTaskID)
		m.Set("dependency_type", dep.DependencyType)
		m.Set("lag_time", dep.LagTime)
		deps = append(deps, m)
	}
	phases := make([]string, 0, len(p.ExecutionPhases))
	for _, ph := range p.ExecutionPhases {
		phases = append(phases, string(ph))
	}
	groups := make([][]string, 0, len(p.ParallelExecutionGroups))
	for _, g := range p.ParallelExecutionGroups {
		groups = append(groups, strs(g))
	}
	d := tmentities.NewOrderedMap[any]()
	d.Set("id", p.ID)
	d.Set("planning_request_id", p.PlanningRequestID)
	d.Set("title", p.Title)
	d.Set("description", p.Description)
	d.Set("tasks", tasks)
	d.Set("dependencies", deps)
	d.Set("total_estimated_hours", p.TotalEstimatedHours)
	d.Set("estimated_duration_days", p.EstimatedDurationDays)
	d.Set("confidence_score", p.ConfidenceScore)
	d.Set("risk_level", p.RiskLevel)
	d.Set("execution_phases", phases)
	d.Set("parallel_execution_groups", groups)
	d.Set("critical_path", strs(p.CriticalPath))
	d.Set("agent_workload", floatMap(p.AgentWorkload))
	d.Set("required_agents", strs(p.RequiredAgents.Items()))
	d.Set("created_at", tmvo.IsoFormat(p.CreatedAt))
	d.Set("created_by", p.CreatedBy)
	d.Set("version", p.Version)
	return d
}
