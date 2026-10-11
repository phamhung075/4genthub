package entities

import (
	"reflect"
	"sort"
	"strings"
	"testing"
)

func keysOf(m map[string]any) []string {
	k := make([]string, 0, len(m))
	for key := range m {
		k = append(k, key)
	}
	sort.Strings(k)
	return k
}

// Expected values below were produced by running the same calls on the Python entities.
func TestTaskContextToDictAndFromDict(t *testing.T) {
	c, err := ContextSchema{}.CreateEmptyContext("t1", "Title", EmptyContextOptions{Assignees: []string{"a"}})
	if err != nil {
		t.Fatal(err)
	}
	d := c.ToDict(false)
	wantKeys := []string{"custom_sections", "dependencies", "metadata", "notes", "objective", "progress", "progress_by_type",
		"progress_milestones", "progress_timeline", "requirements", "subtasks", "task_id", "technical"}
	if !reflect.DeepEqual(keysOf(d), wantKeys) {
		t.Fatalf("keys %v", keysOf(d))
	}
	md := d["metadata"].(map[string]any)
	if !reflect.DeepEqual(keysOf(md), []string{"_domain_events", "assignees", "created_at", "labels", "priority", "status", "task_id", "updated_at", "version"}) {
		t.Fatalf("metadata keys %v", keysOf(md))
	}
	ev := md["_domain_events"].([]any)[0].(map[string]any)
	if !reflect.DeepEqual(keysOf(ev), []string{"aggregate_id", "aggregate_type", "created_timestamp", "entity_id", "event_id", "metadata", "occurred_at", "user_id"}) {
		t.Fatalf("event keys %v", keysOf(ev))
	}
	if emb := c.ToDict(true); !reflect.DeepEqual(keysOf(emb["metadata"].(map[string]any)), []string{"assignees", "labels", "version"}) || emb["task_id"] != nil {
		t.Fatalf("embedded %v", emb["metadata"])
	}

	// Python's known_fields typo: task_id / progress_* come back as root_level_custom_fields.
	back, err := TaskContextFromDict(d)
	if err != nil {
		t.Fatal(err)
	}
	if len(back.CustomSections) != 1 || back.CustomSections[0].Name != "root_level_custom_fields" ||
		!reflect.DeepEqual(keysOf(back.CustomSections[0].Data), []string{"progress_by_type", "progress_milestones", "progress_timeline", "task_id"}) {
		t.Fatalf("custom sections %+v", back.CustomSections)
	}
	d2 := back.ToDict(false)
	if d2["task_id"] != "t1" || len(d2["custom_sections"].([]any)) != 0 {
		t.Fatalf("restored %v", d2["custom_sections"])
	}

	note := "notes"
	if err := c.UpdateCompletionSummary("done", &note, nil); err != nil {
		t.Fatal(err)
	}
	events := c.ToDict(false)["metadata"].(map[string]any)["_domain_events"].([]any)
	if len(events) != 2 || !reflect.DeepEqual(keysOf(events[1].(map[string]any)),
		[]string{"aggregate_id", "aggregate_type", "entity_id", "event_id", "metadata", "new_timestamp", "occurred_at", "old_timestamp", "user_id"}) {
		t.Fatalf("updated event %v", events)
	}
}

func TestTaskContextFromDictErrors(t *testing.T) {
	_, err := TaskContextFromDict(map[string]any{"task_id": "x", "technical": map[string]any{"zz": 1}})
	if err == nil || err.Error() != "ContextTechnical.__init__() got an unexpected keyword argument 'zz'" {
		t.Fatalf("technical: %v", err)
	}
	_, err = TaskContextFromDict(map[string]any{"task_id": "x", "progress": map[string]any{"completed_actions": []any{map[string]any{"action": "a"}}}})
	if err == nil || err.Error() != "ContextProgressAction.__init__() missing 2 required positional arguments: 'timestamp' and 'agent'" {
		t.Fatalf("progress action: %v", err)
	}
	ok, errs := ContextSchema{}.ValidateContext(map[string]any{"metadata": map[string]any{}, "objective": map[string]any{}})
	if ok || strings.Join(errs, "|") != "Missing required field: metadata.task_id|Missing required field: objective.title" {
		t.Fatalf("validate: %v", errs)
	}
	if s := (ContextSchema{}).GetDefaultSchema(); s["title"] != "Task Context Schema" || s["version"] != "1.0" {
		t.Fatal("default schema")
	}
}

