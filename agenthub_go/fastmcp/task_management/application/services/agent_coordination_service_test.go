package services

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type coordTasks struct{ task *entities.Task }

func (r coordTasks) Get(context.Context, string) (*entities.Task, error) { return r.task, nil }

type coordAgents struct{ byID map[string]*entities.Agent }

func (r coordAgents) Get(_ context.Context, id string) (*entities.Agent, error) {
	return r.byID[id], nil
}
func (r coordAgents) Save(context.Context, *entities.Agent) error { return nil }
func (r coordAgents) GetByProject(context.Context, string) ([]*entities.Agent, error) {
	return r.all(), nil
}
func (r coordAgents) GetAll(context.Context) ([]*entities.Agent, error) { return r.all(), nil }
func (r coordAgents) all() []*entities.Agent {
	var out []*entities.Agent
	for _, a := range r.byID {
		out = append(out, a)
	}
	return out
}

type coordBus struct{ published []events.Event }

func (b *coordBus) Publish(_ context.Context, e events.Event) error {
	b.published = append(b.published, e)
	return nil
}

const (
	idA = "11111111-1111-4111-8111-111111111111"
	idB = "22222222-2222-4222-8222-222222222222"
)

func coordAgent(t *testing.T, id string) *entities.Agent {
	t.Helper()
	aid, err := value_objects.NewAgentId(id)
	if err != nil {
		t.Fatal(err)
	}
	two := 2
	a, err := entities.NewAgent(entities.Agent{ID: &aid, Name: id, MaxConcurrentTasks: &two})
	if err != nil {
		t.Fatal(err)
	}
	return a
}

func TestCoordinationHandoffFlow(t *testing.T) {
	a, b := coordAgent(t, idA), coordAgent(t, idB)
	bus := &coordBus{}
	svc := NewAgentCoordinationService(coordTasks{&entities.Task{}},
		coordAgents{map[string]*entities.Agent{idA: a, idB: b}}, bus, nil, nil)
	ctx := context.Background()

	h, err := svc.RequestWorkHandoff(ctx, idA, idB, "t1", "sum", nil, nil, "")
	if err != nil {
		t.Fatal(err)
	}
	if err := svc.AcceptHandoff(ctx, h.HandoffID, idA, nil); err == nil || !strings.Contains(err.Error(), "is not the target") {
		t.Fatalf("wrong target must fail: %v", err)
	}
	if err := svc.AcceptHandoff(ctx, h.HandoffID, idB, nil); err != nil {
		t.Fatal(err)
	}
	if _, ok := b.ActiveTasks["t1"]; !ok {
		t.Fatal("task not reassigned to agent_b")
	}
	if got := len(bus.published); got != 3 { // requested, assigned, accepted
		t.Fatalf("published %d events", got)
	}
	if err := svc.RejectHandoff(ctx, h.HandoffID, idB, "no"); err == nil || !strings.Contains(err.Error(), "Cannot reject handoff in status HandoffStatus.ACCEPTED") {
		t.Fatalf("reject after accept: %v", err)
	}
	w, err := svc.GetAgentWorkload(ctx, idB)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := w.Get("current_tasks"); v != 1 {
		t.Fatalf("current_tasks = %v", v)
	}
}

func TestCoordinationMissingBusIsAttributeError(t *testing.T) {
	a := coordAgent(t, idA)
	svc := NewAgentCoordinationService(coordTasks{&entities.Task{}}, coordAgents{map[string]*entities.Agent{idA: a}}, nil, nil, nil)
	_, err := svc.AssignAgentToTask(context.Background(), "t1", idA, "dev", "lead", nil, nil, nil)
	if err == nil || !strings.Contains(err.Error(), "AttributeError") {
		t.Fatalf("got %v", err)
	}
}
