package adapters

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

type fakeProjectService struct{ calls []string }

func (f *fakeProjectService) rec(args ...string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for _, a := range args {
		f.calls = append(f.calls, a)
	}
	return m
}
func (f *fakeProjectService) CreateProject(p, n, d string) *entities.OrderedMap[any] {
	return f.rec(p, n, d)
}
func (f *fakeProjectService) RegisterAgent(p, a, n, c string) *entities.OrderedMap[any] {
	return f.rec(p, a, n, c)
}
func (f *fakeProjectService) GetProject(p string) *entities.OrderedMap[any] { return f.rec(p) }
func (f *fakeProjectService) AssignAgentToTree(p, a, g string) *entities.OrderedMap[any] {
	return f.rec(p, a, g)
}
func (f *fakeProjectService) ListProjects() *entities.OrderedMap[any] { return f.rec() }
func (f *fakeProjectService) ProjectsFile() any                       { return "pf" }
func (f *fakeProjectService) BrainDir() any                           { return "bd" }
func (f *fakeProjectService) AgentConverter() any                     { return nil }
func (f *fakeProjectService) Orchestrator() any                       { return nil }
func (f *fakeProjectService) Projects() any                           { return map[string]any{} }

func TestSimpleMultiAgentAdapterDefaultsAndDelegation(t *testing.T) {
	svc := &fakeProjectService{}
	a, err := NewSimpleMultiAgentAdapter(nil, svc)
	if err != nil || a.ProjectsFile != "pf" || a.BrainDir != "bd" {
		t.Fatalf("ctor: %v %+v", err, a)
	}
	a.CreateProject("p1", "Name", "")
	a.RegisterAgent("p1", "my_agent", "N", "")
	got := svc.calls
	if got[2] != "Project: Name" || got[6] != "@my-agent-agent" {
		t.Fatalf("defaults wrong: %v", got)
	}
}

func TestSimpleMultiAgentAdapterWithoutServiceRaisesAttributeError(t *testing.T) {
	_, err := NewSimpleMultiAgentAdapter(nil, nil)
	if _, ok := err.(*AttributeError); !ok {
		t.Fatalf("want AttributeError, got %v", err)
	}
}
