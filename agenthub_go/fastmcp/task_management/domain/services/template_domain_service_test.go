package services

import (
	"reflect"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func testTemplate(t *testing.T) *entities.Template {
	tt, cat := value_objects.TemplateTypeTask, value_objects.TemplateCategoryDevelopment
	st, pr := value_objects.TemplateStatusActive, value_objects.TemplatePriorityHigh
	id := value_objects.GenerateNewTemplateId()
	tpl, err := entities.NewTemplate(entities.Template{ID: &id, Name: "n", Description: "d", Content: "c {a}",
		TemplateType: &tt, Category: &cat, Status: &st, Priority: &pr,
		CompatibleAgents: []string{"coding-agent"}, FilePatterns: []string{"*.py"},
		Variables: []string{"a", "b c", "", "x_y"}, Metadata: map[string]any{"k": 1}})
	if err != nil {
		t.Fatal(err)
	}
	return tpl
}

// Expected values come from running the Python TemplateDomainService.
func TestTemplateDomainServiceAgainstPython(t *testing.T) {
	s := &TemplateDomainService{}
	tpl := testTemplate(t)
	want := []string{"Variable 'b c' contains invalid characters", "Variable name cannot be empty", "Variable '' contains invalid characters"}
	if got := s.ValidateTemplate(tpl); !reflect.DeepEqual(got, want) {
		t.Fatalf("%v", got)
	}
	ctx := map[string]any{"task_type": "tas", "category": "development", "k": 1.0}
	stats := map[string]any{"usage_count": 60, "success_rate": 0.5, "avg_generation_time": 200}
	score, err := s.CalculateTemplateScore(tpl, ctx, "coding-agent", []string{"x.py"}, stats)
	if err != nil || score != 155.0 {
		t.Fatal(score, err)
	}
	reason, _ := s.GetSuggestionReason(tpl, ctx, score)
	if reason != "High priority template; Good match for tas tasks; Perfect fit for development category; Highly recommended based on usage patterns" {
		t.Fatal(reason)
	}
	req := entities.TemplateRenderRequest{Variables: map[string]any{"a": 1}, CacheStrategy: "default"}
	if s.GetCacheTTL(tpl, req) != 7200 {
		t.Fatal("ttl")
	}
	m := s.MergeTemplateVariables([]string{"a", "b"}, map[string]any{"z": 1, "a": 2}, map[string]any{"b": 3, "q": 4})
	if !reflect.DeepEqual(m.Keys(), []string{"a", "b", "z"}) {
		t.Fatal(m.Keys())
	}
	if v, _ := m.Get("a"); v != 2 {
		t.Fatal("precedence")
	}
	if errs := s.ValidateRenderRequest(entities.TemplateRenderRequest{CacheStrategy: "x"}); len(errs) != 2 {
		t.Fatal(errs)
	}
	tpl.TemplateType = nil
	if _, err := s.CalculateTemplateScore(tpl, ctx, "coding-agent", nil, nil); err == nil {
		t.Fatal("nil type must error")
	}
}
