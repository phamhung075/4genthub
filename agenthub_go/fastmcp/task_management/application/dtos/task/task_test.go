package task_test

import (
	"context"
	"reflect"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/application/dtos/subtask"
	. "agenthub/fastmcp/task_management/application/dtos/task"
	usecases "agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestCreateTaskRequestNormalization(t *testing.T) {
	r, err := NewCreateTaskRequest(CreateTaskRequest{
		Title: "t", GitBranchID: "b",
		Assignees: []string{"coding-agent", "test-orchestrator-agent", "system-architect-agent", "@custom", "@already"},
		Labels:    []string{"bug", "  Frontend ", "weird label!", ""},
	})
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	wantAssignees := []string{"@coding-agent", "@test-orchestrator-agent", "@system-architect-agent", "@custom", "@already"}
	if !reflect.DeepEqual(r.Assignees, wantAssignees) {
		t.Fatalf("assignees = %v", r.Assignees)
	}
	wantLabels := []string{"bug", "Frontend", "weird label!"}
	if !reflect.DeepEqual(r.Labels, wantLabels) {
		t.Fatalf("labels = %v", r.Labels)
	}
}

func TestDependencyChainProperties(t *testing.T) {
	chain := DependencyChain{
		ChainID: "c1", TotalTasks: 4, CompletedTasks: 1, BlockedTasks: 0, ChainStatus: "in_progress",
		Tasks: []DependencyInfo{{TaskID: "d1", Title: "D1", Status: "todo"}},
	}
	if got := chain.CompletionPercentage(); got != 25.0 {
		t.Fatalf("completion = %v", got)
	}
	if chain.IsBlocked() {
		t.Fatalf("should not be blocked")
	}
	if nt := chain.NextTask(); nt == nil || nt.Title != "D1" {
		t.Fatalf("next = %v", nt)
	}
	empty := DependencyChain{TotalTasks: 0, BlockedTasks: 2}
	if empty.CompletionPercentage() != 0.0 || !empty.IsBlocked() || empty.NextTask() != nil {
		t.Fatalf("empty chain = %v", empty)
	}
}

func TestDependencyRelationshipsMethods(t *testing.T) {
	ch := DependencyChain{ChainID: "c1", TotalTasks: 4, CompletedTasks: 1, ChainStatus: "in_progress",
		Tasks: []DependencyInfo{{TaskID: "d1", Title: "D1", Status: "todo"}}}
	rels := NewDependencyRelationships(DependencyRelationships{
		TaskID:            "t",
		DependsOn:         []DependencyInfo{{TaskID: "d1", Title: "D1", Status: "todo", Priority: "high"}},
		Blocks:            []DependencyInfo{{TaskID: "d2"}},
		UpstreamChains:    []DependencyChain{ch},
		TotalDependencies: 1, CanStart: false, IsBlocked: true, IsBlockingOthers: true,
	})
	if got := rels.DependencyCompletionPercentage(); got != 0.0 {
		t.Fatalf("completion = %v", got)
	}
	info := rels.GetBlockingChainInfo()
	if v, _ := info.Get("is_blocked"); v != true {
		t.Fatalf("is_blocked = %v", v)
	}
	tasks, _ := info.Get("blocking_tasks")
	if list, ok := tasks.([]any); !ok || len(list) != 1 {
		t.Fatalf("blocking_tasks = %#v", tasks)
	}
	chains, _ := info.Get("blocking_chains")
	chainList, ok := chains.([]any)
	if !ok || len(chainList) != 1 {
		t.Fatalf("blocking_chains = %#v", chains)
	}
	cm := chainList[0].(*entities.OrderedMap[any])
	if v, _ := cm.Get("next_task"); v != "D1" {
		t.Fatalf("next_task = %v", v)
	}
	suggestions, _ := info.Get("resolution_suggestions")
	if list, ok := suggestions.([]string); !ok || len(list) != 2 {
		t.Fatalf("suggestions = %#v", suggestions)
	}
	guidance := rels.GetWorkflowGuidance()
	if v, _ := guidance.Get("can_start_immediately"); v != false {
		t.Fatalf("can_start = %v", v)
	}
	rec, _ := guidance.Get("recommended_actions")
	if list, ok := rec.([]string); !ok || len(list) != 3 {
		t.Fatalf("recommended = %#v", rec)
	}
	empty := NewDependencyRelationships(DependencyRelationships{CanStart: true})
	if empty.DependencyCompletionPercentage() != 100.0 {
		t.Fatalf("empty completion = %v", empty.DependencyCompletionPercentage())
	}
}

