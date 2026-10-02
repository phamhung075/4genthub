package services

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func zpRespOM(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}

func TestResponseOptimizer_AutoSelectProfile(t *testing.T) {
	r := NewResponseOptimizer()
	if got := r.AutoSelectProfile(zpRespOM("operation", "list_tasks"), nil); got != ResponseProfileMinimal {
		t.Fatalf("high-frequency op: got %q", got)
	}
	detailed := zpRespOM("operation", "create", "data", zpRespOM("assignees", []any{"coding-agent"}))
	if got := r.AutoSelectProfile(detailed, nil); got != ResponseProfileDetailed {
		t.Fatalf("ai indicator: got %q", got)
	}
	ctx := zpRespOM("profile", "debug")
	if got := r.AutoSelectProfile(zpRespOM("operation", "x"), ctx); got != ResponseProfileDebug {
		t.Fatalf("explicit profile: got %q", got)
	}
	ctx = zpRespOM("debug", true)
	if got := r.AutoSelectProfile(zpRespOM("operation", "x"), ctx); got != ResponseProfileDebug {
		t.Fatalf("debug flag: got %q", got)
	}
	if got := r.AutoSelectProfile(zpRespOM("operation", "create"), nil); got != ResponseProfileStandard {
		t.Fatalf("default: got %q", got)
	}
}

func TestResponseOptimizer_RemoveDuplicates(t *testing.T) {
	r := NewResponseOptimizer()
	details := zpRespOM("operation", "create", "operation_id", "op1", "timestamp", "t1")
	resp := zpRespOM(
		"operation", "create",
		"operation_id", "op1",
		"timestamp", "t1",
		"confirmation", zpRespOM("operation_details", details),
		"status", "success",
		"success", true,
	)
	got := r.RemoveDuplicates(resp)
	if got.Has("status") {
		t.Fatal("status should be removed when it matches success")
	}
	conf := zpRespGetMap(got, "confirmation")
	if conf == nil || conf.Has("operation_details") {
		t.Fatalf("empty operation_details should be removed, got %v", conf)
	}
}

func TestResponseOptimizer_RemoveNulls(t *testing.T) {
	r := NewResponseOptimizer()
	got := r.RemoveNulls(zpRespOM(
		"keep", "v",
		"empty", "",
		"nul", nil,
		"list", []any{},
		"dict", entities.NewOrderedMap[any](),
		"zero", 0,
		"false", false,
		"data", nil,
	)).(*entities.OrderedMap[any])
	wantKeys := []string{"keep", "zero", "false", "data"}
	if got.Len() != len(wantKeys) {
		t.Fatalf("keys = %v", got.Keys())
	}
	for i, k := range wantKeys {
		if got.Keys()[i] != k {
			t.Fatalf("keys = %v, want %v", got.Keys(), wantKeys)
		}
	}
	if data, _ := got.Get("data"); data.(*entities.OrderedMap[any]).Len() != 0 {
		t.Fatal("essential data field must be preserved as empty map")
	}
}

func TestResponseOptimizer_ApplyProfileMinimal(t *testing.T) {
	r := NewResponseOptimizer()
	got := r.ApplyProfile(zpRespOM(
		"success", true, "operation", "x", "data", zpRespOM("a", 1), "extra", 1,
	), ResponseProfileMinimal)
	if got.Len() != 3 || got.Keys()[0] != "success" || got.Keys()[1] != "operation" || got.Keys()[2] != "data" {
		t.Fatalf("minimal keys = %v", got.Keys())
	}
}

func TestResponseOptimizer_GetMetrics(t *testing.T) {
	r := NewResponseOptimizer()
	r.OptimizeResponse(zpRespOM("success", true, "operation", "create"), nil, nil)
	got := r.GetMetrics()
	want := []string{
		"total_responses_optimized", "total_bytes_saved", "average_compression_ratio",
		"target_compression", "target_achieved", "profile_usage", "most_used_profile",
	}
	for i, k := range want {
		if got.Keys()[i] != k {
			t.Fatalf("metrics keys = %v, want %v", got.Keys(), want)
		}
	}
	if v, _ := got.Get("total_responses_optimized"); v.(int) != 1 {
		t.Fatalf("total_responses_optimized = %v", v)
	}
	if v, _ := got.Get("most_used_profile"); v != "standard" {
		t.Fatalf("most_used_profile = %v", v)
	}
}

func TestResponseOptimizer_AutoSelectProfileNonDictDataPanics(t *testing.T) {
	r := NewResponseOptimizer()
	defer func() {
		if recover() == nil {
			t.Fatal("expected panic for non-dict data (Python AttributeError)")
		}
	}()
	r.AutoSelectProfile(zpRespOM("operation", "create", "data", "text"), nil)
}

func TestResponseOptimizer_SimplifyGuidanceTips(t *testing.T) {
	r := NewResponseOptimizer()
	h := r.simplifyWorkflowGuidance(zpRespOM("optional_actions", "héllo"))
	if got, _ := h.Get("tips"); got != "hé" {
		t.Fatalf("string tips: got %v", got)
	}
	h = r.simplifyWorkflowGuidance(zpRespOM("optional_actions", []any{"a", "b", "c"}))
	if got, _ := h.Get("tips"); len(got.([]any)) != 2 {
		t.Fatalf("list tips: got %v", got)
	}
}

func TestResponseOptimizer_FlattenExplicitNilPartialFailures(t *testing.T) {
	r := NewResponseOptimizer()
	resp := zpRespOM("confirmation", zpRespOM("data_persisted", true, "partial_failures", nil))
	out := r.FlattenStructure(resp)
	if !out.Has("confirmation") {
		t.Fatal("explicit None partial_failures must not flatten (None != [])")
	}
	resp = zpRespOM("confirmation", zpRespOM("data_persisted", true, "partial_failures", []any{}))
	if r.FlattenStructure(resp).Has("confirmation") {
		t.Fatal("empty list should flatten")
	}
}
