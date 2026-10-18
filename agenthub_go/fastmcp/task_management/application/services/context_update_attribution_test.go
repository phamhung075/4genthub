package services

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// captureLedger keeps every entry the recorder writes, so a test can read the actor and the payload.
type captureLedger struct {
	events []entities.AppendTaskEvent
}

func (l *captureLedger) AppendInTx(ctx context.Context, in entities.AppendTaskEvent) (*entities.TaskEvent, error) {
	l.events = append(l.events, in)
	return &entities.TaskEvent{}, nil
}

func (l *captureLedger) StatusOf(ctx context.Context, taskID string) (string, error) { return "", nil }

func (l *captureLedger) NextProgressNumberInTx(ctx context.Context, taskID string) (int, error) {
	return 0, nil
}

// ledgerAppender is the service's seam over the REAL recorder: the context write goes through
// RecordContextUpdate, which is what settles the actor; Append stays for the progress note.
type ledgerAppender struct {
	recorder *TaskEventRecorder
}

func (a ledgerAppender) Append(ctx context.Context, in entities.AppendTaskEvent) (*entities.TaskEvent, error) {
	return &entities.TaskEvent{}, nil
}

func (a ledgerAppender) RecordContextUpdate(ctx context.Context, taskID, level string, version int,
	origin string, changes []entities.ContextChange, dropped int) (*entities.TaskEvent, error) {
	return a.recorder.RecordContextUpdate(ctx, taskID, level, version, origin, changes, dropped)
}

// The owner reads a task timeline and cannot tell WHO changed the context or WHAT changed. Both
// writers used to append with `ActorID: "context"`, throwing the seat away. This drives the unified
// service's writer through the REAL recorder: the entry is attributed to the seat the request named,
// and its payload names the changed leaf.
func TestTheUnifiedServiceWriterAttributesTheContextUpdateToTheSeat(t *testing.T) {
	const taskID = "33333333-3333-3333-3333-333333333333"
	const seat = "4genthub-min/go-dev"
	user := "user-1"

	repo := newZucsFakeRepo()
	repo.store[taskID] = zucsTaskContext(taskID, "todo")

	ledger := &captureLedger{}
	svc := NewUnifiedContextService(repo, repo, repo, repo, nil, nil, nil, nil, &user).
		WithEventAppender(ledgerAppender{recorder: NewTaskEventRecorder(ledger, user)})

	data := entities.NewOrderedMap[any]()
	data.Set("implementation_notes", map[string]any{"progress_updates": []any{"one new note"}})
	ctx := WithActor(context.Background(), SeatActor(seat))

	if _, err := svc.UpdateContext(ctx, "task", taskID, data, false, nil); err != nil {
		t.Fatalf("update_context: %v", err)
	}

	event := onlyContextUpdate(t, ledger)
	if event.ActorKind != entities.TaskEventActorSeat || event.ActorID != seat {
		t.Fatalf("actor = %q/%q, want seat/%q", event.ActorKind, event.ActorID, seat)
	}
	if event.Payload["origin"] != "unified_context_service.update" {
		t.Fatalf("origin = %v", event.Payload["origin"])
	}
	if event.Payload["level"] != "task" {
		t.Fatalf("level = %v", event.Payload["level"])
	}
	changes, ok := event.Payload["changes"].([]entities.ContextChange)
	if !ok || len(changes) == 0 {
		t.Fatalf("changes = %#v, want the changed leaf", event.Payload["changes"])
	}
	var paths []string
	for _, change := range changes {
		paths = append(paths, change.Path)
	}
	if !strings.Contains(strings.Join(paths, " "), "implementation_notes") {
		t.Fatalf("change paths = %v, want the implementation_notes leaf", paths)
	}
	if event.Payload["changes_truncated"] != 0 {
		t.Fatalf("changes_truncated = %v, want 0", event.Payload["changes_truncated"])
	}
}

func onlyContextUpdate(t *testing.T, ledger *captureLedger) entities.AppendTaskEvent {
	t.Helper()
	if len(ledger.events) != 1 {
		t.Fatalf("entries = %d, want exactly one: %+v", len(ledger.events), ledger.events)
	}
	event := ledger.events[0]
	if event.Kind != entities.TaskEventKindContextUpdated {
		t.Fatalf("kind = %q, want context_updated", event.Kind)
	}
	return event
}
