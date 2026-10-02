package intelligence

import (
	"fmt"
	"hash/fnv"
	"sort"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// PredictionTrigger: triggers for predictive loading.
type PredictionTrigger string

const (
	TriggerToolSequence   PredictionTrigger = "tool_sequence"
	TriggerSessionPattern PredictionTrigger = "session_pattern"
	TriggerTimeBased      PredictionTrigger = "time_based"
	TriggerContextChain   PredictionTrigger = "context_chain"
	TriggerUserBehavior   PredictionTrigger = "user_behavior"
)

// UsagePattern is a pattern extracted from usage history.
type UsagePattern struct {
	PatternID   string
	PatternType string
	Trigger     PredictionTrigger
	Sequence    []string
	Confidence  float64
	Frequency   int
	LastSeen    time.Time
	SuccessRate float64
}

// PredictionResult is the result of a context prediction.
type PredictionResult struct {
	PredictedContexts []string
	ConfidenceScores  *entities.OrderedMap[float64]
	PatternsUsed      []string
	PredictionReasons []string
	PreloadPriority   *entities.OrderedMap[float64]
}

// SessionContext is the context for the current session analysis.
type SessionContext struct {
	SessionID       string
	StartTime       time.Time
	ToolSequence    []string
	ContextSequence []string
	CurrentTaskType *string
	UserID          *string
}

// SessionRecord is one ended session stored in the history.
type SessionRecord struct {
	SessionID       string
	UserID          *string
	StartTime       time.Time
	EndTime         time.Time
	ToolSequence    []string
	ContextSequence []string
	DurationMinutes float64
}

// PredictionStats is get_prediction_stats' dict.
type PredictionStats struct {
	TotalPatterns              int
	AvgSuccessRate             float64
	HighConfidencePatterns     int
	SessionHistoryCount        int
	PatternConfidenceThreshold float64
	Patterns                   []PatternStat
}

// PatternStat is one entry of PredictionStats.Patterns.
type PatternStat struct {
	PatternID   string
	PatternType string
	Frequency   int
	Confidence  float64
	SuccessRate float64
}

type seqCount struct {
	seq   []string
	count int
}

type transitionCount struct {
	from, to string
	count    int
}

// PredictiveLoader is the predictive context loading engine.
type PredictiveLoader struct {
	PatternMinFrequency        int
	PatternConfidenceThreshold float64
	SessionHistoryDays         int
	MaxPreloadContexts         int

	// Now is the clock (UTC); injectable for tests.
	Now func() time.Time

	usagePatterns  *entities.OrderedMap[*UsagePattern]
	sessionHistory []SessionRecord
	currentSession *SessionContext

	toolSequences      []*seqCount
	toolSequenceIndex  map[string]*seqCount
	contextTransitions []*transitionCount
	transitionIndex    map[[2]string]*transitionCount
	timeBasedPatterns  *entities.OrderedMap[[]time.Time]
}

// NewPredictiveLoader applies the Python defaults (3, 0.6, 30, 5).
func NewPredictiveLoader() *PredictiveLoader {
	return NewPredictiveLoaderWith(3, 0.6, 30, 5)
}

// NewPredictiveLoaderWith creates a loader with explicit settings.
func NewPredictiveLoaderWith(minFrequency int, confidenceThreshold float64, historyDays, maxPreload int) *PredictiveLoader {
	return &PredictiveLoader{
		PatternMinFrequency:        minFrequency,
		PatternConfidenceThreshold: confidenceThreshold,
		SessionHistoryDays:         historyDays,
		MaxPreloadContexts:         maxPreload,
		Now:                        func() time.Time { return time.Now().UTC() },
		usagePatterns:              entities.NewOrderedMap[*UsagePattern](),
		toolSequenceIndex:          map[string]*seqCount{},
		transitionIndex:            map[[2]string]*transitionCount{},
		timeBasedPatterns:          entities.NewOrderedMap[[]time.Time](),
	}
}

// micros truncates to Python's microsecond datetime resolution.
func micros(t time.Time) time.Time { return t.Truncate(time.Microsecond) }

func (p *PredictiveLoader) now() time.Time { return micros(p.Now()) }

func seqKey(seq []string) string { return strings.Join(seq, "\x00") }

// StartSession starts tracking a new session.
func (p *PredictiveLoader) StartSession(sessionID string, userID *string) {
	p.currentSession = &SessionContext{SessionID: sessionID, StartTime: p.now(), UserID: userID}
}

// RecordToolUsage records tool usage for pattern analysis. An empty contextID is
// treated as absent, as in Python's truthiness check.
func (p *PredictiveLoader) RecordToolUsage(toolName, contextID string) {
	s := p.currentSession
	if s == nil {
		return
	}
	s.ToolSequence = append(s.ToolSequence, toolName)
	if contextID != "" {
		s.ContextSequence = append(s.ContextSequence, contextID)
	}
	if len(s.ToolSequence) >= 2 {
		for _, w := range []int{2, 3, 4} {
			if len(s.ToolSequence) >= w {
				seq := append([]string{}, s.ToolSequence[len(s.ToolSequence)-w:]...)
				k := seqKey(seq)
				sc, ok := p.toolSequenceIndex[k]
				if !ok {
					sc = &seqCount{seq: seq}
					p.toolSequenceIndex[k] = sc
					p.toolSequences = append(p.toolSequences, sc)
				}
				sc.count++
			}
		}
	}
}

// RecordContextAccess records context access for transition analysis.
func (p *PredictiveLoader) RecordContextAccess(contextID, contextType string) {
	s := p.currentSession
	if s == nil {
		return
	}
	if len(s.ContextSequence) > 0 {
		prev := s.ContextSequence[len(s.ContextSequence)-1]
		key := [2]string{prev, contextID}
		tc, ok := p.transitionIndex[key]
		if !ok {
			tc = &transitionCount{from: prev, to: contextID}
			p.transitionIndex[key] = tc
			p.contextTransitions = append(p.contextTransitions, tc)
		}
		tc.count++
	}
	s.ContextSequence = append(s.ContextSequence, contextID)

	current := p.now()
	timeKey := fmt.Sprintf("%s_%d", contextType, current.Hour())
	existing, _ := p.timeBasedPatterns.Get(timeKey)
	p.timeBasedPatterns.Set(timeKey, append(existing, current))
}

// EndSession ends the current session and analyses patterns; nil when none is active.
func (p *PredictiveLoader) EndSession() *SessionRecord {
	s := p.currentSession
	if s == nil {
		return nil
	}
	end := p.now()
	rec := SessionRecord{
		SessionID:       s.SessionID,
		UserID:          s.UserID,
		StartTime:       s.StartTime,
		EndTime:         end,
		ToolSequence:    append([]string{}, s.ToolSequence...),
		ContextSequence: append([]string{}, s.ContextSequence...),
		// timedelta.total_seconds() = microseconds / 10**6
		DurationMinutes: value_objects.PyTotalSeconds(end.Sub(s.StartTime)) / 60,
	}
	p.sessionHistory = append(p.sessionHistory, rec)

	cutoff := p.now().Add(-time.Duration(p.SessionHistoryDays) * 24 * time.Hour)
	kept := p.sessionHistory[:0:0]
	for _, h := range p.sessionHistory {
		if h.EndTime.After(cutoff) {
			kept = append(kept, h)
		}
	}
	p.sessionHistory = kept

	p.updateUsagePatterns()
	p.currentSession = nil
	return &rec
}

// SessionHistoryContext is the session_context dict used for history matching.
type SessionHistoryContext struct {
	ToolSequence    []string
	ContextSequence []string
}

// PredictNextContexts predicts the next likely contexts. currentContext is the
// Python dict (keys "id" / "context_id"); sessionContext may be nil.
// The only error is Python's ValueError from int() on a malformed time key.
func (p *PredictiveLoader) PredictNextContexts(currentContext map[string]any, recentTools []string, sessionContext *SessionHistoryContext) (*PredictionResult, error) {
	predictions := entities.NewOrderedMap[float64]()
	confidenceScores := entities.NewOrderedMap[float64]()
	patternsUsed, reasons := []string{}, []string{}

	get := func(m *entities.OrderedMap[float64], k string) float64 { v, _ := m.Get(k); return v }

	for _, kv := range p.predictFromToolSequence(recentTools) {
		predictions.Set(kv.k, pyMax(get(predictions, kv.k), kv.v))
		confidenceScores.Set(kv.k, kv.v)
		patternsUsed = append(patternsUsed, fmt.Sprintf("tool_sequence:%d", len(recentTools)))
		reasons = append(reasons, fmt.Sprintf("Tool sequence pattern suggests %s", kv.k))
	}

	var currentID any = currentContext["id"]
	if !value_objects.PyTruthy(currentID) {
		currentID = currentContext["context_id"]
	}
	if value_objects.PyTruthy(currentID) {
		idStr := value_objects.PyStr(currentID)
		var idMatch *string
		if s, ok := currentID.(string); ok {
			idMatch = &s
		}
		for _, kv := range p.predictFromContextTransitions(idMatch) {
			combined := pyMax(get(predictions, kv.k), kv.v)
			predictions.Set(kv.k, combined)
			confidenceScores.Set(kv.k, combined)
			patternsUsed = append(patternsUsed, "context_transition:"+idStr)
			reasons = append(reasons, fmt.Sprintf("Context transition pattern suggests %s", kv.k))
		}
	}

	timePreds, err := p.predictFromTimePatterns()
	if err != nil {
		return nil, err
	}
	for _, kv := range timePreds {
		combined := pyMax(get(predictions, kv.k), float64(kv.v*0.7))
		predictions.Set(kv.k, combined)
		confidenceScores.Set(kv.k, combined)
		patternsUsed = append(patternsUsed, "time_based")
		reasons = append(reasons, fmt.Sprintf("Time-based pattern suggests %s", kv.k))
	}

	if sessionContext != nil {
		for _, kv := range p.predictFromSessionHistory(sessionContext) {
			combined := pyMax(get(predictions, kv.k), kv.v)
			predictions.Set(kv.k, combined)
			confidenceScores.Set(kv.k, combined)
			patternsUsed = append(patternsUsed, "session_history")
			reasons = append(reasons, fmt.Sprintf("Session history pattern suggests %s", kv.k))
		}
	}

	var sorted []predKV
	for _, k := range predictions.Keys() {
		v, _ := predictions.Get(k)
		if v >= p.PatternConfidenceThreshold {
			sorted = append(sorted, predKV{k, v})
		}
	}
	sort.SliceStable(sorted, func(i, j int) bool { return sorted[i].v > sorted[j].v })
	if len(sorted) > p.MaxPreloadContexts {
		sorted = sorted[:p.MaxPreloadContexts]
	}

	predicted := make([]string, 0, len(sorted))
	priority := entities.NewOrderedMap[float64]()
	for _, kv := range sorted {
		predicted = append(predicted, kv.k)
		priority.Set(kv.k, kv.v)
	}
	return &PredictionResult{
		PredictedContexts: predicted,
		ConfidenceScores:  confidenceScores,
		// list(set(...)): Python's order is arbitrary; first-seen order is used.
		PatternsUsed:      dedupe(patternsUsed),
		PredictionReasons: reasons,
		PreloadPriority:   priority,
	}, nil
}

type predKV struct {
	k string
	v float64
}

func dedupe(in []string) []string {
	seen := map[string]bool{}
	out := []string{}
	for _, s := range in {
		if !seen[s] {
			seen[s] = true
			out = append(out, s)
		}
	}
	return out
}

// orderedSet builds an insertion-ordered dict[str, float] from kv writes.
type orderedPreds struct{ m *entities.OrderedMap[float64] }

func (o orderedPreds) kvs() []predKV {
	out := make([]predKV, 0, o.m.Len())
	for _, k := range o.m.Keys() {
		v, _ := o.m.Get(k)
		out = append(out, predKV{k, v})
	}
	return out
}

func (p *PredictiveLoader) predictFromToolSequence(recentTools []string) []predKV {
	preds := orderedPreds{entities.NewOrderedMap[float64]()}
	if len(recentTools) < 2 {
		return nil
	}
	mapping := toolContextMapping()
	for _, w := range []int{2, 3, 4} {
		if len(recentTools) < w {
			continue
		}
		seq := recentTools[len(recentTools)-w:]
		for _, ps := range p.toolSequences {
			if len(ps.seq) > len(seq) && equalStrings(ps.seq[:len(seq)], seq) && ps.count >= p.PatternMinFrequency {
				if ctxType, ok := mapping[ps.seq[len(seq)]]; ok {
					preds.m.Set("predicted_"+ctxType, pyMin(0.9, float64(ps.count)/10.0))
				}
			}
		}
	}
	return preds.kvs()
}

func equalStrings(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func (p *PredictiveLoader) predictFromContextTransitions(current *string) []predKV {
	preds := orderedPreds{entities.NewOrderedMap[float64]()}
	if current == nil {
		return nil
	}
	for _, tc := range p.contextTransitions {
		if tc.from == *current && tc.count >= p.PatternMinFrequency {
			preds.m.Set(tc.to, pyMin(0.9, float64(tc.count)/10.0))
		}
	}
	return preds.kvs()
}

func (p *PredictiveLoader) predictFromTimePatterns() ([]predKV, error) {
	preds := orderedPreds{entities.NewOrderedMap[float64]()}
	currentHour := p.now().Hour()
	for _, key := range p.timeBasedPatterns.Keys() {
		times, _ := p.timeBasedPatterns.Get(key)
		if len(times) < p.PatternMinFrequency {
			continue
		}
		parts := strings.Split(key, "_")
		if len(parts) >= 2 {
			patternHour, err := strconv.Atoi(strings.TrimSpace(parts[1]))
			if err != nil {
				return nil, &value_objects.ValueError{Msg: fmt.Sprintf("invalid literal for int() with base 10: %s", value_objects.PyRepr(parts[1]))}
			}
			diff := currentHour - patternHour
			if diff < 0 {
				diff = -diff
			}
			if diff <= 1 {
				preds.m.Set("time_based_"+parts[0], pyMin(0.7, float64(len(times))/15.0))
			}
		}
	}
	return preds.kvs(), nil
}

func (p *PredictiveLoader) predictFromSessionHistory(sc *SessionHistoryContext) []predKV {
	preds := orderedPreds{entities.NewOrderedMap[float64]()}
	if len(p.sessionHistory) < 2 {
		return nil
	}
	recent := p.sessionHistory
	if len(recent) > 20 {
		recent = recent[len(recent)-20:]
	}
	for _, h := range recent {
		toolSim := sequenceSimilarity(sc.ToolSequence, h.ToolSequence)
		ctxSim := sequenceSimilarity(sc.ContextSequence, h.ContextSequence)
		if toolSim > 0.5 || ctxSim > 0.5 {
			score := pyMax(toolSim, ctxSim)
			var later []string
			if len(sc.ContextSequence) < len(h.ContextSequence) {
				later = h.ContextSequence[len(sc.ContextSequence):]
			}
			for _, id := range later {
				conf := float64(score * 0.8)
				prev, _ := preds.m.Get(id)
				preds.m.Set(id, pyMax(prev, conf))
			}
		}
	}
	return preds.kvs()
}

func sequenceSimilarity(a, b []string) float64 {
	if len(a) == 0 || len(b) == 0 {
		return 0.0
	}
	s1, s2 := map[string]bool{}, map[string]bool{}
	for _, x := range a {
		s1[x] = true
	}
	for _, x := range b {
		s2[x] = true
	}
	inter := 0
	for k := range s1 {
		if s2[k] {
			inter++
		}
	}
	union := len(s1) + len(s2) - inter
	if union == 0 {
		return 0.0
	}
	return float64(inter) / float64(union)
}

func toolContextMapping() map[string]string {
	return map[string]string{
		"manage_task": "task", "manage_subtask": "task", "manage_git_branch": "branch",
		"manage_project": "project", "manage_context": "context", "Bash": "execution",
		"Read": "file", "Write": "file", "Edit": "file",
	}
}

// patternHash replaces Python's per-process randomised hash(tuple); Python ids
// are not stable across runs, so any deterministic hash is equivalent.
func patternHash(seq []string) string {
	h := fnv.New64a()
	h.Write([]byte(seqKey(seq)))
	return strconv.FormatInt(int64(h.Sum64()), 10)
}

func (p *PredictiveLoader) updateUsagePatterns() {
	if len(p.sessionHistory) == 0 {
		return
	}
	recent := p.sessionHistory
	if len(recent) > 10 {
		recent = recent[len(recent)-10:]
	}
	for _, session := range recent {
		tools := session.ToolSequence
		for _, w := range []int{2, 3, 4} {
			for i := 0; i < len(tools)-w+1; i++ {
				seq := append([]string{}, tools[i:i+w]...)
				id := "tool_seq_" + patternHash(seq)
				if pat, ok := p.usagePatterns.Get(id); !ok {
					p.usagePatterns.Set(id, &UsagePattern{
						PatternID: id, PatternType: "tool_sequence", Trigger: TriggerToolSequence,
						Sequence: seq, Confidence: 0.5, Frequency: 1, LastSeen: p.now(),
					})
				} else {
					pat.Frequency++
					pat.LastSeen = p.now()
					pat.Confidence = pyMin(0.9, float64(pat.Frequency)/10.0)
				}
			}
		}
	}
}

// ValidatePredictions updates pattern success rates and returns them by pattern.
func (p *PredictiveLoader) ValidatePredictions(predictions, actual, patternIDs []string) *entities.OrderedMap[float64] {
	accuracy := entities.NewOrderedMap[float64]()
	act := map[string]bool{}
	for _, a := range actual {
		act[a] = true
	}
	predSet := map[string]bool{}
	correct := 0
	for _, x := range predictions {
		if !predSet[x] {
			predSet[x] = true
			if act[x] {
				correct++
			}
		}
	}
	hitRate := 0.0
	if len(predictions) > 0 {
		hitRate = float64(correct) / float64(len(predictions))
	}
	for _, id := range patternIDs {
		pat, ok := p.usagePatterns.Get(id)
		if !ok {
			continue
		}
		if pat.SuccessRate == 0.0 {
			pat.SuccessRate = hitRate
		} else {
			alpha := 0.2
			pat.SuccessRate = float64(alpha*hitRate) + float64((1-alpha)*pat.SuccessRate)
		}
		accuracy.Set(id, pat.SuccessRate)
	}
	return accuracy
}

// GetPredictionStats returns performance statistics; nil when there are no patterns.
func (p *PredictiveLoader) GetPredictionStats() *PredictionStats {
	if p.usagePatterns.Len() == 0 {
		return nil
	}
	var stats []PatternStat
	var rates []float64
	high := 0
	for _, id := range p.usagePatterns.Keys() {
		pat, _ := p.usagePatterns.Get(id)
		stats = append(stats, PatternStat{pat.PatternID, pat.PatternType, pat.Frequency, pat.Confidence, pat.SuccessRate})
		rates = append(rates, pat.SuccessRate)
		if pat.Confidence > 0.7 {
			high++
		}
	}
	total := p.usagePatterns.Len()
	if len(stats) > 10 {
		stats = stats[len(stats)-10:]
	}
	return &PredictionStats{
		TotalPatterns:              total,
		AvgSuccessRate:             value_objects.PySum(rates) / float64(total),
		HighConfidencePatterns:     high,
		SessionHistoryCount:        len(p.sessionHistory),
		PatternConfidenceThreshold: p.PatternConfidenceThreshold,
		Patterns:                   stats,
	}
}
