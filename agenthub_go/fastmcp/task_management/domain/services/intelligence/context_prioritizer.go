package intelligence

import (
	"fmt"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ScoreFactor is a factor used in context scoring.
type ScoreFactor string

const (
	ScoreSemanticRelevance ScoreFactor = "semantic_relevance"
	ScoreRecency           ScoreFactor = "recency"
	ScoreFrequency         ScoreFactor = "frequency"
	ScoreCompleteness      ScoreFactor = "completeness"
	ScoreSizePenalty       ScoreFactor = "size_penalty"
	ScoreUserPreference    ScoreFactor = "user_preference"
	ScoreProjectPriority   ScoreFactor = "project_priority"
	ScoreDependencyBoost   ScoreFactor = "dependency_boost"
	ScoreTaskStatus        ScoreFactor = "task_status"
	ScoreAgentAffinity     ScoreFactor = "agent_affinity"
)

// ScoringWeights are the configurable weights of the scoring factors.
type ScoringWeights struct {
	SemanticRelevance float64
	Recency           float64
	Frequency         float64
	Completeness      float64
	SizePenalty       float64
	UserPreference    float64
	ProjectPriority   float64
	DependencyBoost   float64
}

// NewScoringWeights returns the Python defaults.
func NewScoringWeights() ScoringWeights {
	return ScoringWeights{0.3, 0.15, 0.15, 0.10, 0.05, 0.10, 0.10, 0.05}
}

// Normalize scales the weights (except the size penalty) to sum to 1.0.
func (w ScoringWeights) Normalize() ScoringWeights {
	total := w.SemanticRelevance + w.Recency + w.Frequency + w.Completeness + w.UserPreference + w.ProjectPriority + w.DependencyBoost
	if total > 0 {
		f := 1.0 / total
		return ScoringWeights{w.SemanticRelevance * f, w.Recency * f, w.Frequency * f, w.Completeness * f,
			w.SizePenalty, w.UserPreference * f, w.ProjectPriority * f, w.DependencyBoost * f}
	}
	return w
}

// ContextScore is the detailed score breakdown of a context. FactorScores keeps the
// insertion order of the Python dict.
type ContextScore struct {
	ContextID    string
	TotalScore   float64
	FactorScores *entities.OrderedMap[float64]
	Explanations []string
	EstimatedTok int
	ContextType  any
	LastAccessed *time.Time
}

// UserPreferences are user-specific context preferences.
type UserPreferences struct {
	PreferredContextTypes []string
	MaxContextSize        int
	PriorityBoostKeywords []string
	PenaltyKeywords       []string
	AgentPreferences      map[string]float64
}

// NewUserPreferences returns the Python defaults.
func NewUserPreferences() *UserPreferences {
	return &UserPreferences{PreferredContextTypes: []string{}, MaxContextSize: 2000, PriorityBoostKeywords: []string{},
		PenaltyKeywords: []string{}, AgentPreferences: map[string]float64{}}
}

// ContextPrioritizer is the multi-factor context prioritization engine.
type ContextPrioritizer struct {
	DefaultWeights       ScoringWeights
	RecencyDecayHours    float64
	FrequencyWindowDays  int
	SizePenaltyThreshold int
	ContextAccessHistory *entities.OrderedMap[[]time.Time]
	Now                  func() time.Time
}

// NewContextPrioritizer builds a prioritizer; weights nil = defaults (24h decay, 30 day
// window, 1500 token threshold are the Python defaults, see DefaultContextPrioritizer).
func NewContextPrioritizer(weights *ScoringWeights, recencyDecayHours float64, frequencyWindowDays, sizePenaltyThreshold int) *ContextPrioritizer {
	w := NewScoringWeights()
	if weights != nil {
		w = *weights
	}
	return &ContextPrioritizer{DefaultWeights: w, RecencyDecayHours: recencyDecayHours, FrequencyWindowDays: frequencyWindowDays,
		SizePenaltyThreshold: sizePenaltyThreshold, ContextAccessHistory: entities.NewOrderedMap[[]time.Time](),
		Now: func() time.Time { return time.Now().UTC() }}
}

func DefaultContextPrioritizer() *ContextPrioritizer {
	return NewContextPrioritizer(nil, 24.0, 30, 1500)
}

// pyMin / pyMax reproduce Python's min(a, b) / max(a, b) (first argument wins ties and NaN).
func pyMin(a, b float64) float64 {
	if b < a {
		return b
	}
	return a
}

func pyMax(a, b float64) float64 {
	if b > a {
		return b
	}
	return a
}

// contextIDOf is `data.get("id") or str(data.get("context_id", ""))`; non-string ids
// are rendered with str().
func contextIDOf(data map[string]any) string {
	if id, ok := data["id"]; ok && value_objects.PyTruthy(id) {
		return value_objects.PyStr(id)
	}
	cid, ok := data["context_id"]
	if !ok {
		return ""
	}
	return value_objects.PyStr(cid)
}

func ctxType(data map[string]any, def string) any {
	if v, ok := data["context_type"]; ok {
		return v
	}
	return def
}

// ScoreContext scores one context. An error is returned where Python raises (a
// non-numeric project priority multiplier). weights nil = default weights, normalized.
func (p *ContextPrioritizer) ScoreContext(contextID string, data map[string]any, query string, semanticSimilarity float64,
	prefs *UserPreferences, projectContext, currentTask map[string]any, weights *ScoringWeights) (*ContextScore, error) {
	w := p.DefaultWeights.Normalize()
	if weights != nil {
		w = *weights
	}
	if prefs == nil {
		prefs = NewUserPreferences()
	}
	factors := entities.NewOrderedMap[float64]()
	var expl []string

	semantic := p.calculateSemanticScore(data, query, semanticSimilarity)
	factors.Set(string(ScoreSemanticRelevance), semantic)
	expl = append(expl, fmt.Sprintf("Semantic relevance: %.3f", semantic))
	recency := p.calculateRecencyScore(contextID)
	factors.Set(string(ScoreRecency), recency)
	expl = append(expl, fmt.Sprintf("Recency: %.3f", recency))
	frequency := p.calculateFrequencyScore(contextID)
	factors.Set(string(ScoreFrequency), frequency)
	expl = append(expl, fmt.Sprintf("Frequency: %.3f", frequency))
	completeness := calculateCompletenessScore(data)
	factors.Set(string(ScoreCompleteness), completeness)
	expl = append(expl, fmt.Sprintf("Completeness: %.3f", completeness))
	sizePenalty := p.calculateSizePenalty(data)
	factors.Set(string(ScoreSizePenalty), sizePenalty)
	if sizePenalty > 0 {
		expl = append(expl, fmt.Sprintf("Size penalty: %.3f", sizePenalty))
	}
	userPref := calculateUserPreferenceScore(data, prefs, query)
	factors.Set(string(ScoreUserPreference), userPref)
	expl = append(expl, fmt.Sprintf("User preference: %.3f", userPref))
	projectScore, err := calculateProjectPriorityScore(data, projectContext)
	if err != nil {
		return nil, err
	}
	factors.Set(string(ScoreProjectPriority), projectScore)
	expl = append(expl, fmt.Sprintf("Project priority: %.3f", projectScore))
	dep := calculateDependencyBoost(data, currentTask)
	factors.Set(string(ScoreDependencyBoost), dep)
	if dep > 0 {
		expl = append(expl, fmt.Sprintf("Dependency boost: %.3f", dep))
	}

	// Each product is converted explicitly so no fused multiply-add changes the last bits.
	total := float64(semantic*w.SemanticRelevance) + float64(recency*w.Recency) + float64(frequency*w.Frequency) +
		float64(completeness*w.Completeness) + float64(userPref*w.UserPreference) + float64(projectScore*w.ProjectPriority) +
		float64(dep*w.DependencyBoost) - float64(sizePenalty*w.SizePenalty)
	total = pyMax(0.0, pyMin(1.0, total))

	return &ContextScore{ContextID: contextID, TotalScore: total, FactorScores: factors, Explanations: expl,
		EstimatedTok: estimateTokens(data), ContextType: ctxType(data, "unknown"), LastAccessed: p.lastAccessTime(contextID)}, nil
}

// ScoreContextsBatch scores many contexts, sorted by total score (descending, stable).
func (p *ContextPrioritizer) ScoreContextsBatch(contexts []map[string]any, query string, similarities map[string]float64,
	prefs *UserPreferences, projectContext, currentTask map[string]any, weights *ScoringWeights) ([]*ContextScore, error) {
	scores := []*ContextScore{}
	for _, c := range contexts {
		id := contextIDOf(c)
		s, err := p.ScoreContext(id, c, query, similarities[id], prefs, projectContext, currentTask, weights)
		if err != nil {
			return nil, err
		}
		scores = append(scores, s)
	}
	sort.SliceStable(scores, func(i, j int) bool { return scores[i].TotalScore > scores[j].TotalScore })
	return scores, nil
}

func wordSet(s string) map[string]struct{} {
	set := map[string]struct{}{}
	for _, w := range value_objects.PySplit(value_objects.PyLower(s)) {
		set[w] = struct{}{}
	}
	return set
}

func (p *ContextPrioritizer) calculateSemanticScore(data map[string]any, query string, similarity float64) float64 {
	queryWords, ctxWords := wordSet(query), wordSet(extractSearchableText(data))
	matches := 0
	for w := range queryWords {
		if _, ok := ctxWords[w]; ok {
			matches++
		}
	}
	boost := pyMin(0.2, float64(matches)*0.05)
	return pyMin(1.0, similarity+boost)
}

func (p *ContextPrioritizer) calculateRecencyScore(contextID string) float64 {
	last := p.lastAccessTime(contextID)
	if last == nil {
		return 0.1
	}
	hoursAgo := value_objects.PyTotalSeconds(p.Now().Sub(*last)) / 3600
	return value_objects.PyExp(-hoursAgo / p.RecencyDecayHours)
}

func (p *ContextPrioritizer) calculateFrequencyScore(contextID string) float64 {
	history, ok := p.ContextAccessHistory.Get(contextID)
	if !ok {
		return 0.1
	}
	cutoff := p.Now().Add(-time.Duration(p.FrequencyWindowDays) * 24 * time.Hour)
	recent := 0
	for _, a := range history {
		if a.After(cutoff) {
			recent++
		}
	}
	return pyMin(1.0, value_objects.PyLog(float64(recent+1))/value_objects.PyLog(float64(p.FrequencyWindowDays+1)))
}

var expectedFields = map[string][]string{
	"task":    {"title", "description", "status", "assignees", "details"},
	"branch":  {"git_branch_name", "branch_info", "branch_workflow"},
	"project": {"name", "description", "project_settings"},
	"global":  {"organization_name", "global_settings"},
}

func calculateCompletenessScore(data map[string]any) float64 {
	fields := expectedFields["task"]
	if t, ok := ctxType(data, "task").(string); ok {
		if f, found := expectedFields[t]; found {
			fields = f
		}
	}
	filled := 0
	for _, f := range fields {
		if v, ok := data[f]; ok && value_objects.PyTruthy(v) {
			filled++
		}
	}
	return float64(filled) / float64(len(fields))
}

func (p *ContextPrioritizer) calculateSizePenalty(data map[string]any) float64 {
	tokens := estimateTokens(data)
	if tokens <= p.SizePenaltyThreshold {
		return 0.0
	}
	return pyMin(0.5, float64(tokens-p.SizePenaltyThreshold)/float64(p.SizePenaltyThreshold))
}

func containsString(list []string, s string) bool {
	for _, x := range list {
		if x == s {
			return true
		}
	}
	return false
}

func calculateUserPreferenceScore(data map[string]any, prefs *UserPreferences, query string) float64 {
	base := 0.5
	if t, ok := ctxType(data, "unknown").(string); ok && containsString(prefs.PreferredContextTypes, t) {
		base += 0.3
	}
	queryLower := value_objects.PyLower(query)
	text := value_objects.PyLower(extractSearchableText(data))
	for _, k := range prefs.PriorityBoostKeywords {
		kl := value_objects.PyLower(k)
		if strings.Contains(queryLower, kl) || strings.Contains(text, kl) {
			base += 0.1
		}
	}
	for _, k := range prefs.PenaltyKeywords {
		kl := value_objects.PyLower(k)
		if strings.Contains(queryLower, kl) || strings.Contains(text, kl) {
			base -= 0.1
		}
	}
	if assignees, ok := data["assignees"].([]any); ok {
		for _, a := range assignees {
			if name, isStr := a.(string); isStr {
				if pref, found := prefs.AgentPreferences[name]; found {
					base += float64(pref * 0.1)
				}
			}
		}
	}
	return pyMax(0.0, pyMin(1.0, base))
}

var statusPriorities = map[string]float64{"in_progress": 0.9, "review": 0.8, "blocked": 0.7, "todo": 0.5, "done": 0.2}

func calculateProjectPriorityScore(data, projectContext map[string]any) (float64, error) {
	base := 0.5
	if len(projectContext) == 0 {
		return base, nil
	}
	ct := ctxType(data, "unknown")
	if priorities, ok := projectContext["priorities"].(map[string]any); ok {
		if name, isStr := ct.(string); isStr {
			if mult, found := priorities[name]; found {
				f, ok := value_objects.PyFloat(mult)
				if !ok {
					return 0, fmt.Errorf("project priority for %q is not a number", name)
				}
				base = f
			}
		}
	}
	if ct == "task" {
		status := "todo"
		if s, ok := data["status"]; ok {
			if str, isStr := s.(string); isStr {
				status = str
			} else {
				status = ""
			}
		}
		mult := 0.5
		if m, ok := statusPriorities[status]; ok {
			mult = m
		}
		base *= mult
	}
	return pyMax(0.0, pyMin(1.0, base)), nil
}

func calculateDependencyBoost(data, currentTask map[string]any) float64 {
	if len(currentTask) == 0 {
		return 0.0
	}
	id := contextIDOf(data)
	if deps, ok := currentTask["dependencies"].([]any); ok {
		for _, d := range deps {
			if s, isStr := d.(string); isStr && s == id {
				return 0.8
			}
		}
	}
	if b, c := data["git_branch_id"], currentTask["git_branch_id"]; value_objects.PyTruthy(b) && value_objects.PyTruthy(c) && value_objects.PyEqual(b, c) {
		return 0.3
	}
	if b, c := data["project_id"], currentTask["project_id"]; value_objects.PyTruthy(b) && value_objects.PyTruthy(c) && value_objects.PyEqual(b, c) {
		return 0.1
	}
	return 0.0
}

// estimateTokens is max(1, len(json.dumps(data, default=str)) // 4).
func estimateTokens(data map[string]any) int {
	n := len([]rune(value_objects.PyJSONDumpsDefaultStr(data, -1))) / 4
	if n < 1 {
		return 1
	}
	return n
}

func extractSearchableText(data map[string]any) string {
	var parts []string
	for _, f := range []string{"title", "description", "details", "name", "git_branch_name"} {
		if s, ok := data[f].(string); ok {
			parts = append(parts, s)
		}
	}
	return strings.Join(parts, " ")
}

func (p *ContextPrioritizer) lastAccessTime(contextID string) *time.Time {
	history, ok := p.ContextAccessHistory.Get(contextID)
	if !ok || len(history) == 0 {
		return nil
	}
	last := history[0]
	for _, t := range history[1:] {
		if t.After(last) {
			last = t
		}
	}
	return &last
}

// RecordContextAccess records an access (zero time = now) and trims history older than
// twice the frequency window.
func (p *ContextPrioritizer) RecordContextAccess(contextID string, accessTime time.Time) {
	if accessTime.IsZero() {
		accessTime = p.Now()
	}
	history, _ := p.ContextAccessHistory.Get(contextID)
	history = append(history, accessTime)
	cutoff := p.Now().Add(-time.Duration(p.FrequencyWindowDays*2) * 24 * time.Hour)
	kept := []time.Time{}
	for _, t := range history {
		if t.After(cutoff) {
			kept = append(kept, t)
		}
	}
	p.ContextAccessHistory.Set(contextID, kept)
}

// AdjustWeightsDynamically adjusts weights from query length, context type and feedback.
func (p *ContextPrioritizer) AdjustWeightsDynamically(query, contextType string, feedback map[string]float64) ScoringWeights {
	w := NewScoringWeights()
	words := len(value_objects.PySplit(query))
	if words > 10 {
		w.SemanticRelevance, w.Completeness = 0.4, 0.15
	} else if words <= 3 {
		w.Frequency, w.Recency = 0.2, 0.2
	}
	switch contextType {
	case "task":
		w.DependencyBoost, w.ProjectPriority = 0.1, 0.15
	case "global":
		w.Frequency, w.Completeness = 0.1, 0.2
	}
	names := make([]string, 0, len(feedback))
	for k := range feedback {
		names = append(names, k)
	}
	sort.Strings(names)
	for _, name := range names {
		if f := w.field(name); f != nil {
			*f = pyMax(0.0, pyMin(1.0, *f+feedback[name]))
		}
	}
	return w.Normalize()
}

func (w *ScoringWeights) field(name string) *float64 {
	switch name {
	case "semantic_relevance":
		return &w.SemanticRelevance
	case "recency":
		return &w.Recency
	case "frequency":
		return &w.Frequency
	case "completeness":
		return &w.Completeness
	case "size_penalty":
		return &w.SizePenalty
	case "user_preference":
		return &w.UserPreference
	case "project_priority":
		return &w.ProjectPriority
	case "dependency_boost":
		return &w.DependencyBoost
	}
	return nil
}

// ScoringStats is the result of GetScoringStats; nil when nothing is tracked.
type ScoringStats struct {
	TotalContextsTracked  int
	TotalAccessesRecorded int
	AvgAccessesPerContext float64
	RecencyDecayHours     float64
	FrequencyWindowDays   int
	SizePenaltyThreshold  int
	MostFrequentContexts  []ContextAccessCount
}

type ContextAccessCount struct {
	ContextID   string
	AccessCount int
}

func (p *ContextPrioritizer) GetScoringStats() *ScoringStats {
	n := p.ContextAccessHistory.Len()
	if n == 0 {
		return nil
	}
	total := 0
	var counts []ContextAccessCount
	for _, id := range p.ContextAccessHistory.Keys() {
		h, _ := p.ContextAccessHistory.Get(id)
		total += len(h)
		counts = append(counts, ContextAccessCount{id, len(h)})
	}
	sort.SliceStable(counts, func(i, j int) bool { return counts[i].AccessCount > counts[j].AccessCount })
	if len(counts) > 5 {
		counts = counts[:5]
	}
	return &ScoringStats{n, total, float64(total) / float64(n), p.RecencyDecayHours, p.FrequencyWindowDays,
		p.SizePenaltyThreshold, counts}
}
