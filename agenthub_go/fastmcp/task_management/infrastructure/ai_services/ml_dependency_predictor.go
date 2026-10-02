// Package ai_services ports task_management/infrastructure/ai_services.
//
// ml_dependency_predictor.go ports ml_dependency_predictor.py. The Python
// TrainingDataCollector reads task.details, an attribute the Task dataclass does not
// define, so for real Task entities _create_project_data raises AttributeError, is
// swallowed and returns None; collect_project_history therefore always returns an empty
// list. That quirk is preserved: tasks are PatternTask duck types and a missing
// "details" attribute makes createProjectData return nil.
package ai_services

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/services/intelligence"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskLister is the part of TaskRepository this module uses (find_all).
type TaskLister interface {
	FindAll(ctx context.Context) ([]*entities.Task, error)
}

func mlNow() time.Time { return time.Now().UTC() }

// MLModelPersistence is ml_dependency_predictor.MLModelPersistence.
type MLModelPersistence struct {
	ModelDir string
	now      func() time.Time
}

// NewMLModelPersistence mirrors __init__: the directory is created if missing.
func NewMLModelPersistence(modelDir string) (*MLModelPersistence, error) {
	if err := os.MkdirAll(modelDir, 0o777); err != nil {
		return nil, err
	}
	return &MLModelPersistence{ModelDir: modelDir, now: mlNow}, nil
}

func mlFeatureList(v any) []string {
	switch x := v.(type) {
	case nil:
		return []string{}
	case []string:
		return x
	case []any:
		out := make([]string, 0, len(x))
		for _, e := range x {
			out = append(out, value_objects.PyStr(e))
		}
		return out
	case string:
		out := []string{}
		for _, r := range x {
			out = append(out, string(r))
		}
		return out
	}
	return []string{}
}

func mlPatternFeaturesToDict(f intelligence.PatternFeatures) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("title_keywords", f.TitleKeywords)
	m.Set("description_keywords", f.DescriptionKeywords)
	m.Set("agents", f.Agents)
	m.Set("priority", f.Priority)
	m.Set("estimated_effort", f.EstimatedEffort)
	m.Set("has_files", f.HasFiles)
	m.Set("file_types", f.FileTypes)
	m.Set("has_entities", f.HasEntities)
	m.Set("entity_types", f.EntityTypes)
	return m
}

func mlPatternFeaturesFromDict(v any) intelligence.PatternFeatures {
	m, _ := v.(*entities.OrderedMap[any])
	if m == nil {
		return intelligence.PatternFeatures{}
	}
	get := func(k string) any { x, _ := m.Get(k); return x }
	return intelligence.PatternFeatures{
		TitleKeywords:       mlFeatureList(get("title_keywords")),
		DescriptionKeywords: mlFeatureList(get("description_keywords")),
		Agents:              mlFeatureList(get("agents")),
		Priority:            value_objects.PyStr(get("priority")),
		EstimatedEffort:     value_objects.PyStr(get("estimated_effort")),
		HasFiles:            value_objects.PyTruthy(get("has_files")),
		FileTypes:           mlFeatureList(get("file_types")),
		HasEntities:         value_objects.PyTruthy(get("has_entities")),
		EntityTypes:         mlFeatureList(get("entity_types")),
	}
}

// mlPatternToDict mirrors dataclasses.asdict(pattern) plus the field overrides in
// save_patterns (datetimes to isoformat, PatternType to its value).
func mlPatternToDict(p *intelligence.DependencyPattern) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("pattern_id", p.PatternID)
	m.Set("pattern_type", string(p.PatternType))
	m.Set("source_features", mlPatternFeaturesToDict(p.SourceFeatures))
	m.Set("target_features", mlPatternFeaturesToDict(p.TargetFeatures))
	m.Set("confidence", p.Confidence)
	m.Set("support_count", p.SupportCount)
	m.Set("success_rate", p.SuccessRate)
	m.Set("created_at", value_objects.IsoFormat(p.CreatedAt))
	m.Set("last_updated", value_objects.IsoFormat(p.LastUpdated))
	m.Set("metadata", p.Metadata)
	return m
}

