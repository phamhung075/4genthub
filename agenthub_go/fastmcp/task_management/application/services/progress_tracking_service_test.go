package services

import (
	"context"
	"math"
	"reflect"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure"
)

type zpPtsFakeTaskRepo struct {
	repositories.TaskRepository
	tasks   map[string]*entities.Task
	findErr error
	saveErr error
	saved   []*entities.Task
}

func (r *zpPtsFakeTaskRepo) FindByID(_ context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
	if r.findErr != nil {
		return nil, r.findErr
	}
	return r.tasks[taskID.String()], nil
}

func (r *zpPtsFakeTaskRepo) Save(_ context.Context, task *entities.Task) (*entities.Task, error) {
	if r.saveErr != nil {
		return nil, r.saveErr
	}
	r.saved = append(r.saved, task)
	return task, nil
}

type zpPtsFakeContextRepo struct {
	repositories.ContextRepository
	contexts  map[string]*entities.TaskContext
	updated   []*entities.TaskContext
	getErr    error
	updateErr error
}

func (r *zpPtsFakeContextRepo) GetContext(_ context.Context, taskID string) (*entities.TaskContext, error) {
	if r.getErr != nil {
		return nil, r.getErr
	}
	return r.contexts[taskID], nil
}

func (r *zpPtsFakeContextRepo) UpdateContext(_ context.Context, c *entities.TaskContext) (map[string]any, error) {
	if r.updateErr != nil {
		return nil, r.updateErr
	}
	r.updated = append(r.updated, c)
	return map[string]any{}, nil
}

func zpPtsNewTestTask(t *testing.T, id, title, description string) *entities.Task {
	t.Helper()
	task, err := entities.NewTask(entities.Task{Title: title, Description: description})
	if err != nil {
		t.Fatalf("NewTask: %v", err)
	}
	taskID, err := value_objects.NewTaskId(id)
	if err != nil {
		t.Fatalf("NewTaskId: %v", err)
	}
	task.ID = &taskID
	return task
}

func zpPtsNewServiceForTask(t *testing.T, task *entities.Task) (*ProgressTrackingService, *zpPtsFakeTaskRepo) {
	t.Helper()
	repo := &zpPtsFakeTaskRepo{tasks: map[string]*entities.Task{task.ID.String(): task}}
	return NewProgressTrackingService(repo, &zpPtsFakeContextRepo{}, infrastructure.NewEventBus(), nil), repo
}

func TestProgressTrackingService_CalculateOverallProgress_Weighting(t *testing.T) {
	task := zpPtsNewTestTask(t, "task-1", "task", "desc")
	if err := task.UpdateProgress(entities.ProgressUpdate{Type: value_objects.ProgressTypeDesign, Percentage: 40}); err != nil {
		t.Fatalf("UpdateProgress design: %v", err)
	}
	if err := task.UpdateProgress(entities.ProgressUpdate{Type: value_objects.ProgressTypeImplementation, Percentage: 60}); err != nil {
		t.Fatalf("UpdateProgress implementation: %v", err)
	}
	svc, _ := zpPtsNewServiceForTask(t, task)
	ctx := context.Background()

	weighted, err := svc.CalculateOverallProgress(ctx, "task-1", true, map[string]float64{"design": 1, "implementation": 3})
	if err != nil {
		t.Fatalf("CalculateOverallProgress: %v", err)
	}
	if math.Abs(weighted-55.0) > 1e-9 {
		t.Fatalf("weighted overall progress = %v, want 55", weighted)
	}

	equal, err := svc.CalculateOverallProgress(ctx, "task-1", true, nil)
	if err != nil {
		t.Fatalf("CalculateOverallProgress equal: %v", err)
	}
	if math.Abs(equal-50.0) > 1e-9 {
		t.Fatalf("equal overall progress = %v, want 50", equal)
	}

	task.Subtasks = []string{"sub-1"}
	withSubtasks, err := svc.CalculateOverallProgress(ctx, "task-1", true, nil)
	if err != nil {
		t.Fatalf("CalculateOverallProgress subtasks: %v", err)
	}
	if math.Abs(withSubtasks-100.0/3.0) > 1e-9 {
		t.Fatalf("overall progress with subtasks = %v, want %v", withSubtasks, 100.0/3.0)
	}

	withoutSubtasks, err := svc.CalculateOverallProgress(ctx, "task-1", false, nil)
	if err != nil {
		t.Fatalf("CalculateOverallProgress include_subtasks=false: %v", err)
	}
	if math.Abs(withoutSubtasks-50.0) > 1e-9 {
		t.Fatalf("overall progress without subtasks = %v, want 50", withoutSubtasks)
	}
}

