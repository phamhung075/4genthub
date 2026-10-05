package common

import (
	"reflect"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestTaskProgressInfoToDict(t *testing.T) {
	p := TaskProgressInfo{CurrentPhaseIndex: 1, TotalPhases: 2, CompletionPercentage: 3.5}
	m := p.ToDict()
	wantKeys := []string{"current_phase_index", "total_phases", "completion_percentage", "estimated_completion"}
	if !reflect.DeepEqual(m.Keys(), wantKeys) {
		t.Fatalf("keys = %v", m.Keys())
	}
	if v, _ := m.Get("current_phase_index"); v != 1 {
		t.Fatalf("current_phase_index = %v", v)
	}
	if v, _ := m.Get("completion_percentage"); v != 3.5 {
		t.Fatalf("completion_percentage = %v", v)
	}
	if v, _ := m.Get("estimated_completion"); v != nil {
		t.Fatalf("estimated_completion = %v", v)
	}
}

func TestTaskContextToDict(t *testing.T) {
	created := time.Date(2025, 1, 2, 3, 4, 5, 0, time.UTC)
	updated := time.Date(2025, 1, 2, 3, 4, 6, 0, time.UTC)
	c := TaskContext{
		ID: "i", Title: "t", Description: "d", Requirements: []string{"r"},
		CurrentPhase: "coding", AssignedRoles: []string{"a"}, PrimaryRole: "p",
		ContextData: nil, CreatedAt: created, UpdatedAt: updated,
		Progress: TaskProgressInfo{CurrentPhaseIndex: 1, TotalPhases: 2, CompletionPercentage: 3.0},
	}
	m := c.ToDict()
	wantKeys := []string{"id", "title", "description", "requirements", "current_phase", "assigned_roles",
		"primary_role", "context_data", "created_at", "updated_at", "progress"}
	if !reflect.DeepEqual(m.Keys(), wantKeys) {
		t.Fatalf("keys = %v", m.Keys())
	}
	if v, _ := m.Get("created_at"); v != "2025-01-02T03:04:05+00:00" {
		t.Fatalf("created_at = %v", v)
	}
	if v, _ := m.Get("updated_at"); v != "2025-01-02T03:04:06+00:00" {
		t.Fatalf("updated_at = %v", v)
	}
	if v, _ := m.Get("context_data"); v == nil {
		t.Fatalf("context_data should default to empty dict")
	}
	progress, _ := m.Get("progress")
	pm, ok := progress.(*entities.OrderedMap[any])
	if !ok || pm.Len() != 4 {
		t.Fatalf("progress = %#v", progress)
	}
}

func TestValidationResult(t *testing.T) {
	r := &ValidationResult{IsValid: true}
	r.AddWarning("w")
	if !r.IsValid || len(r.Warnings) != 1 || r.Warnings[0] != "w" {
		t.Fatalf("after warning = %+v", r)
	}
	r.AddError("e")
	if r.IsValid || len(r.Errors) != 1 || r.Errors[0] != "e" {
		t.Fatalf("after error = %+v", r)
	}
}
