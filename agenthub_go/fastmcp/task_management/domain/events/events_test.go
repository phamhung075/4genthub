package events

import (
	"reflect"
	"testing"
	"time"
)

var fixed = time.Date(2026, 9, 30, 21, 14, 50, 709000000, time.UTC)

func TestTaskCreatedEventToDict(t *testing.T) {
	e := NewTaskCreatedEvent()
	e.EventID, e.OccurredAt = "eid", fixed
	e.TaskID, e.Title = "t1", "T"
	want := map[string]any{
		"event_id": "eid", "occurred_at": "2026-09-30T21:14:50.709000+00:00", "aggregate_id": nil, "aggregate_type": nil,
		"user_id": nil, "task_id": "t1", "branch_id": "", "title": "T", "status": "", "priority": "", "assignees": []string{},
		"event_type": "TaskCreatedEvent",
	}
	if got := e.ToDict(); !reflect.DeepEqual(got, want) {
		t.Fatalf("got %#v", got)
	}
}

func TestDefaultsAndAliases(t *testing.T) {
	if p := NewProjectCreatedEvent(); p.Status != "active" || p.EventID == "" || p.OccurredAt.IsZero() {
		t.Fatal(p)
	}
	var _ TaskCreated = NewTaskCreatedEvent() // alias from events/__init__.py
	if e := NewAgentCollaborationStarted(); e.CollaborationType != "general" || e.Objectives == nil {
		t.Fatal(e)
	}
	if e := NewConflictDetected(); e.ImpactAssessment != "low" {
		t.Fatal(e)
	}
}

func TestContextAndHintDicts(t *testing.T) {
	c := NewContextCreated()
	c.EventID, c.CreatedAt, c.ContextID = "e", fixed, "c"
	d := c.ToDict()
	if d["occurred_at"] != d["created_at"] || d["event_type"] != "ContextCreated" || len(d) != 7 {
		t.Fatal(d)
	}
	h := NewHintGenerated()
	h.EventID, h.OccurredAt = "e", fixed
	hd := h.ToDict()
	if hd["event_type"] != "hint_generated" || hd["hint_type"] != "next_action" || hd["priority"] != "medium" || hd["aggregate_id"] != nil {
		t.Fatal(hd)
	}
}

func TestProgressAndBranchDicts(t *testing.T) {
	p := NewProgressUpdated()
	p.OldPercentage, p.NewPercentage = 10, 35
	if p.ProgressDelta() != 25 || p.ToDict()["status"] != "in_progress" || p.ToDict()["metadata"] != nil {
		t.Fatal(p.ToDict())
	}
	b := NewBranchCreatedEvent()
	b.Timestamp = fixed
	if b.ToDict()["timestamp"] != "2026-09-30T21:14:50.709000" || b.ToDict()["status"] != "active" {
		t.Fatal(b.ToDict())
	}
}

func TestCreateDomainEvent(t *testing.T) {
	id, typ, uid := "a1", "Task", "u1"
	e := CreateDomainEvent(NewTaskDeletedEvent(), &id, &typ, &uid)
	if *e.AggregateID != "a1" || *e.AggregateType != "Task" || *e.UserID != "u1" {
		t.Fatal(e.BaseDomainEvent)
	}
}