func TestTaskListItemResponse(t *testing.T) {
	r := NewTaskListItemResponse("i", "t", "todo", "high", nil, nil,
		[]string{"1", "2", "3", "4"}, nil, nil, []string{"d"})
	if !reflect.DeepEqual(r.Labels, []string{"1", "2", "3"}) {
		t.Fatalf("labels = %v", r.Labels)
	}
	if !r.HasDependencies || r.IsBlocked {
		t.Fatalf("flags = %+v", r)
	}
	m := r.ToDict()
	want := []string{"id", "title", "status", "priority", "progress_percentage", "labels", "due_date", "updated_at", "has_dependencies", "is_blocked"}
	if !reflect.DeepEqual(m.Keys(), want) {
		t.Fatalf("keys = %v", m.Keys())
	}
	if v, _ := m.Get("progress_percentage"); v != 0 {
		t.Fatalf("progress = %v", v)
	}
}

func TestTaskProgressToDict(t *testing.T) {
	m := (TaskProgress{LastUpdated: "now"}).ToDict()
	want := []string{"current_task_id", "current_subtask_id", "task_start_time", "subtask_start_time", "completed_tasks", "completed_subtasks", "last_updated"}
	if !reflect.DeepEqual(m.Keys(), want) {
		t.Fatalf("keys = %v", m.Keys())
	}
}

func TestTaskInfoToDictNestedQuirk(t *testing.T) {
	inner := subtaskInfoForTest()
	info := TaskInfo{ID: 1, Title: "t", Description: "d", Status: value_objects.TaskStatus{Value: "todo"},
		Priority: value_objects.Priority{Value: "high"}, Subtasks: []subtask.SubtaskInfo{inner}}
	m := info.ToDict()
	if v, _ := m.Get("status"); v != "todo" {
		t.Fatalf("status = %v", v)
	}
	nested, _ := m.Get("subtasks")
	list, ok := nested.([]any)
	if !ok || len(list) != 1 {
		t.Fatalf("subtasks = %#v", nested)
	}
	child := list[0].(*entities.OrderedMap[any])
	if v, _ := child.Get("status"); v == "todo" {
		t.Fatalf("nested status should be a dict, got %v", v)
	}
}

func TestTaskResponseToDict(t *testing.T) {
	r := NewTaskResponse(sampleTaskResponse())
	m, err := r.ToDict()
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	want := []string{"id", "title", "description", "status", "priority", "details", "estimatedEffort",
		"assignees", "labels", "dependencies", "subtasks", "dueDate", "created_at", "updated_at",
		"git_branch_id", "project_id", "context_id", "context_data", "dependency_relationships",
		"progress_percentage", "progress_history", "progress_count", "subtask_count", "completed_subtasks"}
	if !reflect.DeepEqual(m.Keys(), want) {
		t.Fatalf("keys = %v", m.Keys())
	}
	if v, _ := m.Get("subtask_count"); v != 2 {
		t.Fatalf("subtask_count = %v", v)
	}
	if v, _ := m.Get("completed_subtasks"); v != 1 {
		t.Fatalf("completed_subtasks = %v", v)
	}
	if v, _ := m.Get("created_at"); v != "2025-01-02T03:04:05+00:00" {
		t.Fatalf("created_at = %v", v)
	}
	if v, _ := m.Get("context_data"); v == nil {
		t.Fatalf("context_data should be empty dict")
	}
}

