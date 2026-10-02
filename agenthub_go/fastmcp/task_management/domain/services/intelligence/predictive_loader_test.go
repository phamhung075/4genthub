package intelligence

import (
	"reflect"
	"sort"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

func plFloat(v any) float64 {
	switch x := v.(type) {
	case int64:
		return float64(x)
	case int:
		return float64(x)
	}
	return v.(float64)
}

func plStrings(v any) []string {
	out := []string{}
	if v == nil {
		return out
	}
	for _, s := range v.([]any) {
		out = append(out, s.(string))
	}
	return out
}

func plPairs(m *entities.OrderedMap[float64]) [][2]any {
	out := [][2]any{}
	for _, k := range m.Keys() {
		v, _ := m.Get(k)
		out = append(out, [2]any{k, v})
	}
	return out
}

func plWantPairs(v any) [][2]any {
	out := [][2]any{}
	for _, p := range v.([]any) {
		pp := p.([]any)
		out = append(out, [2]any{pp[0].(string), plFloat(pp[1])})
	}
	return out
}

func TestPredictiveLoaderMatchesPython(t *testing.T) {
	fx := loadJSON(t, "testdata/predictive_loader_cases.json")
	clock := mustTime(t, fx["start"].(string))
	l := NewPredictiveLoader()
	l.Now = func() time.Time { return clock }

	ends := fx["ends"].([]any)
	endIdx := 0
	for _, o := range fx["script"].([]any) {
		op := o.([]any)
		switch op[0].(string) {
		case "start":
			var uid *string
			if s, ok := op[2].(string); ok {
				uid = &s
			}
			l.StartSession(op[1].(string), uid)
		case "tool":
			l.RecordToolUsage(op[1].(string), op[2].(string))
		case "access":
			l.RecordContextAccess(op[1].(string), op[2].(string))
		case "adv":
			clock = clock.Add(time.Duration(plFloat(op[1])) * time.Second)
		case "end":
			r := l.EndSession()
			want := ends[endIdx].(map[string]any)
			endIdx++
			if r == nil || r.DurationMinutes != plFloat(want["duration"]) ||
				len(r.ToolSequence) != int(plFloat(want["tools"])) ||
				len(r.ContextSequence) != int(plFloat(want["ctx"])) ||
				!r.EndTime.Equal(mustTime(t, want["end"].(string))) {
				t.Fatalf("end %d: got %+v want %+v", endIdx, r, want)
			}
		}
	}
	if len(l.sessionHistory) != int(plFloat(fx["hist"])) {
		t.Fatalf("history %d", len(l.sessionHistory))
	}

	// Predictions advance the clock between hour groups exactly like the generator.
	for i, p := range fx["preds"].([]any) {
		w := p.(map[string]any)
		if i > 0 && i%60 == 0 {
			clock = clock.Add(time.Duration(i/60) * time.Hour)
		}
		var sc *SessionHistoryContext
		if m, ok := w["sc"].(map[string]any); ok {
			sc = &SessionHistoryContext{ToolSequence: plStrings(m["tool_sequence"]), ContextSequence: plStrings(m["context_sequence"])}
		}
		got, err := l.PredictNextContexts(w["cur"].(map[string]any), plStrings(w["tools"]), sc)
		if err != nil {
			t.Fatalf("pred %d: %v", i, err)
		}
		patterns := append([]string{}, got.PatternsUsed...)
		sort.Strings(patterns)
		if !reflect.DeepEqual(got.PredictedContexts, plStrings(w["predicted"])) ||
			!reflect.DeepEqual(plPairs(got.ConfidenceScores), plWantPairs(w["conf"])) ||
			!reflect.DeepEqual(plPairs(got.PreloadPriority), plWantPairs(w["prio"])) ||
			!reflect.DeepEqual(patterns, plStrings(w["patterns"])) ||
			!reflect.DeepEqual(got.PredictionReasons, plStrings(w["reasons"])) {
			t.Fatalf("pred %d mismatch:\n got %+v %v %v\nwant %v", i, got.PredictedContexts, plPairs(got.ConfidenceScores), got.PredictionReasons, w)
		}
	}

	if l.usagePatterns.Len() != int(plFloat(fx["pattern_count"])) {
		t.Fatalf("patterns %d", l.usagePatterns.Len())
	}
	st := l.GetPredictionStats()
	ws := fx["stats"].(map[string]any)
	if st.TotalPatterns != int(plFloat(ws["total_patterns"])) || st.AvgSuccessRate != plFloat(ws["avg_success_rate"]) ||
		st.HighConfidencePatterns != int(plFloat(ws["high_confidence_patterns"])) ||
		st.SessionHistoryCount != int(plFloat(ws["session_history_count"])) ||
		st.PatternConfidenceThreshold != plFloat(ws["pattern_confidence_threshold"]) {
		t.Fatalf("stats %+v want %v", st, ws)
	}
	var gotConf [][2]float64
	for _, p := range st.Patterns {
		gotConf = append(gotConf, [2]float64{float64(p.Frequency), p.Confidence})
	}
	sort.Slice(gotConf, func(i, j int) bool {
		return gotConf[i][0] < gotConf[j][0] || gotConf[i][0] == gotConf[j][0] && gotConf[i][1] < gotConf[j][1]
	})
	for i, c := range fx["stats_conf"].([]any) {
		cc := c.([]any)
		if gotConf[i] != [2]float64{plFloat(cc[0]), plFloat(cc[1])} {
			t.Fatalf("stats pattern %d: %v want %v", i, gotConf[i], cc)
		}
	}

	// Pattern ids are hash-randomised in Python: compare by position.
	ids := l.usagePatterns.Keys()[:3]
	calls := [][3][]string{
		{{"a", "b", "c"}, {"a", "c"}}, {{"a", "b"}, {"z"}}, {{}, {}},
	}
	for i, v := range fx["valid_vals"].([]any) {
		got := l.ValidatePredictions(calls[i][0], calls[i][1], ids)
		var vals []float64
		for _, k := range ids {
			x, _ := got.Get(k)
			vals = append(vals, x)
		}
		for j, w := range v.([]any) {
			if vals[j] != plFloat(w) {
				t.Fatalf("validate %d/%d: %v want %v", i, j, vals[j], w)
			}
		}
	}
}

func TestPredictiveLoaderEdges(t *testing.T) {
	fx := loadJSON(t, "testdata/predictive_loader_cases.json")
	l := NewPredictiveLoader()
	if l.GetPredictionStats() != nil || l.EndSession() != nil {
		t.Fatal("empty loader must have no stats and no session")
	}
	l2 := NewPredictiveLoaderWith(1, 0.6, 30, 5)
	l2.StartSession("x", nil)
	l2.RecordContextAccess("a", "my_type")
	_, err := l2.PredictNextContexts(map[string]any{}, nil, nil)
	if err == nil || err.Error() != fx["bad"].(string) {
		t.Fatalf("got %v want %v", err, fx["bad"])
	}
}
