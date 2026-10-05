package ai_services

import (
	"context"
	"math"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/services/intelligence"
)

func mlStrPtr(s string) *string { return &s }

func mlObj(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

func samplePattern() *intelligence.DependencyPattern {
	ts := time.Date(2024, 1, 2, 3, 4, 5, 0, time.UTC)
	return &intelligence.DependencyPattern{
		PatternID:   "p1",
		PatternType: intelligence.PatternSequential,
		SourceFeatures: intelligence.PatternFeatures{
			TitleKeywords: []string{"a"}, Agents: []string{}, FileTypes: []string{}, EntityTypes: []string{},
		},
		TargetFeatures: intelligence.PatternFeatures{
			TitleKeywords: []string{"b"}, Agents: []string{}, FileTypes: []string{}, EntityTypes: []string{},
		},
		Confidence: 0.75, SupportCount: 2, SuccessRate: 1.0,
		CreatedAt: ts, LastUpdated: ts,
		Metadata: mlObj("project_id", "proj"),
	}
}

func patternMap(patterns ...*intelligence.DependencyPattern) *entities.OrderedMap[*intelligence.DependencyPattern] {
	m := entities.NewOrderedMap[*intelligence.DependencyPattern]()
	for _, p := range patterns {
		m.Set(p.PatternID, p)
	}
	return m
}

func TestMLModelPersistenceSaveAndLoad(t *testing.T) {
	dir := t.TempDir()
	p, err := NewMLModelPersistence(dir)
	if err != nil {
		t.Fatal(err)
	}
	p.now = func() time.Time { return time.Date(2024, 1, 2, 3, 4, 5, 0, time.UTC) }

	path, err := p.SavePatterns(patternMap(samplePattern()), "v1")
	if err != nil {
		t.Fatal(err)
	}
	if path != filepath.Join(dir, "patterns_v1.json") {
		t.Fatalf("path = %s", path)
	}

	// Field order in the serialized pattern matches dataclasses.asdict.
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	decoded, err := entities.DecodeJSON(raw)
	if err != nil {
		t.Fatal(err)
	}
	outer := decoded.(*entities.OrderedMap[any])
	if strings.Join(outer.Keys(), ",") != "p1" {
		t.Fatalf("outer keys = %v", outer.Keys())
	}
	inner := mustGet(outer, "p1").(*entities.OrderedMap[any])
	wantFields := "pattern_id,pattern_type,source_features,target_features,confidence,support_count,success_rate,created_at,last_updated,metadata"
	if strings.Join(inner.Keys(), ",") != wantFields {
		t.Fatalf("pattern keys = %v", inner.Keys())
	}

	metaRaw, err := os.ReadFile(filepath.Join(dir, "metadata_v1.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(string(metaRaw), "{\n  \"model_version\": \"v1\"") {
		t.Fatalf("metadata not indent-2: %q", string(metaRaw))
	}
	metaDecoded, _ := entities.DecodeJSON(metaRaw)
	meta := metaDecoded.(*entities.OrderedMap[any])
	if v, _ := meta.Get("pattern_count"); v != int64(1) {
		t.Fatalf("pattern_count = %v (%T)", v, v)
	}
	if v, _ := meta.Get("saved_at"); v != "2024-01-02T03:04:05+00:00" {
		t.Fatalf("saved_at = %v", v)
	}

	loaded := p.LoadPatterns("v1")
	if loaded.Len() != 1 {
		t.Fatalf("loaded %d", loaded.Len())
	}
	got, _ := loaded.Get("p1")
	if got.PatternType != intelligence.PatternSequential || got.SupportCount != 2 || got.Confidence != 0.75 {
		t.Fatalf("loaded pattern = %+v", got)
	}
	if len(got.SourceFeatures.TitleKeywords) != 1 || got.SourceFeatures.TitleKeywords[0] != "a" {
		t.Fatalf("source features = %+v", got.SourceFeatures)
	}
	if !got.CreatedAt.Equal(time.Date(2024, 1, 2, 3, 4, 5, 0, time.UTC)) {
		t.Fatalf("created_at = %v", got.CreatedAt)
	}

	if p.LoadPatterns("missing").Len() != 0 {
		t.Fatal("missing version should load empty")
	}
}

func TestMLModelPersistenceVersionsAndCleanup(t *testing.T) {
	dir := t.TempDir()
	p, _ := NewMLModelPersistence(dir)
	for _, v := range []string{"a", "b", "c"} {
		_ = os.WriteFile(filepath.Join(dir, "patterns_"+v+".json"), []byte("{}"), 0o666)
	}
	if got := strings.Join(p.GetAvailableVersions(), ","); got != "c,b,a" {
		t.Fatalf("versions = %s", got)
	}

	for _, v := range []string{"a", "b", "c", "d", "e", "f", "g"} {
		_ = os.WriteFile(filepath.Join(dir, "patterns_"+v+".json"), []byte("{}"), 0o666)
		_ = os.WriteFile(filepath.Join(dir, "metadata_"+v+".json"), []byte("{}"), 0o666)
	}
	p.CleanupOldVersions(5)
	left := strings.Join(p.GetAvailableVersions(), ",")
	if left != "g,f,e,d,c" {
		t.Fatalf("after cleanup = %s", left)
	}
	if _, err := os.Stat(filepath.Join(dir, "patterns_b.json")); !os.IsNotExist(err) {
		t.Fatal("patterns_b.json should be deleted")
	}
	if _, err := os.Stat(filepath.Join(dir, "metadata_b.json")); !os.IsNotExist(err) {
		t.Fatal("metadata_b.json should be deleted")
	}
}

type fakeTaskRepo struct{ tasks []*entities.Task }

func (f fakeTaskRepo) FindAll(context.Context) ([]*entities.Task, error) { return f.tasks, nil }

func TestTrainingDataCollectorDetailsQuirk(t *testing.T) {
	branch := "br-1"
	t1, err := entities.NewTask(entities.Task{Title: "t1", Description: "d1", GitBranchID: &branch})
	if err != nil {
		t.Fatal(err)
	}
	t2, err := entities.NewTask(entities.Task{Title: "t2", Description: "d2", GitBranchID: &branch})
	if err != nil {
		t.Fatal(err)
	}
	c := NewTrainingDataCollector(fakeTaskRepo{tasks: []*entities.Task{t1, t2}})
	if got := c.CollectProjectHistory(context.Background(), nil); len(got) != 0 {
		t.Fatalf("expected no projects (task.details raises), got %v", got)
	}
}

func TestMLDependencyPredictorTrainFailureAndFeedback(t *testing.T) {
	dir := t.TempDir()
	predictor, err := NewMLDependencyPredictor(fakeTaskRepo{}, dir)
	if err != nil {
		t.Fatal(err)
	}
	result := predictor.TrainModel(nil, true)
	if v, _ := result.Get("status"); v != "failed" {
		t.Fatalf("status = %v", v)
	}
	if v, _ := result.Get("error"); v != "No training data available" {
		t.Fatalf("error = %v", v)
	}
	if strings.Join(result.Keys(), ",") != "status,error,timestamp" {
		t.Fatalf("keys = %v", result.Keys())
	}

	// Feedback maths, taken from the Python formula.
	predictor.PatternEngine.Patterns = patternMap(samplePattern())
	if !predictor.UpdatePatternFeedback("p1", true) {
		t.Fatal("update failed")
	}
	got, _ := predictor.PatternEngine.Patterns.Get("p1")
	if got.SupportCount != 3 {
		t.Fatalf("support = %d", got.SupportCount)
	}
	want := (1.0*2 + 1.0) / 3
	if math.Abs(got.SuccessRate-want) > 1e-12 {
		t.Fatalf("success rate = %v want %v", got.SuccessRate, want)
	}
	if predictor.UpdatePatternFeedback("missing", true) {
		t.Fatal("missing pattern should return false")
	}

	info := predictor.GetModelInfo()
	if strings.Join(info.Keys(), ",") != "trained,available_versions,current_stats,model_directory" {
		t.Fatalf("info keys = %v", info.Keys())
	}
	if v, _ := info.Get("trained"); v != false {
		t.Fatalf("trained = %v", v)
	}
	if v, _ := info.Get("current_stats"); v != nil {
		t.Fatalf("current_stats = %v", v)
	}
}

func TestMLDependencyPredictorLoadsLatest(t *testing.T) {
	dir := t.TempDir()
	writer, _ := NewMLModelPersistence(dir)
	if _, err := writer.SavePatterns(patternMap(samplePattern()), "20240102_030405"); err != nil {
		t.Fatal(err)
	}
	predictor, err := NewMLDependencyPredictor(fakeTaskRepo{}, dir)
	if err != nil {
		t.Fatal(err)
	}
	if !predictor.PatternEngine.Trained || predictor.PatternEngine.Patterns.Len() != 1 {
		t.Fatalf("model not loaded: trained=%v patterns=%d", predictor.PatternEngine.Trained, predictor.PatternEngine.Patterns.Len())
	}
	stats, _ := predictor.GetModelInfo().Get("current_stats")
	statsMap := stats.(*entities.OrderedMap[any])
	if v, _ := statsMap.Get("status"); v != "trained" {
		t.Fatalf("status = %v", v)
	}
}