func TestTaskResponseToDictDependencyError(t *testing.T) {
	r := NewTaskResponse(sampleTaskResponse())
	r.DependencyRelationships = &DependencyRelationships{}
	if _, err := r.ToDict(); err == nil || err.Error() != "'DependencyRelationships' object has no attribute 'to_dict'" {
		t.Fatalf("err = %v", err)
	}
}

func TestTaskResponseFromDomain(t *testing.T) {
	entities.AgentNameResolver = usecases.ResolveAgentName
	defer func() { entities.AgentNameResolver = nil }()

	task := sampleDomainTask()
	resp, err := TaskResponseFromDomain(context.Background(), task, nil, nil, nil, nil, nil)
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	if want := task.GetProgressHistoryText(); resp.Details != want {
		t.Fatalf("details = %q, want %q", resp.Details, want)
	}
	if !reflect.DeepEqual(resp.Assignees, []string{"coding-agent", "bob-agent"}) {
		t.Fatalf("assignees = %v", resp.Assignees)
	}
	if resp.SubtaskCount() != 2 || resp.CompletedSubtasks != 1 {
		t.Fatalf("counts = %d %d", resp.SubtaskCount(), resp.CompletedSubtasks)
	}
	if pid := resp.ProjectID; pid != nil {
		t.Fatalf("project_id = %v", pid)
	}
}

func sampleTaskResponse() TaskResponse {
	due := "2025-01-01"
	git := "gb"
	ctxID := "cid"
	created := time.Date(2025, 1, 2, 3, 4, 5, 0, time.UTC)
	updated := time.Date(2025, 1, 2, 3, 4, 6, 0, time.UTC)
	return TaskResponse{
		ID: "tid", Title: "T", Description: "D", Status: "todo", Priority: "high",
		Details: "HISTORY", EstimatedEffort: "2h",
		Assignees: []string{"coding-agent", "bob-agent"}, Labels: []string{"bug"},
		Dependencies: []string{"d1"}, Subtasks: []any{"s1", "s2"}, DueDate: &due,
		CreatedAt: &created, UpdatedAt: &updated, GitBranchID: &git, ContextID: &ctxID,
		ProgressPercentage: 42, ProgressHistory: map[string]any{"progress_1": map[string]any{"x": 1}},
		ProgressCount: 1, CompletedSubtasks: 1,
	}
}

func sampleDomainTask() *entities.Task {
	tid, _ := value_objects.NewTaskId("tid")
	dep, _ := value_objects.NewTaskId("d1")
	status := value_objects.TaskStatus{Value: "todo"}
	priority := value_objects.Priority{Value: "high"}
	due := "2025-01-01"
	ctxID := "cid"
	created := time.Date(2025, 1, 2, 3, 4, 5, 0, time.UTC)
	updated := time.Date(2025, 1, 2, 3, 4, 6, 0, time.UTC)
	t := &entities.Task{
		ID: &tid, Title: "T", Description: "D", Status: &status, Priority: &priority,
		ProgressHistory: map[string]any{"progress_1": map[string]any{"x": 1}},
		ProgressCount:   1, EstimatedEffort: "2h", Assignees: []string{"@coding-agent", "bob"},
		Labels: []string{"bug"}, Dependencies: []value_objects.TaskId{dep},
		Subtasks: []string{"s1", "s2"}, CompletedSubtasks: 1, DueDate: &due,
		ContextID: &ctxID, OverallProgress: 42,
	}
	t.CreatedAt = &created
	t.UpdatedAt = &updated
	return t
}

func subtaskInfoForTest() subtask.SubtaskInfo {
	return subtask.SubtaskInfo{ID: 2, Title: "c", Status: value_objects.TaskStatus{Value: "done"}, Priority: value_objects.Priority{Value: "high"}}
}

type fakeBranchRepo struct {
	branches map[string]*entities.GitBranch
}