// SavePatterns mirrors save_patterns and returns the patterns file path.
func (p *MLModelPersistence) SavePatterns(patterns *entities.OrderedMap[*intelligence.DependencyPattern], modelVersion string) (string, error) {
	patternsFile := filepath.Join(p.ModelDir, "patterns_"+modelVersion+".json")

	serializable := entities.NewOrderedMap[any]()
	for _, id := range patterns.Keys() {
		pattern, _ := patterns.Get(id)
		serializable.Set(id, mlPatternToDict(pattern))
	}
	text, err := value_objects.PyJSONDumps(serializable, 2)
	if err != nil {
		return "", err
	}
	if err := os.WriteFile(patternsFile, []byte(text), 0o666); err != nil {
		return "", err
	}

	fi, err := os.Stat(patternsFile)
	if err != nil {
		return "", err
	}
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("model_version", modelVersion)
	metadata.Set("pattern_count", patterns.Len())
	metadata.Set("saved_at", value_objects.IsoFormat(p.now()))
	metadata.Set("file_size", fi.Size())
	metaText, err := value_objects.PyJSONDumps(metadata, 2)
	if err != nil {
		return "", err
	}
	if err := os.WriteFile(filepath.Join(p.ModelDir, "metadata_"+modelVersion+".json"), []byte(metaText), 0o666); err != nil {
		return "", err
	}
	return patternsFile, nil
}

func mlParseTime(v any) (time.Time, error) {
	s, ok := v.(string)
	if !ok {
		return time.Time{}, fmt.Errorf("created_at is not a string")
	}
	return value_objects.ParseISO(s)
}

func mlValidPatternType(v string) bool {
	switch intelligence.PatternType(v) {
	case intelligence.PatternSequential, intelligence.PatternParallel, intelligence.PatternConverging,
		intelligence.PatternBranching, intelligence.PatternCyclical, intelligence.PatternAgentBased,
		intelligence.PatternTemporal:
		return true
	}
	return false
}

func mlInt(v any) int {
	switch x := v.(type) {
	case int:
		return x
	case int64:
		return int(x)
	case float64:
		return int(x)
	}
	return 0
}

func mlPatternFromDict(d *entities.OrderedMap[any]) (*intelligence.DependencyPattern, error) {
	created, err := mlParseTime(mustGet(d, "created_at"))
	if err != nil {
		return nil, err
	}
	lastUpdated, err := mlParseTime(mustGet(d, "last_updated"))
	if err != nil {
		return nil, err
	}
	ptype, ok := mustGet(d, "pattern_type").(string)
	if !ok {
		return nil, fmt.Errorf("pattern_type is not a string")
	}
	if !mlValidPatternType(ptype) {
		return nil, fmt.Errorf("'%s' is not a valid PatternType", ptype)
	}
	patternID := value_objects.PyStr(mustGet(d, "pattern_id"))
	confidence, ok := value_objects.PyFloat(mustGet(d, "confidence"))
	if !ok {
		return nil, fmt.Errorf("confidence is not a number")
	}
	success, ok := value_objects.PyFloat(mustGet(d, "success_rate"))
	if !ok {
		return nil, fmt.Errorf("success_rate is not a number")
	}
	source, _ := mustGet(d, "source_features").(*entities.OrderedMap[any])
	target, _ := mustGet(d, "target_features").(*entities.OrderedMap[any])
	metadata, _ := mustGet(d, "metadata").(*entities.OrderedMap[any])

	return &intelligence.DependencyPattern{
		PatternID:      patternID,
		PatternType:    intelligence.PatternType(ptype),
		SourceFeatures: mlPatternFeaturesFromDict(source),
		TargetFeatures: mlPatternFeaturesFromDict(target),
		Confidence:     confidence,
		SupportCount:   mlInt(mustGet(d, "support_count")),
		SuccessRate:    success,
		CreatedAt:      created,
		LastUpdated:    lastUpdated,
		Metadata:       metadata,
	}, nil
}