func TestTaskContextUnified(t *testing.T) {
	tc := NewTaskContextUnified("i", "b")
	tc.TaskData["title"] = ""
	tc.Progress = 150
	tc.Insights = []any{1, map[string]any{"category": "zzz"}}
	tc.Blockers["x"] = map[string]any{"description": ""}
	ok, errs := tc.ValidateContextData()
	want := "Progress must be between 0-100, got 150|task_data must contain a title|Insight 0 must be a dictionary|" +
		"Insight 1 missing required field: timestamp|Insight 1 missing required field: content|" +
		"Insight 1 has invalid category: zzz|Blocker 'x' must have a description"
	if ok || strings.Join(errs, "|") != want {
		t.Fatalf("validate: %v", errs)
	}

	tc2 := NewTaskContextUnified("i", "b")
	tc2.Progress = 40
	err := tc2.MergeContextUpdates(map[string]any{"progress": 10, "next_steps": "x", "insights": map[string]any{"a": 1},
		"task_data": map[string]any{"k": 1}, "zzz": 1, "blockers": map[string]any{"b": 1}})
	if err != nil || tc2.Progress != 40 || !reflect.DeepEqual(tc2.NextSteps, []any{"x"}) || len(tc2.Insights) != 1 || tc2.TaskData["k"] != 1 {
		t.Fatalf("merge: %v %+v", err, tc2)
	}
	if err := tc2.UpdateProgress(10, nil, false); err == nil || err.Error() != "Progress cannot decrease from 40 to 10. Set allow_decrease=True to override." {
		t.Fatalf("decrease: %v", err)
	}
	// One home for one idea: the entry lands in progress_updates (the key the live path writes)
	// and carries the whole transition, and the retired progress_history name is not written at all.
	notes := "halfway"
	if err := tc2.UpdateProgress(60, &notes, true); err != nil || tc2.Progress != 60 {
		t.Fatalf("update: %v %d", err, tc2.Progress)
	}
	if _, retired := tc2.Metadata["progress_history"]; retired {
		t.Fatalf("progress_history is the retired name and must not be written: %#v", tc2.Metadata["progress_history"])
	}
	updates, _ := tc2.ImplementationNotes["progress_updates"].([]any)
	if len(updates) != 1 {
		t.Fatalf("progress_updates entries = %d, want 1: %#v", len(updates), tc2.ImplementationNotes)
	}
	entry, _ := updates[0].(map[string]any)
	if entry["old_progress"] != 40 || entry["new_progress"] != 60 || entry["notes"] != "halfway" || entry["timestamp"] == nil {
		t.Fatalf("progress_updates entry lost the transition: %#v", entry)
	}
	if err := tc2.AddInsight("nope", "c", "system", "medium"); err == nil ||
		err.Error() != "Invalid category: nope. Must be one of ['insight', 'challenge', 'solution', 'decision', 'technical', 'business']" {
		t.Fatalf("category: %v", err)
	}
}

func TestGlobalContext(t *testing.T) {
	g := NewGlobalContext("g", "o", map[string]any{"custom": 1}, nil)
	d := g.ToDict()
	if d["custom"] != 1 || d["id"] != "g" {
		t.Fatalf("dict %v", d)
	}
	md := d["metadata"].(map[string]any)
	if md["nested_structure"] == nil || md["schema_version"] != "2.0" {
		t.Fatal("metadata nested info")
	}
	if err := g.UpdateGlobalSettings(map[string]any{"security": map[string]any{"encryption": map[string]any{"a": 1}}}, true); err != nil {
		t.Fatal(err)
	}
	if _, ok := g.GlobalSettings["custom"]; ok {
		t.Fatal("nested sync replaces flat settings")
	}
	if !reflect.DeepEqual(g.GlobalSettings["security"], map[string]any{"access_control": map[string]any{}, "authentication": map[string]any{},
		"encryption": map[string]any{"a": 1}}) {
		t.Fatalf("security %v", g.GlobalSettings["security"])
	}
}
