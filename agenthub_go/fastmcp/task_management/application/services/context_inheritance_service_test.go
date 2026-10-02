package services

import (
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// zpCtxInhTestOM builds an OrderedMap from key/value pairs (test helper).
func zpCtxInhTestOM(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

// zpCtxInhPath walks dot-separated keys, failing the test if any is missing.
func zpCtxInhPath(t *testing.T, m *entities.OrderedMap[any], keys ...string) any {
	t.Helper()
	var current any = m
	for _, key := range keys {
		om, ok := zpCtxInhDict(current)
		if !ok {
			t.Fatalf("path %v: %q is not a map", keys, key)
		}
		value, ok := om.Get(key)
		if !ok {
			t.Fatalf("path %v: missing key %q", keys, key)
		}
		current = value
	}
	return current
}

func zpCtxInhAssertEqual(t *testing.T, got, want any) {
	t.Helper()
	if !value_objects.PyEqual(got, want) {
		t.Fatalf("got %#v, want %#v", got, want)
	}
}

func zpCtxInhKeyOrder(t *testing.T, m *entities.OrderedMap[any], want []string) {
	t.Helper()
	if !value_objects.PyEqual(m.Keys(), want) {
		t.Fatalf("keys = %v, want %v", m.Keys(), want)
	}
}

func TestContextInheritanceService_Init(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	if svc.Repository != nil {
		t.Fatalf("repository = %#v, want nil", svc.Repository)
	}
	if svc.UserID != nil {
		t.Fatalf("user id = %#v, want nil", svc.UserID)
	}
}

func TestContextInheritanceService_WithUser(t *testing.T) {
	svc1 := NewContextInheritanceService("repo", nil)
	svc2 := svc1.WithUser("user456")
	if svc2.UserID == nil || *svc2.UserID != "user456" {
		t.Fatalf("user id = %#v", svc2.UserID)
	}
	if svc1.UserID != nil {
		t.Fatalf("original user id mutated")
	}
	if svc1 == svc2 {
		t.Fatalf("with_user did not create a new instance")
	}
	if svc2.Repository != "repo" {
		t.Fatalf("repository not carried over")
	}
}

func TestContextInheritanceService_GetUserScopedRepository(t *testing.T) {
	svc := NewContextInheritanceService(nil, zpCtxInhStrPtr("user123"))
	if svc.getUserScopedRepository(nil) != nil {
		t.Fatalf("nil repository not returned unchanged")
	}
	repo := struct{ Name string }{Name: "repo"}
	if svc.getUserScopedRepository(repo) != repo {
		t.Fatalf("repository not returned unchanged")
	}
}

func TestContextInheritanceService_GetInheritedContextNil(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	if got := svc.GetInheritedContext("task", "task123"); got != nil {
		t.Fatalf("got %#v, want nil", got)
	}
}

func TestContextInheritanceService_InheritProjectFromGlobalBasic(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	global := zpCtxInhTestOM(
		"security_policies", zpCtxInhTestOM("mfa_required", false),
		"coding_standards", zpCtxInhTestOM("style", "PEP8"),
	)
	project := zpCtxInhTestOM(
		"team_preferences", zpCtxInhTestOM("timezone", "UTC"),
		"technology_stack", zpCtxInhTestOM("backend", "Python"),
	)
	result := svc.InheritProjectFromGlobal(global, project)

	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "security_policies", "mfa_required"), false)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "coding_standards", "style"), "PEP8")
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "team_preferences", "timezone"), "UTC")
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "technology_stack", "backend"), "Python")
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "inheritance_metadata", "inherited_from"), "global")
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "inheritance_metadata", "project_overrides_applied"), 0)

	zpCtxInhKeyOrder(t, result, []string{"security_policies", "coding_standards", "team_preferences",
		"technology_stack", "project_workflow", "local_standards", "inheritance_metadata"})
}

func TestContextInheritanceService_ProjectGlobalOverrides(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	global := zpCtxInhTestOM(
		"security_policies", zpCtxInhTestOM("mfa_required", false),
		"code_review", zpCtxInhTestOM("required", true),
	)
	project := zpCtxInhTestOM(
		"team_preferences", zpCtxInhTestOM("timezone", "EST"),
		"global_overrides", zpCtxInhTestOM("security_policies.mfa_required", true),
	)
	result := svc.InheritProjectFromGlobal(global, project)

	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "security_policies", "mfa_required"), true)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "inheritance_metadata", "project_overrides_applied"), 1)
}