func TestProgressTrackingService_InferProgressFromContext_KeywordOrder(t *testing.T) {
	ctx := context.Background()

	cases := []struct {
		name    string
		content string
		want    *float64
	}{
		{"completed", "we have completed the module", zpPtsFloatPtr(100)},
		{"almost done hits completed first", "almost done with it", zpPtsFloatPtr(100)},
		{"finalizing", "finalizing the release", zpPtsFloatPtr(85)},
		{"testing", "testing the module", zpPtsFloatPtr(70)},
		{"in progress", "working on the module", zpPtsFloatPtr(50)},
		{"started", "began the work", zpPtsFloatPtr(25)},
		{"no keyword", "nothing relevant here", nil},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			task := zpPtsNewTestTask(t, "task-1", "task", "desc")
			contextID := "ctx1"
			task.ContextID = &contextID
			contextData := &entities.TaskContext{}
			contextData.Notes.AgentInsights = []entities.ContextInsight{{Content: tc.content}}

			repo := &zpPtsFakeTaskRepo{tasks: map[string]*entities.Task{"task-1": task}}
			ctxRepo := &zpPtsFakeContextRepo{contexts: map[string]*entities.TaskContext{"ctx1": contextData}}
			svc := NewProgressTrackingService(repo, ctxRepo, infrastructure.NewEventBus(), nil)

			got, err := svc.InferProgressFromContext(ctx, "task-1")
			if err != nil {
				t.Fatalf("InferProgressFromContext: %v", err)
			}
			if (got == nil) != (tc.want == nil) {
				t.Fatalf("InferProgressFromContext = %v, want %v", got, tc.want)
			}
			if got != nil && math.Abs(*got-*tc.want) > 1e-9 {
				t.Fatalf("InferProgressFromContext = %v, want %v", *got, *tc.want)
			}
		})
	}
}

func TestProgressTrackingService_InferProgressFromContext_UsesProgressActions(t *testing.T) {
	task := zpPtsNewTestTask(t, "task-1", "task", "desc")
	contextID := "ctx1"
	task.ContextID = &contextID
	contextData := &entities.TaskContext{}
	contextData.Progress.CompletedActions = []entities.ContextProgressAction{{Details: "finalizing now"}}

	repo := &zpPtsFakeTaskRepo{tasks: map[string]*entities.Task{"task-1": task}}
	ctxRepo := &zpPtsFakeContextRepo{contexts: map[string]*entities.TaskContext{"ctx1": contextData}}
	svc := NewProgressTrackingService(repo, ctxRepo, infrastructure.NewEventBus(), nil)

	got, err := svc.InferProgressFromContext(context.Background(), "task-1")
	if err != nil {
		t.Fatalf("InferProgressFromContext: %v", err)
	}
	if got == nil || *got != 85.0 {
		t.Fatalf("InferProgressFromContext = %v, want 85", got)
	}
}

func TestProgressTrackingService_BatchUpdateProgress_SkipsFailures(t *testing.T) {
	task1 := zpPtsNewTestTask(t, "task-1", "task one", "desc")
	task2 := zpPtsNewTestTask(t, "task-2", "task two", "desc")
	repo := &zpPtsFakeTaskRepo{tasks: map[string]*entities.Task{"task-1": task1, "task-2": task2}}
	svc := NewProgressTrackingService(repo, &zpPtsFakeContextRepo{}, infrastructure.NewEventBus(), nil)

	updates := []map[string]any{
		{"task_id": "task-1", "progress_type": value_objects.ProgressTypeGeneral, "percentage": 10.0},
		{"progress_type": value_objects.ProgressTypeGeneral, "percentage": 10.0},
		{"task_id": "task-2", "progress_type": value_objects.ProgressTypeGeneral, "percentage": 10.0, "bogus": 1},
		{"task_id": "missing", "progress_type": value_objects.ProgressTypeGeneral, "percentage": 10.0},
		{"task_id": "task-2", "progress_type": value_objects.ProgressTypeGeneral, "percentage": 20.0},
	}

	got := svc.BatchUpdateProgress(context.Background(), updates)
	if len(got) != 2 {
		t.Fatalf("BatchUpdateProgress returned %d tasks, want 2", len(got))
	}
	if got[0] != task1 || got[1] != task2 {
		t.Fatalf("BatchUpdateProgress returned unexpected tasks")
	}
	if len(repo.saved) != 2 {
		t.Fatalf("Save calls = %d, want 2", len(repo.saved))
	}
}