func mustGet(d *entities.OrderedMap[any], key string) any {
	v, _ := d.Get(key)
	return v
}

// LoadPatterns mirrors load_patterns; any failure yields an empty map.
func (p *MLModelPersistence) LoadPatterns(modelVersion string) *entities.OrderedMap[*intelligence.DependencyPattern] {
	empty := entities.NewOrderedMap[*intelligence.DependencyPattern]()
	patternsFile := filepath.Join(p.ModelDir, "patterns_"+modelVersion+".json")
	if _, err := os.Stat(patternsFile); err != nil {
		return empty
	}
	data, err := os.ReadFile(patternsFile)
	if err != nil {
		return empty
	}
	raw, err := entities.DecodeJSON(data)
	if err != nil {
		return empty
	}
	obj, ok := raw.(*entities.OrderedMap[any])
	if !ok {
		return empty
	}
	patterns := entities.NewOrderedMap[*intelligence.DependencyPattern]()
	for _, patternID := range obj.Keys() {
		pv, _ := obj.Get(patternID)
		pd, ok := pv.(*entities.OrderedMap[any])
		if !ok {
			return empty
		}
		pattern, err := mlPatternFromDict(pd)
		if err != nil {
			return empty
		}
		patterns.Set(patternID, pattern)
	}
	return patterns
}

// GetAvailableVersions mirrors get_available_versions (most recent first).
func (p *MLModelPersistence) GetAvailableVersions() []string {
	versions := []string{}
	matches, err := filepath.Glob(filepath.Join(p.ModelDir, "patterns_*.json"))
	if err != nil {
		return versions
	}
	for _, filePath := range matches {
		base := filepath.Base(filePath)
		stem := strings.TrimSuffix(base, filepath.Ext(base))
		versions = append(versions, strings.ReplaceAll(stem, "patterns_", ""))
	}
	sort.Strings(versions)
	for i, j := 0, len(versions)-1; i < j; i, j = i+1, j-1 {
		versions[i], versions[j] = versions[j], versions[i]
	}
	return versions
}

// CleanupOldVersions mirrors cleanup_old_versions; errors are swallowed like Python's.
func (p *MLModelPersistence) CleanupOldVersions(keepVersions int) {
	versions := p.GetAvailableVersions()
	if len(versions) <= keepVersions {
		return
	}
	for _, version := range versions[keepVersions:] {
		patternFile := filepath.Join(p.ModelDir, "patterns_"+version+".json")
		if _, err := os.Stat(patternFile); err == nil {
			_ = os.Remove(patternFile)
		}
		metadataFile := filepath.Join(p.ModelDir, "metadata_"+version+".json")
		if _, err := os.Stat(metadataFile); err == nil {
			_ = os.Remove(metadataFile)
		}
	}
}

// TrainingDataCollector is ml_dependency_predictor.TrainingDataCollector.
type TrainingDataCollector struct {
	TaskRepository TaskLister
}

func NewTrainingDataCollector(repo TaskLister) *TrainingDataCollector {
	return &TrainingDataCollector{TaskRepository: repo}
}

// mlTask wraps an entity into a PatternTask and adds get_dependency_ids.
type mlTask struct {
	intelligence.EntityTask
}

func (t mlTask) GetDependencyIDs() []string { return t.Task.GetDependencyIDs() }