func (f fakeBranchRepo) FindByIDs(ctx context.Context, ids []string) *entities.OrderedMap[*entities.GitBranch] {
	m := entities.NewOrderedMap[*entities.GitBranch]()
	for k, v := range f.branches {
		m.Set(k, v)
	}
	return m
}

type fakeTaskRepo struct{ counts map[string]int }

func (f fakeTaskRepo) GetCompletedSubtaskCounts(ctx context.Context, ids []string) (map[string]int, error) {
	return f.counts, nil
}

func TestTaskListResponseFromDomainList(t *testing.T) {
	entities.AgentNameResolver = usecases.ResolveAgentName
	defer func() { entities.AgentNameResolver = nil }()

	gb := "gb-1"
	task := sampleDomainTask()
	task.GitBranchID = &gb

	resp, err := TaskListResponseFromDomainList(context.Background(), []*entities.Task{task},
		fakeBranchRepo{branches: map[string]*entities.GitBranch{"gb-1": {ProjectID: "proj-9"}}},
		fakeTaskRepo{counts: map[string]int{"tid": 3}}, nil, nil)
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	if resp.Count != 1 || len(resp.Tasks) != 1 {
		t.Fatalf("count = %d", resp.Count)
	}
	if resp.Tasks[0].ProjectID == nil || *resp.Tasks[0].ProjectID != "proj-9" {
		t.Fatalf("project_id = %v", resp.Tasks[0].ProjectID)
	}
	if resp.Tasks[0].CompletedSubtasks != 3 {
		t.Fatalf("completed = %d", resp.Tasks[0].CompletedSubtasks)
	}
}

// Every path that writes an assignee goes through entities.NormalizeAssignees: the same
// inputs must give the same result (or the same error) through the REST request DTO,
// Task.UpdateAssignees, Subtask.UpdateAssignees and NewSubtask.
func TestAssigneeRuleIsIdenticalOnEveryPath(t *testing.T) {
	parent := value_objects.GenerateNewTaskId()
	taskID := value_objects.GenerateNewTaskId()
	cases := [][]string{
		{"coding-agent"},
		{"@go-dev", "@lead"},
		{" @lead ", "", "coding-agent"},
		{"go-dev"},
		{"custom", "@x"},
		{"system-architect-agent"},
	}
	for _, in := range cases {
		want, wantErr := entities.NormalizeAssignees(in)

		check := func(path string, got []string, err error) {
			t.Helper()
			if (err == nil) != (wantErr == nil) || (err != nil && err.Error() != wantErr.Error()) {
				t.Errorf("%v via %s: err = %v, want %v", in, path, err, wantErr)
			}
			if err == nil && !reflect.DeepEqual(got, want) {
				t.Errorf("%v via %s: got %v, want %v", in, path, got, want)
			}
		}

		req, err := NewCreateTaskRequest(CreateTaskRequest{Title: "t", GitBranchID: "b", Assignees: in})
		var dto []string
		if err == nil {
			dto = req.Assignees
		}
		check("CreateTaskRequest", dto, err)

		tk, err := entities.CreateTask(entities.Task{ID: &taskID, Title: "t", Description: "d"})
		if err != nil {
			t.Fatal(err)
		}
		err = tk.UpdateAssignees(in)
		check("Task.UpdateAssignees", tk.Assignees, err)

		st, err := entities.NewSubtask(entities.Subtask{Title: "s", Description: "d", ParentTaskID: &parent})
		if err != nil {
			t.Fatal(err)
		}
		err = st.UpdateAssignees(in)
		check("Subtask.UpdateAssignees", st.Assignees, err)

		ns, err := entities.NewSubtask(entities.Subtask{Title: "s", Description: "d", ParentTaskID: &parent, Assignees: in})
		var nsa []string
		if err == nil {
			nsa = ns.Assignees
		}
		if len(in) > 0 { // NewSubtask normalizes only when assignees are given
			check("NewSubtask", nsa, err)
		}
	}
}