func TestProgressTrackingService_UpdateProgress_UpdatesContextAndPublishes(t *testing.T) {
	task := zpPtsNewTestTask(t, "task-1", "task", "desc")
	contextID := "ctx1"
	task.ContextID = &contextID
	contextData := &entities.TaskContext{}

	repo := &zpPtsFakeTaskRepo{tasks: map[string]*entities.Task{"task-1": task}}
	ctxRepo := &zpPtsFakeContextRepo{contexts: map[string]*entities.TaskContext{"ctx1": contextData}}
	bus := infrastructure.NewEventBus()
	var published []any
	bus.Subscribe(reflect.TypeOf(events.ProgressEvent{}), "capture", func(event any) {
		published = append(published, event)
	}, 0)
	svc := NewProgressTrackingService(repo, ctxRepo, bus, nil)

	description := "half way"
	updated, err := svc.UpdateProgress(context.Background(), "task-1", value_objects.ProgressTypeImplementation, 30, &description, map[string]any{"blockers": []string{"b1"}}, nil)
	if err != nil {
		t.Fatalf("UpdateProgress: %v", err)
	}
	if updated != task {
		t.Fatalf("UpdateProgress did not return the task")
	}
	if len(repo.saved) != 1 {
		t.Fatalf("Save calls = %d, want 1", len(repo.saved))
	}
	if len(ctxRepo.updated) != 1 {
		t.Fatalf("UpdateContext calls = %d, want 1", len(ctxRepo.updated))
	}
	if len(contextData.ProgressTimeline) != 1 {
		t.Fatalf("context progress timeline length = %d, want 1", len(contextData.ProgressTimeline))
	}
	entry := contextData.ProgressTimeline[0]
	if entry["type"] != "implementation" || entry["percentage"] != 30.0 || entry["description"] != "half way" {
		t.Fatalf("context progress entry = %#v", entry)
	}
	if _, ok := published[0].(events.ProgressUpdated); !ok {
		t.Fatalf("first published event = %T, want events.ProgressUpdated", published[0])
	}
}

func TestProgressTrackingService_UpdateProgress_DefaultDescription(t *testing.T) {
	task := zpPtsNewTestTask(t, "task-1", "task", "desc")
	contextID := "ctx1"
	task.ContextID = &contextID
	contextData := &entities.TaskContext{}

	repo := &zpPtsFakeTaskRepo{tasks: map[string]*entities.Task{"task-1": task}}
	ctxRepo := &zpPtsFakeContextRepo{contexts: map[string]*entities.TaskContext{"ctx1": contextData}}
	svc := NewProgressTrackingService(repo, ctxRepo, infrastructure.NewEventBus(), nil)

	if _, err := svc.UpdateProgress(context.Background(), "task-1", value_objects.ProgressTypeImplementation, 30, nil, nil, nil); err != nil {
		t.Fatalf("UpdateProgress: %v", err)
	}
	if got := contextData.ProgressTimeline[0]["description"]; got != "Updated implementation progress to 30.0%" {
		t.Fatalf("default description = %q", got)
	}
}

func TestProgressTrackingService_UpdateProgress_TaskNotFound(t *testing.T) {
	svc := NewProgressTrackingService(&zpPtsFakeTaskRepo{}, &zpPtsFakeContextRepo{}, infrastructure.NewEventBus(), nil)
	_, err := svc.UpdateProgress(context.Background(), "nope", value_objects.ProgressTypeGeneral, 10, nil, nil, nil)
	if err == nil {
		t.Fatal("UpdateProgress did not error for a missing task")
	}
	if err.Error() != "Task nope not found" {
		t.Fatalf("error = %q, want %q", err.Error(), "Task nope not found")
	}
}

