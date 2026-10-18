package use_cases_test

import (
	"context"
	"strings"
	"testing"

	ctxdto "agenthub/fastmcp/task_management/application/dtos/context"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// captureLedger keeps every entry the real recorder writes.
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

// ledgerContextRepository serves the three calls the use case makes.
type ledgerContextRepository struct {
	repositories.ContextRepository
	current *entities.TaskContext
}

func (r *ledgerContextRepository) ContextExists(ctx context.Context, taskID string) (bool, error) {
	return r.current != nil, nil
}

func (r *ledgerContextRepository) GetContext(ctx context.Context, taskID string) (*entities.TaskContext, error) {
	return r.current, nil
}

func (r *ledgerContextRepository) UpdateContext(ctx context.Context, c *entities.TaskContext) (map[string]any, error) {
	r.current = c
	return c.ToDict(false), nil
}

// The manage_context writer used to append with `ActorID: "context"`, throwing away the seat the
// request named. Through the REAL recorder, the entry is attributed to that seat and its payload
// names the changed leaf - the same contract the unified service's writer keeps.
func TestTheManageContextWriterAttributesTheContextUpdateToTheSeat(t *testing.T) {
	const taskID = "55555555-5555-5555-5555-555555555555"
	const seat = "4genthub-min/go-dev"
	const user = "user-1"

	metadata, err := entities.NewContextMetadata(entities.ContextMetadata{TaskID: taskID})
	if err != nil {
		t.Fatalf("metadata: %v", err)
	}
	repo := &ledgerContextRepository{current: entities.NewTaskContext(metadata, entities.ContextObjective{Title: "t"})}

	ledger := &captureLedger{}
	uc := use_cases.NewUpdateContextUseCase(repo).
		WithEvents(services.NewTaskEventRecorder(ledger, user))

	data := entities.NewOrderedMap[any]()
	data.Set("progress", map[string]any{"completion_percentage": 40})
	ctx := services.WithActor(context.Background(), services.SeatActor(seat))

	response, err := uc.Execute(ctx, &ctxdto.UpdateContextRequest{TaskID: taskID, Data: data})
	if err != nil {
		t.Fatalf("execute: %v", err)
	}
	if !response.Success {
		t.Fatalf("response = %#v", response)
	}

	if len(ledger.events) != 1 {
		t.Fatalf("entries = %d, want exactly one: %+v", len(ledger.events), ledger.events)
	}
	event := ledger.events[0]
	if event.Kind != entities.TaskEventKindContextUpdated {
		t.Fatalf("kind = %q, want context_updated", event.Kind)
	}
	if event.ActorKind != entities.TaskEventActorSeat || event.ActorID != seat {
		t.Fatalf("actor = %q/%q, want seat/%q", event.ActorKind, event.ActorID, seat)
	}
	if event.Payload["origin"] != "manage_context.update" || event.Payload["level"] != "task" {
		t.Fatalf("payload = %#v", event.Payload)
	}
	changes, ok := event.Payload["changes"].([]entities.ContextChange)
	if !ok || len(changes) == 0 {
		t.Fatalf("changes = %#v, want the changed leaf", event.Payload["changes"])
	}
	var paths []string
	for _, change := range changes {
		paths = append(paths, change.Path)
	}
	if !strings.Contains(strings.Join(paths, " "), "progress.completion_percentage") {
		t.Fatalf("change paths = %v, want progress.completion_percentage", paths)
	}
}