func TestContextInheritanceService_ProjectDelegationRules(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	global := zpCtxInhTestOM("delegation_rules", zpCtxInhTestOM("auto_delegate", zpCtxInhTestOM("enabled", true)))
	project := zpCtxInhTestOM("delegation_rules", zpCtxInhTestOM("auto_delegate", zpCtxInhTestOM("max_depth", 3)))
	result := svc.InheritProjectFromGlobal(global, project)

	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "delegation_rules", "auto_delegate", "enabled"), true)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "delegation_rules", "auto_delegate", "max_depth"), 3)
	auto := zpCtxInhPath(t, result, "delegation_rules", "auto_delegate").(*entities.OrderedMap[any])
	zpCtxInhKeyOrder(t, auto, []string{"enabled", "max_depth"})
}

func TestContextInheritanceService_ProjectArbitraryFields(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	global := zpCtxInhTestOM("base_field", "value")
	project := zpCtxInhTestOM(
		"custom_field", "custom_value",
		"another_field", zpCtxInhTestOM("nested", "data"),
	)
	result := svc.InheritProjectFromGlobal(global, project)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "custom_field"), "custom_value")
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "another_field", "nested"), "data")
}

func TestContextInheritanceService_InheritBranchFromProject(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	project := zpCtxInhTestOM(
		"security_policies", zpCtxInhTestOM("mfa_required", true),
		"team_preferences", zpCtxInhTestOM("timezone", "UTC"),
	)
	branch := zpCtxInhTestOM(
		"branch_workflow", zpCtxInhTestOM("ci_cd", "enabled"),
		"branch_standards", zpCtxInhTestOM("commit_format", "conventional"),
	)
	result := svc.InheritBranchFromProject(project, branch)

	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "security_policies", "mfa_required"), true)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "branch_workflow", "ci_cd"), "enabled")
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "branch_standards", "commit_format"), "conventional")
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "inheritance_metadata", "inherited_from"), "project")
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "inheritance_metadata", "inheritance_chain"), []any{"global", "project", "branch"})
}

func TestContextInheritanceService_BranchLocalOverrides(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	project := zpCtxInhTestOM("code_review", zpCtxInhTestOM("required", true, "min_approvals", 2))
	branch := zpCtxInhTestOM(
		"branch_workflow", zpCtxInhTestOM("feature_flags", true),
		"local_overrides", zpCtxInhTestOM("code_review.min_approvals", 1),
	)
	result := svc.InheritBranchFromProject(project, branch)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "code_review", "min_approvals"), 1)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "inheritance_metadata", "branch_overrides_applied"), 1)
}

func TestContextInheritanceService_BranchAgentAssignments(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	project := zpCtxInhTestOM("base", "data")
	branch := zpCtxInhTestOM("agent_assignments", zpCtxInhTestOM(
		"coding-agent", []any{"task1", "task2"},
		"test-agent", []any{"task3"},
	))
	result := svc.InheritBranchFromProject(project, branch)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "agent_assignments", "coding-agent"), []any{"task1", "task2"})
}

func TestContextInheritanceService_InheritTaskFromBranch(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	branch := zpCtxInhTestOM(
		"security_policies", zpCtxInhTestOM("mfa_required", true),
		"branch_workflow", zpCtxInhTestOM("ci_cd", "enabled"),
	)
	task := zpCtxInhTestOM("task_data", zpCtxInhTestOM("priority", "high", "deadline", "2025-12-31"))
	result := svc.InheritTaskFromBranch(branch, task)

	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "security_policies", "mfa_required"), true)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "task_data", "priority"), "high")
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "inheritance_metadata", "inherited_from"), "branch")
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "inheritance_metadata", "inheritance_chain"), []any{"global", "project", "branch", "task"})
}