func TestProgressTrackingService_CheckMilestones(t *testing.T) {
	task := zpPtsNewTestTask(t, "task-1", "task", "desc")
	if err := task.UpdateProgress(entities.ProgressUpdate{Type: value_objects.ProgressTypeDesign, Percentage: 60}); err != nil {
		t.Fatalf("UpdateProgress: %v", err)
	}
	if err := task.AddProgressMilestone("m1", 50); err != nil {
		t.Fatalf("AddProgressMilestone m1: %v", err)
	}
	if err := task.AddProgressMilestone("m2", 80); err != nil {
		t.Fatalf("AddProgressMilestone m2: %v", err)
	}
	svc, _ := zpPtsNewServiceForTask(t, task)

	reached, err := svc.CheckMilestones(context.Background(), "task-1")
	if err != nil {
		t.Fatalf("CheckMilestones: %v", err)
	}
	if !reflect.DeepEqual(reached, []string{"m1"}) {
		t.Fatalf("CheckMilestones = %v, want [m1]", reached)
	}
}

func TestProgressTrackingService_GetProgressSummary_KeyOrder(t *testing.T) {
	task := zpPtsNewTestTask(t, "task-1", "task", "desc")
	if err := task.UpdateProgress(entities.ProgressUpdate{
		Type: value_objects.ProgressTypeDesign, Percentage: 60, Metadata: map[string]any{"blockers": []string{"b1"}},
	}); err != nil {
		t.Fatalf("UpdateProgress: %v", err)
	}
	if err := task.AddProgressMilestone("m1", 50); err != nil {
		t.Fatalf("AddProgressMilestone: %v", err)
	}
	svc, _ := zpPtsNewServiceForTask(t, task)

	summary, err := svc.GetProgressSummary(context.Background(), "task-1")
	if err != nil {
		t.Fatalf("GetProgressSummary: %v", err)
	}
	wantKeys := []string{"task_id", "overall_progress", "progress_by_type", "subtask_progress", "milestones", "recent_updates", "is_stalled", "blockers"}
	if got := summary.Keys(); !reflect.DeepEqual(got, wantKeys) {
		t.Fatalf("summary keys = %v, want %v", got, wantKeys)
	}
	if got := summary.GetAny("blockers"); !reflect.DeepEqual(got, []string{"b1"}) {
		t.Fatalf("blockers = %#v, want [b1]", got)
	}
	if got := summary.GetAny("task_id"); got != "task-1" {
		t.Fatalf("task_id = %v", got)
	}
	progressByType, ok := summary.Get("progress_by_type")
	if !ok {
		t.Fatal("missing progress_by_type")
	}
	if got := progressByType.(*entities.OrderedMap[any]).Keys(); !reflect.DeepEqual(got, []string{"design"}) {
		t.Fatalf("progress_by_type keys = %v, want [design]", got)
	}
	milestones, _ := summary.Get("milestones")
	milestoneMap := milestones.(*entities.OrderedMap[any])
	if got := milestoneMap.Keys(); !reflect.DeepEqual(got, []string{"m1"}) {
		t.Fatalf("milestones keys = %v, want [m1]", got)
	}
	milestoneEntry, _ := milestoneMap.Get("m1")
	entry := milestoneEntry.(*entities.OrderedMap[any])
	if got := entry.Keys(); !reflect.DeepEqual(got, []string{"target", "reached"}) {
		t.Fatalf("milestone entry keys = %v, want [target reached]", got)
	}
}

func TestProgressTrackingService_SuggestProgressUpdate(t *testing.T) {
	task := zpPtsNewTestTask(t, "task-1", "Design and implement the API", "Please document it")
	svc, _ := zpPtsNewServiceForTask(t, task)

	suggestion, err := svc.SuggestProgressUpdate(context.Background(), "task-1")
	if err != nil {
		t.Fatalf("SuggestProgressUpdate: %v", err)
	}
	wantTop := []string{"task_id", "suggested_updates"}
	if got := suggestion.Keys(); !reflect.DeepEqual(got, wantTop) {
		t.Fatalf("suggestion keys = %v, want %v", got, wantTop)
	}
	updatesValue, _ := suggestion.Get("suggested_updates")
	updates := updatesValue.([]any)
	if len(updates) != 3 {
		t.Fatalf("suggested_updates length = %d, want 3", len(updates))
	}
	wantTypes := []value_objects.ProgressType{
		value_objects.ProgressTypeDesign,
		value_objects.ProgressTypeImplementation,
		value_objects.ProgressTypeDocumentation,
	}
	wantDescriptions := []string{"Start design phase", "Begin implementation", "Begin documentation"}
	for i, raw := range updates {
		update := raw.(*entities.OrderedMap[any])
		if got := update.Keys(); !reflect.DeepEqual(got, []string{"progress_type", "percentage", "description"}) {
			t.Fatalf("update %d keys = %v", i, got)
		}
		if got := update.GetAny("progress_type"); got != wantTypes[i] {
			t.Fatalf("update %d progress_type = %v, want %v", i, got, wantTypes[i])
		}
		if got := update.GetAny("description"); got != wantDescriptions[i] {
			t.Fatalf("update %d description = %v, want %v", i, got, wantDescriptions[i])
		}
	}
}

