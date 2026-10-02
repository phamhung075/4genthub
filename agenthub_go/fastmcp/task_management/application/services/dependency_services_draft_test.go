package services

import (
	"context"
	"strings"
	"testing"

	taskdto "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

const depResTestUUID = "123e4567-e89b-42d3-a456-426614174000"

type depResFakeRepo struct {
	repositories.TaskRepository
	tasks map[string]*entities.Task
}

func (r *depResFakeRepo) FindByID(ctx context.Context, id value_objects.TaskId) (*entities.Task, error) {
	return r.tasks[id.Value], nil
}

func (r *depResFakeRepo) FindAll(ctx context.Context) ([]*entities.Task, error) {
	out := []*entities.Task{}
	for _, t := range r.tasks {
		out = append(out, t)
	}
	return out, nil
}

func depResTestTask(t *testing.T, id, title, status string, deps ...string) *entities.Task {
	t.Helper()
	tid, err := value_objects.NewTaskId(id)
	if err != nil {
		t.Fatalf("task id: %v", err)
	}
	st, err := value_objects.NewTaskStatus(status)
	if err != nil {
		t.Fatalf("status: %v", err)
	}
	pr := value_objects.PriorityMedium()
	task, err := entities.NewTask(entities.Task{ID: &tid, Title: title, Description: "d", Status: &st, Priority: &pr})
	if err != nil {
		t.Fatalf("new task: %v", err)
	}
	for _, d := range deps {
		dep, err := value_objects.NewTaskId(d)
		if err != nil {
			t.Fatalf("dep id: %v", err)
		}
		task.Dependencies = append(task.Dependencies, dep)
	}
	return task
}

func TestDependencyResolverResolveDependencies(t *testing.T) {
	ctx := context.Background()
	done := depResTestTask(t, depResTestUUID, "B", "done")
	todoA := depResTestTask(t, "223e4567-e89b-42d3-a456-426614174001", "A", "todo", depResTestUUID)
	blockedByA := depResTestTask(t, "323e4567-e89b-42d3-a456-426614174002", "C", "todo", "223e4567-e89b-42d3-a456-426614174001")

	repo := &depResFakeRepo{tasks: map[string]*entities.Task{
		done.ID.Value:       done,
		todoA.ID.Value:      todoA,
		blockedByA.ID.Value: blockedByA,
	}}
	svc := NewDependencyResolverService(repo, nil)

	rels, err := svc.ResolveDependencies(ctx, todoA.ID.Value)
	if err != nil {
		t.Fatalf("resolve: %v", err)
	}
	if len(rels.DependsOn) != 1 || rels.DependsOn[0].Status != "done" {
		t.Fatalf("depends_on = %+v", rels.DependsOn)
	}
	if rels.CanStart != true || rels.IsBlocked != false || rels.IsBlockingOthers != true {
		t.Fatalf("flags = can_start:%v blocked:%v blocking:%v", rels.CanStart, rels.IsBlocked, rels.IsBlockingOthers)
	}
	if rels.TotalDependencies != 1 || rels.CompletedDependencies != 1 || rels.BlockedDependencies != 0 {
		t.Fatalf("counts = %d/%d/%d", rels.TotalDependencies, rels.CompletedDependencies, rels.BlockedDependencies)
	}
	if rels.DependencySummary != "Depends on 1 task(s) (1/1 completed) | Blocks 1 task(s)" {
		t.Fatalf("summary = %q", rels.DependencySummary)
	}
	if rels.NextActions[0] != "✅ Ready to start - no blocking dependencies" {
		t.Fatalf("next_actions = %v", rels.NextActions)
	}
	// Python defect preserved: the graph only walks upstream from the root, so no task in it
	// ever depends on the root and downstream_chains is always empty
	if len(rels.DownstreamChains) != 0 {
		t.Fatalf("downstream = %+v", rels.DownstreamChains)
	}

	if _, err := svc.ResolveDependencies(ctx, "423e4567-e89b-42d3-a456-426614174003"); err == nil {
		t.Fatal("expected TaskNotFoundError")
	}
}

func TestDependencyResolverBlockedAndWait(t *testing.T) {
	ctx := context.Background()
	todoDep := depResTestTask(t, depResTestUUID, "B", "todo")
	taskA := depResTestTask(t, "223e4567-e89b-42d3-a456-426614174001", "A", "todo", depResTestUUID)
	repo := &depResFakeRepo{tasks: map[string]*entities.Task{todoDep.ID.Value: todoDep, taskA.ID.Value: taskA}}
	svc := NewDependencyResolverService(repo, nil)

	rels, err := svc.ResolveDependencies(ctx, taskA.ID.Value)
	if err != nil {
		t.Fatalf("resolve: %v", err)
	}
	if rels.CanStart || rels.DependencySummary != "Depends on 1 task(s) (0/1 completed)" {
		t.Fatalf("summary = %q can_start = %v", rels.DependencySummary, rels.CanStart)
	}
	if rels.BlockingReasons[0] != "'B' (todo)" {
		t.Fatalf("reasons = %v", rels.BlockingReasons)
	}
	if len(rels.NextActions) != 2 || rels.NextActions[0] != "⏳ Wait for 1 dependencies to complete" ||
		rels.NextActions[1] != "💡 Consider working on 1 unstarted dependencies" {
		t.Fatalf("actions = %v", rels.NextActions)
	}
}

func TestContextValidationService(t *testing.T) {
	svc := NewContextValidationService(nil, nil)

	tid, _ := value_objects.NewTaskId(depResTestUUID)
	status, _ := value_objects.NewTaskStatus("todo")
	priority := value_objects.PriorityMedium()
	task, _ := entities.NewTask(entities.Task{ID: &tid, Title: "T", Description: "d", Status: &status, Priority: &priority})
	md, _ := entities.NewContextMetadata(entities.ContextMetadata{TaskID: depResTestUUID})
	taskCtx := entities.NewTaskContext(md, entities.ContextObjective{})

	ok, errs := svc.ValidateCompletionContext(task, taskCtx, "   ", nil, nil)
	if ok || len(errs) != 1 || errs[0] != "completion_summary is required and cannot be empty" {
		t.Fatalf("empty summary => %v %v", ok, errs)
	}

	other := "923e4567-e89b-42d3-a456-426614174009"
	taskCtx.Metadata.TaskID = other
	ok, errs = svc.ValidateCompletionContext(task, taskCtx, "done", nil, nil)
	if ok || len(errs) != 1 || errs[0] != "Context task_id "+other+" does not match task "+depResTestUUID {
		t.Fatalf("mismatch => %v %v", ok, errs)
	}

	bad, _ := svc.ValidateContextData(value_objects.ContextLevelTask, map[string]any{"completion_percentage": 150})
	valid, _ := bad.Get("valid")
	errsAny, _ := bad.Get("errors")
	errs = errsAny.([]string)
	if valid != false || len(errs) != 1 || errs[0] != "completion_percentage must be a number between 0 and 100" {
		t.Fatalf("ctx data => %v", errs)
	}

	good, _ := svc.ValidateContextData(value_objects.ContextLevelProject, map[string]any{"name": "P", "labels": []string{"a"}})
	valid, _ = good.Get("valid")
	errsAny, _ = good.Get("errors")
	errs = errsAny.([]string)
	if valid != true || len(errs) != 0 {
		t.Fatalf("valid ctx => %v", errs)
	}
}

func TestContextValidationProgressAndCompletion(t *testing.T) {
	svc := NewContextValidationService(nil, nil)

	ok, errs := svc.ValidateProgressUpdate("bogus", "  ", nil)
	if ok || len(errs) != 2 ||
		errs[0] != "Invalid progress_type. Must be one of: analysis, design, implementation, testing, documentation, review, deployment, general" ||
		errs[1] != "Progress details cannot be empty" {
		t.Fatalf("progress => %v", errs)
	}
	pct := 120.0
	ok, errs = svc.ValidateProgressUpdate("general", "x", &pct)
	if ok || errs[0] != "Progress percentage must be between 0 and 100" {
		t.Fatalf("progress pct => %v", errs)
	}

	md, _ := entities.NewContextMetadata(entities.ContextMetadata{TaskID: depResTestUUID})
	ctx := entities.NewTaskContext(md, entities.ContextObjective{})
	if ok, errs := svc.ValidateContextUpdate(ctx, map[string]any{"next_steps": "no"}); ok || errs[0] != "next_steps must be a list" {
		t.Fatalf("update => %v", errs)
	}

	if err := svc.EnsureCompletionSummaryInContext(ctx, "  ", nil, nil); err == nil {
		t.Fatal("expected InvalidContextUpdateError")
	} else if !strings.Contains(err.Error(), "completion_summary cannot be empty") {
		t.Fatalf("err = %v", err)
	}
}

func TestContentAnalyzerDetailsQuirk(t *testing.T) {
	repo := &depResFakeRepo{tasks: map[string]*entities.Task{}}
	task := depResTestTask(t, depResTestUUID, "requires B after", "todo")
	repo.tasks[task.ID.Value] = task
	analyzer := NewContentAnalyzer(repo)
	if hints := analyzer.AnalyzeTaskContent(context.Background(), task); len(hints) != 0 {
		t.Fatalf("expected no hints (Python AttributeError quirk), got %d", len(hints))
	}
}

func TestDependencyHintValidation(t *testing.T) {
	if _, err := NewDependencyHint(DependencyHint{ConfidenceScore: 1.5}); err == nil {
		t.Fatal("expected ValueError for confidence > 1")
	}
	h, err := NewDependencyHint(DependencyHint{ConfidenceScore: 0.5})
	if err != nil || h.Evidence == nil {
		t.Fatalf("hint => %v %v", h, err)
	}
}

func TestEngineScoresAndSummaries(t *testing.T) {
	repo := &depResFakeRepo{tasks: map[string]*entities.Task{}}
	resolver := NewDependencyResolverService(repo, nil)
	engine := NewDependencyManagementEngine(resolver, repo, nil)

	noDeps := taskdto.DependencyRelationships{}
	if s := engine.calculateOptimizationScore(&noDeps, nil); s != 0.0 {
		t.Fatalf("empty score = %v", s)
	}
	if s := engine.generateSuggestionSummary(nil); s != "No AI suggestions available" {
		t.Fatalf("empty summary = %q", s)
	}

	hHigh, _ := NewDependencyHint(DependencyHint{ConfidenceScore: 0.8})
	score := engine.calculateOptimizationScore(&noDeps, []*DependencySuggestion{{Hint: hHigh}})
	if score != 0.9 {
		t.Fatalf("high score = %v", score)
	}
	if s := engine.generateSuggestionSummary([]*DependencySuggestion{{Hint: hHigh}}); s != "Found 1 AI suggestions: 1 high-confidence suggestion(s)" {
		t.Fatalf("high summary = %q", s)
	}
	hMed, _ := NewDependencyHint(DependencyHint{ConfidenceScore: 0.5})
	if s := engine.generateSuggestionSummary([]*DependencySuggestion{{Hint: hMed}}); s != "Found 1 AI suggestions: 1 medium-confidence suggestion(s)" {
		t.Fatalf("medium summary = %q", s)
	}
	hLow, _ := NewDependencyHint(DependencyHint{ConfidenceScore: 0.3})
	if s := engine.generateSuggestionSummary([]*DependencySuggestion{{Hint: hLow}}); s != "Found 1 low-confidence AI suggestions" {
		t.Fatalf("low summary = %q", s)
	}

	if keys := engine.GetPerformanceMetrics().Keys(); len(keys) != 5 || keys[0] != "analysis_time" || keys[4] != "cache_misses" {
		t.Fatalf("metric keys = %v", keys)
	}
}
