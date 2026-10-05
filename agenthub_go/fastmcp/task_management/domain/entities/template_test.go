package entities

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

func newTestTemplate(t *testing.T) *Template {
	id := value_objects.GenerateNewTemplateId()
	tt, cat, st, pr := value_objects.TemplateTypeTask, value_objects.TemplateCategoryGeneral, value_objects.TemplateStatusDraft, value_objects.TemplatePriorityMedium
	tpl, err := NewTemplate(Template{ID: &id, Name: "n", Description: "d", Content: "c", TemplateType: &tt, Category: &cat, Status: &st, Priority: &pr})
	if err != nil {
		t.Fatal(err)
	}
	return tpl
}

func TestTemplateBehaviour(t *testing.T) {
	tpl := newTestTemplate(t)
	if err := tpl.UpdateContent("  "); err == nil || err.Error() != "Template content cannot be empty" {
		t.Fatalf("got %v", err)
	}
	_ = tpl.UpdateContent("v2")
	if *tpl.Version != 2 || !tpl.IsCompatibleWithAgent("x") == false {
		t.Fatal("version/compat")
	}
	_ = tpl.AddCompatibleAgent("*")
	_ = tpl.AddCompatibleAgent("*")
	if len(tpl.CompatibleAgents) != 1 || !tpl.IsCompatibleWithAgent("anyone") {
		t.Fatal("agents")
	}
	_ = tpl.AddFilePattern("*.py")
	if !tpl.MatchesFilePatterns([]string{"a/b.py"}) || tpl.MatchesFilePatterns([]string{"a.go"}) {
		t.Fatal("patterns")
	}
	_ = tpl.Archive()
	if *tpl.IsActive || *tpl.Status != value_objects.TemplateStatusArchived {
		t.Fatal("archive")
	}
	d, err := tpl.ToDict()
	if err != nil {
		t.Fatal(err)
	}
	back, err := TemplateFromDict(d)
	if err != nil || back.Name != "n" || *back.Version != 2 || !back.CreatedAt.Equal(*tpl.CreatedAt) {
		t.Fatalf("roundtrip: %v", err)
	}
	if _, err := TemplateFromDict(map[string]any{}); err == nil || err.Error() != "'id'" {
		t.Fatalf("keyerror: %v", err)
	}
	tpl.Status = nil
	if _, err := tpl.ToDict(); err == nil {
		t.Fatal("expected AttributeError")
	}
}

func TestTemplateFromDictJSONNumbers(t *testing.T) {
	tpl := newTestTemplate(t)
	d, _ := tpl.ToDict()
	d["version"] = float64(3)
	back, err := TemplateFromDict(d)
	if err != nil || *back.Version != 3 {
		t.Fatalf("float64 version: %v", err)
	}
}
