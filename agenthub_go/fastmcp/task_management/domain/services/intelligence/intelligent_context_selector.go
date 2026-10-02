package intelligence

import (
	"fmt"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// SelectionResult is the result of an intelligent context selection.
type SelectionResult struct {
	SelectedContexts []map[string]any
	TotalTokensUsed  int
	SelectionTimeMs  float64
	HitRateEstimate  float64
	SizeReductionPct float64
	Metadata         *entities.OrderedMap[any]
}

// SelectionMetrics are the metrics for monitoring selection performance.
type SelectionMetrics struct {
	TotalSelections    int
	AvgSelectionTimeMs float64
	AvgHitRate         float64
	AvgSizeReduction   float64
	ContextsSelected   int
	ContextsAvailable  int
	CacheHitRate       float64
}

// PerformanceEntry is one performance_history record.
type PerformanceEntry struct {
	Timestamp        time.Time
	SelectionTimeMs  float64
	HitRateEstimate  float64
	SizeReductionPct float64
	TokensUsed       int
	ContextsSelected int
}

type cachedSelection struct {
	key    string
	result *SelectionResult
	at     time.Time
}

// IntelligentContextSelector orchestrates semantic matching, prioritization,
// progressive expansion and predictive loading.
type IntelligentContextSelector struct {
	SemanticMatcher     *SemanticMatcher
	ProgressiveExpander *ProgressiveExpander
	PredictiveLoader    *PredictiveLoader
	ContextPrioritizer  *ContextPrioritizer

	DefaultTokenBudget  int
	MaxSelectionTimeMs  float64
	TargetHitRate       float64
	TargetSizeReduction float64
	EnableCaching       bool
	CacheTTLSeconds     int
	EnableMetrics       bool

	// Now is the clock (UTC) used for timing, cache age and history stamps.
	Now func() time.Time

	resultCache        []*cachedSelection
	Metrics            SelectionMetrics
	PerformanceHistory []PerformanceEntry

	AvailableContexts []map[string]any
	CurrentSessionID  *string
}

// SelectorConfig holds the constructor arguments with Python's defaults via
// DefaultSelectorConfig.
type SelectorConfig struct {
	SemanticModel       string
	SimilarityThreshold float64
	DefaultTokenBudget  int
	MaxSelectionTimeMs  float64
	TargetHitRate       float64
	TargetSizeReduction float64
	EnableCaching       bool
	CacheTTLSeconds     int
	EnableMetrics       bool
	// CacheDir is the embedding cache directory ("" = <cwd>/.cache/embeddings).
	CacheDir string
}

// DefaultSelectorConfig returns the Python defaults.
func DefaultSelectorConfig() SelectorConfig {
	return SelectorConfig{
		SemanticModel: "all-MiniLM-L6-v2", SimilarityThreshold: 0.5, DefaultTokenBudget: 2000,
		MaxSelectionTimeMs: 200.0, TargetHitRate: 0.9, TargetSizeReduction: 0.5,
		EnableCaching: true, CacheTTLSeconds: 300, EnableMetrics: true,
	}
}

// NewIntelligentContextSelector builds the selector and its four components.
func NewIntelligentContextSelector(cfg SelectorConfig) (*IntelligentContextSelector, error) {
	matcher, err := NewSemanticMatcher(cfg.SemanticModel, cfg.SimilarityThreshold, true, cfg.CacheDir, "", nil)
	if err != nil {
		return nil, err
	}
	expander := DefaultProgressiveExpander()
	expander.DefaultTokenBudget = cfg.DefaultTokenBudget
	return &IntelligentContextSelector{
		SemanticMatcher:     matcher,
		ProgressiveExpander: expander,
		PredictiveLoader:    NewPredictiveLoader(),
		ContextPrioritizer:  DefaultContextPrioritizer(),
		DefaultTokenBudget:  cfg.DefaultTokenBudget,
		MaxSelectionTimeMs:  cfg.MaxSelectionTimeMs,
		TargetHitRate:       cfg.TargetHitRate,
		TargetSizeReduction: cfg.TargetSizeReduction,
		EnableCaching:       cfg.EnableCaching,
		CacheTTLSeconds:     cfg.CacheTTLSeconds,
		EnableMetrics:       cfg.EnableMetrics,
		Now:                 func() time.Time { return time.Now().UTC() },
	}, nil
}

func (s *IntelligentContextSelector) now() time.Time { return micros(s.Now()) }

func cacheKey(query string, maxTokens int) string { return fmt.Sprintf("%s\x00%d", query, maxTokens) }

// SelectOptions are the optional arguments of SelectContext (Python keyword args).
// UserPreferences are the prioritizer's preferences (Python annotates the expander's
// type but only ever hands them to the prioritizer).
type SelectOptions struct {
	UserPreferences     *UserPreferences
	CurrentTask         map[string]any
	ProjectContext      map[string]any
	AggressiveExpansion bool
}

// SelectContext selects the optimized context for query within maxTokens. Any
// internal failure falls back to the first contexts that fit the budget.
func (s *IntelligentContextSelector) SelectContext(query string, maxTokens int, opt SelectOptions) *SelectionResult {
	r, err := s.selectContext(query, maxTokens, opt)
	if err != nil {
		return s.fallbackSelection(query, maxTokens)
	}
	return r
}

func (s *IntelligentContextSelector) selectContext(query string, maxTokens int, opt SelectOptions) (*SelectionResult, error) {
	start := s.Now()

	if s.EnableCaching {
		if cached := s.getCachedResult(query, maxTokens); cached != nil {
			s.Metrics.CacheHitRate = float64(s.Metrics.CacheHitRate*0.9) + 0.1
			return cached, nil
		}
	}

	_ = s.SemanticMatcher.GenerateEmbedding(query)

	topK := len(s.AvailableContexts)
	if topK > 20 {
		topK = 20
	}
	minSim := float64(s.SemanticMatcher.SimilarityThreshold * 0.7)
	similar := s.SemanticMatcher.FindSimilarContexts(query, topK, &minSim)

	var contextScores []*ContextScore
	if len(similar) > 0 {
		contexts := make([]map[string]any, 0, len(similar))
		sims := map[string]float64{}
		for _, r := range similar {
			contexts = append(contexts, r.Item.Metadata["context_data"].(map[string]any))
			sims[r.Item.ID] = r.SimilarityScore
		}
		var err error
		contextScores, err = s.ContextPrioritizer.ScoreContextsBatch(contexts, query, sims, opt.UserPreferences, opt.ProjectContext, opt.CurrentTask, nil)
		if err != nil {
			return nil, err
		}
	}

	var selected []map[string]any
	var tokensUsed int
	expansionPath := []string{}

	if len(contextScores) > 0 {
		var candidates []ExpansionCandidate
		top := contextScores
		if len(top) > 15 {
			top = top[:15]
		}
		for _, score := range top {
			ctxTypeVal := score.ContextType
			level := ContextLevelTask
			if name, ok := ctxTypeVal.(string); ok {
				switch name {
				case "global":
					level = ContextLevelGlobal
				case "project":
					level = ContextLevelProject
				case "branch":
					level = ContextLevelBranch
				}
			}
			sem, _ := score.FactorScores.Get(string(ScoreSemanticRelevance))
			dep, _ := score.FactorScores.Get(string(ScoreDependencyBoost))
			trigger := TriggerPatternBased
			if sem > 0.7 {
				trigger = TriggerSimilarityMatch
			} else if dep > 0.3 {
				trigger = TriggerDependencyChain
			}
			var lastAccessed any
			if score.LastAccessed != nil {
				lastAccessed = value_objects.IsoFormat(*score.LastAccessed)
			}
			candidates = append(candidates, ExpansionCandidate{
				ContextID:       score.ContextID,
				ContextLevel:    level,
				ContextType:     ctxTypeVal,
				PriorityScore:   score.TotalScore,
				EstimatedTokens: score.EstimatedTok,
				Trigger:         trigger,
				ContextData: map[string]any{
					"estimated_tokens": score.EstimatedTok,
					"context_type":     ctxTypeVal,
					"last_accessed":    lastAccessed,
				},
			})
		}
		budget := maxTokens
		res := s.ProgressiveExpander.ExpandContextProgressive(map[string]any{"loaded_contexts": []any{}}, candidates, &budget, opt.AggressiveExpansion)
		selected = res.ExpandedContexts
		tokensUsed = res.TotalTokensUsed
		expansionPath = res.ExpansionPath
	} else {
		current := opt.CurrentTask
		if current == nil {
			current = map[string]any{}
		}
		pred, err := s.PredictiveLoader.PredictNextContexts(current, []string{}, nil)
		if err != nil {
			return nil, err
		}
		for _, id := range pred.PredictedContexts {
			data := s.findContextByID(id)
			if data == nil {
				continue
			}
			est := estimateTokens(data)
			if tokensUsed+est <= maxTokens {
				selected = append(selected, data)
				tokensUsed += est
			}
		}
	}

	timeMs := float64(s.Now().Sub(start).Microseconds()) / 1e6 * 1000
	hitRate := s.estimateHitRate(selected, query)
	reduction := s.estimateSizeReduction(selected, s.AvailableContexts)

	md := entities.NewOrderedMap[any]()
	md.Set("query", query)
	md.Set("max_tokens", maxTokens)
	md.Set("contexts_considered", len(s.AvailableContexts))
	md.Set("contexts_selected", len(selected))
	md.Set("semantic_matches", len(similar))
	md.Set("expansion_path", expansionPath)
	md.Set("cache_used", false)

	result := &SelectionResult{
		SelectedContexts: selected, TotalTokensUsed: tokensUsed, SelectionTimeMs: timeMs,
		HitRateEstimate: hitRate, SizeReductionPct: reduction, Metadata: md,
	}
	if s.EnableMetrics {
		s.updateMetrics(result)
	}
	if s.EnableCaching {
		s.cacheResult(query, maxTokens, result)
	}
	return result, nil
}

// LoadAvailableContexts loads contexts and indexes them for semantic matching.
func (s *IntelligentContextSelector) LoadAvailableContexts(contexts []map[string]any) {
	s.AvailableContexts = contexts
	var items []*ContextItem
	for _, c := range contexts {
		item := NewContextItem(contextIDOf(c), s.extractContextContent(c), value_objects.PyStr(ctxType(c, "unknown")))
		item.LastUpdated = s.now()
		item.Metadata = map[string]any{"context_data": c}
		items = append(items, item)
	}
	if len(items) > 0 {
		s.SemanticMatcher.AddContextItems(items)
	}
}

// StartSession starts a session for predictive loading.
func (s *IntelligentContextSelector) StartSession(sessionID string, userID *string) {
	s.CurrentSessionID = &sessionID
	s.PredictiveLoader.StartSession(sessionID, userID)
}

// RecordToolUsage records tool usage for pattern learning and context access.
func (s *IntelligentContextSelector) RecordToolUsage(toolName, contextID string) {
	s.PredictiveLoader.RecordToolUsage(toolName, contextID)
	if contextID != "" {
		s.ContextPrioritizer.RecordContextAccess(contextID, time.Time{})
	}
}

// EndSession ends the current session; nil when none was started.
func (s *IntelligentContextSelector) EndSession() *SessionRecord {
	if s.CurrentSessionID == nil || *s.CurrentSessionID == "" {
		return nil
	}
	rec := s.PredictiveLoader.EndSession()
	s.CurrentSessionID = nil
	return rec
}

// extractContextContent returns the searchable text. Python iterates the metadata
// dict in insertion order; Go maps are unordered so keys are visited sorted.
func (s *IntelligentContextSelector) extractContextContent(data map[string]any) string {
	var parts []string
	for _, f := range []string{"title", "description", "details", "name", "git_branch_name"} {
		if v, ok := data[f].(string); ok {
			parts = append(parts, v)
		}
	}
	if md, ok := data["metadata"].(map[string]any); ok {
		keys := make([]string, 0, len(md))
		for k := range md {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			if v, ok := md[k].(string); ok && len([]rune(v)) > 5 {
				parts = append(parts, v)
			}
		}
	}
	return strings.Join(parts, " ")
}

func (s *IntelligentContextSelector) findContextByID(id string) map[string]any {
	for _, c := range s.AvailableContexts {
		if v, ok := c["id"].(string); ok && v == id {
			return c
		}
		// str(context.get("context_id")) renders a missing key as "None".
		cid := "None"
		if v, ok := c["context_id"]; ok {
			cid = value_objects.PyStr(v)
		}
		if cid == id {
			return c
		}
	}
	return nil
}

func (s *IntelligentContextSelector) estimateHitRate(selected []map[string]any, query string) float64 {
	if len(selected) == 0 {
		return 0.0
	}
	queryWords := wordSet(query)
	relevant := 0
	for _, c := range selected {
		contextWords := wordSet(s.extractContextContent(c))
		overlap := 0
		for w := range queryWords {
			if _, ok := contextWords[w]; ok {
				overlap++
			}
		}
		ratio := 0.0
		if len(queryWords) > 0 {
			ratio = float64(overlap) / float64(len(queryWords))
		}
		if ratio > 0.3 {
			relevant++
		}
	}
	return float64(relevant) / float64(len(selected))
}

func (s *IntelligentContextSelector) estimateSizeReduction(selected, all []map[string]any) float64 {
	if len(all) == 0 {
		return 0.0
	}
	sel, total := 0, 0
	for _, c := range selected {
		sel += estimateTokens(c)
	}
	for _, c := range all {
		total += estimateTokens(c)
	}
	if total == 0 {
		return 0.0
	}
	return pyMax(0.0, 1.0-float64(sel)/float64(total))
}

func (s *IntelligentContextSelector) cacheIndex(key string) int {
	for i, e := range s.resultCache {
		if e.key == key {
			return i
		}
	}
	return -1
}

func (s *IntelligentContextSelector) getCachedResult(query string, maxTokens int) *SelectionResult {
	key := cacheKey(query, maxTokens)
	i := s.cacheIndex(key)
	if i < 0 {
		return nil
	}
	e := s.resultCache[i]
	age := float64(s.now().Sub(e.at).Microseconds()) / 1e6
	if age < float64(s.CacheTTLSeconds) {
		return e.result
	}
	s.resultCache = append(s.resultCache[:i], s.resultCache[i+1:]...)
	return nil
}

func (s *IntelligentContextSelector) cacheResult(query string, maxTokens int, r *SelectionResult) {
	key := cacheKey(query, maxTokens)
	entry := &cachedSelection{key: key, result: r, at: s.now()}
	if i := s.cacheIndex(key); i >= 0 {
		s.resultCache[i] = entry // dict assignment keeps the key's position
	} else {
		s.resultCache = append(s.resultCache, entry)
	}
	if len(s.resultCache) > 100 {
		sort.SliceStable(s.resultCache, func(i, j int) bool { return s.resultCache[i].at.Before(s.resultCache[j].at) })
		s.resultCache = append([]*cachedSelection{}, s.resultCache[len(s.resultCache)-80:]...)
	}
}

func (s *IntelligentContextSelector) updateMetrics(r *SelectionResult) {
	m := &s.Metrics
	m.TotalSelections++
	alpha := 0.1
	m.AvgSelectionTimeMs = float64(alpha*r.SelectionTimeMs) + float64((1-alpha)*m.AvgSelectionTimeMs)
	m.AvgHitRate = float64(alpha*r.HitRateEstimate) + float64((1-alpha)*m.AvgHitRate)
	m.AvgSizeReduction = float64(alpha*r.SizeReductionPct) + float64((1-alpha)*m.AvgSizeReduction)
	m.ContextsSelected += len(r.SelectedContexts)
	considered, _ := r.Metadata.Get("contexts_considered")
	m.ContextsAvailable += considered.(int)

	s.PerformanceHistory = append(s.PerformanceHistory, PerformanceEntry{
		Timestamp: s.now(), SelectionTimeMs: r.SelectionTimeMs, HitRateEstimate: r.HitRateEstimate,
		SizeReductionPct: r.SizeReductionPct, TokensUsed: r.TotalTokensUsed, ContextsSelected: len(r.SelectedContexts),
	})
	if len(s.PerformanceHistory) > 1000 {
		s.PerformanceHistory = append([]PerformanceEntry{}, s.PerformanceHistory[len(s.PerformanceHistory)-800:]...)
	}
}

func (s *IntelligentContextSelector) fallbackSelection(query string, maxTokens int) *SelectionResult {
	var selected []map[string]any
	tokens := 0
	limit := s.AvailableContexts
	if len(limit) > 10 {
		limit = limit[:10]
	}
	for _, c := range limit {
		est := estimateTokens(c)
		if tokens+est <= maxTokens {
			selected = append(selected, c)
			tokens += est
		}
	}
	md := entities.NewOrderedMap[any]()
	md.Set("fallback", true)
	return &SelectionResult{SelectedContexts: selected, TotalTokensUsed: tokens, SelectionTimeMs: 10.0,
		HitRateEstimate: 0.5, SizeReductionPct: 0.3, Metadata: md}
}

// PerformanceStats is get_performance_stats' dict. Component stats are nil when the
// component has nothing to report (Python returns None / {}).
type PerformanceStats struct {
	TotalSelections                int
	AvgSelectionTimeMs             float64
	AvgHitRate                     float64
	AvgSizeReduction               float64
	CacheHitRate                   float64
	TimeTargetAchievement          float64
	HitRateTargetAchievement       float64
	SizeReductionTargetAchievement float64
	SemanticMatching               map[string]any
	ProgressiveExpansion           *ExpansionStats
	PredictiveLoading              *PredictionStats
	ContextPrioritization          *ScoringStats
	AvailableContexts              int
	CachedResults                  int
	CurrentSession                 *string
}

// GetPerformanceStats returns comprehensive statistics. A zero target hit rate or
// size reduction raises ZeroDivisionError in Python.
func (s *IntelligentContextSelector) GetPerformanceStats() (*PerformanceStats, error) {
	if s.TargetHitRate == 0 || s.TargetSizeReduction == 0 {
		return nil, entities.ErrZeroDivision
	}
	timeAchievement := 0.0
	if s.MaxSelectionTimeMs > 0 {
		timeAchievement = (s.MaxSelectionTimeMs - s.Metrics.AvgSelectionTimeMs) / s.MaxSelectionTimeMs
	}
	return &PerformanceStats{
		TotalSelections:                s.Metrics.TotalSelections,
		AvgSelectionTimeMs:             s.Metrics.AvgSelectionTimeMs,
		AvgHitRate:                     s.Metrics.AvgHitRate,
		AvgSizeReduction:               s.Metrics.AvgSizeReduction,
		CacheHitRate:                   s.Metrics.CacheHitRate,
		TimeTargetAchievement:          timeAchievement,
		HitRateTargetAchievement:       s.Metrics.AvgHitRate / s.TargetHitRate,
		SizeReductionTargetAchievement: s.Metrics.AvgSizeReduction / s.TargetSizeReduction,
		SemanticMatching:               s.SemanticMatcher.GetStats(),
		ProgressiveExpansion:           s.ProgressiveExpander.GetExpansionStats(),
		PredictiveLoading:              s.PredictiveLoader.GetPredictionStats(),
		ContextPrioritization:          s.ContextPrioritizer.GetScoringStats(),
		AvailableContexts:              len(s.AvailableContexts),
		CachedResults:                  len(s.resultCache),
		CurrentSession:                 s.CurrentSessionID,
	}, nil
}

// OptimizationReport is optimize_performance's dict.
type OptimizationReport struct {
	Actions             []string
	AvgSelectionTimeMs  float64
	AvgHitRate          float64
	AvgSizeReduction    float64
	MaxSelectionTimeMs  float64
	TargetHitRate       float64
	TargetSizeReduction float64
}

// OptimizePerformance tunes the similarity threshold and cache from the metrics.
func (s *IntelligentContextSelector) OptimizePerformance() *OptimizationReport {
	actions := []string{}
	m := s.Metrics
	if m.AvgSelectionTimeMs > float64(s.MaxSelectionTimeMs*0.8) {
		cur := s.SemanticMatcher.SimilarityThreshold
		next := pyMin(0.8, cur+0.05)
		s.SemanticMatcher.SimilarityThreshold = next
		actions = append(actions, fmt.Sprintf("Increased similarity threshold: %.2f → %.2f", cur, next))
		actions = append(actions, "Reduced expansion candidates for faster selection")
	}
	if m.AvgHitRate < float64(s.TargetHitRate*0.8) {
		cur := s.SemanticMatcher.SimilarityThreshold
		next := pyMax(0.3, cur-0.05)
		s.SemanticMatcher.SimilarityThreshold = next
		actions = append(actions, fmt.Sprintf("Decreased similarity threshold: %.2f → %.2f", cur, next))
	}
	if m.CacheHitRate < 0.1 && len(s.resultCache) > 10 {
		s.resultCache = nil
		actions = append(actions, "Cleared result cache to improve freshness")
	}
	return &OptimizationReport{
		Actions: actions, AvgSelectionTimeMs: m.AvgSelectionTimeMs, AvgHitRate: m.AvgHitRate,
		AvgSizeReduction: m.AvgSizeReduction, MaxSelectionTimeMs: s.MaxSelectionTimeMs,
		TargetHitRate: s.TargetHitRate, TargetSizeReduction: s.TargetSizeReduction,
	}
}
