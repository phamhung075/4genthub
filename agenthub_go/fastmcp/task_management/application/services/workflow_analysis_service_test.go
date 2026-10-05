package services

import (
	"context"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Stubs: embed the interfaces so only the methods under test need definitions.
type wfStubTaskRepo struct {
	repositories.TaskRepository
	byID  map[string]*entities.Task
	lists map[string][]*entities.Task
}

func (r *wfStubTaskRepo) FindByID(_ context.Context, id value_objects.TaskId) (*entities.Task, error) {
	return r.byID[id.String()], nil
}

func (r *wfStubTaskRepo) FindByLabels(_ context.Context, labels []string) ([]*entities.Task, error) {
	out := []*entities.Task{}
	for _, l := range labels {
		out = append(out, r.lists[l]...)
	}
	return out, nil
}

type wfStubContextRepo struct {
	repositories.ContextRepository
	ctx *entities.TaskContext
	err error
}

func (r *wfStubContextRepo) GetContext(_ context.Context, _ string) (*entities.TaskContext, error) {
	return r.ctx, r.err
}

func wfNewTask(t *testing.T, id string, ageDays float64, mods ...func(*entities.Task)) *entities.Task {
	t.Helper()
	tid, err := value_objects.NewTaskId(id)
	if err != nil {
		t.Fatalf("NewTaskId(%q): %v", id, err)
	}
	task := &entities.Task{Title: "T", Description: "D", ID: &tid, Assignees: []string{}, Labels: []string{}}
	st, _ := value_objects.NewTaskStatus("todo")
	task.Status = &st
	pr := value_objects.PriorityMedium()
	task.Priority = &pr
	created := time.Now().UTC().Add(-time.Duration(ageDays * 24 * float64(time.Hour)))
	updated := time.Now().UTC()
	task.CreatedAt = &created
	task.UpdatedAt = &updated
	for _, m := range mods {
		m(task)
	}
	return task
}

func wfNewContext(t *testing.T, taskID string) *entities.TaskContext {
	t.Helper()
	md, err := entities.NewContextMetadata(entities.ContextMetadata{TaskID: taskID})
	if err != nil {
		t.Fatalf("NewContextMetadata: %v", err)
	}
	return entities.NewTaskContext(md, entities.ContextObjective{Title: "x"})
}

// Python: hasattr(task, "progress_breakdown") is False, so the pattern never fires.
func TestWorkflowDetectProgressPatternsAlwaysEmpty(t *testing.T) {
	svc := NewWorkflowAnalysisService(nil, nil, nil, nil)
	if got := svc.detectProgressPatterns(wfNewTask(t, "11111111-1111-1111-1111-111111111111", 20)); len(got) != 0 {
		t.Fatalf("expected no patterns, got %d", len(got))
	}
}

// Python: `t.status == "done"` is always False (dataclass vs str), so even three
// completed related tasks produce no completion pattern.
func TestWorkflowDetectCompletionKeepsPythonStatusBug(t *testing.T) {
	svc := NewWorkflowAnalysisService(nil, nil, nil, nil)
	task := wfNewTask(t, "11111111-1111-1111-1111-111111111111", 20)
	related := []*entities.Task{}
	for i, id := range []string{"22222222-2222-2222-2222-222222222222", "33333333-3333-3333-3333-333333333333", "44444444-4444-4444-4444-444444444444"} {
		rt := wfNewTask(t, id, float64(1+i))
		done, _ := value_objects.NewTaskStatus("done")
		rt.Status = &done
		related = append(related, rt)
	}
	if got := svc.detectCompletionPatterns(task, related); len(got) != 0 {
		t.Fatalf("expected no patterns, got %d", len(got))
	}
}

func TestWorkflowDetectCollaborationTwoIndicators(t *testing.T) {
	svc := NewWorkflowAnalysisService(nil, nil, nil, nil)
	task := wfNewTask(t, "22222222-2222-2222-2222-222222222222", 20, func(x *entities.Task) {
		x.Assignees = []string{"a", "b", "c"}
	})
	patterns, err := svc.detectCollaborationPatterns(task, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(patterns) != 1 {
		t.Fatalf("expected 1 pattern, got %d", len(patterns))
	}
	p := patterns[0]
	if p.PatternName != "collaboration_opportunity" || p.PatternType != "optimization" || p.Confidence != 0.75 {
		t.Fatalf("unexpected pattern: %+v", p)
	}
	indicators, _ := p.Metrics.Get("indicators")
	got, _ := indicators.([]string)
	if len(got) != 2 || got[0] != "long_running" || got[1] != "multiple_assignees" {
		t.Fatalf("indicators = %v", got)
	}
	if n, _ := p.Metrics.Get("indicator_count"); n != 2 {
		t.Fatalf("indicator_count = %v", n)
	}
}

func TestWorkflowDetectCollaborationKeywordFromNotesRepr(t *testing.T) {
	svc := NewWorkflowAnalysisService(nil, nil, nil, nil)
	task := wfNewTask(t, "33333333-3333-3333-3333-333333333333", 20)
	ctx := wfNewContext(t, "33333333-3333-3333-3333-333333333333")
	ctx.Notes.GeneralNotes = "please HELP me"
	patterns, err := svc.detectCollaborationPatterns(task, ctx)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(patterns) != 1 {
		t.Fatalf("expected 1 pattern, got %d", len(patterns))
	}
	indicators, _ := patterns[0].Metrics.Get("indicators")
	got, _ := indicators.([]string)
	if len(got) != 2 || got[1] != "collaboration_keywords" {
		t.Fatalf("indicators = %v", got)
	}
}

func TestWorkflowFindOptimizationEffortAndOrder(t *testing.T) {
	svc := NewWorkflowAnalysisService(nil, nil, nil, nil)
	task := wfNewTask(t, "11111111-1111-1111-1111-111111111111", 1, func(x *entities.Task) {
		x.EstimatedEffort = "5d"
	})
	opps, err := svc.findOptimizationOpportunities(task, nil, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(opps) != 1 {
		t.Fatalf("expected 1 opportunity, got %d", len(opps))
	}
	keys := opps[0].Keys()
	want := []string{"type", "potential_impact", "description", "benefits", "implementation"}
	if len(keys) != len(want) {
		t.Fatalf("keys = %v", keys)
	}
	for i := range want {
		if keys[i] != want[i] {
			t.Fatalf("keys = %v, want %v", keys, want)
		}
	}
	if v, _ := opps[0].Get("type"); v != "task_decomposition" {
		t.Fatalf("type = %v", v)
	}
}

func TestWorkflowFindOptimizationAutomation(t *testing.T) {
	svc := NewWorkflowAnalysisService(nil, nil, nil, nil)
	task := wfNewTask(t, "11111111-1111-1111-1111-111111111111", 1)
	ctx := wfNewContext(t, "11111111-1111-1111-1111-111111111111")
	ctx.Notes.GeneralNotes = "manual repetitive work"
	opps, err := svc.findOptimizationOpportunities(task, ctx, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(opps) != 1 {
		t.Fatalf("expected 1 opportunity, got %d", len(opps))
	}
	if v, _ := opps[0].Get("type"); v != "automation" {
		t.Fatalf("type = %v", v)
	}
}

// Python risk order: missing context, no assignees, high dependencies. The
// urgent-priority risk never fires (`priority in [...]` is always False).
func TestWorkflowAssessRiskFactors(t *testing.T) {
	svc := NewWorkflowAnalysisService(nil, nil, nil, nil)
	task := wfNewTask(t, "44444444-4444-4444-4444-444444444444", 1, func(x *entities.Task) {
		p := value_objects.PriorityUrgent()
		x.Priority = &p
		x.Dependencies = []value_objects.TaskId{}
		for i := 0; i < 6; i++ {
			id, _ := value_objects.NewTaskId(string(rune('a'+i)) + "0000000-0000-0000-0000-000000000000")
			x.Dependencies = append(x.Dependencies, id)
		}
	})
	risks, err := svc.assessRiskFactors(task, nil, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	want := []string{"Limited context information available", "No assignees on task", "High number of dependencies"}
	if len(risks) != len(want) {
		t.Fatalf("risks = %v", risks)
	}
	for i := range want {
		if risks[i] != want[i] {
			t.Fatalf("risks = %v, want %v", risks, want)
		}
	}
}

func TestWorkflowAssessRiskFactorsContextRaises(t *testing.T) {
	svc := NewWorkflowAnalysisService(nil, nil, nil, nil)
	task := wfNewTask(t, "44444444-4444-4444-4444-444444444444", 1)
	ctx := wfNewContext(t, "44444444-4444-4444-4444-444444444444")
	_, err := svc.assessRiskFactors(task, ctx, nil)
	if err == nil || err.Error() != "'TaskContext' object has no attribute 'data'" {
		t.Fatalf("err = %v", err)
	}
}

func TestWorkflowIdentifySuccessIndicatorsAlwaysErrors(t *testing.T) {
	svc := NewWorkflowAnalysisService(nil, nil, nil, nil)
	task := wfNewTask(t, "11111111-1111-1111-1111-111111111111", 1)
	if _, err := svc.identifySuccessIndicators(task, nil); err == nil || err.Error() != "object of type 'NoneType' has no len()" {
		t.Fatalf("nil timeline err = %v", err)
	}
	task.ProgressTimeline = value_objects.NewProgressTimeline(task.ID.String())
	if _, err := svc.identifySuccessIndicators(task, nil); err == nil || err.Error() != "object of type 'ProgressTimeline' has no len()" {
		t.Fatalf("timeline err = %v", err)
	}
}

func TestWorkflowIdentifyBottlenecksKeepsPythonDependencyBug(t *testing.T) {
	tid, _ := value_objects.NewTaskId("dddddddd-dddd-dddd-dddd-dddddddddddd")
	blocked, _ := value_objects.NewTaskStatus("blocked")
	dep := &entities.Task{ID: &tid, Status: &blocked}
	repo := &wfStubTaskRepo{byID: map[string]*entities.Task{tid.String(): dep}}
	svc := NewWorkflowAnalysisService(repo, nil, nil, nil)
	task := wfNewTask(t, "55555555-5555-5555-5555-555555555555", 1)
	// 4 dependencies (>3) but `dep.status in ["blocked","cancelled"]` is always False.
	for i := 0; i < 4; i++ {
		id, _ := value_objects.NewTaskId(string(rune('a'+i)) + "0000000-0000-0000-0000-000000000000")
		task.Dependencies = append(task.Dependencies, id)
	}
	got, err := svc.identifyBottlenecks(context.Background(), task, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(got) != 0 {
		t.Fatalf("expected no bottlenecks, got %d", len(got))
	}

	// A non-nil timeline raises before the stall dictionary can be built.
	task.ProgressTimeline = value_objects.NewProgressTimeline(task.ID.String())
	if _, err := svc.identifyBottlenecks(context.Background(), task, nil); err == nil || err.Error() != "'ProgressTimeline' object is not subscriptable" {
		t.Fatalf("timeline err = %v", err)
	}
}

func TestWorkflowGetRelatedTasksDeduplicates(t *testing.T) {
	a := wfNewTask(t, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", 1, func(x *entities.Task) {
		x.Labels = []string{"x"}
		x.Subtasks = []string{"bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"}
	})
	b := wfNewTask(t, "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", 1, func(x *entities.Task) {
		x.Labels = []string{"x"}
	})
	repo := &wfStubTaskRepo{
		byID:  map[string]*entities.Task{b.ID.String(): b},
		lists: map[string][]*entities.Task{"x": {a, b}},
	}
	svc := NewWorkflowAnalysisService(repo, nil, nil, nil)
	got, err := svc.getRelatedTasks(context.Background(), a)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(got) != 1 || got[0].ID.String() != b.ID.String() {
		t.Fatalf("related = %v", got)
	}
}

func TestWorkflowAnalyzeTaskNotFoundAndAlwaysErrors(t *testing.T) {
	repo := &wfStubTaskRepo{byID: map[string]*entities.Task{}, lists: map[string][]*entities.Task{}}
	svc := NewWorkflowAnalysisService(repo, nil, nil, nil)
	missing, _ := value_objects.NewTaskId("99999999-9999-9999-9999-999999999999")
	if _, err := svc.AnalyzeTaskWorkflow(context.Background(), missing, true); err == nil || err.Error() != "Task not found: "+missing.String() {
		t.Fatalf("not-found err = %v", err)
	}

	// A present task still errors: _identify_success_indicators always raises.
	task := wfNewTask(t, "11111111-1111-1111-1111-111111111111", 1)
	repo.byID[task.ID.String()] = task
	tid, _ := value_objects.NewTaskId(task.ID.String())
	if _, err := svc.AnalyzeTaskWorkflow(context.Background(), tid, true); err == nil || err.Error() != "object of type 'NoneType' has no len()" {
		t.Fatalf("analyze err = %v", err)
	}
}
