package intelligence

import (
	"reflect"
	"strconv"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

func icsIDs(cs []map[string]any) []string {
	out := []string{}
	for _, c := range cs {
		if v, ok := c["id"].(string); ok && v != "" {
			out = append(out, v)
		} else {
			out = append(out, c["context_id"].(string))
		}
	}
	return out
}

func icsMetadata(m *entities.OrderedMap[any]) [][2]any {
	out := [][2]any{}
	for _, k := range m.Keys() {
		v, _ := m.Get(k)
		if p, ok := v.([]string); ok && len(p) == 0 {
			v = []any{}
		}
		out = append(out, [2]any{k, v})
	}
	return out
}

func icsWantMetadata(v any) [][2]any {
	out := [][2]any{}
	for _, p := range v.([]any) {
		pp := p.([]any)
		val := pp[1]
		if f, ok := val.(int64); ok {
			val = int(f)
		}
		out = append(out, [2]any{pp[0].(string), val})
	}
	return out
}

func icsContexts(fx map[string]any) []map[string]any {
	var out []map[string]any
	for _, c := range fx["contexts"].([]any) {
		out = append(out, c.(map[string]any))
	}
	return out
}

func newTestSelector(t *testing.T, clock *time.Time) *IntelligentContextSelector {
	cfg := DefaultSelectorConfig()
	cfg.CacheDir = t.TempDir()
	s, err := NewIntelligentContextSelector(cfg)
	if err != nil {
		t.Fatal(err)
	}
	now := func() time.Time { return *clock }
	s.Now, s.PredictiveLoader.Now, s.ContextPrioritizer.Now, s.ProgressiveExpander.Now = now, now, now, now
	return s
}

func TestIntelligentContextSelectorMatchesPython(t *testing.T) {
	fx := loadJSON(t, "testdata/intelligent_context_selector_cases.json")
	clock := mustTime(t, "2026-03-01T10:00:00Z")
	s := newTestSelector(t, &clock)
	s.LoadAvailableContexts(icsContexts(fx))

	// The Python script advances the clock at fixed points between selections 2..4.
	advances := map[int]time.Duration{2: 10 * time.Second, 3: 400 * time.Second}
	sel := 0
	results := fx["res"].([]any)
	for _, o := range fx["ops"].([]any) {
		op := o.([]any)
		switch op[0].(string) {
		case "select":
			if d, ok := advances[sel]; ok {
				clock = clock.Add(d)
			}
			var task map[string]any
			if m, ok := op[3].(map[string]any); ok {
				task = m
			}
			r := s.SelectContext(op[1].(string), int(plFloat(op[2])), SelectOptions{CurrentTask: task})
			w := results[sel].(map[string]any)
			sel++
			if !reflect.DeepEqual(icsIDs(r.SelectedContexts), plStrings(w["ids"])) ||
				r.TotalTokensUsed != int(plFloat(w["tokens"])) || r.HitRateEstimate != plFloat(w["hit"]) ||
				r.SizeReductionPct != plFloat(w["red"]) || r.SelectionTimeMs != plFloat(w["time"]) ||
				!reflect.DeepEqual(icsMetadata(r.Metadata), icsWantMetadata(w["md"])) {
				t.Fatalf("select %d (%v): got %+v ids=%v md=%v\nwant %v", sel, op[1], r, icsIDs(r.SelectedContexts), icsMetadata(r.Metadata), w)
			}
		case "start":
			uid := op[2].(string)
			s.StartSession(op[1].(string), &uid)
		case "tool":
			s.RecordToolUsage(op[1].(string), op[2].(string))
		case "access":
			s.PredictiveLoader.RecordContextAccess(op[1].(string), op[2].(string))
		case "end":
			r := s.EndSession()
			if r == nil || !reflect.DeepEqual(r.ToolSequence, plStrings(fx["end_tools"])) || !reflect.DeepEqual(r.ContextSequence, plStrings(fx["end_ctx"])) {
				t.Fatalf("end: %+v", r)
			}
		}
	}
	if s.EndSession() != nil {
		t.Fatal("second EndSession must return nothing")
	}

	st, err := s.GetPerformanceStats()
	if err != nil {
		t.Fatal(err)
	}
	ws := fx["stats"].(map[string]any)
	if st.TotalSelections != int(plFloat(ws["total_selections"])) || st.AvgSelectionTimeMs != plFloat(ws["avg_selection_time_ms"]) ||
		st.AvgHitRate != plFloat(ws["avg_hit_rate"]) || st.AvgSizeReduction != plFloat(ws["avg_size_reduction"]) ||
		st.CacheHitRate != plFloat(ws["cache_hit_rate"]) || st.TimeTargetAchievement != plFloat(ws["time_target_achievement"]) ||
		st.HitRateTargetAchievement != plFloat(ws["hit_rate_target_achievement"]) ||
		st.SizeReductionTargetAchievement != plFloat(ws["size_reduction_target_achievement"]) ||
		st.AvailableContexts != int(plFloat(ws["available_contexts"])) || st.CachedResults != int(plFloat(ws["cached_results"])) {
		t.Fatalf("stats %+v want %v", st, ws)
	}
	if st.ProgressiveExpansion != nil || st.PredictiveLoading.TotalPatterns != int(plFloat(fx["stats_pred_total"])) ||
		st.ContextPrioritization.TotalContextsTracked != int(plFloat(fx["stats_prior"])) {
		t.Fatalf("component stats %+v", st)
	}
	if len(s.PerformanceHistory) != int(plFloat(fx["hist_len"])) {
		t.Fatalf("history %d", len(s.PerformanceHistory))
	}

	for i, o := range fx["opt"].([]any) {
		w := o.(map[string]any)
		in := w["in"].([]any)
		s.Metrics.AvgSelectionTimeMs, s.Metrics.AvgHitRate, s.Metrics.CacheHitRate = plFloat(in[0]), plFloat(in[1]), plFloat(in[2])
		s.resultCache = nil
		for j := 0; j < int(plFloat(in[3])); j++ {
			s.resultCache = append(s.resultCache, &cachedSelection{key: "k"})
		}
		r := s.OptimizePerformance()
		wc := w["cur"].(map[string]any)
		wt := w["tg"].(map[string]any)
		if !reflect.DeepEqual(r.Actions, plStrings(w["actions"])) || s.SemanticMatcher.SimilarityThreshold != plFloat(w["thr"]) ||
			r.AvgSelectionTimeMs != plFloat(wc["avg_selection_time_ms"]) || r.AvgHitRate != plFloat(wc["avg_hit_rate"]) ||
			r.AvgSizeReduction != plFloat(wc["avg_size_reduction"]) || r.MaxSelectionTimeMs != plFloat(wt["max_selection_time_ms"]) ||
			r.TargetHitRate != plFloat(wt["target_hit_rate"]) || r.TargetSizeReduction != plFloat(wt["target_size_reduction"]) {
			t.Fatalf("optimize %d: %+v want %v", i, r, w)
		}
	}

	wf := fx["fb"].(map[string]any)
	fb := s.fallbackSelection("q", 150)
	if !reflect.DeepEqual(icsIDs(fb.SelectedContexts), plStrings(wf["ids"])) || fb.TotalTokensUsed != int(plFloat(wf["tokens"])) ||
		fb.SelectionTimeMs != plFloat(wf["t"]) || fb.HitRateEstimate != plFloat(wf["h"]) || fb.SizeReductionPct != plFloat(wf["s"]) ||
		!reflect.DeepEqual(icsMetadata(fb.Metadata), [][2]any{{"fallback", true}}) {
		t.Fatalf("fallback %+v want %v", fb, wf)
	}

	for i, c := range icsContexts(fx) {
		if got := s.extractContextContent(c); got != fx["content"].([]any)[i].(string) {
			t.Fatalf("content %d: %q want %q", i, got, fx["content"].([]any)[i])
		}
	}
	for _, f := range fx["find"].([]any) {
		p := f.([]any)
		got := s.findContextByID(p[0].(string))
		switch {
		case p[1] == nil && got != nil, p[1] != nil && got == nil, p[1] != nil && icsIDs([]map[string]any{got})[0] != p[1].(string):
			t.Fatalf("find %v: %v", p, got)
		}
	}
}

func TestIntelligentContextSelectorCacheEviction(t *testing.T) {
	fx := loadJSON(t, "testdata/intelligent_context_selector_cases.json")
	clock := mustTime(t, "2026-03-01T10:00:00Z")
	s := newTestSelector(t, &clock)
	s.LoadAvailableContexts(icsContexts(fx))
	for i := 0; i < 105; i++ {
		clock = clock.Add(time.Second)
		s.SelectContext("query "+strconv.Itoa(i), 100+i, SelectOptions{})
	}
	if len(s.resultCache) != int(plFloat(fx["evict_len"])) {
		t.Fatalf("cache len %d want %v", len(s.resultCache), fx["evict_len"])
	}
	for i, w := range fx["evict_keys_tokens"].([]any) {
		if !strings.HasSuffix(s.resultCache[i].key, "\x00"+strconv.Itoa(int(plFloat(w)))) {
			t.Fatalf("key %d: %q want tokens %v", i, s.resultCache[i].key, w)
		}
	}
}
