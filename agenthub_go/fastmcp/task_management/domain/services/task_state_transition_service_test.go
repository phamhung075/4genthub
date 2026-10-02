package services

import (
	"context"
	"encoding/json"
	"os"
	"reflect"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type tstCase struct {
	From    string                `json:"from"`
	Can     map[string][2]any     `json:"can"`
	Suggest map[string]any        `json:"suggest"`
	Allowed map[string]tstAllowed `json:"allowed"`
	Order   []string              `json:"order"`
	Trans   map[string][2]any     `json:"transition"`
}

type tstAllowed struct {
	Allowed       bool     `json:"allowed"`
	Reason        *string  `json:"reason"`
	Description   string   `json:"description"`
	Prerequisites []string `json:"prerequisites"`
}

func tstTask(t *testing.T, status string) *entities.Task {
	t.Helper()
	id, _ := value_objects.NewTaskId("00000000-0000-4000-8000-000000000001")
	st := tstStatus(t, status)
	task, err := entities.NewTask(entities.Task{ID: &id, Title: "T", Description: "d", Status: &st})
	if err != nil {
		t.Fatal(err)
	}
	return task
}

func tstStatus(t *testing.T, s string) value_objects.TaskStatus {
	st, err := value_objects.NewTaskStatus(s)
	if err != nil {
		t.Fatal(err)
	}
	return st
}

func TestTaskStateTransitionMatchesPython(t *testing.T) {
	raw, err := os.ReadFile("testdata/task_state_transition_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []tstCase
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	svc := NewTaskStateTransitionService(nil, nil)
	ctx := context.Background()
	for _, c := range cases {
		for target, want := range c.Can {
			ok, reason := svc.CanTransitionTo(ctx, tstTask(t, c.From), tstStatus(t, target), TransitionUserInitiated)
			wantReason, _ := want[1].(string)
			if ok != want[0].(bool) || reason != wantReason {
				t.Errorf("can %s->%s: got %v %q want %v", c.From, target, ok, reason, want)
			}
		}
		for target, want := range c.Trans {
			ok, msg := svc.TransitionTo(ctx, tstTask(t, c.From), tstStatus(t, target), TransitionUserInitiated)
			if ok != want[0].(bool) || msg != want[1].(string) {
				t.Errorf("transition %s->%s: got %v %q want %v", c.From, target, ok, msg, want)
			}
		}
		got := svc.GetAllowedTransitions(ctx, tstTask(t, c.From))
		if !reflect.DeepEqual(got.Keys(), append([]string{}, c.Order...)) && !(len(c.Order) == 0 && got.Len() == 0) {
			t.Errorf("order %s: %v want %v", c.From, got.Keys(), c.Order)
		}
		for k, w := range c.Allowed {
			g, _ := got.Get(k)
			if g.Allowed != w.Allowed || g.Description != w.Description ||
				!reflect.DeepEqual(g.Prerequisites, w.Prerequisites) || (g.Reason == nil) != (w.Reason == nil) ||
				(g.Reason != nil && *g.Reason != *w.Reason) {
				t.Errorf("allowed %s->%s: got %+v want %+v", c.From, k, g, w)
			}
		}
		sg := svc.SuggestNextStatus(ctx, tstTask(t, c.From))
		gb, _ := json.Marshal(sg)
		wb, _ := json.Marshal(c.Suggest)
		if string(gb) != string(wb) {
			t.Errorf("suggest %s: got %s want %s", c.From, gb, wb)
		}
	}
}

type fakeTaskRepo struct{ tasks []*entities.Task }

func (f fakeTaskRepo) FindAll(context.Context) ([]*entities.Task, error) { return f.tasks, nil }

// Python defect preserved: the service rules allow blocked->todo but TaskStatus forbids it,
// so dependency completion never unblocks anything.
func TestHandleDependencyCompletionCannotUnblock(t *testing.T) {
	done := tstTask(t, "in_progress")
	blocked := tstTask(t, "blocked")
	id2, _ := value_objects.NewTaskId("00000000-0000-4000-8000-000000000002")
	blocked.ID = &id2
	blocked.Dependencies = []value_objects.TaskId{*done.ID}
	svc := NewTaskStateTransitionService(nil, fakeTaskRepo{[]*entities.Task{done, blocked}})
	ok, _ := svc.TransitionTo(context.Background(), done, tstStatus(t, "done"), TransitionUserInitiated)
	if !ok || blocked.Status.Value != "blocked" {
		t.Fatalf("ok=%v blocked=%v", ok, blocked.Status)
	}
	if got := svc.HandleDependencyCompletion(context.Background(), done); len(got) != 0 {
		t.Fatalf("got %v", got)
	}
}

type fakeSubtaskRepo struct{ gotNilID bool }

func (f *fakeSubtaskRepo) FindByParentTaskID(_ context.Context, id *value_objects.TaskId) ([]*entities.Subtask, error) {
	f.gotNilID = id == nil
	return nil, nil
}

// Python passes task.id=None through to the subtask repository.
func TestCanTransitionToDonePassesNilTaskIDToSubtaskRepository(t *testing.T) {
	repo := &fakeSubtaskRepo{}
	task := tstTask(t, "in_progress")
	task.ID = nil
	ok, reason := NewTaskStateTransitionService(repo, nil).CanTransitionTo(context.Background(), task,
		tstStatus(t, "done"), TransitionUserInitiated)
	if !ok || reason != "" || !repo.gotNilID {
		t.Fatalf("ok=%v reason=%q nil=%v", ok, reason, repo.gotNilID)
	}
}
