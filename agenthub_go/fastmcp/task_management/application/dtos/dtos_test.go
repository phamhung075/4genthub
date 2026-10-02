package dtos

import (
	"reflect"
	"testing"
	"time"
)

func TestCreateTaskDTOToDict(t *testing.T) {
	m := (CreateTaskDTO{Title: "t", Description: "d"}).ToDict()
	want := []string{"title", "description", "git_branch_id", "status", "priority", "assignees", "labels", "due_date", "estimated_effort", "details"}
	if !reflect.DeepEqual(m.Keys(), want) {
		t.Fatalf("keys = %v", m.Keys())
	}
	if v, _ := m.Get("assignees"); !reflect.DeepEqual(v, []string{}) {
		t.Fatalf("assignees = %#v", v)
	}
	if v, _ := m.Get("details"); v != "" {
		t.Fatalf("details = %v", v)
	}
}

func TestUpdateTaskDTOToDict(t *testing.T) {
	m := (UpdateTaskDTO{TaskID: "x", Assignees: []string{}}).ToDict()
	if !reflect.DeepEqual(m.Keys(), []string{"task_id", "assignees"}) {
		t.Fatalf("keys = %v", m.Keys())
	}
}

func TestTaskResponseDTOToDict(t *testing.T) {
	m := (TaskResponseDTO{Success: true}).ToDict()
	if !reflect.DeepEqual(m.Keys(), []string{"success"}) {
		t.Fatalf("keys = %v", m.Keys())
	}
}

func TestCompleteTaskDTOToDict(t *testing.T) {
	m := (CompleteTaskDTO{TaskID: "t", CompletionSummary: "c"}).ToDict()
	if !reflect.DeepEqual(m.Keys(), []string{"task_id", "completion_summary"}) {
		t.Fatalf("keys = %v", m.Keys())
	}
	ts := time.Date(2025, 1, 2, 3, 4, 5, 0, time.UTC)
	m = (CompleteTaskDTO{TaskID: "t", CompletionSummary: "c", ContextUpdatedAt: &ts}).ToDict()
	if v, _ := m.Get("context_updated_at"); v != "2025-01-02T03:04:05+00:00" {
		t.Fatalf("context_updated_at = %v", v)
	}
}

func TestTemplateDTOdefaults(t *testing.T) {
	tc := NewTemplateCreateDTO(TemplateCreateDTO{Name: "n"})
	if tc.Priority != "medium" || !reflect.DeepEqual(tc.CompatibleAgents, []string{"*"}) || tc.FilePatterns == nil || tc.Variables == nil || tc.Metadata == nil {
		t.Fatalf("template create = %+v", tc)
	}
	if s := NewTemplateSearchDTO(TemplateSearchDTO{Query: "q"}); s.Limit != 50 || s.Offset != 0 {
		t.Fatalf("search = %+v", s)
	}
	if c := NewTemplateCacheDTO(TemplateCacheDTO{}); c.Operation != "get" {
		t.Fatalf("cache = %+v", c)
	}
	u := NewTemplateUsageDTO(TemplateUsageDTO{TemplateID: "t"})
	if u.VariablesUsed == nil {
		t.Fatalf("usage variables_used nil")
	}
	a := NewTemplateAnalyticsDTO(TemplateAnalyticsDTO{})
	if a.UsageByAgent == nil || a.UsageByTask == nil || a.MostUsedVariables == nil || a.UsageOverTime == nil {
		t.Fatalf("analytics = %+v", a)
	}
	v := NewTemplateValidationDTO(TemplateValidationDTO{})
	if v.Errors == nil || v.Warnings == nil {
		t.Fatalf("validation = %+v", v)
	}
}
