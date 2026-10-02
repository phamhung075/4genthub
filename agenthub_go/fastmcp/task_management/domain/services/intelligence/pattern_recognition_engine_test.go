package intelligence

import (
	"reflect"
	"sort"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

var preNow = time.Date(2026, 3, 1, 10, 0, 0, 123456000, time.UTC)

func preSorted(in []string) []string {
	out := append([]string{}, in...)
	sort.Strings(out)
	return out
}

func preAnySlice(v any) []string { return plStrings(v) }

func preIso(v any) any {
	switch x := v.(type) {
	case time.Time:
		return value_objects.IsoFormat(x)
	}
	return v
}

func preFeatures(f PatternFeatures) map[string]any {
	return map[string]any{
		"title_keywords": f.TitleKeywords, "description_keywords": f.DescriptionKeywords, "agents": f.Agents,
		"priority": f.Priority, "estimated_effort": f.EstimatedEffort, "has_files": f.HasFiles,
		"file_types": preSorted(f.FileTypes), "has_entities": f.HasEntities, "entity_types": preSorted(f.EntityTypes),
	}
}

func preWantFeatures(t *testing.T, w map[string]any) map[string]any {
	return map[string]any{
		"title_keywords": preAnySlice(w["title_keywords"]), "description_keywords": preAnySlice(w["description_keywords"]),
		"agents": preAnySlice(w["agents"]), "priority": w["priority"], "estimated_effort": w["estimated_effort"],
		"has_files": w["has_files"], "file_types": preAnySlice(w["file_types"]), "has_entities": w["has_entities"],
		"entity_types": preAnySlice(w["entity_types"]),
	}
}

func preCounts(m *entities.OrderedMap[int]) [][2]any {
	out := [][2]any{}
	for _, k := range m.Keys() {
		v, _ := m.Get(k)
		out = append(out, [2]any{k, v})
	}
	return out
}

func preWantCounts(v any) [][2]any {
	out := [][2]any{}
	for _, p := range v.([]any) {
		pp := p.([]any)
		out = append(out, [2]any{pp[0].(string), int(plFloat(pp[1]))})
	}
	return out
}

func orderedPairs(v any) [][2]any {
	out := [][2]any{}
	for _, p := range v.([]any) {
		pp := p.([]any)
		out = append(out, [2]any{pp[0].(string), pp[1]})
	}
	return out
}

func TestPatternRecognitionEngineMatchesPython(t *testing.T) {
	fx := loadJSON(t, "testdata/pattern_recognition_cases.json")
	var projects []map[string]any
	for _, p := range fx["projects"].([]any) {
		projects = append(projects, p.(map[string]any))
	}

	e := NewPatternRecognitionEngine()
	e.SetClock(func() time.Time { return preNow })

	// Feature extraction of every training task.
	ex := NewFeatureExtractor()
	ex.Now = func() time.Time { return preNow }
	for i, in := range fx["vecs_input"].([]any) {
		w := fx["vecs"].([]any)[i].(map[string]any)
		v := ex.ExtractTaskVector(DictTask(in.(map[string]any)))
		got := map[string]any{
			"task_id": v.TaskID, "title_tokens": v.TitleTokens, "description_tokens": v.DescriptionTokens,
			"agents": v.Agents, "priority": v.Priority, "estimated_effort": v.EstimatedEffort,
			"file_references": preSorted(v.FileReferences), "technical_entities": preSorted(v.TechnicalEntities),
			"creation_time": preIso(v.CreationTime), "completion_time": preIso(v.CompletionTime),
		}
		want := map[string]any{
			"task_id": w["task_id"], "title_tokens": preAnySlice(w["title_tokens"]), "description_tokens": preAnySlice(w["description_tokens"]),
			"agents": preAnySlice(w["agents"]), "priority": w["priority"], "estimated_effort": w["estimated_effort"],
			"file_references": preSorted(preAnySlice(w["file_references"])), "technical_entities": preSorted(preAnySlice(w["technical_entities"])),
			"creation_time": w["creation_time"], "completion_time": w["completion_time"],
		}
		if !reflect.DeepEqual(got, want) {
			t.Fatalf("vector %d (%v):\n got %v\nwant %v", i, in, got, want)
		}
	}

	if st := e.GetEngineStats(); st.Status != "not_trained" || st.TotalPatterns != 0 {
		t.Fatalf("untrained stats %+v", st)
	}
	if got := e.PredictDependencies(DictTask{"id": "x"}, nil); len(got) != 0 {
		t.Fatalf("untrained predictions %v", got)
	}

	sum := e.TrainFromHistoricalData(projects)
	ws := fx["summary"].(map[string]any)
	if sum.TotalProjects != int(plFloat(ws["total_projects"])) || sum.PatternsLearned != int(plFloat(ws["patterns_learned"])) ||
		sum.AverageConfidence != plFloat(ws["average_confidence"]) || sum.TrainingCompletedAt != ws["training_completed_at"] {
		t.Fatalf("summary %+v want %v", sum, ws)
	}
	if got, want := preCounts(sum.PatternTypes), preWantCounts(fx["summary_types"]); !reflect.DeepEqual(got, want) {
		t.Fatalf("types %v want %v", got, want)
	}

	wp := fx["patterns"].([]any)
	if e.Patterns.Len() != len(wp) {
		t.Fatalf("patterns %d want %d", e.Patterns.Len(), len(wp))
	}
	for i, id := range e.Patterns.Keys() {
		p, _ := e.Patterns.Get(id)
		w := wp[i].(map[string]any)
		md := [][2]any{}
		for _, k := range p.Metadata.Keys() {
			v, _ := p.Metadata.Get(k)
			md = append(md, [2]any{k, v})
		}
		if p.PatternID != w["id"] || string(p.PatternType) != w["type"] || p.Confidence != plFloat(w["conf"]) ||
			p.SupportCount != int(plFloat(w["support"])) || p.SuccessRate != plFloat(w["succ"]) ||
			value_objects.IsoFormat(p.CreatedAt) != w["created"] ||
			!reflect.DeepEqual(preFeatures(p.SourceFeatures), preWantFeatures(t, w["src"].(map[string]any))) ||
			!reflect.DeepEqual(preFeatures(p.TargetFeatures), preWantFeatures(t, w["tgt"].(map[string]any))) ||
			!reflect.DeepEqual(md, orderedPairs(w["meta"])) {
			t.Fatalf("pattern %d:\n got %+v\nwant %v", i, p, w)
		}
	}
	if e.PatternLearner.PatternCounter != int(plFloat(fx["counter"])) {
		t.Fatalf("counter %d want %v", e.PatternLearner.PatternCounter, fx["counter"])
	}
	preCheckStats(t, e.GetEngineStats(), fx["stats"].(map[string]any))

	// Candidates: the tasks of projects P1 then P7 (the generator's order).
	var ordered []PatternTask
	for _, id := range []string{"P1", "P7"} {
		for _, p := range projects {
			if p["id"] == id {
				for _, task := range p["tasks"].([]any) {
					ordered = append(ordered, DictTask(task.(map[string]any)))
				}
			}
		}
	}
	subjectTasks := fx["subject_tasks"].([]any)
	for i, w := range fx["preds"].([]any) {
		got := e.PredictDependencies(DictTask(subjectTasks[i].(map[string]any)), ordered)
		want := w.([]any)
		if len(got) != len(want) {
			t.Fatalf("subject %d: %d predictions want %d", i, len(got), len(want))
		}
		for j, g := range got {
			x := want[j].(map[string]any)
			ev := x["ev"].(map[string]any)
			if g.SourceTaskID != x["s"] || g.TargetTaskID != x["t"] || !reflect.DeepEqual(g.PatternIDs, preAnySlice(x["ids"])) ||
				g.Confidence != plFloat(x["conf"]) || g.Reasoning != x["why"] || !reflect.DeepEqual(g.FeaturesMatched, preAnySlice(x["fm"])) ||
				g.PatternEvidence.MatchingPatterns != int(plFloat(ev["matching_patterns"])) ||
				g.PatternEvidence.AvgSupport != plFloat(ev["avg_support"]) ||
				!reflect.DeepEqual(g.PatternEvidence.PatternTypes, preAnySlice(ev["pattern_types"])) {
				t.Fatalf("subject %d prediction %d:\n got %+v\nwant %v", i, j, g, x)
			}
		}
	}
	for i, id := range e.Patterns.Keys() {
		p, _ := e.Patterns.Get(id)
		w := fx["pattern_scores"].([]any)[i]
		v, ok := p.Metadata.Get("current_match_score")
		if w == nil && ok || w != nil && (!ok || v.(float64) != plFloat(w)) {
			t.Fatalf("pattern %s current_match_score %v want %v", id, v, w)
		}
	}
	preCheckStats(t, e.GetEngineStats(), fx["stats_after"].(map[string]any))

	empty := NewPatternRecognitionEngine()
	empty.SetClock(func() time.Time { return preNow })
	es := empty.TrainFromHistoricalData(nil)
	we := fx["empty_summary"].(map[string]any)
	if es.PatternsLearned != 0 || es.AverageConfidence != plFloat(we["average_confidence"]) || es.PatternTypes.Len() != 0 {
		t.Fatalf("empty summary %+v", es)
	}
	if st := empty.GetEngineStats(); st.Status != "not_trained" || st.TotalPatterns != 0 {
		t.Fatalf("empty stats %+v", st)
	}
}

func preCheckStats(t *testing.T, got EngineStats, w map[string]any) {
	t.Helper()
	if got.Status != w["status"] || got.TotalPatterns != int(plFloat(w["total_patterns"])) ||
		got.AverageConfidence != plFloat(w["average_confidence"]) || got.AverageSupport != plFloat(w["average_support"]) ||
		got.LastUpdated != w["last_updated"] || !reflect.DeepEqual(preCounts(got.PatternTypes), preWantCounts(w["pattern_types"])) {
		t.Fatalf("stats %+v want %v", got, w)
	}
}
