package intelligence

import (
	"bytes"
	"encoding/json"
	"os"
	"reflect"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

func numberize(v any) any {
	switch x := v.(type) {
	case json.Number:
		if strings.ContainsAny(string(x), ".eE") {
			f, _ := x.Float64()
			return f
		}
		n, _ := x.Int64()
		return n
	case []any:
		for i := range x {
			x[i] = numberize(x[i])
		}
	case map[string]any:
		for k := range x {
			x[k] = numberize(x[k])
		}
	}
	return v
}

func loadJSON(t *testing.T, path string) map[string]any {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber()
	var out map[string]any
	if err := dec.Decode(&out); err != nil {
		t.Fatal(err)
	}
	return numberize(out).(map[string]any)
}

func mustTime(t *testing.T, s string) time.Time {
	tm, err := time.Parse(time.RFC3339Nano, s)
	if err != nil {
		t.Fatal(err)
	}
	return tm
}

type cpFixture struct {
	fx    map[string]any
	now   time.Time
	ctxs  []map[string]any
	sims  map[string]float64
	prefs *UserPreferences
	proj  map[string]any
	cur   map[string]any
}

func cpLoad(t *testing.T) cpFixture {
	f := cpFixture{fx: loadJSON(t, "testdata/context_prioritizer_cases.json")}
	f.now = mustTime(t, f.fx["now"].(string))
	for _, c := range f.fx["contexts"].([]any) {
		f.ctxs = append(f.ctxs, c.(map[string]any))
	}
	f.sims = map[string]float64{}
	for k, v := range f.fx["sims"].(map[string]any) {
		f.sims[k] = v.(float64)
	}
	f.prefs = &UserPreferences{PreferredContextTypes: []string{"task", "global"}, MaxContextSize: 2000,
		PriorityBoostKeywords: []string{"login", "Crash"}, PenaltyKeywords: []string{"bug", "zzz"},
		AgentPreferences: map[string]float64{"alice": 1.0, "carol": -2.0, "bob": 0.5}}
	f.proj = map[string]any{"priorities": map[string]any{"task": 0.9, "branch": 0.4, "project": 1.5, "weird": 0.0}, "x": int64(1)}
	f.cur = map[string]any{"id": "cur", "dependencies": []any{"c3"}, "git_branch_id": "b1", "project_id": "p1"}
	return f
}

func (f cpFixture) prioritizer(t *testing.T) *ContextPrioritizer {
	p := DefaultContextPrioritizer()
	p.Now = func() time.Time { return f.now }
	for _, h := range f.fx["history"].([]any) {
		pair := h.([]any)
		p.RecordContextAccess(pair[0].(string), mustTime(t, pair[1].(string)))
	}
	return p
}

func TestContextPrioritizerScoringMatchesPython(t *testing.T) {
	f := cpLoad(t)
	p := f.prioritizer(t)
	custom := ScoringWeights{0.5, 0.1, 0.1, 0.1, 0.2, 0.1, 0.05, 0.05}
	variants := map[string]func() (*UserPreferences, map[string]any, map[string]any, *ScoringWeights){
		"plain": func() (*UserPreferences, map[string]any, map[string]any, *ScoringWeights) { return nil, nil, nil, nil },
		"prefs": func() (*UserPreferences, map[string]any, map[string]any, *ScoringWeights) {
			return f.prefs, nil, nil, nil
		},
		"proj": func() (*UserPreferences, map[string]any, map[string]any, *ScoringWeights) {
			return nil, f.proj, nil, nil
		},
		"cur": func() (*UserPreferences, map[string]any, map[string]any, *ScoringWeights) {
			return nil, nil, f.cur, nil
		},
		"all": func() (*UserPreferences, map[string]any, map[string]any, *ScoringWeights) {
			return f.prefs, f.proj, f.cur, nil
		},
		"custom_w": func() (*UserPreferences, map[string]any, map[string]any, *ScoringWeights) {
			return nil, nil, nil, &custom
		},
	}
	runs := f.fx["runs"].(map[string]any)
	if len(runs) != 18 {
		t.Fatalf("expected 18 runs, got %d", len(runs))
	}
	for key, want := range runs {
		name, query, _ := strings.Cut(key, "|")
		prefs, proj, cur, w := variants[name]()
		got, err := p.ScoreContextsBatch(f.ctxs, query, f.sims, prefs, proj, cur, w)
		if err != nil {
			t.Fatalf("%s: %v", key, err)
		}
		wl := want.([]any)
		if len(got) != len(wl) {
			t.Fatalf("%s: %d scores want %d", key, len(got), len(wl))
		}
		for i, g := range got {
			w := wl[i].(map[string]any)
			if g.ContextID != w["id"] || g.TotalScore != w["total"].(float64) || int64(g.EstimatedTok) != w["tokens"] ||
				!reflect.DeepEqual(g.ContextType, w["ctype"]) {
				t.Errorf("%s[%d]: got %s %v tokens=%d ctype=%v want %v", key, i, g.ContextID, g.TotalScore, g.EstimatedTok, g.ContextType, w)
				continue
			}
			var expl []string
			for _, e := range w["expl"].([]any) {
				expl = append(expl, e.(string))
			}
			if !reflect.DeepEqual(g.Explanations, expl) {
				t.Errorf("%s[%d]: explanations %v want %v", key, i, g.Explanations, expl)
			}
			for j, kv := range w["factors"].([]any) {
				pair := kv.([]any)
				v, _ := g.FactorScores.Get(pair[0].(string))
				if g.FactorScores.Keys()[j] != pair[0] || v != pair[1].(float64) {
					t.Errorf("%s[%d]: factor %v = %v want %v", key, i, pair[0], v, pair[1])
				}
			}
			last, _ := w["last"].(string)
			if (g.LastAccessed == nil) != (last == "") || (last != "" && !g.LastAccessed.Equal(mustTime(t, last))) {
				t.Errorf("%s[%d]: last accessed %v want %q", key, i, g.LastAccessed, last)
			}
		}
	}
}

func TestContextPrioritizerNonNumericProjectPriorityErrors(t *testing.T) {
	f := cpLoad(t)
	p := f.prioritizer(t)
	_, err := p.ScoreContext("e", map[string]any{"context_type": "task"}, "q", 0.5, nil,
		map[string]any{"priorities": map[string]any{"task": "high"}}, nil, nil)
	if err == nil || f.fx["err"] != "TypeError" {
		t.Fatalf("err=%v python=%v", err, f.fx["err"])
	}
}

func TestContextPrioritizerAdjustWeightsMatchesPython(t *testing.T) {
	f := cpLoad(t)
	p := f.prioritizer(t)
	for key, want := range f.fx["adjust"].(map[string]any) {
		parts := strings.SplitN(key, "|", 3)
		var fb map[string]float64
		if parts[2] != "null" {
			fb = map[string]float64{"recency": 0.3, "nope": 1.0, "frequency": -0.9, "semantic_relevance": 2.0}
		}
		w := p.AdjustWeightsDynamically(parts[0], parts[1], fb)
		got := []float64{w.SemanticRelevance, w.Recency, w.Frequency, w.Completeness, w.SizePenalty, w.UserPreference, w.ProjectPriority, w.DependencyBoost}
		for i, x := range want.([]any) {
			if f, _ := value_objects.PyFloat(x); got[i] != f {
				t.Errorf("%s: field %d = %v want %v", key, i, got[i], x)
			}
		}
	}
	zero := ScoringWeights{SizePenalty: 0.05}.Normalize()
	zn := f.fx["zero_norm"].([]any)
	if z0, _ := value_objects.PyFloat(zn[0]); zero.SemanticRelevance != z0 || zero.SizePenalty != zn[1].(float64) {
		t.Fatalf("zero normalize %+v", zero)
	}
}

func TestContextPrioritizerStatsAndHistoryMatchPython(t *testing.T) {
	f := cpLoad(t)
	p := f.prioritizer(t)
	for id, times := range f.fx["hist_after"].(map[string]any) {
		got, ok := p.ContextAccessHistory.Get(id)
		if !ok || len(got) != len(times.([]any)) {
			t.Fatalf("%s: history %v want %v", id, got, times)
		}
		for i, ts := range times.([]any) {
			if !got[i].Equal(mustTime(t, ts.(string))) {
				t.Errorf("%s[%d] = %v want %v", id, i, got[i], ts)
			}
		}
	}
	s := p.GetScoringStats()
	w := f.fx["stats"].(map[string]any)
	if int64(s.TotalContextsTracked) != w["total_contexts_tracked"] || int64(s.TotalAccessesRecorded) != w["total_accesses_recorded"] ||
		s.AvgAccessesPerContext != w["avg_accesses_per_context"].(float64) {
		t.Fatalf("stats %+v want %v", s, w)
	}
	for i, m := range w["most_frequent_contexts"].([]any) {
		mm := m.(map[string]any)
		if s.MostFrequentContexts[i].ContextID != mm["context_id"] || int64(s.MostFrequentContexts[i].AccessCount) != mm["access_count"] {
			t.Errorf("most frequent[%d] = %+v want %v", i, s.MostFrequentContexts[i], mm)
		}
	}
	if DefaultContextPrioritizer().GetScoringStats() != nil || f.fx["empty_stats"] == nil && false {
		t.Fatal("empty stats must be nil")
	}
}
