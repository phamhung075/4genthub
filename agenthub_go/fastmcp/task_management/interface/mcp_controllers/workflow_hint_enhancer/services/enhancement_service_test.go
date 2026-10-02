package services

import (
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestEnhanceResponseKeyOrder(t *testing.T) {
	resp := entities.NewOrderedMap[any]()
	resp.Set("success", true)

	out := NewEnhancementService().EnhanceResponse(resp, nil)
	if strings.Join(out.Keys(), ",") != "success,workflow_hints" {
		t.Fatalf("response keys: %v", out.Keys())
	}
	hints := out.GetAny("workflow_hints").(*entities.OrderedMap[any])
	if strings.Join(hints.Keys(), ",") != "enhanced_at,enhancement_version,features_applied" {
		t.Fatalf("hint keys: %v", hints.Keys())
	}
	if hints.GetAny("enhancement_version") != "2.0" {
		t.Fatalf("version: %v", hints.GetAny("enhancement_version"))
	}
	features := hints.GetAny("features_applied").([]any)
	if len(features) != 3 || features[1] != "temporal_awareness" {
		t.Fatalf("features: %v", features)
	}
}

func TestAddTaskHintsWithoutData(t *testing.T) {
	resp := entities.NewOrderedMap[any]()
	resp.Set("success", true)

	out := NewEnhancementService().AddTaskHints(resp, nil)
	hints := out.GetAny("workflow_hints").(*entities.OrderedMap[any])
	guidance := hints.GetAny("task_guidance").(*entities.OrderedMap[any])
	if strings.Join(guidance.Keys(), ",") != "next_steps,best_practices" {
		t.Fatalf("guidance keys: %v", guidance.Keys())
	}
	steps := guidance.GetAny("next_steps").([]any)
	if steps[0] != "Review task requirements" {
		t.Fatalf("steps: %v", steps)
	}
}

func TestAnalyzeTaskStateAndComplexity(t *testing.T) {
	s := NewEnhancementService()
	task := entities.NewOrderedMap[any]()
	task.Set("status", "PENDING")
	task.Set("priority", "HIGH")
	task.Set("description", strings.Repeat("x", 101))
	task.Set("dependencies", []any{"a", "b", "c", "d"})
	task.Set("assignees", []any{"u1", "u2"})

	state := s.analyzeTaskState(task)
	if state.GetAny("status") != "pending" || state.GetAny("priority") != "high" {
		t.Fatalf("state: %v", state)
	}
	if state.GetAny("has_description") != true || state.GetAny("has_assignees") != true {
		t.Fatalf("presence: %v", state)
	}
	if state.GetAny("complexity_level") != "complex" {
		t.Fatalf("complexity: %v", state.GetAny("complexity_level"))
	}

	actions := s.suggestNextActions(state, task)
	item := actions[0].(*entities.OrderedMap[any])
	if strings.Join(item.Keys(), ",") != "action,description,priority" || item.GetAny("action") != "start_work" {
		t.Fatalf("action: %v", item.Keys())
	}
}

func TestAnalyzeErrorType(t *testing.T) {
	s := NewEnhancementService()
	resp := entities.NewOrderedMap[any]()
	resp.Set("error", "Validation failed for field")
	if got := s.analyzeErrorType(resp); got != "validation_error" {
		t.Fatalf("type: %v", got)
	}
	fixes := s.suggestErrorFixes(resp, "create")
	if len(fixes) != 3 || fixes[0] != "Check required parameters" {
		t.Fatalf("fixes: %v", fixes)
	}
}