func TestContextInheritanceService_TaskLocalOverrides(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	branch := zpCtxInhTestOM("testing", zpCtxInhTestOM("coverage_threshold", 80))
	task := zpCtxInhTestOM(
		"task_data", zpCtxInhTestOM("type", "bug_fix"),
		"local_overrides", zpCtxInhTestOM("testing.coverage_threshold", 70),
	)
	result := svc.InheritTaskFromBranch(branch, task)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "testing", "coverage_threshold"), 70)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "inheritance_metadata", "local_overrides_applied"), 1)
}

func TestContextInheritanceService_TaskImplementationNotes(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	branch := zpCtxInhTestOM("base", "data")
	task := zpCtxInhTestOM("implementation_notes", zpCtxInhTestOM(
		"approach", "TDD",
		"considerations", []any{"performance", "security"},
	))
	result := svc.InheritTaskFromBranch(branch, task)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "implementation_notes", "approach"), "TDD")
}

func TestContextInheritanceService_TaskCustomInheritanceRules(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	branch := zpCtxInhTestOM("field1", "value1", "field2", "value2")
	task := zpCtxInhTestOM("custom_inheritance_rules", zpCtxInhTestOM(
		"exclude_keys", []any{"field1"},
		"force_values", zpCtxInhTestOM("field3", "forced"),
	))
	result := svc.InheritTaskFromBranch(branch, task)

	if result.Has("field1") {
		t.Fatalf("field1 was not excluded")
	}
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "field3"), "forced")
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "inheritance_metadata", "custom_rules_applied"), 2)
}

func TestContextInheritanceService_TaskDelegationTriggers(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	branch := zpCtxInhTestOM("base", "data")
	task := zpCtxInhTestOM("delegation_triggers", zpCtxInhTestOM(
		"on_completion", []any{"notify_team"},
		"on_error", []any{"escalate"},
	))
	result := svc.InheritTaskFromBranch(branch, task)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "delegation_triggers", "on_completion"), []any{"notify_team"})
}

func TestContextInheritanceService_DeepMerge(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)

	simple := svc.deepMerge(
		zpCtxInhTestOM("a", 1, "b", 2),
		zpCtxInhTestOM("b", 3, "c", 4),
	)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, simple, "a"), 1)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, simple, "b"), 3)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, simple, "c"), 4)
	zpCtxInhKeyOrder(t, simple, []string{"a", "b", "c"})

	nested := svc.deepMerge(
		zpCtxInhTestOM("config", zpCtxInhTestOM("setting1", "value1", "setting2", "value2")),
		zpCtxInhTestOM("config", zpCtxInhTestOM("setting2", "new_value", "setting3", "value3")),
	)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, nested, "config", "setting1"), "value1")
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, nested, "config", "setting2"), "new_value")
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, nested, "config", "setting3"), "value3")

	dedup := svc.deepMerge(
		zpCtxInhTestOM("assignees", []any{"agent1", "agent2"}),
		zpCtxInhTestOM("assignees", []any{"agent2", "agent3"}),
	)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, dedup, "assignees"), []any{"agent1", "agent2", "agent3"})

	appended := svc.deepMerge(
		zpCtxInhTestOM("requirements", []any{"req1", "req2"}),
		zpCtxInhTestOM("requirements", []any{"req3"}),
	)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, appended, "requirements"), []any{"req1", "req2", "req3"})

	// Base must not be mutated (deepcopy semantics).
	base := zpCtxInhTestOM("nested", zpCtxInhTestOM("x", 1))
	_ = svc.deepMerge(base, zpCtxInhTestOM("nested", zpCtxInhTestOM("x", 2)))
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, base, "nested", "x"), 1)
}

func TestContextInheritanceService_ApplyOverrides(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)

	simple := svc.applyOverrides(zpCtxInhTestOM("field1", "value1"), zpCtxInhTestOM("field2", "value2"))
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, simple, "field1"), "value1")
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, simple, "field2"), "value2")

	nested := svc.applyOverrides(
		zpCtxInhTestOM("config", zpCtxInhTestOM("database", zpCtxInhTestOM("host", "localhost"))),
		zpCtxInhTestOM("config.database.host", "prod-server"),
	)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, nested, "config", "database", "host"), "prod-server")

	created := svc.applyOverrides(zpCtxInhTestOM("existing", "data"), zpCtxInhTestOM("new.nested.field", "value"))
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, created, "new", "nested", "field"), "value")
}

