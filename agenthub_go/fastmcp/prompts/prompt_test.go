package prompts

import (
	"testing"

	"agenthub/fastmcp/utilities"
)

func TestPromptArgumentToDictOrder(t *testing.T) {
	desc := "the city"
	a := PromptArgument{Name: "city", Description: &desc, Required: true}
	d := a.ToDict()
	want := []string{"name", "description", "required"}
	if len(d.Keys()) != len(want) {
		t.Fatalf("keys = %v", d.Keys())
	}
	for i, k := range want {
		if d.Keys()[i] != k {
			t.Fatalf("key[%d] = %q, want %q", i, d.Keys()[i], k)
		}
	}
	if v, _ := d.Get("required"); v != true {
		t.Fatalf("required = %v", v)
	}
}

func TestMessageDefaults(t *testing.T) {
	m := Message("hi", nil)
	if m.Role != "user" {
		t.Fatalf("role = %q", m.Role)
	}
	tc, ok := m.Content.(TextContent)
	if !ok || tc.Type != "text" || tc.Text != "hi" {
		t.Fatalf("content = %#v", m.Content)
	}
	role := "assistant"
	m2 := Message("yo", &role)
	if m2.Role != "assistant" {
		t.Fatalf("role = %q", m2.Role)
	}
}

func TestFunctionPromptRender(t *testing.T) {
	fp := &FunctionPrompt{
		Prompt: NewPrompt(utilities.NewFastMCPComponent("greet", nil, nil, nil, nil),
			[]PromptArgument{{Name: "name", Required: true}}),
		Fn: func(args map[string]any) (any, error) {
			return "Hello " + args["name"].(string), nil
		},
	}
	msgs, err := fp.Render(map[string]any{"name": "Ada"})
	if err != nil {
		t.Fatal(err)
	}
	if len(msgs) != 1 || msgs[0].Role != "user" {
		t.Fatalf("msgs = %#v", msgs)
	}
	if msgs[0].Content.(TextContent).Text != "Hello Ada" {
		t.Fatalf("content = %#v", msgs[0].Content)
	}
	if _, err := fp.Render(map[string]any{}); err == nil {
		t.Fatal("expected missing-argument ValueError")
	} else if err.Error() != "Missing required arguments: {'name'}" {
		t.Fatalf("err = %q", err.Error())
	}
}

func TestPromptManagerDuplicate(t *testing.T) {
	m, err := NewPromptManager(nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if m.DuplicateBehavior != "warn" {
		t.Fatalf("duplicate = %q", m.DuplicateBehavior)
	}
	p := NewPrompt(utilities.NewFastMCPComponent("p", nil, nil, nil, nil), nil)
	m.AddPrompt(p)
	p2 := NewPrompt(utilities.NewFastMCPComponent("p", nil, nil, nil, nil), nil)
	if got := m.AddPrompt(p2); got != p2 {
		t.Fatal("warn should replace and return the new prompt")
	}
	bad := "bogus"
	if _, err := NewPromptManager(&bad, nil); err == nil {
		t.Fatal("expected ValueError for invalid duplicate_behavior")
	}
	ignore := "ignore"
	mi, _ := NewPromptManager(&ignore, nil)
	first := NewPrompt(utilities.NewFastMCPComponent("q", nil, nil, nil, nil), nil)
	mi.AddPrompt(first)
	second := NewPrompt(utilities.NewFastMCPComponent("q", nil, nil, nil, nil), nil)
	if got := mi.AddPrompt(second); got != first {
		t.Fatal("ignore should return existing")
	}
}
