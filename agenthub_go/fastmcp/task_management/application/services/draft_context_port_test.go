package services

import (
	"context"
	"math"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func cptOM(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}

func TestContextFieldSelectorGetTaskFields(t *testing.T) {
	s := NewContextFieldSelector()

	// default -> summary with dependencies expanded
	got := s.GetTaskFields("t1", nil)
	if v, _ := got.Get("entity_type"); v != "task" {
		t.Fatalf("entity_type=%v", v)
	}
	if v, _ := got.Get("optimized"); v != true {
		t.Fatalf("optimized=%v", v)
	}
	fields, _ := got.Get("fields")
	want := []string{"id", "title", "description", "status", "priority", "assignees", "labels", "assignee_ids", "label_ids"}
	if !cptEqStrSlice(fields.([]string), want) {
		t.Fatalf("fields=%v want %v", fields, want)
	}

	// MINIMAL
	got = s.GetTaskFields("t1", FieldSetMinimal)
	fields, _ = got.Get("fields")
	if !cptEqStrSlice(fields.([]string), []string{"id", "title", "status", "priority"}) {
		t.Fatalf("minimal fields=%v", fields)
	}

	// FULL -> fields None, optimized False
	got = s.GetTaskFields("t1", FieldSetFull)
	if v, _ := got.Get("fields"); v != nil {
		t.Fatalf("full fields=%v", v)
	}
	if v, _ := got.Get("optimized"); v != false {
		t.Fatalf("full optimized=%v", v)
	}
}

func TestContextFieldSelectorEstimateSavings(t *testing.T) {
	s := NewContextFieldSelector()
	got := s.EstimateSavings("task", FieldSetMinimal)
	want := map[string]any{
		"field_reduction_percent":    92.0,
		"query_time_savings_percent": 64.4,
		"bandwidth_savings_percent":  82.8,
		"cache_efficiency_percent":   95,
		"selected_fields":            4,
		"full_fields":                50,
	}
	for k, w := range want {
		v, _ := got.Get(k)
		if !cptEqNum(v, w) {
			t.Fatalf("%s=%v want %v", k, v, w)
		}
	}
	bad := s.EstimateSavings("nope", FieldSetMinimal)
	if v, _ := bad.Get("error"); v != "Unknown entity type" {
		t.Fatalf("error=%v", v)
	}
}

func TestContextFieldSelectorSelectFields(t *testing.T) {
	s := NewContextFieldSelector()
	ctx := cptOM(
		"id", "1", "title", "T", "description", "D", "status", "todo",
		"priority", "high", "assignees", []any{"a"}, "labels", []any{"l"}, "extra", "x",
	)
	got := s.SelectFields(ctx, FieldSetSummary, nil, nil, nil, nil, nil, nil, nil)
	if got.Len() != 7 || got.Has("extra") {
		t.Fatalf("keys=%v", got.Keys())
	}
	if got.Keys()[0] != "id" || got.Keys()[6] != "labels" {
		t.Fatalf("order=%v", got.Keys())
	}

	// custom fields
	got = s.SelectFields(ctx, nil, []string{"id", "title"}, nil, nil, nil, nil, nil, nil)
	if !cptEqStrSlice(got.Keys(), []string{"id", "title"}) {
		t.Fatalf("custom keys=%v", got.Keys())
	}

	// nested custom fields
	nested := cptOM("meta", cptOM("a", 1, "b", 2), "x", 3)
	got = s.SelectFields(nested, nil, []string{"meta.a"}, nil, nil, nil, nil, nil, nil)
	meta, _ := got.Get("meta")
	if !cptEqStrSlice(meta.(*entities.OrderedMap[any]).Keys(), []string{"a"}) {
		t.Fatalf("nested=%v", got.Keys())
	}

	// exclusions
	got = s.SelectFields(ctx, FieldSetSummary, nil, []string{"description"}, nil, nil, nil, nil, nil)
	if got.Has("description") {
		t.Fatalf("exclusion failed")
	}
}

func TestContextFieldSelectorMetrics(t *testing.T) {
	s := NewContextFieldSelector()
	ctx := cptOM("id", "1", "title", "T")
	s.CacheFieldMapping("e1", []string{"id"}, ctx)
	if v := s.GetCachedFields("e1", []string{"id"}); v == nil {
		t.Fatalf("expected cache hit")
	}
	_ = s.GetCachedFields("e1", []string{"other"})
	m := s.GetMetrics()
	if v, _ := m.Get("cache_hits"); v != 1 {
		t.Fatalf("cache_hits=%v", v)
	}
	if v, _ := m.Get("cache_misses"); v != 1 {
		t.Fatalf("cache_misses=%v", v)
	}
	s.ResetMetrics()
	if v, _ := s.GetMetrics().Get("cache_hits"); v != 0 {
		t.Fatalf("reset failed")
	}
}

func TestContextFieldSelectorMisc(t *testing.T) {
	s := NewContextFieldSelector()
	if fs := s.GetOptimalFieldSet("list", "task"); fs != FieldSetMinimal {
		t.Fatalf("list=%v", fs)
	}
	if fs := s.GetOptimalFieldSet("audit", "task"); fs != FieldSetFull {
		t.Fatalf("audit=%v", fs)
	}
	if fs := s.DetermineFieldSetForOperation("unknown"); fs != FieldSetSummary {
		t.Fatalf("unknown=%v", fs)
	}
	got := s.MergeFieldSelections([]string{"a", "b"}, []string{"b", "c"})
	if !cptEqStrSlice(got, []string{"a", "b", "c"}) {
		t.Fatalf("merge=%v", got)
	}
}

func TestContextHierarchyValidator(t *testing.T) {
	global := &cptMockRepo{get: map[string]any{"00000000-0000-0000-0000-000000000001": &struct{}{}}}
	project := &cptMockRepo{get: map[string]any{"p1": &struct{}{}}}
	branch := &cptMockRepo{get: map[string]any{"b1": &entities.GitBranch{ProjectID: "p1"}}}
	task := &cptMockRepo{}
	v := NewContextHierarchyValidator(global, project, branch, task, nil)

	ok, msg, g := v.ValidateHierarchyRequirements(value_objects.ContextLevelGlobal, "global", nil)
	if !ok || msg != nil || g != nil {
		t.Fatalf("global=%v %v %v", ok, msg, g)
	}

	ok, msg, g = v.ValidateHierarchyRequirements(value_objects.ContextLevelProject, "p1", nil)
	if !ok || msg != nil || g != nil {
		t.Fatalf("project=%v %v %v", ok, msg, g)
	}

	// branch without project_id
	ok, msg, g = v.ValidateHierarchyRequirements(value_objects.ContextLevelBranch, "bX", cptOM())
	if ok || msg == nil || *msg != "Branch context requires project_id" {
		t.Fatalf("branch missing: ok=%v msg=%v", ok, msg)
	}
	if e, _ := g.Get("error"); e != "Missing required field: project_id" {
		t.Fatalf("branch guidance=%v", e)
	}

	// branch with project_id and existing project
	ok, msg, g = v.ValidateHierarchyRequirements(value_objects.ContextLevelBranch, "b1", cptOM("project_id", "p1"))
	if !ok || msg != nil || g != nil {
		t.Fatalf("branch valid=%v %v %v", ok, msg, g)
	}

	// branch auto-resolves project_id from git branch
	ok, _, _ = v.ValidateHierarchyRequirements(value_objects.ContextLevelBranch, "b1", cptOM())
	if !ok {
		t.Fatalf("branch auto-resolve failed")
	}

	// task without branch
	ok, msg, _ = v.ValidateHierarchyRequirements(value_objects.ContextLevelTask, "t1", cptOM())
	if ok || msg == nil || *msg != "Missing required field: branch_id (or parent_branch_id or git_branch_id)" {
		t.Fatalf("task missing: ok=%v msg=%v", ok, msg)
	}

	// task with existing branch
	ok, msg, g = v.ValidateHierarchyRequirements(value_objects.ContextLevelTask, "t1", cptOM("branch_id", "b1"))
	if !ok || msg != nil || g != nil {
		t.Fatalf("task valid=%v %v %v", ok, msg, g)
	}
}

func TestContextHierarchyValidatorStatus(t *testing.T) {
	global := &cptMockRepo{get: map[string]any{"00000000-0000-0000-0000-000000000001": &struct{}{}, "global_singleton": &struct{}{}}}
	project := &cptMockRepo{list: []any{1, 2}}
	branch := &cptMockRepo{list: []any{1}}
	task := &cptMockRepo{list: []any{}}
	v := NewContextHierarchyValidator(global, project, branch, task, nil)
	status := v.GetHierarchyStatus()
	levels, _ := status.Get("hierarchy_levels")
	if !cptEqStrSlice(levels.([]string), []string{"global", "project", "branch", "task"}) {
		t.Fatalf("levels=%v", levels)
	}
	cs, _ := status.Get("current_state")
	state := cs.(*entities.OrderedMap[any])
	g, _ := state.Get("global")
	if v, _ := g.(*entities.OrderedMap[any]).Get("exists"); v != true {
		t.Fatalf("global exists=%v", v)
	}
	p, _ := state.Get("projects")
	if v, _ := p.(*entities.OrderedMap[any]).Get("count"); v != 2 {
		t.Fatalf("projects=%v", v)
	}
}

func TestContextTemplateManagerGetTemplate(t *testing.T) {
	m := NewContextTemplateManager(nil)
	got := m.GetTemplate(OperationTypeTaskGet, nil)
	task, _ := got.Get("task")
	if !cptEqStrSlice(task, []string{"*"}) {
		t.Fatalf("task=%v", task)
	}
	if got.Keys()[0] != "task" {
		t.Fatalf("order=%v", got.Keys())
	}

	// inheritance: subtask.create inherits task.create
	sub := m.GetTemplate(OperationTypeSubtaskCreate, nil)
	if !cptEqStrSlice(sub.Keys(), []string{"parent_task", "project", "user", "git_branch", "recent_tasks", "parent_context"}) {
		t.Fatalf("keys=%v", sub.Keys())
	}
	proj, _ := sub.Get("project")
	if !cptEqStrSlice(proj, []string{"id", "subtask_rules", "name", "default_priority", "workflow_rules"}) {
		t.Fatalf("project=%v", proj)
	}

	// overrides
	ov := entities.NewOrderedMap[[]string]()
	ov.Set("task", []string{"*"})
	ov.Set("custom", []string{"x"})
	got = m.GetTemplate(OperationTypeTaskGet, ov)
	if v, _ := got.Get("task"); !cptEqStrSlice(v, []string{"*"}) {
		t.Fatalf("override task=%v", v)
	}
	if v, _ := got.Get("custom"); !cptEqStrSlice(v, []string{"x"}) {
		t.Fatalf("override custom=%v", v)
	}
}

func TestContextTemplateManagerMinimalAndSavings(t *testing.T) {
	m := NewContextTemplateManager(nil)
	available := cptOM(
		"task", cptOM("id", "1", "title", "T", "extra", "x"),
		"subtasks", cptOM("id", "s1", "title", "S", "status", "todo", "progress_percentage", 0, "zzz", 1),
	)
	minimal := m.GetMinimalContext(OperationTypeTaskGet, available)
	task, _ := minimal.Get("task")
	if task.(*entities.OrderedMap[any]).Len() != 3 {
		t.Fatalf("full task copy len=%d", task.(*entities.OrderedMap[any]).Len())
	}
	subs, _ := minimal.Get("subtasks")
	if !cptEqStrSlice(subs.(*entities.OrderedMap[any]).Keys(), []string{"id", "title", "status", "progress_percentage"}) {
		t.Fatalf("subtasks=%v", subs.(*entities.OrderedMap[any]).Keys())
	}
	if v, _ := m.GetMetrics().Get("fields_saved"); v != 1 {
		t.Fatalf("fields_saved=%v", v)
	}

	sav := m.EstimateSavings()
	if v, _ := sav.Get("field_reduction_percent"); !cptEqNum(v, 1.7) {
		t.Fatalf("field_reduction=%v", v)
	}
	if v, _ := sav.Get("estimated_time_savings_ms"); v != 1 {
		t.Fatalf("time=%v", v)
	}
	if v, _ := sav.Get("estimated_bandwidth_savings_kb"); !cptEqNum(v, 0.1) {
		t.Fatalf("bandwidth=%v", v)
	}
	if v, _ := sav.Get("cache_hit_rate"); !cptEqNum(v, 0.0) {
		t.Fatalf("cache_hit_rate=%v", v)
	}
}

func TestContextTemplateManagerMisc(t *testing.T) {
	m := NewContextTemplateManager(nil)
	if !m.ValidateTemplate(OperationTypeTaskGet, []string{"task", "subtasks"}) {
		t.Fatalf("validate should pass")
	}
	if m.ValidateTemplate(OperationTypeTaskGet, []string{"nope"}) {
		t.Fatalf("validate should fail")
	}
	if len(m.GetAllOperations()) != 33 {
		t.Fatalf("ops=%d", len(m.GetAllOperations()))
	}
	m.ResetMetrics()
	if v, _ := m.GetMetrics().Get("templates_used"); v != 0 {
		t.Fatalf("reset=%v", v)
	}
	// zero-metric savings shape
	sav := m.EstimateSavings()
	if sav.Keys()[0] != "field_reduction_percent" || sav.Has("cache_hit_rate") {
		t.Fatalf("empty savings keys=%v", sav.Keys())
	}
}

// --- helpers ---

type cptMockRepo struct {
	get  map[string]any
	list []any
}

func (r *cptMockRepo) Get(ctx context.Context, id string) (any, error) {
	if r.get == nil {
		return nil, nil
	}
	return r.get[id], nil
}

func (r *cptMockRepo) List(ctx context.Context) ([]any, error) { return r.list, nil }

func cptEqStrSlice(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func cptEqNum(a, b any) bool {
	af, aok := a.(float64)
	bf, bok := b.(float64)
	if aok && bok {
		return math.Abs(af-bf) < 1e-9
	}
	return a == b
}
