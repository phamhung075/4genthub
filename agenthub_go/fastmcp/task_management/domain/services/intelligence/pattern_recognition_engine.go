package intelligence

import (
	"fmt"
	"sort"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/dlclark/regexp2"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// PatternType: types of dependency patterns.
type PatternType string

const (
	PatternSequential PatternType = "sequential"
	PatternParallel   PatternType = "parallel"
	PatternConverging PatternType = "converging"
	PatternBranching  PatternType = "branching"
	PatternCyclical   PatternType = "cyclical"
	PatternAgentBased PatternType = "agent_based"
	PatternTemporal   PatternType = "temporal"
)

// PatternTask is the duck-typed task of the Python engine: attributes are read with
// getattr, so a missing attribute is reported by ok == false.
type PatternTask interface {
	Attr(name string) (value any, ok bool)
}

// DictTask is a task given as a dict (the training data shape); Python wraps it in an
// object with one attribute per key.
type DictTask map[string]any

func (d DictTask) Attr(name string) (any, bool) { v, ok := d[name]; return v, ok }

// EntityTask adapts a Task entity: it has no `details` or `completed_at` attribute.
type EntityTask struct{ Task *entities.Task }

func (e EntityTask) Attr(name string) (any, bool) {
	t := e.Task
	switch name {
	case "id":
		return t.ID.String(), true
	case "title":
		return t.Title, true
	case "description":
		return t.Description, true
	case "assignees":
		out := make([]any, len(t.Assignees))
		for i, a := range t.Assignees {
			out[i] = a
		}
		return out, true
	case "priority":
		return t.Priority.Value, true
	case "estimated_effort":
		return t.EstimatedEffort, true
	case "created_at":
		if t.CreatedAt == nil {
			return nil, true
		}
		return *t.CreatedAt, true
	}
	return nil, false
}

// TaskVector is the vector representation of a task. CreationTime and CompletionTime are
// `any` because training data carries ISO strings while entities carry datetimes.
type TaskVector struct {
	TaskID            string
	TitleTokens       []string
	DescriptionTokens []string
	Agents            []string
	Priority          string
	EstimatedEffort   string
	FileReferences    []string
	TechnicalEntities []string
	CreationTime      any
	CompletionTime    any
}

// PatternFeatures characterise a task for pattern matching.
type PatternFeatures struct {
	TitleKeywords       []string
	DescriptionKeywords []string
	Agents              []string
	Priority            string
	EstimatedEffort     string
	HasFiles            bool
	FileTypes           []string
	HasEntities         bool
	EntityTypes         []string
}

// DependencyPattern is a learned dependency pattern. Metadata keeps Python's dict order
// and is mutated with current_match_score during matching.
type DependencyPattern struct {
	PatternID      string
	PatternType    PatternType
	SourceFeatures PatternFeatures
	TargetFeatures PatternFeatures
	Confidence     float64
	SupportCount   int
	SuccessRate    float64
	CreatedAt      time.Time
	LastUpdated    time.Time
	Metadata       *entities.OrderedMap[any]
}

// PatternEvidence is PatternPrediction.pattern_evidence.
type PatternEvidence struct {
	MatchingPatterns int
	AvgSupport       float64
	PatternTypes     []string
}

// PatternPrediction is a predicted dependency based on learned patterns.
type PatternPrediction struct {
	SourceTaskID    string
	TargetTaskID    string
	PatternIDs      []string
	Confidence      float64
	Reasoning       string
	FeaturesMatched []string
	PatternEvidence PatternEvidence
}

var stopWords = map[string]struct{}{}

func init() {
	for _, w := range strings.Fields("the a an and or but in on at to for of with by from into through during before after above below up down out off over under") {
		stopWords[w] = struct{}{}
	}
}

var (
	tokenRe    = services.PyRegex(`\b[a-zA-Z][a-zA-Z0-9_]*\b`, false)
	fileRefRes = []*regexp2.Regexp{
		services.PyRegex(`[\w\-/]+\.(?:py|js|ts|tsx|jsx|java|cpp|c|h|php|rb|go|rs|swift|kt|sql|json|yaml|yml|md)`, true),
		services.PyRegex(`(?:src|test|config|docs?)/[\w\-/]+`, true),
	}
	entityRes = []*regexp2.Regexp{
		services.PyRegex(`\b[A-Z][a-zA-Z0-9]*(?:Service|Controller|Model|Component|Manager|Handler|Repository)\b`, true),
		services.PyRegex(`\b(?:GET|POST|PUT|DELETE|PATCH)\s+[/\w\-{}]+`, true),
		services.PyRegex(`\btable\s+([a-z_][a-z0-9_]*)\b`, true),
		services.PyRegex(`\bclass\s+([A-Z][a-zA-Z0-9_]*)\b`, true),
	}
)

// findAll is re.findall for patterns with at most one group.
func findAll(re *regexp2.Regexp, text string) []string {
	out := []string{}
	rs := []rune(text)
	m, _ := re.FindRunesMatch(rs)
	for m != nil {
		if gs := m.Groups(); len(gs) > 1 {
			out = append(out, gs[1].String())
		} else {
			out = append(out, m.String())
		}
		m, _ = re.FindNextMatch(m)
	}
	return out
}

// uniqueFirstSeen is list(set(x)) with a deterministic (first-seen) order; Python's
// set order is per-process randomised.
func uniqueFirstSeen(in []string) []string {
	seen := map[string]struct{}{}
	out := []string{}
	for _, s := range in {
		if _, ok := seen[s]; !ok {
			seen[s] = struct{}{}
			out = append(out, s)
		}
	}
	return out
}

func truncate(in []string, n int) []string {
	if len(in) > n {
		return in[:n]
	}
	return in
}

// FeatureExtractor extracts features from tasks.
type FeatureExtractor struct {
	Now func() time.Time
}

func NewFeatureExtractor() *FeatureExtractor {
	return &FeatureExtractor{Now: func() time.Time { return time.Now().UTC() }}
}

// textAttr is `getattr(task, name, "") or ""`; a truthy non-string fails like Python's
// later str operations.
func textAttr(task PatternTask, name string) (string, error) {
	v, _ := task.Attr(name)
	if !value_objects.PyTruthy(v) {
		return "", nil
	}
	s, ok := v.(string)
	if !ok {
		return "", &value_objects.TypeError{Msg: fmt.Sprintf("%s is not a string", name)}
	}
	return s, nil
}

// ExtractTaskVector extracts the feature vector; any failure yields Python's minimal vector.
func (f *FeatureExtractor) ExtractTaskVector(task PatternTask) TaskVector {
	v, err := f.extractTaskVector(task)
	if err != nil {
		id := "unknown"
		if raw, ok := task.Attr("id"); ok {
			id = value_objects.PyStr(raw)
		}
		return TaskVector{
			TaskID: id, TitleTokens: []string{}, DescriptionTokens: []string{}, Agents: []string{},
			Priority: "medium", EstimatedEffort: "unknown", FileReferences: []string{},
			TechnicalEntities: []string{}, CreationTime: micros(f.Now()),
		}
	}
	return v
}

func (f *FeatureExtractor) extractTaskVector(task PatternTask) (TaskVector, error) {
	title, err := textAttr(task, "title")
	if err != nil {
		return TaskVector{}, err
	}
	details, err := textAttr(task, "details")
	if err != nil {
		return TaskVector{}, err
	}
	description, err := textAttr(task, "description")
	if err != nil {
		return TaskVector{}, err
	}
	text := description + " " + details

	idRaw, ok := task.Attr("id")
	if !ok {
		return TaskVector{}, &value_objects.TypeError{Msg: "task has no id"}
	}

	agents := []string{}
	if raw, _ := task.Attr("assignees"); value_objects.PyTruthy(raw) {
		list, ok := raw.([]any)
		if !ok {
			return TaskVector{}, &value_objects.TypeError{Msg: "assignees has no copy()"}
		}
		for _, a := range list {
			agents = append(agents, value_objects.PyStr(a))
		}
	}

	prioRaw, ok := task.Attr("priority")
	if !ok {
		return TaskVector{}, &value_objects.TypeError{Msg: "task has no priority"}
	}

	effort := "unknown"
	if raw, _ := task.Attr("estimated_effort"); value_objects.PyTruthy(raw) {
		effort = value_objects.PyStr(raw)
	}

	var created any = micros(f.Now())
	if raw, ok := task.Attr("created_at"); ok {
		created = raw
	}
	completed, _ := task.Attr("completed_at")

	return TaskVector{
		TaskID:            value_objects.PyStr(idRaw),
		TitleTokens:       f.tokenizeText(title),
		DescriptionTokens: f.tokenizeText(text),
		Agents:            agents,
		Priority:          value_objects.PyStr(prioRaw),
		EstimatedEffort:   effort,
		FileReferences:    f.extractFileReferences(text),
		TechnicalEntities: f.extractTechnicalEntities(text),
		CreationTime:      created,
		CompletionTime:    completed,
	}, nil
}

func (f *FeatureExtractor) tokenizeText(text string) []string {
	if text == "" {
		return []string{}
	}
	out := []string{}
	for _, tok := range findAll(tokenRe, value_objects.PyLower(text)) {
		if _, stop := stopWords[tok]; !stop && utf8.RuneCountInString(tok) > 2 {
			out = append(out, tok)
		}
	}
	return truncate(out, 50)
}

func (f *FeatureExtractor) extractFileReferences(text string) []string {
	var refs []string
	for _, re := range fileRefRes {
		refs = append(refs, findAll(re, text)...)
	}
	return truncate(uniqueFirstSeen(refs), 20)
}

func (f *FeatureExtractor) extractTechnicalEntities(text string) []string {
	var found []string
	for _, re := range entityRes {
		found = append(found, findAll(re, text)...)
	}
	return truncate(uniqueFirstSeen(found), 15)
}

// mostCommon is Counter(items).most_common(n): count descending, ties in first-seen order.
func mostCommon(items []string, n int) []string {
	counts := map[string]int{}
	order := []string{}
	for _, s := range items {
		if _, ok := counts[s]; !ok {
			order = append(order, s)
		}
		counts[s]++
	}
	sort.SliceStable(order, func(i, j int) bool { return counts[order[i]] > counts[order[j]] })
	return truncate(order, n)
}

// pyGreater is `a > b` for the creation-time values: datetimes, ISO strings or numbers.
func pyGreater(a, b any) (bool, error) {
	switch x := a.(type) {
	case time.Time:
		if y, ok := b.(time.Time); ok {
			return x.After(y), nil
		}
	case string:
		if y, ok := b.(string); ok {
			return x > y, nil
		}
	}
	return false, &value_objects.TypeError{Msg: "'>' not supported between these creation times"}
}

func stringSet(in []string) map[string]struct{} {
	s := make(map[string]struct{}, len(in))
	for _, x := range in {
		s[x] = struct{}{}
	}
	return s
}

func setsEqual(a, b map[string]struct{}) bool {
	if len(a) != len(b) {
		return false
	}
	for k := range a {
		if _, ok := b[k]; !ok {
			return false
		}
	}
	return true
}

// jaccardParts returns |a ∩ b| and |a ∪ b|.
func jaccardParts(a, b map[string]struct{}) (int, int) {
	inter := 0
	for k := range a {
		if _, ok := b[k]; ok {
			inter++
		}
	}
	return inter, len(a) + len(b) - inter
}

// PatternLearner learns patterns from historical dependency data.
type PatternLearner struct {
	Now              func() time.Time
	FeatureExtractor *FeatureExtractor
	Patterns         *entities.OrderedMap[*DependencyPattern]
	PatternCounter   int
}

func NewPatternLearner() *PatternLearner {
	return &PatternLearner{
		Now:              func() time.Time { return time.Now().UTC() },
		FeatureExtractor: NewFeatureExtractor(),
		Patterns:         entities.NewOrderedMap[*DependencyPattern](),
	}
}

// LearnFromProjectHistory learns patterns from projects; a failing project is skipped.
func (l *PatternLearner) LearnFromProjectHistory(projects []map[string]any) []*DependencyPattern {
	learned := []*DependencyPattern{}
	for _, project := range projects {
		if ps, err := l.analyzeProjectPatterns(project); err == nil {
			learned = append(learned, ps...)
		}
	}
	for _, p := range learned {
		l.Patterns.Set(p.PatternID, p)
	}
	return learned
}

// dependencyItems iterates `dependencies` like Python: a list, or a string by character.
func dependencyItems(v any) ([]any, error) {
	switch x := v.(type) {
	case []any:
		return x, nil
	case string:
		out := []any{}
		for _, r := range x {
			out = append(out, string(r))
		}
		return out, nil
	}
	return nil, &value_objects.TypeError{Msg: "dependencies is not iterable"}
}

func (l *PatternLearner) analyzeProjectPatterns(project map[string]any) ([]*DependencyPattern, error) {
	patterns := []*DependencyPattern{}
	rawTasks, _ := project["tasks"].([]any)
	if len(rawTasks) < 2 {
		return patterns, nil
	}

	vectors := entities.NewOrderedMap[TaskVector]()
	tasks := make([]map[string]any, 0, len(rawTasks))
	for _, rt := range rawTasks {
		td, ok := rt.(map[string]any)
		if !ok {
			return nil, &value_objects.TypeError{Msg: "task is not a dict"}
		}
		tasks = append(tasks, td)
		v := l.FeatureExtractor.ExtractTaskVector(DictTask(td))
		vectors.Set(v.TaskID, v)
	}

	for _, td := range tasks {
		taskID := ""
		if raw, ok := td["id"]; ok {
			taskID = value_objects.PyStr(raw)
		}
		rawDeps, _ := td["dependencies"]
		if !value_objects.PyTruthy(rawDeps) {
			continue
		}
		source, ok := vectors.Get(taskID)
		if !ok {
			continue
		}
		deps, err := dependencyItems(rawDeps)
		if err != nil {
			return nil, err
		}
		for _, d := range deps {
			target, ok := vectors.Get(value_objects.PyStr(d))
			if !ok {
				continue
			}
			ptype, err := l.identifyPatternType(source, target, len(deps))
			if err != nil {
				return nil, err
			}
			if p := l.extractDependencyPattern(source, target, ptype, project); p != nil {
				patterns = append(patterns, p)
			}
		}
	}
	return patterns, nil
}

func (l *PatternLearner) identifyPatternType(source, target TaskVector, depCount int) (PatternType, error) {
	if depCount > 2 {
		return PatternBranching, nil
	}
	if len(source.Agents) > 0 && len(target.Agents) > 0 {
		sa, ta := stringSet(source.Agents), stringSet(target.Agents)
		if inter, _ := jaccardParts(sa, ta); !setsEqual(sa, ta) && inter > 0 {
			return PatternAgentBased, nil
		}
	}
	if value_objects.PyTruthy(source.CreationTime) && value_objects.PyTruthy(target.CreationTime) {
		later, err := pyGreater(source.CreationTime, target.CreationTime)
		if err != nil {
			return "", err
		}
		if later {
			return PatternSequential, nil
		}
	}
	if len(source.Agents) > 0 && len(target.Agents) > 0 && setsEqual(stringSet(source.Agents), stringSet(target.Agents)) {
		return PatternAgentBased, nil
	}
	return PatternSequential, nil
}

func (l *PatternLearner) extractDependencyPattern(source, target TaskVector, ptype PatternType, project map[string]any) *DependencyPattern {
	id := fmt.Sprintf("pattern_%d", l.PatternCounter)
	l.PatternCounter++

	sf, tf := l.extractPatternFeatures(source), l.extractPatternFeatures(target)
	confidence := calculatePatternConfidence(sf, tf)
	if confidence < 0.3 {
		return nil
	}

	var projectID any = ""
	if v, ok := project["id"]; ok {
		projectID = v
	}
	var domain any = "unknown"
	if v, ok := project["domain"]; ok {
		domain = v
	}
	md := entities.NewOrderedMap[any]()
	md.Set("project_id", projectID)
	md.Set("project_domain", domain)
	md.Set("source_task_id", source.TaskID)
	md.Set("target_task_id", target.TaskID)

	now := micros(l.Now())
	return &DependencyPattern{
		PatternID: id, PatternType: ptype, SourceFeatures: sf, TargetFeatures: tf,
		Confidence: confidence, SupportCount: 1, SuccessRate: 1.0,
		CreatedAt: now, LastUpdated: now, Metadata: md,
	}
}

func (l *PatternLearner) extractPatternFeatures(v TaskVector) PatternFeatures {
	fileTypes := []string{}
	for _, ref := range v.FileReferences {
		if i := strings.LastIndex(ref, "."); i >= 0 {
			fileTypes = append(fileTypes, ref[i+1:])
		}
	}
	return PatternFeatures{
		TitleKeywords:       mostCommon(v.TitleTokens, 5),
		DescriptionKeywords: mostCommon(v.DescriptionTokens, 10),
		Agents:              v.Agents,
		Priority:            v.Priority,
		EstimatedEffort:     v.EstimatedEffort,
		HasFiles:            len(v.FileReferences) > 0,
		FileTypes:           uniqueFirstSeen(fileTypes),
		HasEntities:         len(v.TechnicalEntities) > 0,
		EntityTypes:         categorizeEntities(v.TechnicalEntities),
	}
}

func categorizeEntities(ents []string) []string {
	cats := []string{}
	for _, e := range ents {
		switch {
		case strings.HasSuffix(e, "Service") || strings.HasSuffix(e, "service"):
			cats = append(cats, "service")
		case strings.HasSuffix(e, "Controller") || strings.HasSuffix(e, "controller"):
			cats = append(cats, "controller")
		case strings.HasSuffix(e, "Model") || strings.HasSuffix(e, "model"):
			cats = append(cats, "model")
		case strings.HasSuffix(e, "Component") || strings.HasSuffix(e, "component"):
			cats = append(cats, "component")
		case strings.HasPrefix(e, "GET") || strings.HasPrefix(e, "POST") || strings.HasPrefix(e, "PUT") || strings.HasPrefix(e, "DELETE"):
			cats = append(cats, "api_endpoint")
		case strings.Contains(value_objects.PyLower(e), "table"):
			cats = append(cats, "database")
		default:
			cats = append(cats, "other")
		}
	}
	return uniqueFirstSeen(cats)
}

// mockMean is MockNumpy.mean (numpy is not a dependency): sum(values) / len(values).
func mockMean(values []float64) float64 {
	if len(values) == 0 {
		return 0.0
	}
	return value_objects.PySum(values) / float64(len(values))
}

func calculatePatternConfidence(sf, tf PatternFeatures) float64 {
	var factors []float64

	sk := stringSet(append(append([]string{}, sf.TitleKeywords...), sf.DescriptionKeywords...))
	tk := stringSet(append(append([]string{}, tf.TitleKeywords...), tf.DescriptionKeywords...))
	if len(sk) > 0 && len(tk) > 0 {
		inter, union := jaccardParts(sk, tk)
		sim := 0.0
		if union > 0 {
			sim = float64(inter) / float64(union)
		}
		factors = append(factors, sim)
	}
	if sa, ta := stringSet(sf.Agents), stringSet(tf.Agents); len(sa) > 0 && len(ta) > 0 {
		inter, union := jaccardParts(sa, ta)
		factors = append(factors, float64(float64(inter)/float64(union)*0.8))
	}
	if sf2, tf2 := stringSet(sf.FileTypes), stringSet(tf.FileTypes); len(sf2) > 0 && len(tf2) > 0 {
		inter, union := jaccardParts(sf2, tf2)
		factors = append(factors, float64(float64(inter)/float64(union)*0.6))
	}
	if se, te := stringSet(sf.EntityTypes), stringSet(tf.EntityTypes); len(se) > 0 && len(te) > 0 {
		inter, union := jaccardParts(se, te)
		factors = append(factors, float64(float64(inter)/float64(union)*0.7))
	}
	if len(factors) == 0 {
		return 0.2
	}
	return value_objects.PySum(factors) / float64(len(factors))
}

// PatternRecognitionEngine predicts likely dependencies from learned patterns.
type PatternRecognitionEngine struct {
	Now              func() time.Time
	FeatureExtractor *FeatureExtractor
	PatternLearner   *PatternLearner
	Patterns         *entities.OrderedMap[*DependencyPattern]
	Trained          bool
}

func NewPatternRecognitionEngine() *PatternRecognitionEngine {
	return &PatternRecognitionEngine{
		Now:              func() time.Time { return time.Now().UTC() },
		FeatureExtractor: NewFeatureExtractor(),
		PatternLearner:   NewPatternLearner(),
		Patterns:         entities.NewOrderedMap[*DependencyPattern](),
	}
}

// SetClock sets the clock of the engine and its components.
func (e *PatternRecognitionEngine) SetClock(now func() time.Time) {
	e.Now, e.FeatureExtractor.Now, e.PatternLearner.Now, e.PatternLearner.FeatureExtractor.Now = now, now, now, now
}

// TrainingSummary is the result of TrainFromHistoricalData.
type TrainingSummary struct {
	TotalProjects       int
	PatternsLearned     int
	PatternTypes        *entities.OrderedMap[int]
	AverageConfidence   float64
	TrainingCompletedAt string
}

func countTypes(patterns []*DependencyPattern) *entities.OrderedMap[int] {
	m := entities.NewOrderedMap[int]()
	for _, p := range patterns {
		n, _ := m.Get(string(p.PatternType))
		m.Set(string(p.PatternType), n+1)
	}
	return m
}

func confidences(patterns []*DependencyPattern) []float64 {
	out := make([]float64, len(patterns))
	for i, p := range patterns {
		out[i] = p.Confidence
	}
	return out
}

// TrainFromHistoricalData trains the engine from completed projects.
func (e *PatternRecognitionEngine) TrainFromHistoricalData(history []map[string]any) TrainingSummary {
	learned := e.PatternLearner.LearnFromProjectHistory(history)
	for _, p := range learned {
		e.Patterns.Set(p.PatternID, p)
	}
	e.Trained = true
	return TrainingSummary{
		TotalProjects:       len(history),
		PatternsLearned:     len(learned),
		PatternTypes:        countTypes(learned),
		AverageConfidence:   mockMean(confidences(learned)),
		TrainingCompletedAt: value_objects.IsoFormat(micros(e.Now())),
	}
}

// PredictDependencies predicts the top five dependencies of task among available.
// Any failure (e.g. a task without an id) yields no predictions, as in Python.
func (e *PatternRecognitionEngine) PredictDependencies(task PatternTask, available []PatternTask) []PatternPrediction {
	none := []PatternPrediction{}
	if !e.Trained || e.Patterns.Len() == 0 {
		return none
	}
	// Without an id, str(task.id) raises on the first candidate and the whole call is
	// caught, so no predictions are produced.
	taskIDRaw, ok := task.Attr("id")
	if !ok {
		return none
	}
	taskID := value_objects.PyStr(taskIDRaw)

	sv := e.FeatureExtractor.ExtractTaskVector(task)
	sf := e.PatternLearner.extractPatternFeatures(sv)

	var predictions []PatternPrediction
	for _, cand := range available {
		cidRaw, ok := cand.Attr("id")
		if !ok {
			return none
		}
		if value_objects.PyStr(cidRaw) == taskID {
			continue
		}
		cv := e.FeatureExtractor.ExtractTaskVector(cand)
		cf := e.PatternLearner.extractPatternFeatures(cv)
		if matching := e.findMatchingPatterns(sf, cf); len(matching) > 0 {
			predictions = append(predictions, createPrediction(sv.TaskID, cv.TaskID, matching))
		}
	}
	sort.SliceStable(predictions, func(i, j int) bool { return predictions[i].Confidence > predictions[j].Confidence })
	return truncatePredictions(predictions, 5)
}

func truncatePredictions(in []PatternPrediction, n int) []PatternPrediction {
	if len(in) > n {
		return in[:n]
	}
	if in == nil {
		return []PatternPrediction{}
	}
	return in
}

func matchScoreOf(p *DependencyPattern) float64 {
	v, _ := p.Metadata.Get("current_match_score")
	if f, ok := v.(float64); ok {
		return f
	}
	return 0
}

func (e *PatternRecognitionEngine) findMatchingPatterns(sf, tf PatternFeatures) []*DependencyPattern {
	var matching []*DependencyPattern
	for _, id := range e.Patterns.Keys() {
		p, _ := e.Patterns.Get(id)
		if score := calculatePatternMatchScore(sf, tf, p); score > 0.5 {
			p.Metadata.Set("current_match_score", score)
			matching = append(matching, p)
		}
	}
	sort.SliceStable(matching, func(i, j int) bool { return matchScoreOf(matching[i]) > matchScoreOf(matching[j]) })
	return matching
}

func calculatePatternMatchScore(sf, tf PatternFeatures, p *DependencyPattern) float64 {
	base := mockMean([]float64{matchFeatures(sf, p.SourceFeatures), matchFeatures(tf, p.TargetFeatures)})
	successBoost := float64(p.SuccessRate * 0.2)
	supportBoost := pyMin(0.1, float64(p.SupportCount)/10.0)
	return pyMin(base+successBoost+supportBoost, 1.0)
}

func matchFeatures(a, b PatternFeatures) float64 {
	var sims []float64
	jaccard := func(x, y []string) (float64, bool) {
		sx, sy := stringSet(x), stringSet(y)
		if len(sx) == 0 && len(sy) == 0 {
			return 0, false
		}
		inter, union := jaccardParts(sx, sy)
		if union > 0 {
			return float64(inter) / float64(union), true
		}
		return 0, true
	}
	for _, pair := range [][2][]string{{a.TitleKeywords, b.TitleKeywords}, {a.DescriptionKeywords, b.DescriptionKeywords}} {
		if s, ok := jaccard(pair[0], pair[1]); ok {
			sims = append(sims, s)
		}
	}
	if s, ok := jaccard(a.Agents, b.Agents); ok {
		sims = append(sims, float64(s*1.5))
	}
	for _, pair := range [][2]string{{a.Priority, b.Priority}, {a.EstimatedEffort, b.EstimatedEffort}} {
		if pair[0] == pair[1] {
			sims = append(sims, 1.0)
		} else {
			sims = append(sims, 0.0)
		}
	}
	for _, pair := range [][2][]string{{a.FileTypes, b.FileTypes}, {a.EntityTypes, b.EntityTypes}} {
		if s, ok := jaccard(pair[0], pair[1]); ok {
			sims = append(sims, s)
		}
	}
	return mockMean(sims)
}

func createPrediction(sourceID, targetID string, matching []*DependencyPattern) PatternPrediction {
	weights := make([]float64, len(matching))
	totalSupport := 0
	types := make([]string, len(matching))
	ids := make([]string, len(matching))
	for i, p := range matching {
		weights[i] = float64(p.Confidence * float64(p.SupportCount))
		totalSupport += p.SupportCount
		types[i] = string(p.PatternType)
		ids[i] = p.PatternID
	}
	confidence := 0.0
	if totalSupport > 0 {
		confidence = value_objects.PySum(weights) / float64(totalSupport)
	}
	mostCommonType := "unknown"
	if mc := mostCommon(types, 1); len(mc) > 0 {
		mostCommonType = mc[0]
	}
	avgSupport := float64(totalSupport) / float64(len(matching))
	reasoning := fmt.Sprintf("Predicted based on %d similar %s pattern(s) with average support of %.1f", len(matching), mostCommonType, avgSupport)

	matched := []string{}
	top := matching
	if len(top) > 3 {
		top = top[:3]
	}
	for _, p := range top {
		if score := matchScoreOf(p); score > 0.7 {
			matched = append(matched, fmt.Sprintf("%s (score: %.2f)", p.PatternType, score))
		}
	}
	return PatternPrediction{
		SourceTaskID: sourceID, TargetTaskID: targetID, PatternIDs: ids, Confidence: confidence,
		Reasoning: reasoning, FeaturesMatched: matched,
		PatternEvidence: PatternEvidence{MatchingPatterns: len(matching), AvgSupport: avgSupport, PatternTypes: types},
	}
}

// EngineStats is get_engine_stats' dict. Untrained engines report only Status
// "not_trained" and TotalPatterns 0 (Python's key there is "patterns").
type EngineStats struct {
	Status            string
	TotalPatterns     int
	PatternTypes      *entities.OrderedMap[int]
	AverageConfidence float64
	AverageSupport    float64
	LastUpdated       string
}

// GetEngineStats returns statistics about the engine.
func (e *PatternRecognitionEngine) GetEngineStats() EngineStats {
	if e.Patterns.Len() == 0 {
		return EngineStats{Status: "not_trained"}
	}
	var all []*DependencyPattern
	supports := make([]float64, 0, e.Patterns.Len())
	var last time.Time
	for i, id := range e.Patterns.Keys() {
		p, _ := e.Patterns.Get(id)
		all = append(all, p)
		supports = append(supports, float64(p.SupportCount))
		if i == 0 || p.LastUpdated.After(last) {
			last = p.LastUpdated
		}
	}
	status := "not_trained"
	if e.Trained {
		status = "trained"
	}
	return EngineStats{
		Status: status, TotalPatterns: len(all), PatternTypes: countTypes(all),
		AverageConfidence: mockMean(confidences(all)), AverageSupport: mockMean(supports),
		LastUpdated: value_objects.IsoFormat(last),
	}
}
