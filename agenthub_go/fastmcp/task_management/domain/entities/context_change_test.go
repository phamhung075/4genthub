package entities

import (
	"encoding/json"
	"fmt"
	"strings"
	"testing"
)

// The change set names each leaf, compares arrays as a whole, and caps one value by its bytes.
func TestContextChangesNamesEachLeafAndCapsOneValue(t *testing.T) {
	before := OrderedFromMap(map[string]any{
		"status": "todo",
		"implementation_notes": map[string]any{
			"progress": "one",
			"removed":  "gone",
		},
		"labels": []any{"a", "b"},
	})
	after := OrderedFromMap(map[string]any{
		"status": "done",
		"implementation_notes": map[string]any{
			"progress": "one",
			"added":    "here",
		},
		"labels":  []any{"a", "b", "c"},
		"new_key": "v",
	})

	changes, dropped := ContextChanges(before, after)
	if dropped != 0 {
		t.Fatalf("dropped = %d, want 0", dropped)
	}
	got := map[string]ContextChange{}
	for _, change := range changes {
		got[change.Path] = change
	}
	want := []struct {
		path  string
		op    string
		old   any
		new   any
	}{
		{path: "implementation_notes.added", op: "add", new: "here"},
		{path: "implementation_notes.removed", op: "remove", old: "gone"},
		{path: "labels", op: "set"},
		{path: "new_key", op: "add", new: "v"},
		{path: "status", op: "set", old: "todo", new: "done"},
	}
	if len(changes) != len(want) {
		t.Fatalf("changes = %+v, want %d entries", changes, len(want))
	}
	for i, expected := range want {
		change := changes[i]
		if change.Path != expected.path || change.Op != expected.op {
			t.Fatalf("change %d = %+v, want path %q op %q", i, change, expected.path, expected.op)
		}
		if expected.old != nil && change.Old != expected.old {
			t.Fatalf("%s old = %v, want %v", expected.path, change.Old, expected.old)
		}
		if expected.new != nil && change.New != expected.new {
			t.Fatalf("%s new = %v, want %v", expected.path, change.New, expected.new)
		}
	}

	// An array is compared as a whole: the labels change carries both arrays, element-diffed never.
	labels := got["labels"]
	encoded, _ := json.Marshal(labels.Old)
	if string(encoded) != `["a","b"]` {
		t.Fatalf("labels old = %s, want the whole array", encoded)
	}

	// A value over the cap keeps its hash and byte count, never the bytes.
	long := strings.Repeat("x", MaxContextChangeValue+10)
	big, _ := ContextChanges(OrderedFromMap(map[string]any{"notes": "small"}), OrderedFromMap(map[string]any{"notes": long}))
	if len(big) != 1 {
		t.Fatalf("changes = %+v, want one", big)
	}
	marker, ok := big[0].New.(map[string]any)
	if !ok || marker["truncated"] != true {
		t.Fatalf("an over-cap value = %#v, want the truncation marker", big[0].New)
	}
	if marker["bytes"].(int) <= MaxContextChangeValue {
		t.Fatalf("marker bytes = %v, want the encoded length", marker["bytes"])
	}
	if hash, _ := marker["sha256"].(string); len(hash) != 64 {
		t.Fatalf("marker sha256 = %v, want 64 hex", marker["sha256"])
	}
}

// A change set longer than the payload cap keeps the first entries in canonical order and reports the
// count it left out.
func TestContextChangesDropsAChangeSetOverThePayloadCap(t *testing.T) {
	before := OrderedFromMap(map[string]any{})
	after := OrderedFromMap(map[string]any{})
	for i := range 300 {
		after.Set(fmt.Sprintf("key_%03d", i), strings.Repeat("v", 80))
	}
	changes, dropped := ContextChanges(before, after)
	if dropped == 0 {
		t.Fatalf("dropped = 0, want the entries past the cap")
	}
	if len(changes)+dropped != after.Len() {
		t.Fatalf("kept %d + dropped %d != %d changes", len(changes), dropped, after.Len())
	}
	encoded, err := json.Marshal(changes)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	if len(encoded) > MaxContextChangesPayload {
		t.Fatalf("kept set is %d bytes, want <= %d", len(encoded), MaxContextChangesPayload)
	}
	for i := 1; i < len(changes); i++ {
		if changes[i-1].Path > changes[i].Path {
			t.Fatalf("the kept set is not in canonical order at %d: %q > %q", i, changes[i-1].Path, changes[i].Path)
		}
	}
}

// The payload the two writers hand the ledger carries the level, version, origin and the bounded set.
func TestContextUpdatePayloadCarriesTheChangeSetAndTheTruncationCount(t *testing.T) {
	payload := ContextUpdatePayload("task", "task-1", 4, "manage_context.update",
		[]ContextChange{{Path: "status", Op: "set", Old: "todo", New: "done"}}, 2)
	for key, want := range map[string]any{
		"level":             "task",
		"id":                "task-1",
		"version":           4,
		"origin":            "manage_context.update",
		"changes_truncated": 2,
	} {
		if payload[key] != want {
			t.Fatalf("%s = %v, want %v", key, payload[key], want)
		}
	}
	if changes, ok := payload["changes"].([]ContextChange); !ok || len(changes) != 1 || changes[0].Path != "status" {
		t.Fatalf("changes = %#v", payload["changes"])
	}
	if changes, ok := ContextUpdatePayload("task", "id", 0, "origin", nil, 0)["changes"].([]ContextChange); !ok || changes == nil {
		t.Fatalf("a nil set must serialize as [], got %#v", changes)
	}
}
