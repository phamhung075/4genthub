package intelligence

import (
	"reflect"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

type peFixture struct {
	fx       map[string]any
	now      time.Time
	contexts []map[string]any
	current  map[string]any
	sims     map[string]float64
}

func peLoad(t *testing.T) peFixture {
	f := peFixture{fx: loadJSON(t, "testdata/progressive_expander_cases.json")}
	f.now = mustTime(t, f.fx["now"].(string))
	for _, c := range f.fx["contexts"].([]any) {
		f.contexts = append(f.contexts, c.(map[string]any))
	}
	f.current = f.fx["current"].(map[string]any)
	f.sims = map[string]float64{}
	for k, v := range f.fx["sims"].(map[string]any) {
		f.sims[k] = v.(float64)
	}
	return f
}

func (f peFixture) expander(t *testing.T) *ProgressiveExpander {
	e := DefaultProgressiveExpander()
	e.Now = func() time.Time { return f.now }
	for _, id := range []string{"a", "b", "c"} {
		e.recordContextAccess(id)
	}
	for _, id := range []string{"a", "b", "c"} {
		p, _ := e.ContextAccessPatterns.Get(id)
		pre := f.fx["presets"].(map[string]any)[id].(map[string]any)
		p.AccessCount = int(pre["access_count"].(int64))
		p.TotalSessions = int(pre["total_sessions"].(int64))
		if last, ok := pre["last"].(string); ok {
			tm := mustTime(t, last)
			p.LastAccessed = &tm
		}
		for _, k := range pre["kw"].([]any) {
			p.CommonKeywords = append(p.CommonKeywords, k.(string))
		}
	}
	return e
}

func candKey(c ExpansionCandidate) []any {
	return []any{c.ContextID, string(c.ContextLevel), c.ContextType, c.PriorityScore, int64(c.EstimatedTokens), string(c.Trigger), c.SimilarityScore}
}

func TestProgressiveExpanderCandidatesMatchPython(t *testing.T) {
	f := peLoad(t)
	e := f.expander(t)
	queries := map[string]string{"login": "login flow oauth", "empty": "", "other": "zzz"}
	for key, want := range f.fx["ident"].(map[string]any) {
		qn, sn, _ := strings.Cut(key, "|")
		var sims map[string]float64
		switch sn {
		case "sims":
			sims = f.sims
		case "empty":
			sims = map[string]float64{}
		}
		got := e.IdentifyExpansionCandidates(f.current, queries[qn], f.contexts, sims)
		w := want.([]any)
		if len(got) != len(w) {
			t.Errorf("%s: %d candidates want %d", key, len(got), len(w))
			continue
		}
		for i, c := range got {
			m := w[i].(map[string]any)
			wantKey := []any{value_objects.PyStr(m["id"]), m["level"], m["type"], m["prio"], m["tokens"], m["trigger"], m["sim"]}
			if !reflect.DeepEqual(candKey(c), wantKey) {
				t.Errorf("%s[%d]: got %v want %v", key, i, candKey(c), wantKey)
			}
		}
	}
	for i, c := range f.contexts {
		if got := e.EstimateContextTokens(c); int64(got) != f.fx["tokens"].([]any)[i] {
			t.Errorf("tokens[%d] = %d want %v", i, got, f.fx["tokens"].([]any)[i])
		}
	}
}

func TestProgressiveExpanderExpansionAndStatsMatchPython(t *testing.T) {
	f := peLoad(t)
	e := f.expander(t)
	cands := e.IdentifyExpansionCandidates(f.current, "login", f.contexts, f.sims)
	cl := append([]ExpansionCandidate{{ContextID: "a", ContextLevel: ContextLevelTask, ContextType: "task", PriorityScore: 0.95,
		EstimatedTokens: 40, Trigger: TriggerUserRequest, ContextData: f.contexts[0]}}, cands...)
	for i, want := range f.fx["expand"].([]any) {
		w := want.(map[string]any)
		var budget *int
		if b, ok := w["budget"].(int64); ok {
			v := int(b)
			budget = &v
		}
		r := e.ExpandContextProgressive(f.current, cl, budget, w["agg"].(bool))
		var path, pre []string
		for _, p := range w["path"].([]any) {
			path = append(path, p.(string))
		}
		for _, p := range w["prefetched"].([]any) {
			pre = append(pre, p.(string))
		}
		if int64(r.TotalTokensUsed) != w["tokens_used"] || int64(r.RemainingTokenBudget) != w["remaining"] ||
			int64(len(r.ExpandedContexts)) != w["n"] || !equalOrBothEmpty(r.ExpansionPath, path) || !equalOrBothEmpty(r.PrefetchedContexts, pre) {
			t.Errorf("step %d: got %+v want %v", i, r, w)
		}
	}
	s, w := e.GetExpansionStats(), f.fx["stats"].(map[string]any)
	if int64(s.TotalExpansions) != w["total_expansions"] || s.AvgTokensUsed != w["avg_tokens_used"].(float64) ||
		s.AvgContextsExpanded != w["avg_contexts_expanded"].(float64) || int64(s.TrackedContextPatterns) != w["tracked_context_patterns"] {
		t.Errorf("stats %+v want %v", s, w)
	}
	if DefaultProgressiveExpander().GetExpansionStats() != nil {
		t.Error("empty stats must be nil")
	}
	for id, want := range f.fx["patterns"].(map[string]any) {
		p, ok := e.ContextAccessPatterns.Get(id)
		wm := want.(map[string]any)
		if !ok || int64(p.AccessCount) != wm["count"] || (p.LastAccessed == nil) != (wm["last"] == nil) ||
			(p.LastAccessed != nil && !p.LastAccessed.Equal(mustTime(t, wm["last"].(string)))) {
			t.Errorf("pattern %s: %+v want %v", id, p, wm)
		}
	}
}

func equalOrBothEmpty(a, b []string) bool {
	return (len(a) == 0 && len(b) == 0) || reflect.DeepEqual(a, b)
}
