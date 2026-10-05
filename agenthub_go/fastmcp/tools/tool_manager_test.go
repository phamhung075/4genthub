package tools

import (
	"context"
	"errors"
	"testing"

	"agenthub/fastmcp"
	"agenthub/fastmcp/task_management/domain/entities"
)

type fakeTool struct {
	key string
	err error
}

func (f *fakeTool) Key() string           { return f.key }
func (f *fakeTool) WithKey(k string) Tool { return &fakeTool{key: k, err: f.err} }
func (f *fakeTool) Run(ctx context.Context, args *entities.OrderedMap[any]) ([]any, error) {
	if f.err != nil {
		return nil, f.err
	}
	v, _ := args.Get("x")
	return []any{v}, nil
}

type fakeMounted struct {
	prefix string
	tools  []Tool
}

func (m fakeMounted) Prefix() string { return m.prefix }
func (m fakeMounted) ServerListTools(ctx context.Context) ([]Tool, error) {
	return m.tools, nil
}
func (m fakeMounted) ServerToolManagerListTools(ctx context.Context) ([]Tool, error) {
	return m.tools, nil
}
func (m fakeMounted) ServerCallTool(ctx context.Context, key string, arguments *entities.OrderedMap[any]) ([]any, error) {
	for _, t := range m.tools {
		if t.Key() == key {
			return t.Run(ctx, arguments)
		}
	}
	return nil, &fastmcp.NotFoundError{Msg: "nope"}
}

func TestToolManagerAddGetRemove(t *testing.T) {
	m, err := NewToolManager(nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if m.DuplicateBehavior != fastmcp.DuplicateBehaviorWarn {
		t.Errorf("default dup=%q", m.DuplicateBehavior)
	}
	if _, err := m.AddTool(&fakeTool{key: "a"}); err != nil {
		t.Fatal(err)
	}
	if !m.HasTool(context.Background(), "a") {
		t.Errorf("HasTool=false")
	}
	if err := m.RemoveTool("a"); err != nil {
		t.Fatal(err)
	}
	if m.HasTool(context.Background(), "a") {
		t.Errorf("tool not removed")
	}
	if err := m.RemoveTool("a"); err == nil {
		t.Errorf("expected NotFoundError")
	}
}

func TestToolManagerDuplicateError(t *testing.T) {
	b := fastmcp.DuplicateBehaviorError
	m, err := NewToolManager(&b, nil)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := m.AddTool(&fakeTool{key: "a"}); err != nil {
		t.Fatal(err)
	}
	if _, err := m.AddTool(&fakeTool{key: "a"}); err == nil {
		t.Fatalf("expected duplicate error")
	}
}

func TestToolManagerInvalidBehavior(t *testing.T) {
	b := fastmcp.DuplicateBehavior("bogus")
	if _, err := NewToolManager(&b, nil); err == nil {
		t.Fatalf("expected ValueError")
	}
}

func TestToolManagerMountedPrefixAndCall(t *testing.T) {
	m, err := NewToolManager(nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	m.Mount(fakeMounted{prefix: "srv", tools: []Tool{&fakeTool{key: "t"}}})
	tools := m.GetTools(context.Background())
	if !tools.Has("srv_t") {
		t.Fatalf("prefixed key missing: %v", tools.Keys())
	}
	args := entities.NewOrderedMap[any]()
	args.Set("x", 7)
	out, err := m.CallTool(context.Background(), "srv_t", args)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 1 || out[0] != 7 {
		t.Fatalf("out=%#v", out)
	}
	if _, err := m.CallTool(context.Background(), "missing", args); err == nil {
		t.Fatalf("expected NotFoundError")
	}
}

func TestToolManagerCallToolErrorHandling(t *testing.T) {
	m, err := NewToolManager(nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := m.AddTool(&fakeTool{key: "boom", err: errors.New("kaboom")}); err != nil {
		t.Fatal(err)
	}
	_, err = m.CallTool(context.Background(), "boom", entities.NewOrderedMap[any]())
	var te *fastmcp.ToolError
	if !errors.As(err, &te) {
		t.Fatalf("err=%v", err)
	}
}
