package services

import (
	"context"
	"encoding/json"
	"os"
	"reflect"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

const tvU = "00000000-0000-4000-8000-0000000000"

func tvTask(t *testing.T, mut func(*entities.Task)) *entities.Task {
	t.Helper()
	id, _ := value_objects.NewTaskId(tvU + "01")
	branch := tvU + "02"
	st, pr := tstStatus(t, "todo"), value_objects.PriorityHigh()
	task, err := entities.NewTask(entities.Task{ID: &id, Title: "Implement login flow",
		Description: "Detailed description here", Status: &st, Priority: &pr, GitBranchID: &branch})
	if err != nil {
		t.Fatal(err)
	}
	if mut != nil {
		mut(task)
	}
	return task
}

func tvSetStatus(t *testing.T, task *entities.Task, s string) {
	st := tstStatus(t, s)
	task.Status = &st
}

func tvSetPriority(task *entities.Task, p string) {
	pr, err := value_objects.NewPriority(p)
	if err != nil {
		panic(err)
	}
	task.Priority = &pr
}

func tvCases(t *testing.T) map[string]func(*entities.Task) {
	sp := func(s string) *string { return &s }
	return map[string]func(*entities.Task){
		"ok":          nil,
		"short_title": func(k *entities.Task) { k.Title = "ab" },
		"empty_title": func(k *entities.Task) { k.Title = "" },
		"ws_title":    func(k *entities.Task) { k.Title = "   " },
		"long_title":  func(k *entities.Task) { k.Title = strings.Repeat("x", 201) },
		"placeholder": func(k *entities.Task) { k.Title = "TODO later" },
		"repeat":      func(k *entities.Task) { k.Title = "work work work done" },
		"repeat_half": func(k *entities.Task) { k.Title = "a b a b" },
		"brief_desc":  func(k *entities.Task) { k.Description = "short" },
		"na_desc":     func(k *entities.Task) { k.Description = " N/A " },
		"long_desc":   func(k *entities.Task) { k.Description = strings.Repeat("d", 2001) },
		"effort_bad":  func(k *entities.Task) { k.EstimatedEffort = "lots" },
		"effort_ok":   func(k *entities.Task) { k.EstimatedEffort = "2 Hours" },
		"assignees":   func(k *entities.Task) { k.Assignees = []string{"a", "", strings.Repeat("b", 51), "c", "d", "e"} },
		"labels": func(k *entities.Task) {
			k.Labels = append([]string{strings.Repeat("x", 31), " "}, strings.Split(strings.Repeat("l,", 10), ",")[:10]...)
		},
		"due":         func(k *entities.Task) { k.DueDate = sp("2026-10-01") },
		"crit_todo":   func(k *entities.Task) { tvSetPriority(k, "critical") },
		"done_urgent": func(k *entities.Task) { tvSetStatus(t, k, "done"); tvSetPriority(k, "urgent") },
		"done_urgent_cs": func(k *entities.Task) {
			tvSetStatus(t, k, "done")
			tvSetPriority(k, "urgent")
			k.CompletionSummary = sp("ok")
		},
		"bad_id":      func(k *entities.Task) { id, _ := value_objects.NewTaskId("not-a-uuid"); k.ID = &id },
		"same_branch": func(k *entities.Task) { b := tvU + "01"; k.GitBranchID = &b },
		"no_branch":   func(k *entities.Task) { k.GitBranchID = nil },
		"bad_branch":  func(k *entities.Task) { k.GitBranchID = sp("xyz") },
		"deps": func(k *entities.Task) {
			for i := 1; i <= 12; i++ {
				id, _ := value_objects.NewTaskId(tvU + string(rune('0'+i/10)) + string(rune('0'+i%10)))
				k.Dependencies = append(k.Dependencies, id)
			}
		},
		"unicode": func(k *entities.Task) { k.Title = "  Ünï    ünï ünï" },
	}
}

func eqStrings(t *testing.T, label string, got []string, want any) {
	t.Helper()
	w := []string{}
	for _, x := range want.([]any) {
		w = append(w, x.(string))
	}
	if got == nil {
		got = []string{}
	}
	if !reflect.DeepEqual(got, w) {
		t.Errorf("%s: got %q want %q", label, got, w)
	}
}

func TestTaskValidationMatchesPython(t *testing.T) {
	raw, err := os.ReadFile("testdata/task_validation_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var fx map[string]any
	if err := json.Unmarshal(raw, &fx); err != nil {
		t.Fatal(err)
	}
	svc := NewTaskValidationService(nil, nil)
	ctx := context.Background()
	for name, mut := range tvCases(t) {
		want := fx[name].(map[string]any)
		task := tvTask(t, mut)
		eqStrings(t, name+" create", svc.ValidateTaskCreation(ctx, task, nil), want["create"])
		eqStrings(t, name+" constraints", svc.ValidateBusinessConstraints(task, "general"), want["constraints"])
		eqStrings(t, name+" content", svc.ValidateContentAppropriateness(task), want["content"])
		ok, errs := svc.ValidateTaskRelationships(ctx, task)
		rel := want["rel"].([]any)
		if ok != rel[0].(bool) {
			t.Errorf("%s rel ok: %v", name, ok)
		}
		eqStrings(t, name+" rel", errs, rel[1])
		eqStrings(t, name+" update_self", svc.ValidateTaskUpdate(task, task), want["update_self"])
	}
}

func TestTaskValidationTransitionsAndContextMatchPython(t *testing.T) {
	raw, _ := os.ReadFile("testdata/task_validation_cases.json")
	var fx map[string]any
	if err := json.Unmarshal(raw, &fx); err != nil {
		t.Fatal(err)
	}
	svc := NewTaskValidationService(nil, nil)
	ctx := context.Background()
	for a, row := range fx["_trans"].(map[string]any) {
		for b, want := range row.(map[string]any) {
			cur := tvTask(t, func(k *entities.Task) { tvSetStatus(t, k, a) })
			upd := tvTask(t, func(k *entities.Task) { tvSetStatus(t, k, b) })
			eqStrings(t, a+"->"+b, svc.ValidateTaskUpdate(cur, upd), want)
		}
	}
	other := tvTask(t, func(k *entities.Task) { id, _ := value_objects.NewTaskId(tvU + "09"); k.ID = &id })
	eqStrings(t, "update id", svc.ValidateTaskUpdate(tvTask(t, nil), other), fx["_update_id"])
	eqStrings(t, "similar", svc.ValidateTaskCreation(ctx, tvTask(t, nil), []SimilarTask{{" implement LOGIN flow "}}), fx["_similar"])
	eqStrings(t, "similar none", svc.ValidateTaskCreation(ctx, tvTask(t, nil), []SimilarTask{{}}), fx["_similar_none"])

	a, b := tvU+"01", tvU+"02"
	ids := fx["_ids"].(map[string]any)
	eqStrings(t, "map", svc.ValidateIDParameters(&a, &a, nil, nil), ids["map"])
	eqStrings(t, "ok", svc.ValidateIDParameters(&a, &b, nil, nil), ids["ok"])
	eqStrings(t, "none", svc.ValidateIDParameters(nil, nil, nil, nil), ids["none"])
	eqStrings(t, "ctx_same", svc.ValidateTaskContextIntegrity(a, a), ids["ctx_same"])
	eqStrings(t, "ctx_ok", svc.ValidateTaskContextIntegrity(a, b), ids["ctx_ok"])
	eqStrings(t, "ctx_bad", svc.ValidateTaskContextIntegrity("zz", b), ids["ctx_bad"])
	eqStrings(t, "ctx_none", svc.ValidateTaskContextIntegrity(a, ""), ids["ctx_none"])
}