// CollectProjectHistory mirrors collect_project_history.
func (c *TrainingDataCollector) CollectProjectHistory(ctx context.Context, limit *int) []map[string]any {
	projects := []map[string]any{}
	allTasks, err := c.TaskRepository.FindAll(ctx)
	if err != nil || len(allTasks) == 0 {
		return projects
	}

	order := []string{}
	byBranch := map[string][]intelligence.PatternTask{}
	for _, task := range allTasks {
		branchID := ""
		if task.GitBranchID != nil {
			branchID = *task.GitBranchID
		}
		if _, ok := byBranch[branchID]; !ok {
			order = append(order, branchID)
		}
		byBranch[branchID] = append(byBranch[branchID], mlTask{intelligence.EntityTask{Task: task}})
	}

	for _, branchID := range order {
		branchTasks := byBranch[branchID]
		if len(branchTasks) < 2 {
			continue
		}
		if projectData := c.createProjectData(branchID, branchTasks); projectData != nil {
			projects = append(projects, projectData)
		}
		if limit != nil && len(projects) >= *limit {
			break
		}
	}
	return projects
}

// createProjectData mirrors _create_project_data. A missing "details" attribute (as on
// every real Task) makes it return nil, exactly like the caught AttributeError.
func (c *TrainingDataCollector) createProjectData(branchID string, tasks []intelligence.PatternTask) map[string]any {
	taskData := []map[string]any{}
	for _, task := range tasks {
		if _, ok := task.Attr("details"); !ok {
			return nil
		}
		idRaw, ok := task.Attr("id")
		if !ok {
			return nil
		}
		titleRaw, ok := task.Attr("title")
		if !ok {
			return nil
		}
		descRaw, ok := task.Attr("description")
		if !ok {
			return nil
		}
		detailsRaw, _ := task.Attr("details")
		assigneesRaw, ok := task.Attr("assignees")
		if !ok {
			return nil
		}
		prioRaw, ok := task.Attr("priority")
		if !ok {
			return nil
		}
		statusRaw, ok := task.Attr("status")
		if !ok {
			return nil
		}
		effortRaw, ok := task.Attr("estimated_effort")
		if !ok {
			return nil
		}
		createdRaw, ok := task.Attr("created_at")
		if !ok {
			return nil
		}
		updatedRaw, ok := task.Attr("updated_at")
		if !ok {
			return nil
		}

		taskDict := map[string]any{
			"id":               value_objects.PyStr(idRaw),
			"title":            value_objects.PyStr(titleRaw),
			"description":      mlOrEmpty(descRaw),
			"details":          mlOrEmpty(detailsRaw),
			"assignees":        mlOrEmptyList(assigneesRaw),
			"priority":         value_objects.PyStr(prioRaw),
			"status":           value_objects.PyStr(statusRaw),
			"estimated_effort": mlOrEmpty(effortRaw),
			"created_at":       mlIsoOrNil(createdRaw),
			"updated_at":       mlIsoOrNil(updatedRaw),
			"dependencies":     mlDependencyIDs(task),
		}
		taskData = append(taskData, taskDict)
	}

	totalDeps := 0
	for _, task := range taskData {
		if deps, ok := task["dependencies"].([]string); ok {
			totalDeps += len(deps)
		}
	}
	if totalDeps == 0 {
		return nil
	}

	return map[string]any{
		"id":               branchID,
		"domain":           c.inferProjectDomain(taskData),
		"task_count":       len(taskData),
		"dependency_count": totalDeps,
		"tasks":            taskData,
		"collected_at":     value_objects.IsoFormat(mlNow()),
	}
}

func mlOrEmpty(v any) any {
	if value_objects.PyTruthy(v) {
		return v
	}
	return ""
}

func mlOrEmptyList(v any) any {
	if value_objects.PyTruthy(v) {
		return v
	}
	return []any{}
}

func mlIsoOrNil(v any) any {
	if t, ok := v.(time.Time); ok {
		return value_objects.IsoFormat(t)
	}
	return nil
}

type mlDependencyProvider interface{ GetDependencyIDs() []string }

func mlDependencyIDs(task intelligence.PatternTask) []string {
	if t, ok := task.(mlDependencyProvider); ok {
		return t.GetDependencyIDs()
	}
	return []string{}
}

