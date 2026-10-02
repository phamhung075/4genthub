package services

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestRuleApplicationSummariesKeyOrder(t *testing.T) {
	rules := []*entities.RuleContent{
		{
			Metadata: &entities.RuleMetadata{
				Path:        "rules/a.md",
				Type:        value_objects.RuleTypeCore,
				Format:      value_objects.RuleFormatMd,
				Description: "desc",
				Tags:        []string{"x", "y"},
			},
		},
	}
	out := zpRuleApplicationSummaries(rules)
	if len(out) != 1 {
		t.Fatalf("len = %d", len(out))
	}
	entry := out[0].(*entities.OrderedMap[any])
	want := []string{"path", "type", "format", "description", "tags"}
	got := entry.Keys()
	if len(got) != len(want) {
		t.Fatalf("keys = %v", got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("key[%d] = %q want %q", i, got[i], want[i])
		}
	}
	if v, _ := entry.Get("path"); v.(string) != "rules/a.md" {
		t.Fatalf("path = %v", v)
	}
	if v, _ := entry.Get("type"); v.(string) != "core" {
		t.Fatalf("type = %v", v)
	}
	if v, _ := entry.Get("format"); v.(string) != "md" {
		t.Fatalf("format = %v", v)
	}
	if v, _ := entry.Get("description"); v.(string) != "desc" {
		t.Fatalf("description = %v", v)
	}
	tags, _ := entry.Get("tags")
	if len(tags.([]string)) != 2 || tags.([]string)[0] != "x" {
		t.Fatalf("tags = %v", tags)
	}
}
