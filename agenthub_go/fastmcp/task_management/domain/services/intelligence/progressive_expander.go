package intelligence

import (
	"fmt"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ProgressiveExpanderUserPreferences are the user preferences for context expansion
// (progressive_expander.UserPreferences; prefixed because context_prioritizer owns the
// plain name in this package).
type ProgressiveExpanderUserPreferences struct {
	AutoExpandRelated      bool
	MaxExpansionDepth      int
	PreferredContextLevel  string
	MaxTokensPerRequest    int
	PrefetchEnabled        bool
	CacheExpansionResults  bool
	IncludeArchived        bool
	IncludeCompleted       bool
	PriorityThreshold      string
	NotifyOnExpansion      bool
	ExpansionNotifications []string
}

// NewProgressiveExpanderUserPreferences returns the Python defaults.
func NewProgressiveExpanderUserPreferences() ProgressiveExpanderUserPreferences {
	return ProgressiveExpanderUserPreferences{AutoExpandRelated: true, MaxExpansionDepth: 3, PreferredContextLevel: "PROJECT",
		MaxTokensPerRequest: 4000, PrefetchEnabled: true, CacheExpansionResults: true, IncludeCompleted: true,
		PriorityThreshold: "LOW", ExpansionNotifications: []string{}}
}

// ContextLevel is a level of the 4-tier context hierarchy.
type ContextLevel string

const (
	ContextLevelGlobal  ContextLevel = "global"
	ContextLevelProject ContextLevel = "project"
	ContextLevelBranch  ContextLevel = "branch"
	ContextLevelTask    ContextLevel = "task"
)

// ExpansionTrigger is what triggered a context expansion.
type ExpansionTrigger string

const (
	TriggerUserRequest     ExpansionTrigger = "user_request"
	TriggerSimilarityMatch ExpansionTrigger = "similarity_match"
	TriggerDependencyChain ExpansionTrigger = "dependency_chain"
	TriggerPatternBased    ExpansionTrigger = "pattern_based"
	TriggerTokenAvailable  ExpansionTrigger = "token_available"
	TriggerPrefetch        ExpansionTrigger = "prefetch"
)

// ExpansionCandidate is a candidate for context expansion. ContextType is `any` because
// Python takes it unvalidated from the context dict.
type ExpansionCandidate struct {
	ContextID       string
	ContextLevel    ContextLevel
	ContextType     any
	PriorityScore   float64
	EstimatedTokens int
	Trigger         ExpansionTrigger
	SimilarityScore float64
	ContextData     map[string]any
}

// ExpansionResult is the result of a context expansion.
type ExpansionResult struct {
	ExpandedContexts     []map[string]any
	TotalTokensUsed      int
	RemainingTokenBudget int
	ExpansionPath        []string
	PrefetchedContexts   []string
}

// AccessPattern is one entry of context_access_patterns. TotalSessions and
// CommonKeywords are never modified by Python either.
type AccessPattern struct {
	AccessCount    int
	TotalSessions  int
	LastAccessed   *time.Time
	CommonKeywords []string
}

// ExpansionRecord is one entry of expansion_history.
type ExpansionRecord struct {
	Timestamp          time.Time
	TokenBudget        int
	TokensUsed         int
	ContextsExpanded   int
	ContextsPrefetched int
	ExpansionPath      []string
}

// ProgressiveExpander is the progressive context expansion engine.
type ProgressiveExpander struct {
	DefaultTokenBudget    int
	MinContextTokens      int
	PrefetchThreshold     float64
	ExpansionFactor       float64
	ExpansionHistory      []ExpansionRecord
	ContextAccessPatterns *entities.OrderedMap[*AccessPattern]
	Now                   func() time.Time
}

// NewProgressiveExpander builds an expander (Python defaults: 2000, 100, 0.7, 1.5).
func NewProgressiveExpander(defaultTokenBudget, minContextTokens int, prefetchThreshold, expansionFactor float64) *ProgressiveExpander {
	return &ProgressiveExpander{DefaultTokenBudget: defaultTokenBudget, MinContextTokens: minContextTokens,
		PrefetchThreshold: prefetchThreshold, ExpansionFactor: expansionFactor,
		ContextAccessPatterns: entities.NewOrderedMap[*AccessPattern](), Now: func() time.Time { return time.Now().UTC() }}
}

func DefaultProgressiveExpander() *ProgressiveExpander {
	return NewProgressiveExpander(2000, 100, 0.7, 1.5)
}

// EstimateContextTokens is 0 for empty data, else max(1, len(json.dumps(data, default=str)) // 4).
func (e *ProgressiveExpander) EstimateContextTokens(data map[string]any) int {
	if len(data) == 0 {
		return 0
	}
	return estimateTokens(data)
}

var levelScores = map[ContextLevel]float64{ContextLevelTask: 0.9, ContextLevelBranch: 0.7, ContextLevelProject: 0.5, ContextLevelGlobal: 0.3}

var triggerModifiers = map[ExpansionTrigger]float64{TriggerUserRequest: 1.0, TriggerSimilarityMatch: 0.8, TriggerDependencyChain: 0.9,
	TriggerPatternBased: 0.6, TriggerTokenAvailable: 0.4, TriggerPrefetch: 0.3}

func (p *AccessPattern) frequency() float64 {
	total := p.TotalSessions
	if total < 1 {
		total = 1
	}
	return float64(p.AccessCount) / float64(total)
}

func (e *ProgressiveExpander) calculateExpansionPriority(contextID string, level ContextLevel, trigger ExpansionTrigger) float64 {
	base, ok := levelScores[level]
	if !ok {
		base = 0.5
	}
	modifier, ok := triggerModifiers[trigger]
	if !ok {
		modifier = 0.5
	}
	accessBonus, recencyBonus := 0.0, 0.0
	if pattern, found := e.ContextAccessPatterns.Get(contextID); found {
		accessBonus = pyMin(0.3, pattern.frequency())
		if pattern.LastAccessed != nil {
			hoursAgo := value_objects.PyTotalSeconds(e.Now().Sub(*pattern.LastAccessed)) / 3600
			recencyBonus = pyMax(0.0, 0.2*(1.0-pyMin(1.0, hoursAgo/24)))
		}
	}
	final := float64(base*modifier) + accessBonus + recencyBonus
	return pyMin(1.0, pyMax(0.0, final))
}

// rawContextID is `context.get("id", str(context.get("context_id", "")))`.
func rawContextID(c map[string]any) any {
	if id, ok := c["id"]; ok {
		return id
	}
	if cid, ok := c["context_id"]; ok {
		return value_objects.PyStr(cid)
	}
	return ""
}

func inAnyList(list any, v any) bool {
	items, ok := list.([]any)
	if !ok {
		return false
	}
	for _, x := range items {
		if value_objects.PyEqual(x, v) {
			return true
		}
	}
	return false
}

// IdentifyExpansionCandidates identifies candidates sorted by priority (descending, stable).
func (e *ProgressiveExpander) IdentifyExpansionCandidates(current map[string]any, query string,
	available []map[string]any, similarity map[string]float64) []ExpansionCandidate {
	candidates := []ExpansionCandidate{}
	for _, context := range available {
		idRaw := rawContextID(context)
		contextType := any("unknown")
		if t, ok := context["context_type"]; ok {
			contextType = t
		}
		if inAnyList(current["loaded_contexts"], idRaw) {
			continue
		}
		level := ContextLevelGlobal
		switch contextType {
		case "task":
			level = ContextLevelTask
		case "branch":
			level = ContextLevelBranch
		case "project":
			level = ContextLevelProject
		}
		idStr, isStr := idRaw.(string) // dict lookups only ever match string ids
		lookupID := idStr
		if !isStr {
			lookupID = "\x00non-string-id"
		}
		tokens := e.EstimateContextTokens(context)

		var triggers []ExpansionTrigger
		sim, hasSim := similarity[idStr]
		if len(similarity) > 0 && isStr && hasSim {
			if sim >= e.PrefetchThreshold {
				triggers = append(triggers, TriggerSimilarityMatch)
			} else if sim >= float64(e.PrefetchThreshold*0.7) {
				triggers = append(triggers, TriggerPrefetch)
			}
		}
		if hasDependencyRelationship(context, current) {
			triggers = append(triggers, TriggerDependencyChain)
		}
		if isStr && e.matchesUsagePattern(idStr, query) {
			triggers = append(triggers, TriggerPatternBased)
		}
		if float64(tokens) <= float64(e.DefaultTokenBudget)*0.1 {
			triggers = append(triggers, TriggerTokenAvailable)
		}
		if len(triggers) == 0 {
			triggers = []ExpansionTrigger{TriggerTokenAvailable}
		}
		simScore := 0.0
		if isStr && len(similarity) > 0 {
			simScore = similarity[idStr]
		}
		for _, trigger := range triggers {
			candidates = append(candidates, ExpansionCandidate{ContextID: value_objects.PyStr(idRaw), ContextLevel: level,
				ContextType: contextType, PriorityScore: e.calculateExpansionPriority(lookupID, level, trigger),
				EstimatedTokens: tokens, Trigger: trigger, SimilarityScore: simScore, ContextData: context})
		}
	}
	sort.SliceStable(candidates, func(i, j int) bool { return candidates[i].PriorityScore > candidates[j].PriorityScore })
	return candidates
}

// ExpandContextProgressive expands context within the token budget (nil = default).
func (e *ProgressiveExpander) ExpandContextProgressive(current map[string]any, candidates []ExpansionCandidate,
	tokenBudget *int, aggressive bool) ExpansionResult {
	budget := e.DefaultTokenBudget
	if tokenBudget != nil {
		budget = *tokenBudget
	}
	available := budget - e.MinContextTokens
	if available < 0 {
		available = 0
	}
	expanded, path, prefetched := []map[string]any{}, []string{}, []string{}
	used := 0
	multiplier := e.ExpansionFactor
	if aggressive {
		multiplier = e.ExpansionFactor * 1.2
	}
	for _, c := range candidates {
		needed := int(float64(c.EstimatedTokens) * multiplier)
		if used+needed > available {
			if c.PriorityScore > 0.8 && float64(c.EstimatedTokens) < float64(available)*0.1 {
				prefetched = append(prefetched, c.ContextID)
				path = append(path, "prefetch:"+c.ContextID)
			}
			continue
		}
		expanded = append(expanded, c.ContextData)
		used += needed
		path = append(path, fmt.Sprintf("%s:%s:%s", c.Trigger, c.ContextLevel, c.ContextID))
		e.recordContextAccess(c.ContextID)
		if c.Trigger == TriggerUserRequest {
			continue
		} else if float64(used) >= float64(available)*0.8 {
			aggressive = false
			multiplier = e.ExpansionFactor * 0.8
		}
	}
	result := ExpansionResult{ExpandedContexts: expanded, TotalTokensUsed: used, RemainingTokenBudget: available - used,
		ExpansionPath: path, PrefetchedContexts: prefetched}
	e.ExpansionHistory = append(e.ExpansionHistory, ExpansionRecord{Timestamp: e.Now(), TokenBudget: budget, TokensUsed: used,
		ContextsExpanded: len(expanded), ContextsPrefetched: len(prefetched), ExpansionPath: path})
	return result
}

func hasDependencyRelationship(candidate, current map[string]any) bool {
	candidateID := candidate["id"]
	if !value_objects.PyTruthy(candidateID) {
		candidateID = candidate["context_id"]
	}
	if inAnyList(current["dependencies"], candidateID) {
		return true
	}
	b, c := candidate["git_branch_id"], current["git_branch_id"]
	return value_objects.PyTruthy(b) && value_objects.PyTruthy(c) && value_objects.PyEqual(b, c)
}

func (e *ProgressiveExpander) matchesUsagePattern(contextID, query string) bool {
	pattern, ok := e.ContextAccessPatterns.Get(contextID)
	if !ok {
		return false
	}
	if pattern.frequency() > 0.3 {
		return true
	}
	queryLower := value_objects.PyLower(query)
	for _, k := range pattern.CommonKeywords {
		if strings.Contains(queryLower, value_objects.PyLower(k)) {
			return true
		}
	}
	return false
}

func (e *ProgressiveExpander) recordContextAccess(contextID string) {
	pattern, ok := e.ContextAccessPatterns.Get(contextID)
	if !ok {
		pattern = &AccessPattern{CommonKeywords: []string{}}
		e.ContextAccessPatterns.Set(contextID, pattern)
	}
	pattern.AccessCount++
	now := e.Now()
	pattern.LastAccessed = &now
}

// ExpansionStats is the result of GetExpansionStats; nil when no expansion happened.
type ExpansionStats struct {
	TotalExpansions        int
	AvgTokensUsed          float64
	AvgContextsExpanded    float64
	TrackedContextPatterns int
	ExpansionFactor        float64
	TokenBudget            int
}

func (e *ProgressiveExpander) GetExpansionStats() *ExpansionStats {
	if len(e.ExpansionHistory) == 0 {
		return nil
	}
	recent := e.ExpansionHistory
	if len(recent) > 10 {
		recent = recent[len(recent)-10:]
	}
	tokens, contexts := 0, 0
	for _, r := range recent {
		tokens += r.TokensUsed
		contexts += r.ContextsExpanded
	}
	return &ExpansionStats{len(e.ExpansionHistory), float64(tokens) / float64(len(recent)),
		float64(contexts) / float64(len(recent)), e.ContextAccessPatterns.Len(), e.ExpansionFactor, e.DefaultTokenBudget}
}