// mlDomainIndicators is _infer_project_domain's table, in insertion order.
var mlDomainIndicators = []struct {
	domain     string
	indicators []string
}{
	{"web", []string{"frontend", "backend", "api", "html", "css", "javascript", "react", "vue"}},
	{"mobile", []string{"android", "ios", "mobile", "app", "flutter", "react native"}},
	{"data", []string{"database", "sql", "analytics", "etl", "data", "ml", "ai"}},
	{"devops", []string{"docker", "kubernetes", "ci", "cd", "deployment", "infrastructure"}},
	{"testing", []string{"test", "qa", "automation", "selenium", "cypress", "junit"}},
}

func (c *TrainingDataCollector) inferProjectDomain(taskData []map[string]any) string {
	scores := make([]int, len(mlDomainIndicators))
	for _, task := range taskData {
		content := strings.ToLower(value_objects.PyStr(task["title"]) + " " +
			value_objects.PyStr(task["description"]) + " " + value_objects.PyStr(task["details"]))
		for di, d := range mlDomainIndicators {
			for _, indicator := range d.indicators {
				if strings.Contains(content, indicator) {
					scores[di]++
				}
			}
		}
	}
	best := 0
	for i := range scores {
		if scores[i] > scores[best] {
			best = i
		}
	}
	if scores[best] > 0 {
		return mlDomainIndicators[best].domain
	}
	return "general"
}

// MLDependencyPredictor is ml_dependency_predictor.MLDependencyPredictor.
type MLDependencyPredictor struct {
	TaskRepository TaskLister
	Persistence    *MLModelPersistence
	DataCollector  *TrainingDataCollector
	PatternEngine  *intelligence.PatternRecognitionEngine

	now func() time.Time
}

// NewMLDependencyPredictor mirrors __init__ and loads the latest model.
func NewMLDependencyPredictor(taskRepository TaskLister, modelDir string) (*MLDependencyPredictor, error) {
	persistence, err := NewMLModelPersistence(modelDir)
	if err != nil {
		return nil, err
	}
	p := &MLDependencyPredictor{
		TaskRepository: taskRepository,
		Persistence:    persistence,
		DataCollector:  NewTrainingDataCollector(taskRepository),
		PatternEngine:  intelligence.NewPatternRecognitionEngine(),
		now:            mlNow,
	}
	p.loadLatestModel()
	return p, nil
}

func (p *MLDependencyPredictor) loadLatestModel() {
	versions := p.Persistence.GetAvailableVersions()
	if len(versions) == 0 {
		return
	}
	latestVersion := versions[0]
	patterns := p.Persistence.LoadPatterns(latestVersion)
	if patterns.Len() > 0 {
		p.PatternEngine.Patterns = patterns
		p.PatternEngine.Trained = true
	}
}

func mlTrainingSummaryDict(s intelligence.TrainingSummary) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("total_projects", s.TotalProjects)
	m.Set("patterns_learned", s.PatternsLearned)
	pt := entities.NewOrderedMap[any]()
	if s.PatternTypes != nil {
		for _, k := range s.PatternTypes.Keys() {
			v, _ := s.PatternTypes.Get(k)
			pt.Set(k, v)
		}
	}
	m.Set("pattern_types", pt)
	m.Set("average_confidence", s.AverageConfidence)
	m.Set("training_completed_at", s.TrainingCompletedAt)
	return m
}

func mlTrainingFailure(msg string, now time.Time) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("status", "failed")
	m.Set("error", msg)
	m.Set("timestamp", value_objects.IsoFormat(now))
	return m
}

