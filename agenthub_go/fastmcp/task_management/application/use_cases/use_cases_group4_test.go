package use_cases

import (
	"context"
	"fmt"
	"math"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// useCasesGroup4EqualStrings compares two string slices.
func useCasesGroup4EqualStrings(a, b []string) bool {
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

// useCasesGroup4FakeContextService records rollback's update_context call.
type useCasesGroup4FakeContextService struct {
	calls         int
	lastLevel     value_objects.ContextLevel
	lastContextID string
	lastData      *entities.OrderedMap[any]
	lastUserID    string
	err           error
}

func (f *useCasesGroup4FakeContextService) UpdateContext(ctx context.Context, contextLevel value_objects.ContextLevel, contextID string, data *entities.OrderedMap[any], userID string) error {
	f.calls++
	f.lastLevel = contextLevel
	f.lastContextID = contextID
	f.lastData = data
	f.lastUserID = userID
	return f.err
}

// ---------------------------------------------------------------------------
// context_search
// ---------------------------------------------------------------------------

func TestGroup4ContextSearchEmptyQuery(t *testing.T) {
	engine := NewContextSearchEngine(nil)
	ctx := context.Background()
	levels := []value_objects.ContextLevel{value_objects.ContextLevelGlobal}

	results, err := engine.Search(ctx, NewSearchQuery("", levels))
	if err != nil || len(results) != 0 {
		t.Fatalf("empty query = %v, %v; want empty", results, err)
	}

	results, err = engine.Search(ctx, NewSearchQuery("   ", levels))
	if err != nil || len(results) != 0 {
		t.Fatalf("whitespace query = %v, %v; want empty", results, err)
	}

	// Wildcard regex passes the guard but _get_contexts_for_level returns [].
	wildcard := NewSearchQuery("*", levels)
	wildcard.Mode = SearchModeRegex
	results, err = engine.Search(ctx, wildcard)
	if err != nil || len(results) != 0 {
		t.Fatalf("wildcard query = %v, %v; want empty", results, err)
	}
}

func TestGroup4ContextSearchContainsScoringAndHighlighting(t *testing.T) {
	engine := NewContextSearchEngine(nil)

	data := entities.NewOrderedMap[any]()
	data.Set("content", "world world")

	score, matches := engine.calculateRelevance(data, "world", SearchModeContains)
	if math.Abs(score-0.4) > 1e-12 {
		t.Fatalf("contains score = %v, want 0.4", score)
	}
	if len(matches) != 2 {
		t.Fatalf("matches = %d, want 2", len(matches))
	}
	if pos, _ := matches[0].Get("position"); pos != 8 {
		t.Fatalf("first position = %v, want 8", pos)
	}
	if pos, _ := matches[1].Get("position"); pos != 14 {
		t.Fatalf("second position = %v, want 14", pos)
	}
	if matched, _ := matches[0].Get("matched"); matched != "world" {
		t.Fatalf("first matched = %v, want world", matched)
	}

	results := []*SearchResult{{Matches: matches}}
	engine.highlightMatches(results, "world")
	highlighted, _ := matches[0].Get("highlighted")
	if highlighted != "**world**" {
		t.Fatalf("highlighted = %v, want **world**", highlighted)
	}

	// Important-field boost: name and description each contribute 1.5.
	boosted := entities.NewOrderedMap[any]()
	boosted.Set("name", "Hello World")
	boosted.Set("description", "world of go")
	boostedScore, _ := engine.calculateRelevance(boosted, "world", SearchModeContains)
	if math.Abs(boostedScore-0.9) > 1e-12 {
		t.Fatalf("boosted score = %v, want 0.9", boostedScore)
	}
}

func TestGroup4ContextSearchFuzzyAndSimilarity(t *testing.T) {
	engine := NewContextSearchEngine(nil)

	cases := []struct {
		s1, s2 string
		want   float64
	}{
		{"", "", 1.0},
		{"abc", "", 0.0},
		{"", "abc", 0.0},
		{"abc", "abc", 1.0},
		{"ABC", "abc", 1.0},
		{"abc", "abcdef", 0.5},
		{"abcd", "abce", 0.6},
		{"abcdefgh", "abcdefgi", 0.75},
	}
	for _, c := range cases {
		if got := engine.stringSimilarity(c.s1, c.s2); math.Abs(got-c.want) > 1e-12 {
			t.Fatalf("stringSimilarity(%q, %q) = %v, want %v", c.s1, c.s2, got, c.want)
		}
	}

	if got := engine.fuzzyScore("wrld", "hello world"); math.Abs(got-0.8) > 1e-12 {
		t.Fatalf("fuzzyScore = %v, want 0.8", got)
	}

	// FUZZY mode reports a match only when the score is > 0.5.
	data := entities.NewOrderedMap[any]()
	data.Set("content", "hello world")
	score, matches := engine.calculateRelevance(data, "wrld", SearchModeFuzzy)
	if math.Abs(score-0.8) > 1e-12 || len(matches) != 1 {
		t.Fatalf("fuzzy relevance = %v, %d matches; want 0.8, 1", score, len(matches))
	}
}

func TestGroup4ContextSearchRegex(t *testing.T) {
	engine := NewContextSearchEngine(nil)

	data := entities.NewOrderedMap[any]()
	data.Set("x", "abc")

	// Invalid pattern: the re.error branch is a no-op.
	score, matches := engine.calculateRelevance(data, "[", SearchModeRegex)
	if score != 0.0 || len(matches) != 0 {
		t.Fatalf("invalid regex = %v, %d matches; want 0.0, 0", score, len(matches))
	}

	// Valid pattern with one match.
	score, matches = engine.calculateRelevance(data, "a.c", SearchModeRegex)
	if math.Abs(score-0.2) > 1e-12 || len(matches) != 1 {
		t.Fatalf("regex relevance = %v, %d matches; want 0.2, 1", score, len(matches))
	}
	if matched, _ := matches[0].Get("matched"); matched != "abc" {
		t.Fatalf("regex matched = %v, want abc", matched)
	}
	if pos, _ := matches[0].Get("position"); pos != 2 {
		t.Fatalf("regex position = %v, want 2", pos)
	}

	// Wildcard.
	score, matches = engine.calculateRelevance(data, "*", SearchModeRegex)
	if score != 0.5 || len(matches) != 1 {
		t.Fatalf("wildcard = %v, %d matches; want 0.5, 1", score, len(matches))
	}
	if wildcard, _ := matches[0].Get("wildcard"); wildcard != true {
		t.Fatalf("wildcard flag = %v, want true", wildcard)
	}
}

func TestGroup4ContextSearchExpandLevels(t *testing.T) {
	engine := NewContextSearchEngine(nil)

	got := engine.expandSearchLevels([]value_objects.ContextLevel{value_objects.ContextLevelBranch}, SearchScopeWithChildren)
	want := []value_objects.ContextLevel{value_objects.ContextLevelBranch, value_objects.ContextLevelTask}
	if len(got) != len(want) || got[0] != want[0] || got[1] != want[1] {
		t.Fatalf("with children = %v, want %v", got, want)
	}

	got = engine.expandSearchLevels([]value_objects.ContextLevel{value_objects.ContextLevelTask}, SearchScopeWithParents)
	wantAll := []value_objects.ContextLevel{
		value_objects.ContextLevelGlobal,
		value_objects.ContextLevelProject,
		value_objects.ContextLevelBranch,
		value_objects.ContextLevelTask,
	}
	if len(got) != len(wantAll) {
		t.Fatalf("with parents = %v, want %v", got, wantAll)
	}
	for i := range wantAll {
		if got[i] != wantAll[i] {
			t.Fatalf("with parents[%d] = %v, want %v", i, got[i], wantAll[i])
		}
	}

	got = engine.expandSearchLevels(nil, SearchScopeAllLevels)
	if len(got) != len(wantAll) {
		t.Fatalf("all levels = %v, want %v", got, wantAll)
	}

	got = engine.expandSearchLevels([]value_objects.ContextLevel{value_objects.ContextLevelGlobal}, SearchScopeCurrentLevel)
	if len(got) != 1 || got[0] != value_objects.ContextLevelGlobal {
		t.Fatalf("current level = %v, want [global]", got)
	}
}

// ---------------------------------------------------------------------------
// context_versioning
// ---------------------------------------------------------------------------

func TestGroup4ContextVersioningDeltaAndNumbering(t *testing.T) {
	svc := NewContextVersioningService(nil)
	ctx := context.Background()

	d1 := entities.NewOrderedMap[any]()
	d1.Set("a", int64(1))
	d1.Set("b", int64(2))

	v1, err := svc.CreateVersion(ctx, value_objects.ContextLevelProject, "ctx1", d1, ChangeTypeCreate, "init", "u1", false, nil)
	if err != nil {
		t.Fatalf("create v1: %v", err)
	}
	if v1.VersionNumber != 1 {
		t.Fatalf("v1 number = %d, want 1", v1.VersionNumber)
	}
	if len(v1.VersionID) < len("v_ctx1_1_") || v1.VersionID[:len("v_ctx1_1_")] != "v_ctx1_1_" {
		t.Fatalf("v1 id = %q, want prefix v_ctx1_1_", v1.VersionID)
	}
	if v1.ParentVersionID != nil || v1.Delta != nil {
		t.Fatalf("v1 should have no parent/delta")
	}
	if v1.Data == d1 {
		t.Fatalf("v1 data must be a shallow copy")
	}
	if v1.Tags == nil || len(v1.Tags) != 0 {
		t.Fatalf("v1 tags = %v, want empty", v1.Tags)
	}

	d2 := entities.NewOrderedMap[any]()
	d2.Set("a", int64(1))
	d2.Set("b", int64(3))
	d2.Set("c", int64(4))

	v2, err := svc.CreateVersion(ctx, value_objects.ContextLevelProject, "ctx1", d2, ChangeTypeUpdate, "change", "u1", false, nil)
	if err != nil {
		t.Fatalf("create v2: %v", err)
	}
	if v2.VersionNumber != 2 {
		t.Fatalf("v2 number = %d, want 2", v2.VersionNumber)
	}
	if v2.ParentVersionID == nil || *v2.ParentVersionID != v1.VersionID {
		t.Fatalf("v2 parent = %v, want %v", v2.ParentVersionID, v1.VersionID)
	}
	if len(v1.ChildVersionIDs) != 1 || v1.ChildVersionIDs[0] != v2.VersionID {
		t.Fatalf("v1 children = %v, want [%v]", v1.ChildVersionIDs, v2.VersionID)
	}

	added, _ := v2.Delta.Get("added")
	addedMap, ok := added.(*entities.OrderedMap[any])
	if !ok || !useCasesGroup4EqualStrings(addedMap.Keys(), []string{"c"}) {
		t.Fatalf("delta.added keys = %v, want [c]", added)
	}
	modified, _ := v2.Delta.Get("modified")
	modifiedMap, ok := modified.(*entities.OrderedMap[any])
	if !ok || !useCasesGroup4EqualStrings(modifiedMap.Keys(), []string{"b"}) {
		t.Fatalf("delta.modified keys = %v, want [b]", modified)
	}
	removed, _ := v2.Delta.Get("removed")
	if removedList, ok := removed.([]string); !ok || len(removedList) != 0 {
		t.Fatalf("delta.removed = %v, want []", removed)
	}

	// A third version drops b and c.
	d3 := entities.NewOrderedMap[any]()
	d3.Set("a", int64(1))
	v3, err := svc.CreateVersion(ctx, value_objects.ContextLevelProject, "ctx1", d3, ChangeTypeUpdate, "drop", "u1", false, nil)
	if err != nil {
		t.Fatalf("create v3: %v", err)
	}
	removed, _ = v3.Delta.Get("removed")
	if removedList, ok := removed.([]string); !ok || !useCasesGroup4EqualStrings(removedList, []string{"b", "c"}) {
		t.Fatalf("v3 delta.removed = %v, want [b c]", removed)
	}
}

func TestGroup4ContextVersioningGetDiff(t *testing.T) {
	svc := NewContextVersioningService(nil)
	ctx := context.Background()

	d1 := entities.NewOrderedMap[any]()
	d1.Set("a", int64(1))
	d1.Set("b", int64(2))
	v1, _ := svc.CreateVersion(ctx, value_objects.ContextLevelProject, "ctx1", d1, ChangeTypeCreate, "init", "u1", false, nil)

	d2 := entities.NewOrderedMap[any]()
	d2.Set("a", int64(1))
	d2.Set("b", int64(3))
	d2.Set("c", int64(4))
	v2, _ := svc.CreateVersion(ctx, value_objects.ContextLevelProject, "ctx1", d2, ChangeTypeUpdate, "change", "u1", false, nil)

	diff := svc.GetDiff(ctx, v1.VersionID, v2.VersionID)
	if diff == nil {
		t.Fatalf("diff is nil")
	}
	if !useCasesGroup4EqualStrings(diff.Added.Keys(), []string{"c"}) {
		t.Fatalf("diff.added keys = %v, want [c]", diff.Added.Keys())
	}
	if !useCasesGroup4EqualStrings(diff.Modified.Keys(), []string{"b"}) {
		t.Fatalf("diff.modified keys = %v, want [b]", diff.Modified.Keys())
	}
	if len(diff.Removed) != 0 {
		t.Fatalf("diff.removed = %v, want []", diff.Removed)
	}

	wantDiff := "--- Version 1\n" +
		"+++ Version 2\n" +
		"@@ -1,4 +1,5 @@\n" +
		" {\n" +
		"   \"a\": 1,\n" +
		"-  \"b\": 2\n" +
		"+  \"b\": 3,\n" +
		"+  \"c\": 4\n" +
		" }"
	if diff.UnifiedDiff != wantDiff {
		t.Fatalf("unified diff =\n%q\nwant\n%q", diff.UnifiedDiff, wantDiff)
	}

	// v2 -> v3 removes b and c.
	d3 := entities.NewOrderedMap[any]()
	d3.Set("a", int64(1))
	v3, _ := svc.CreateVersion(ctx, value_objects.ContextLevelProject, "ctx1", d3, ChangeTypeUpdate, "drop", "u1", false, nil)

	removedDiff := svc.GetDiff(ctx, v2.VersionID, v3.VersionID)
	if removedDiff == nil {
		t.Fatalf("removed diff is nil")
	}
	if !useCasesGroup4EqualStrings(removedDiff.Removed, []string{"b", "c"}) {
		t.Fatalf("removed = %v, want [b c]", removedDiff.Removed)
	}
	if !useCasesGroup4EqualStrings(removedDiff.Added.Keys(), []string{}) || !useCasesGroup4EqualStrings(removedDiff.Modified.Keys(), []string{}) {
		t.Fatalf("removed diff added/modified should be empty")
	}

	if svc.GetDiff(ctx, "missing", v1.VersionID) != nil {
		t.Fatalf("diff with a missing version should be nil")
	}
}

func TestGroup4ContextVersioningRollback(t *testing.T) {
	fake := &useCasesGroup4FakeContextService{}
	svc := NewContextVersioningService(fake)
	ctx := context.Background()
	level := value_objects.ContextLevelProject

	d1 := entities.NewOrderedMap[any]()
	d1.Set("x", int64(1))
	v1, _ := svc.CreateVersion(ctx, level, "ctxR", d1, ChangeTypeCreate, "init", "u1", false, nil)

	d2 := entities.NewOrderedMap[any]()
	d2.Set("x", int64(2))
	_, _ = svc.CreateVersion(ctx, level, "ctxR", d2, ChangeTypeUpdate, "change", "u1", false, nil)

	rollback, err := svc.Rollback(ctx, level, "ctxR", v1.VersionID, "user7", "oops")
	if err != nil {
		t.Fatalf("rollback: %v", err)
	}
	if rollback.VersionNumber != 3 || rollback.ChangeType != ChangeTypeRollback {
		t.Fatalf("rollback version = %d, %s; want 3, rollback", rollback.VersionNumber, rollback.ChangeType)
	}
	if rollback.ChangeSummary != "Rollback to version 1: oops" {
		t.Fatalf("rollback summary = %q", rollback.ChangeSummary)
	}
	if !useCasesGroup4EqualStrings(rollback.Tags, []string{"rollback_from_v1"}) {
		t.Fatalf("rollback tags = %v, want [rollback_from_v1]", rollback.Tags)
	}
	if x, _ := rollback.Data.Get("x"); x != int64(1) {
		t.Fatalf("rollback data x = %v, want 1", x)
	}

	if fake.calls != 1 || fake.lastData != v1.Data || fake.lastUserID != "user7" || fake.lastLevel != level || fake.lastContextID != "ctxR" {
		t.Fatalf("context service call not recorded as expected: %+v", fake)
	}

	if _, err := svc.Rollback(ctx, level, "ctxR", "missing", "u", "r"); err == nil {
		t.Fatalf("rollback to a missing version should error")
	}
	if _, err := svc.Rollback(ctx, value_objects.ContextLevelTask, "other", v1.VersionID, "u", "r"); err == nil {
		t.Fatalf("rollback of a different context should error")
	}
}

func TestGroup4ContextVersioningPrune(t *testing.T) {
	svc := NewContextVersioningService(nil)
	ctx := context.Background()
	level := value_objects.ContextLevelBranch

	var ids []string
	for i := 1; i <= 5; i++ {
		data := entities.NewOrderedMap[any]()
		data.Set("i", int64(i))
		v, _ := svc.CreateVersion(ctx, level, "ctxP", data, ChangeTypeUpdate, "n", "u", false, nil)
		ids = append(ids, v.VersionID)
	}

	pruned := svc.PruneOldVersions(ctx, level, "ctxP", 2, true)
	if pruned != 3 || len(svc.Versions) != 2 {
		t.Fatalf("prune = %d, versions = %d; want 3, 2", pruned, len(svc.Versions))
	}
	if !useCasesGroup4EqualStrings(svc.VersionChains[contextVersioningKey{string(level), "ctxP"}], []string{ids[3], ids[4]}) {
		t.Fatalf("remaining chain = %v, want last two", svc.VersionChains[contextVersioningKey{string(level), "ctxP"}])
	}

	// keep_milestones skips milestone versions in the pruned prefix.
	msvc := NewContextVersioningService(nil)
	var mids []string
	for i := 1; i <= 4; i++ {
		data := entities.NewOrderedMap[any]()
		data.Set("i", int64(i))
		v, _ := msvc.CreateVersion(ctx, level, "ctxM", data, ChangeTypeUpdate, "n", "u", i == 2, nil)
		mids = append(mids, v.VersionID)
	}
	pruned = msvc.PruneOldVersions(ctx, level, "ctxM", 1, true)
	if pruned != 2 || len(msvc.Versions) != 2 {
		t.Fatalf("milestone prune = %d, versions = %d; want 2, 2", pruned, len(msvc.Versions))
	}
	if !msvc.Versions[mids[1]].IsMilestone {
		t.Fatalf("milestone version should be kept")
	}
	if _, ok := msvc.Versions[mids[3]]; !ok {
		t.Fatalf("newest version should be kept")
	}
}

func TestGroup4ContextVersioningMerge(t *testing.T) {
	svc := NewContextVersioningService(nil)
	ctx := context.Background()
	level := value_objects.ContextLevelGlobal

	d1 := entities.NewOrderedMap[any]()
	d1.Set("a", int64(1))
	d1.Set("shared", "first")
	v1, _ := svc.CreateVersion(ctx, level, "ctxG", d1, ChangeTypeCreate, "n", "u", false, nil)

	d2 := entities.NewOrderedMap[any]()
	d2.Set("b", int64(2))
	d2.Set("shared", "second")
	v2, _ := svc.CreateVersion(ctx, level, "ctxG", d2, ChangeTypeCreate, "n", "u", false, nil)

	merged, err := svc.MergeVersions(ctx, level, "ctxG", []string{v1.VersionID, v2.VersionID}, "union", "u")
	if err != nil {
		t.Fatalf("merge union: %v", err)
	}
	if !useCasesGroup4EqualStrings(merged.Data.Keys(), []string{"a", "shared", "b"}) {
		t.Fatalf("union keys = %v, want [a shared b]", merged.Data.Keys())
	}
	if shared, _ := merged.Data.Get("shared"); shared != "second" {
		t.Fatalf("union shared = %v, want second", shared)
	}
	if !useCasesGroup4EqualStrings(merged.Tags, []string{"merged_v1", "merged_v2"}) {
		t.Fatalf("merge tags = %v", merged.Tags)
	}

	if _, err := svc.MergeVersions(ctx, level, "ctxG", []string{v1.VersionID, v2.VersionID}, "bogus", "u"); err == nil {
		t.Fatalf("unknown merge strategy should error")
	}
	if _, err := svc.MergeVersions(ctx, level, "ctxG", []string{v1.VersionID}, "union", "u"); err == nil {
		t.Fatalf("fewer than 2 versions should error")
	}
}

// ---------------------------------------------------------------------------
// rule_orchestration_use_case
// ---------------------------------------------------------------------------

func TestGroup4RuleOrchestrationStaticKeyOrder(t *testing.T) {
	u := NewRuleOrchestrationUseCase()

	info := u.GetEnhancedRuleInfo()
	if !useCasesGroup4EqualStrings(info.Keys(), []string{"success", "phase_5_features", "cache_type", "performance_features_enabled"}) {
		t.Fatalf("GetEnhancedRuleInfo keys = %v", info.Keys())
	}
	phase5, _ := info.Get("phase_5_features")
	phase5Map, ok := phase5.(*entities.OrderedMap[any])
	if !ok || !useCasesGroup4EqualStrings(phase5Map.Keys(), []string{"enhanced_caching", "performance_monitoring", "cache_optimization", "benchmarking"}) {
		t.Fatalf("phase_5_features keys = %v", phase5)
	}

	nested := u.LoadNestedRules("/tmp/rules/root")
	if !useCasesGroup4EqualStrings(nested.Keys(), []string{"success", "action", "root_path", "nested_rules_loaded"}) {
		t.Fatalf("LoadNestedRules keys = %v", nested.Keys())
	}
	if root, _ := nested.Get("root_path"); root != "/tmp/rules/root" {
		t.Fatalf("root_path = %v", root)
	}

	composed := u.ComposeNestedRules("a/b")
	if !useCasesGroup4EqualStrings(composed.Keys(), []string{"success", "action", "rule_path", "composed_rules"}) {
		t.Fatalf("ComposeNestedRules keys = %v", composed.Keys())
	}

	cacheStatus := u.GetCacheStatus()
	if !useCasesGroup4EqualStrings(cacheStatus.Keys(), []string{"success", "action", "cache_type", "performance_features_enabled", "cache_statistics"}) {
		t.Fatalf("GetCacheStatus keys = %v", cacheStatus.Keys())
	}
}

func TestGroup4RuleOrchestrationLoadCoreRulesNotFound(t *testing.T) {
	u := NewRuleOrchestrationUseCase()

	notFound := u.LoadCoreRules("rules/core/group4-does-not-exist-xyz.md")
	if !useCasesGroup4EqualStrings(notFound.Keys(), []string{"success", "action", "target", "error", "file_path", "rules_directory", "core_directory", "available_files", "runtime_mode"}) {
		t.Fatalf("not-found keys = %v", notFound.Keys())
	}
	if success, _ := notFound.Get("success"); success != false {
		t.Fatalf("not-found success = %v, want false", success)
	}
	if action, _ := notFound.Get("action"); action != "load_core" {
		t.Fatalf("not-found action = %v", action)
	}
	if errText, _ := notFound.Get("error"); errText != "Rule file not found: group4-does-not-exist-xyz.md" {
		t.Fatalf("not-found error = %v", errText)
	}

	noTarget := u.LoadCoreRules("")
	if !useCasesGroup4EqualStrings(noTarget.Keys(), []string{"success", "action", "core_rules_loaded", "rules_directory", "runtime_mode"}) {
		t.Fatalf("no-target keys = %v", noTarget.Keys())
	}
	if success, _ := noTarget.Get("success"); success != true {
		t.Fatalf("no-target success = %v, want true", success)
	}
	if mode, _ := noTarget.Get("runtime_mode"); mode != "http" && mode != "stdio" {
		t.Fatalf("no-target runtime_mode = %v", mode)
	}
}

func TestGroup4ContextVersioningHashAndStats(t *testing.T) {
	svc := NewContextVersioningService(nil)
	ctx := context.Background()

	d := entities.NewOrderedMap[any]()
	d.Set("a", int64(1))
	d.Set("b", int64(2))
	v, _ := svc.CreateVersion(ctx, value_objects.ContextLevelProject, "ctxH", d, ChangeTypeCreate, "n", "u", false, nil)

	// json.dumps({"a":1,"b":2}, sort_keys=True) = {"a": 1, "b": 2}
	hash, err := v.GetHash()
	if err != nil || hash != "d8497d9d82770a70729261095aa98f7ef5154d7af499f8037b6ca250296785a6" {
		t.Fatalf("hash = %q, %v", hash, err)
	}

	// Nested dicts and lists are sorted recursively like sort_keys=True.
	nested := entities.NewOrderedMap[any]()
	inner := entities.NewOrderedMap[any]()
	inner.Set("y", int64(2))
	inner.Set("x", int64(3))
	listItem := entities.NewOrderedMap[any]()
	listItem.Set("q", int64(1))
	listItem.Set("p", int64(2))
	nested.Set("z", int64(1))
	nested.Set("a", inner)
	nested.Set("m", []any{listItem})
	nestedHash, err := (&ContextVersion{Data: nested}).GetHash()
	if err != nil || nestedHash != "e71eef4a92613090e00b2c3290abc11944f7f19b51e86e2719d8c3b5b4c7df1e" {
		t.Fatalf("nested hash = %q, %v", nestedHash, err)
	}

	stats := svc.GetStorageStats()
	if !useCasesGroup4EqualStrings(stats.Keys(), []string{"total_versions", "total_size_bytes", "contexts_tracked", "average_versions_per_context"}) {
		t.Fatalf("stats keys = %v", stats.Keys())
	}
	if tv, _ := stats.Get("total_versions"); tv != 1 {
		t.Fatalf("total_versions = %v", tv)
	}
	if sz, _ := stats.Get("total_size_bytes"); sz != 16 {
		t.Fatalf("total_size_bytes = %v", sz)
	}
	if contexts, _ := stats.Get("contexts_tracked"); contexts != 1 {
		t.Fatalf("contexts_tracked = %v", contexts)
	}
	if avg, _ := stats.Get("average_versions_per_context"); avg != 1.0 {
		t.Fatalf("average = %v", avg)
	}

	// No contexts -> Python int 0, not a float.
	empty := NewContextVersioningService(nil).GetStorageStats()
	if avg, _ := empty.Get("average_versions_per_context"); avg != 0 {
		t.Fatalf("empty average = %v (%T), want int 0", avg, avg)
	}
}

func TestGroup4ContextVersioningUnifiedDiff(t *testing.T) {
	small := []struct {
		name string
		a, b []string
		want string
	}{
		{"unchanged", []string{"{", `  "a": 1`, "}"}, []string{"{", `  "a": 1`, "}"}, ""},
		{
			"replace-one",
			[]string{"{", `  "a": 1`, "}"},
			[]string{"{", `  "a": 2`, "}"},
			"--- Version 1\n+++ Version 2\n@@ -1,3 +1,3 @@\n {\n-  \"a\": 1\n+  \"a\": 2\n }",
		},
		{"insert-end", []string{"a", "b", "c"}, []string{"a", "b", "c", "d"}, "--- Version 1\n+++ Version 2\n@@ -1,3 +1,4 @@\n a\n b\n c\n+d"},
		{"delete-start", []string{"a", "b", "c"}, []string{"b", "c"}, "--- Version 1\n+++ Version 2\n@@ -1,3 +1,2 @@\n-a\n b\n c"},
		{"single-group", []string{"a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"}, []string{"a", "b", "c", "d", "e", "f", "g", "h", "i", "X", "k"}, "--- Version 1\n+++ Version 2\n@@ -7,5 +7,5 @@\n g\n h\n i\n-j\n+X\n k"},
		{"repeated", []string{"x", "x", "x"}, []string{"x", "x", "x"}, ""},
		{"empty", []string{}, []string{}, ""},
		{"trailing-window", []string{"same1", "same2", "same3", "same4", "same5", "same6", "same7", "old"}, []string{"same1", "same2", "same3", "same4", "same5", "same6", "same7", "new"}, "--- Version 1\n+++ Version 2\n@@ -5,4 +5,4 @@\n same5\n same6\n same7\n-old\n+new"},
		{"two-to-one", []string{"a", "b", "old1", "old2", "c", "d"}, []string{"a", "b", "new", "c", "d"}, "--- Version 1\n+++ Version 2\n@@ -1,6 +1,5 @@\n a\n b\n-old1\n-old2\n+new\n c\n d"},
		{"insert-middle", []string{"1", "2", "3"}, []string{"1", "X", "2", "3"}, "--- Version 1\n+++ Version 2\n@@ -1,3 +1,4 @@\n 1\n+X\n 2\n 3"},
	}

	for _, c := range small {
		if got := contextVersioningUnifiedDiff(c.a, c.b, "Version 1", "Version 2"); got != c.want {
			t.Fatalf("%s: got %q want %q", c.name, got, c.want)
		}
	}

	// Two changes far apart produce two groups (equal run longer than 2*3).
	a := []string{"L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10", "L11", "L12", "L13", "L14", "L15", "L16", "L17", "L18", "L19"}
	b := append([]string{}, a...)
	b[2] = "X"
	b[17] = "Y"
	wantGroups := "--- Version 1\n+++ Version 2\n@@ -1,6 +1,6 @@\n L0\n L1\n-L2\n+X\n L3\n L4\n L5\n@@ -15,6 +15,6 @@\n L14\n L15\n L16\n-L17\n+Y\n L18\n L19"
	if got := contextVersioningUnifiedDiff(a, b, "Version 1", "Version 2"); got != wantGroups {
		t.Fatalf("two groups: got %q want %q", got, wantGroups)
	}

	// >=200 lines with a popular element exercises autojunk (difflib purges
	// b-elements occurring more than n/100+1 times).
	big := []string{}
	for i := 0; i < 150; i++ {
		big = append(big, "dup")
	}
	for i := 0; i < 60; i++ {
		big = append(big, fmt.Sprintf("u%d", i))
	}
	changed := append([]string{}, big...)
	changed[140] = "CHANGED"
	wantAutojunk := "--- Version 1\n+++ Version 2\n@@ -138,7 +138,7 @@\n dup\n dup\n dup\n-dup\n+CHANGED\n dup\n dup\n dup"
	if got := contextVersioningUnifiedDiff(big, changed, "Version 1", "Version 2"); got != wantAutojunk {
		t.Fatalf("autojunk: got %q want %q", got, wantAutojunk)
	}
}
