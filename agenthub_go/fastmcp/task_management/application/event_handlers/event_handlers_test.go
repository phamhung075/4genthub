package event_handlers

import (
	"context"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/events"
)

func TestAgentEventHandlersStatistics(t *testing.T) {
	h := NewAgentEventHandlers(nil, nil, nil)
	ctx := context.Background()

	a := events.NewAgentAssigned()
	a.AgentID, a.TaskID, a.Role = "agent-1", "task-1", "worker"
	h.HandleAgentAssigned(ctx, a)

	b := events.NewAgentAssigned()
	b.AgentID, b.TaskID, b.Role = "agent-1", "task-2", "worker"
	h.HandleAgentAssigned(ctx, b)

	u := events.NewAgentUnassigned()
	u.AgentID, u.TaskID = "agent-1", "task-1"
	h.HandleAgentUnassigned(ctx, u)

	id := "agent-1"
	got := h.GetAgentStatistics(ctx, &id)
	stats := got["statistics"].(map[string]int)
	if stats["assignments"] != 2 || stats["unassignments"] != 1 {
		t.Fatalf("unexpected stats: %#v", stats)
	}
	workload := got["workload"].(map[string]any)
	tasks := workload["active_tasks"].([]string)
	if len(tasks) != 1 || tasks[0] != "task-2" {
		t.Fatalf("unexpected active_tasks: %#v", tasks)
	}
	if workload["total_assignments"].(int) != 2 {
		t.Fatalf("unexpected total_assignments: %#v", workload["total_assignments"])
	}
}

func TestAgentEventHandlersPerformanceCap(t *testing.T) {
	h := NewAgentEventHandlers(nil, nil, nil)
	ctx := context.Background()
	for i := 0; i < 35; i++ {
		e := events.NewAgentPerformanceEvaluated()
		e.AgentID = "a"
		e.OverallScore = float64(i)
		h.HandleAgentPerformanceEvaluated(ctx, e)
	}
	if len(h.PerformanceHistory["a"]) != 30 {
		t.Fatalf("expected cap of 30, got %d", len(h.PerformanceHistory["a"]))
	}
}

func TestAgentEventHandlersProcessEventRoutes(t *testing.T) {
	h := NewAgentEventHandlers(nil, nil, nil)
	e := events.NewAgentAssigned()
	e.AgentID, e.TaskID = "x", "y"
	h.ProcessEvent(context.Background(), e)
	if h.AgentStats["x"]["assignments"] != 1 {
		t.Fatalf("ProcessEvent did not route AgentAssigned")
	}
}

func TestHintEventHandlersStatistics(t *testing.T) {
	h := NewHintEventHandlers(nil, nil)
	ctx := context.Background()
	for i := 0; i < 3; i++ {
		e := events.NewHintGenerated()
		e.SourceRule, e.HintType = "rule-a", "next_action"
		h.HandleHintGenerated(ctx, e)
	}
	got := h.GetHintStatistics(ctx)
	summary := got["summary"].(map[string]any)
	if summary["total_generated"].(int) != 3 {
		t.Fatalf("unexpected summary: %#v", summary)
	}
	if summary["overall_acceptance_rate"].(float64) != 0.0 {
		t.Fatalf("expected 0 acceptance rate, got %v", summary["overall_acceptance_rate"])
	}
}

func TestProjectEventHandlersStatistics(t *testing.T) {
	h := NewProjectEventHandlers(nil, nil, nil, nil)
	ctx := context.Background()

	created := events.NewProjectCreatedEvent()
	created.ProjectID = "p1"
	created.Name = "Proj"
	uid := "u1"
	created.UserID = &uid
	h.HandleProjectCreated(ctx, created)

	statsEvent := events.NewProjectStatisticsUpdatedEvent()
	statsEvent.ProjectID = "p1"
	statsEvent.BranchCount = 2
	statsEvent.TotalTasks = 10
	statsEvent.CompletedTasks = 5
	statsEvent.InProgressTasks = 3
	statsEvent.TodoTasks = 2
	statsEvent.OverallProgressPercentage = 50
	h.HandleProjectStatisticsUpdated(ctx, statsEvent)

	got := h.GetProjectStatistics(ctx, nil)
	if got["total_projects"].(int) != 1 || got["active_projects"].(int) != 1 {
		t.Fatalf("unexpected project counts: %#v", got)
	}
	summary := got["summary"].(map[string]any)
	if summary["total_tasks"].(int) != 10 || summary["completed_tasks"].(int) != 5 {
		t.Fatalf("unexpected summary: %#v", summary)
	}
	byProject := got["by_project"].(map[string]map[string]any)
	if byProject["p1"]["branch_count"].(int) != 2 {
		t.Fatalf("unexpected by_project: %#v", byProject)
	}
}

func TestProjectEventHandlersArchive(t *testing.T) {
	h := NewProjectEventHandlers(nil, nil, nil, nil)
	ctx := context.Background()
	created := events.NewProjectCreatedEvent()
	created.ProjectID = "p1"
	created.Name = "Proj"
	h.HandleProjectCreated(ctx, created)

	archived := events.NewProjectArchived()
	archived.ProjectID = "p1"
	archived.ArchivedBy = "u1"
	h.HandleProjectArchived(ctx, archived)

	got := h.GetArchivedProjects(ctx)
	if got["total_archived"].(int) != 1 {
		t.Fatalf("unexpected archived count: %#v", got)
	}
	all := h.GetProjectStatistics(ctx, nil)
	if all["active_projects"].(int) != 0 {
		t.Fatalf("project should be inactive: %#v", all)
	}
}

type hintRepoStub struct{ patterns int }

func (r *hintRepoStub) StoreGeneratedHint(context.Context, events.HintGenerated) error { return nil }
func (r *hintRepoStub) StoreHintAcceptance(context.Context, events.HintAccepted) error { return nil }
func (r *hintRepoStub) StoreHintDismissal(context.Context, events.HintDismissed) error { return nil }
func (r *hintRepoStub) StoreHintFeedback(context.Context, events.HintFeedbackProvided) error {
	return nil
}
func (r *hintRepoStub) StoreDetectedPattern(context.Context, events.HintPatternDetected) error {
	r.patterns++
	return nil
}
func (r *hintRepoStub) StoreEffectivenessScore(context.Context, events.HintEffectivenessCalculated) error {
	return nil
}
func (r *hintRepoStub) StoreImprovementSuggestion(context.Context, string, string) error { return nil }
func (r *hintRepoStub) Get(_ context.Context, id string) (*HintRecord, error) {
	return &HintRecord{ID: id, SourceRule: "rule-a", HintType: "next_action"}, nil
}

// A pattern detected from inside a locked handler must not re-take the lock.
func TestHintPatternFromLockedHandlerDoesNotDeadlock(t *testing.T) {
	repo := &hintRepoStub{}
	h := NewHintEventHandlers(nil, repo)
	h.PatternThresholds["min_hints_for_pattern"] = 1
	ctx := context.Background()
	g := events.NewHintGenerated()
	g.SourceRule, g.HintType = "rule-a", "next_action"
	h.HandleHintGenerated(ctx, g)
	done := make(chan struct{})
	go func() {
		a := events.NewHintAccepted()
		a.HintID = "h1"
		h.HandleHintAccepted(ctx, a)
		close(done)
	}()
	select {
	case <-done:
	case <-time.After(2 * time.Second):
		t.Fatal("deadlock in HandleHintAccepted")
	}
	if repo.patterns != 1 {
		t.Fatalf("patterns stored = %d, want 1", repo.patterns)
	}
}