// TrainModel mirrors train_model.
func (p *MLDependencyPredictor) TrainModel(projectLimit *int, saveModel bool) *entities.OrderedMap[any] {
	ctx := context.Background()
	trainingData := p.DataCollector.CollectProjectHistory(ctx, projectLimit)
	if len(trainingData) == 0 {
		return mlTrainingFailure("No training data available", p.now())
	}

	summary := p.PatternEngine.TrainFromHistoricalData(trainingData)
	results := mlTrainingSummaryDict(summary)

	if saveModel && p.PatternEngine.Patterns.Len() > 0 {
		modelVersion := p.now().Format("20060102_150405")
		modelPath, err := p.Persistence.SavePatterns(p.PatternEngine.Patterns, modelVersion)
		if err != nil {
			return mlTrainingFailure("Error training model: "+err.Error(), p.now())
		}
		results.Set("model_saved", modelPath)
		results.Set("model_version", modelVersion)
		p.Persistence.CleanupOldVersions(5)
	}

	results.Set("status", "completed")
	results.Set("training_data_projects", len(trainingData))
	return results
}

// PredictDependencies mirrors predict_dependencies (min confidence 0.4).
func (p *MLDependencyPredictor) PredictDependencies(task intelligence.PatternTask, candidateTasks []intelligence.PatternTask) []intelligence.PatternPrediction {
	if !p.PatternEngine.Trained {
		return []intelligence.PatternPrediction{}
	}
	predictions := p.PatternEngine.PredictDependencies(task, candidateTasks)
	filtered := []intelligence.PatternPrediction{}
	for _, pred := range predictions {
		if pred.Confidence >= 0.4 {
			filtered = append(filtered, pred)
		}
	}
	return filtered
}

func mlEngineStatsDict(s intelligence.EngineStats) *entities.OrderedMap[any] {
	if s.PatternTypes == nil {
		m := entities.NewOrderedMap[any]()
		m.Set("status", "not_trained")
		m.Set("patterns", 0)
		return m
	}
	m := entities.NewOrderedMap[any]()
	m.Set("status", s.Status)
	m.Set("total_patterns", s.TotalPatterns)
	pt := entities.NewOrderedMap[any]()
	for _, k := range s.PatternTypes.Keys() {
		v, _ := s.PatternTypes.Get(k)
		pt.Set(k, v)
	}
	m.Set("pattern_types", pt)
	m.Set("average_confidence", s.AverageConfidence)
	m.Set("average_support", s.AverageSupport)
	m.Set("last_updated", s.LastUpdated)
	return m
}

// GetModelInfo mirrors get_model_info.
func (p *MLDependencyPredictor) GetModelInfo() *entities.OrderedMap[any] {
	info := entities.NewOrderedMap[any]()
	info.Set("trained", p.PatternEngine.Trained)
	versions := p.Persistence.GetAvailableVersions()
	info.Set("available_versions", versions)
	if p.PatternEngine.Trained {
		info.Set("current_stats", mlEngineStatsDict(p.PatternEngine.GetEngineStats()))
	} else {
		info.Set("current_stats", nil)
	}
	info.Set("model_directory", p.Persistence.ModelDir)

	if len(versions) > 0 {
		metadataFile := filepath.Join(p.Persistence.ModelDir, "metadata_"+versions[0]+".json")
		if data, err := os.ReadFile(metadataFile); err == nil {
			if v, err := entities.DecodeJSON(data); err == nil {
				info.Set("latest_version_metadata", v)
			}
		}
	}
	return info
}

// RetrainModel mirrors retrain_model.
func (p *MLDependencyPredictor) RetrainModel() *entities.OrderedMap[any] {
	return p.TrainModel(nil, true)
}

// UpdatePatternFeedback mirrors update_pattern_feedback.
func (p *MLDependencyPredictor) UpdatePatternFeedback(patternID string, accepted bool) bool {
	pattern, ok := p.PatternEngine.Patterns.Get(patternID)
	if !ok {
		return false
	}
	support := float64(pattern.SupportCount)
	if accepted {
		pattern.SuccessRate = (pattern.SuccessRate*support + 1.0) / (support + 1)
	} else {
		pattern.SuccessRate = (pattern.SuccessRate * support) / (support + 1)
	}
	pattern.SupportCount++
	pattern.LastUpdated = p.now()
	return true
}