func TestContextInheritanceService_MergeDelegationRules(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)

	auto := svc.mergeDelegationRules(
		zpCtxInhTestOM("auto_delegate", zpCtxInhTestOM("enabled", true, "max_depth", 3)),
		zpCtxInhTestOM("auto_delegate", zpCtxInhTestOM("max_depth", 5, "timeout", 60)),
	)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, auto, "auto_delegate", "enabled"), true)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, auto, "auto_delegate", "max_depth"), 5)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, auto, "auto_delegate", "timeout"), 60)

	thresholds := svc.mergeDelegationRules(
		zpCtxInhTestOM("thresholds", zpCtxInhTestOM("complexity", 10)),
		zpCtxInhTestOM("thresholds", zpCtxInhTestOM("complexity", 15, "priority", "high")),
	)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, thresholds, "thresholds", "complexity"), 15)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, thresholds, "thresholds", "priority"), "high")
}

func TestContextInheritanceService_ExcludeKeys(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	context := zpCtxInhTestOM(
		"keep_this", "value1",
		"remove_this", "value2",
		"nested", zpCtxInhTestOM("keep", "yes", "remove", "no"),
	)
	result := svc.processExcludeKeys(context, []any{"remove_this", "nested.remove"})
	if !result.Has("keep_this") || result.Has("remove_this") {
		t.Fatalf("top-level exclusion failed: %v", result.Keys())
	}
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "nested", "keep"), "yes")
	nested := zpCtxInhPath(t, result, "nested").(*entities.OrderedMap[any])
	if nested.Has("remove") {
		t.Fatalf("nested exclusion failed: %v", nested.Keys())
	}
	// Original context untouched (deepcopy).
	if !zpCtxInhPath(t, context, "nested").(*entities.OrderedMap[any]).Has("remove") {
		t.Fatalf("original context mutated")
	}
}

func TestContextInheritanceService_ForceValues(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	result := svc.processForceValues(zpCtxInhTestOM("field", "old_value"), zpCtxInhTestOM("field", "forced_value"))
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "field"), "forced_value")
}

func TestContextInheritanceService_ConditionalOverrides(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	context := zpCtxInhTestOM("environment", "production", "debug", true)
	conditional := []any{
		zpCtxInhTestOM(
			"name", "prod_settings",
			"condition", zpCtxInhTestOM("type", "key_equals", "key", "environment", "value", "production"),
			"overrides", zpCtxInhTestOM("debug", false),
		),
	}
	result := svc.processConditionalOverrides(context, conditional)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, result, "debug"), false)
}

func TestContextInheritanceService_EvaluateCondition(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	context := zpCtxInhTestOM(
		"field1", "value",
		"nested", zpCtxInhTestOM("field2", "value", "value", 42),
		"status", "active",
		"message", "Hello World",
	)

	if !svc.evaluateCondition(context, zpCtxInhTestOM("type", "key_exists", "key", "field1")) {
		t.Fatalf("key_exists field1 = false")
	}
	if !svc.evaluateCondition(context, zpCtxInhTestOM("type", "key_exists", "key", "nested.field2")) {
		t.Fatalf("key_exists nested.field2 = false")
	}
	if svc.evaluateCondition(context, zpCtxInhTestOM("type", "key_exists", "key", "nonexistent")) {
		t.Fatalf("key_exists nonexistent = true")
	}
	if !svc.evaluateCondition(context, zpCtxInhTestOM("type", "key_equals", "key", "status", "value", "active")) {
		t.Fatalf("key_equals active = false")
	}
	if !svc.evaluateCondition(context, zpCtxInhTestOM("type", "key_equals", "key", "nested.value", "value", 42)) {
		t.Fatalf("key_equals 42 = false")
	}
	if svc.evaluateCondition(context, zpCtxInhTestOM("type", "key_equals", "key", "status", "value", "inactive")) {
		t.Fatalf("key_equals inactive = true")
	}
	if !svc.evaluateCondition(context, zpCtxInhTestOM("type", "key_contains", "key", "message", "value", "Hello")) {
		t.Fatalf("key_contains Hello = false")
	}
	if svc.evaluateCondition(context, zpCtxInhTestOM("type", "key_contains", "key", "message", "value", "Goodbye")) {
		t.Fatalf("key_contains Goodbye = true")
	}
	if svc.evaluateCondition(context, zpCtxInhTestOM("type", "unknown")) {
		t.Fatalf("unknown condition = true")
	}
}