func TestProgressTrackingService_SuggestProgressUpdate_GeneralFallback(t *testing.T) {
	task := zpPtsNewTestTask(t, "task-1", "Something unrelated", "nothing to match")
	svc, _ := zpPtsNewServiceForTask(t, task)

	suggestion, err := svc.SuggestProgressUpdate(context.Background(), "task-1")
	if err != nil {
		t.Fatalf("SuggestProgressUpdate: %v", err)
	}
	updatesValue, _ := suggestion.Get("suggested_updates")
	updates := updatesValue.([]any)
	if len(updates) != 1 {
		t.Fatalf("suggested_updates length = %d, want 1", len(updates))
	}
	update := updates[0].(*entities.OrderedMap[any])
	if update.GetAny("progress_type") != value_objects.ProgressTypeGeneral || update.GetAny("description") != "Start task" {
		t.Fatalf("general fallback update = %#v", update)
	}
}

func TestProgressTrackingService_CheckStalledProgress_Publishes(t *testing.T) {
	task := zpPtsNewTestTask(t, "task-1", "task", "desc")
	timeline := value_objects.NewProgressTimeline(task.ID.String())
	snapshot, err := value_objects.NewProgressSnapshot(value_objects.ProgressSnapshot{
		TaskID: task.ID.String(), ProgressType: value_objects.ProgressTypeGeneral,
		Percentage: 50, Timestamp: time.Now().UTC().Add(-48 * time.Hour),
	})
	if err != nil {
		t.Fatalf("NewProgressSnapshot: %v", err)
	}
	if err := timeline.AddSnapshot(snapshot); err != nil {
		t.Fatalf("AddSnapshot: %v", err)
	}
	task.ProgressTimeline = timeline

	bus := infrastructure.NewEventBus()
	var published []any
	bus.Subscribe(reflect.TypeOf(events.ProgressEvent{}), "capture", func(event any) {
		published = append(published, event)
	}, 0)
	svc := NewProgressTrackingService(&zpPtsFakeTaskRepo{}, &zpPtsFakeContextRepo{}, bus, nil)

	svc.zpPtsCheckStalledProgress(context.Background(), task)
	if len(published) != 1 {
		t.Fatalf("published events = %d, want 1", len(published))
	}
	stalled, ok := published[0].(events.ProgressStalled)
	if !ok {
		t.Fatalf("published event = %T, want events.ProgressStalled", published[0])
	}
	if stalled.CurrentPercentage != 50 || stalled.StallDurationHours < 47 || stalled.StallDurationHours > 49 {
		t.Fatalf("stalled event = %#v", stalled)
	}
}

func TestProgressTrackingService_GetProgressTimeline_FilterByType(t *testing.T) {
	task := zpPtsNewTestTask(t, "task-1", "task", "desc")
	if err := task.UpdateProgress(entities.ProgressUpdate{Type: value_objects.ProgressTypeDesign, Percentage: 20}); err != nil {
		t.Fatalf("UpdateProgress design: %v", err)
	}
	if err := task.UpdateProgress(entities.ProgressUpdate{Type: value_objects.ProgressTypeTesting, Percentage: 40}); err != nil {
		t.Fatalf("UpdateProgress testing: %v", err)
	}
	svc, _ := zpPtsNewServiceForTask(t, task)

	designType := value_objects.ProgressTypeDesign
	snapshots, err := svc.GetProgressTimeline(context.Background(), "task-1", 24, &designType)
	if err != nil {
		t.Fatalf("GetProgressTimeline: %v", err)
	}
	if len(snapshots) != 1 || snapshots[0].ProgressType != value_objects.ProgressTypeDesign {
		t.Fatalf("filtered snapshots = %#v", snapshots)
	}

	all, err := svc.GetProgressTimeline(context.Background(), "task-1", 24, nil)
	if err != nil {
		t.Fatalf("GetProgressTimeline all: %v", err)
	}
	if len(all) != 2 {
		t.Fatalf("all snapshots = %d, want 2", len(all))
	}
}
