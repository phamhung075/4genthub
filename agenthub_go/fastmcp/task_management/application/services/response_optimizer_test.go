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

func TestResponseOptimizer_MergeMetadataWithholdsAnUnpersistedHandle(t *testing.T) {
	// Measured vectors, not one invented case: four refused add_insight calls missing a required
	// context_id, a create refused for an invalid assignee, and a create refused for an over-length
	// description. They differ in action name, in validation class (a length bound versus a missing
	// required field) and in operation_id, which is regenerated per call. A test covering only one
	// of them passes while the other five still ship a handle.
	vectors := []struct {
		name      string
		operation string
		id        string
		persisted bool
	}{
		{"refused add_insight, missing context_id (ec5eeacf)", "add_insight", "ec5eeacf-cc93-4664-9669-74fa4891845e", false},
		{"refused add_insight, missing context_id (362855c4)", "add_insight", "362855c4-0d5e-4e8f-9d1a-6b6f4a6dc3ee", false},
		{"refused add_insight, missing context_id (bdfb07f0)", "add_insight", "bdfb07f0-6c8a-4f2f-9a1f-4b0b2b1b6a11", false},
		{"refused add_insight, missing context_id (b3f291c5)", "add_insight", "b3f291c5-2f1e-4c7d-8a3b-5d9c0e7f4a22", false},
		{"refused create, invalid assignee (1b9d74f2)", "create", "1b9d74f2-828c-438e-8daa-2a6eb9f09d6a", false},
		{"refused create, description over the length bound", "create", "6f1c9d2e-3a4b-4c5d-8e9f-0a1b2c3d4e5f", false},
	}

	r := NewResponseOptimizer()
	for _, v := range vectors {
		t.Run(v.name, func(t *testing.T) {
			resp := zpRespOM(
				"success", false,
				"operation_id", v.id,
				"operation", v.operation,
				"timestamp", "2026-10-08T16:40:48.997744+00:00",
				"confirmation", zpRespOM("data_persisted", v.persisted),
			)
			metaAny, _ := r.MergeMetadata(resp).Get("meta")
			meta, _ := metaAny.(*entities.OrderedMap[any])
			if meta == nil {
				t.Fatalf("meta should survive to carry the persisted flag")
			}
			// THE ASSERTION: whenever the outcome is not persisted, meta.id is absent or null.
			if id, has := meta.Get("id"); has && id != nil {
				t.Errorf("refused call exposed a handle: %#v", id)
			}
			if persisted, ok := meta.Get("persisted"); !ok || persisted != false {
				t.Errorf("persisted must still be reported as false: %v %#v", ok, meta)
			}
		})
	}

	// The same envelope on a persisted call keeps its id: that is the handle callers rely on,
	// so withholding it unconditionally would be a different defect, not this fix.
	ok := r.MergeMetadata(zpRespOM(
		"success", true,
		"operation_id", "1b9d74f2-828c-438e-8daa-2a6eb9f09d6a",
		"operation", "create",
		"confirmation", zpRespOM("data_persisted", true),
	))
	metaOKAny, _ := ok.Get("meta")
	metaOK, _ := metaOKAny.(*entities.OrderedMap[any])
	if v, has := metaOK.Get("id"); !has || v == nil {
		t.Fatalf("persisted call lost its handle: %#v", metaOK)
	}
}