func TestContextInheritanceService_ValidateInheritanceChain(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)

	validTask := svc.ValidateInheritanceChain("task", "task123", zpCtxInhTestOM(
		"inheritance_metadata", zpCtxInhTestOM(
			"inherited_from", "branch",
			"inheritance_chain", []any{"global", "project", "branch", "task"},
		),
	))
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, validTask, "valid"), true)
	if len(zpCtxInhPath(t, validTask, "issues").([]any)) != 0 {
		t.Fatalf("issues = %v", zpCtxInhPath(t, validTask, "issues"))
	}

	validBranch := svc.ValidateInheritanceChain("branch", "branch123", zpCtxInhTestOM(
		"inheritance_metadata", zpCtxInhTestOM(
			"inherited_from", "project",
			"inheritance_chain", []any{"global", "project", "branch"},
		),
	))
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, validBranch, "valid"), true)

	missing := svc.ValidateInheritanceChain("task", "task123", zpCtxInhTestOM())
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, missing, "valid"), false)
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, missing, "issues"), []any{"Missing inheritance metadata"})

	incorrect := svc.ValidateInheritanceChain("task", "task123", zpCtxInhTestOM(
		"inheritance_metadata", zpCtxInhTestOM(
			"inherited_from", "branch",
			"inheritance_chain", []any{"global", "task"},
		),
	))
	warnings := zpCtxInhPath(t, incorrect, "warnings").([]any)
	if len(warnings) == 0 || !strings.Contains(value_objects.PyStr(warnings[0]), "Unexpected inheritance chain") {
		t.Fatalf("warnings = %v", warnings)
	}

	overrideMissing := svc.ValidateInheritanceChain("branch", "branch123", zpCtxInhTestOM(
		"inheritance_metadata", zpCtxInhTestOM(
			"inherited_from", "project",
			"inheritance_chain", []any{"global", "project", "branch"},
		),
		"local_overrides", zpCtxInhTestOM("nonexistent.field", "value"),
	))
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, overrideMissing, "valid"), false)
	issues := zpCtxInhPath(t, overrideMissing, "issues").([]any)
	found := false
	for _, issue := range issues {
		if strings.Contains(value_objects.PyStr(issue), "Override path not found") {
			found = true
		}
	}
	if !found {
		t.Fatalf("issues = %v", issues)
	}

	// Result key order: valid, issues, warnings, metadata.
	zpCtxInhKeyOrder(t, missing, []string{"valid", "issues", "warnings", "metadata"})
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, missing, "metadata", "context_level"), "task")
	zpCtxInhAssertEqual(t, zpCtxInhPath(t, missing, "metadata", "context_id"), "task123")
}

func TestContextInheritanceService_GetTimestamp(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	ts := svc.getTimestamp()
	if !strings.HasSuffix(ts, "Z") {
		t.Fatalf("timestamp %q does not end with Z", ts)
	}
	if !strings.Contains(ts, "T") {
		t.Fatalf("timestamp %q does not contain T", ts)
	}
}

func TestContextInheritanceService_KeyExistsAndNestedValue(t *testing.T) {
	svc := NewContextInheritanceService(nil, nil)
	context := zpCtxInhTestOM("config", zpCtxInhTestOM("database", zpCtxInhTestOM("host", "localhost")))
	zpCtxInhAssertEqual(t, svc.getNestedValue(context, "config.database.host"), "localhost")
	if !svc.keyExists(context, "config.database.host") {
		t.Fatalf("config.database.host not found")
	}
	if svc.keyExists(context, "config.nonexistent") {
		t.Fatalf("config.nonexistent found")
	}
	// A value of nil still counts as existing.
	nilContext := zpCtxInhTestOM("maybe", nil)
	if !svc.keyExists(nilContext, "maybe") {
		t.Fatalf("nil value should count as existing")
	}
}

func zpCtxInhStrPtr(s string) *string { return &s }
