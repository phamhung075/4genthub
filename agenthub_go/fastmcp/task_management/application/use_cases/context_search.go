// Package use_cases ports task_management/application/use_cases modules.
//
// context_search.go ports context_search.py: full-text and semantic search across
// the context hierarchy.
package use_cases

import (
	"context"
	"math"
	"sort"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/dlclark/regexp2"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/cache"
)

// SearchScope mirrors context_search.SearchScope.
type SearchScope string

const (
	SearchScopeCurrentLevel SearchScope = "current"
	SearchScopeWithChildren SearchScope = "children"
	SearchScopeWithParents  SearchScope = "parents"
	SearchScopeAllLevels    SearchScope = "all"
)

func (e SearchScope) String() string { return string(e) }

// SearchMode mirrors context_search.SearchMode.
type SearchMode string

const (
	SearchModeExact    SearchMode = "exact"
	SearchModeContains SearchMode = "contains"
	SearchModeFuzzy    SearchMode = "fuzzy"
	SearchModeRegex    SearchMode = "regex"
	SearchModeSemantic SearchMode = "semantic"
)

func (e SearchMode) String() string { return string(e) }

// SearchQuery mirrors the context_search.SearchQuery dataclass (field order and
// defaults preserved).
type SearchQuery struct {
	Query  string
	Levels []value_objects.ContextLevel
	Scope  SearchScope
	Mode   SearchMode

	UserID      *string
	ProjectID   *string
	GitBranchID *string

	CreatedAfter  *time.Time
	CreatedBefore *time.Time
	UpdatedAfter  *time.Time
	UpdatedBefore *time.Time

	Limit            int
	Offset           int
	IncludeScore     bool
	IncludeInherited bool
	HighlightMatches bool
}

// NewSearchQuery applies the Python dataclass defaults for the required fields.
func NewSearchQuery(query string, levels []value_objects.ContextLevel) *SearchQuery {
	return &SearchQuery{
		Query:            query,
		Levels:           levels,
		Scope:            SearchScopeCurrentLevel,
		Mode:             SearchModeContains,
		Limit:            50,
		Offset:           0,
		IncludeScore:     true,
		IncludeInherited: false,
		HighlightMatches: true,
	}
}

// SearchResult mirrors the context_search.SearchResult dataclass.
type SearchResult struct {
	Level     value_objects.ContextLevel
	ContextID string
	Data      *entities.OrderedMap[any]
	Score     float64
	Matches   []*entities.OrderedMap[any]
	Metadata  *entities.OrderedMap[any]
}

// ContextSearchContextService is the consumer-side view of the
// UnifiedContextService. context_search stores it but never calls it
// (_get_contexts_for_level is a placeholder that returns []).
type ContextSearchContextService interface{}

// ContextSearchEngine mirrors context_search.ContextSearchEngine.
type ContextSearchEngine struct {
	contextService ContextSearchContextService
	cache          *cache.ContextCache
}

// NewContextSearchEngine mirrors ContextSearchEngine.__init__.
func NewContextSearchEngine(contextService ContextSearchContextService) *ContextSearchEngine {
	return &ContextSearchEngine{contextService: contextService, cache: cache.GetContextCache()}
}

// Search mirrors ContextSearchEngine.search.
func (e *ContextSearchEngine) Search(ctx context.Context, query *SearchQuery) ([]*SearchResult, error) {
	results := []*SearchResult{}

	// Return empty results for empty query (but allow '*' for wildcard).
	if query.Query == "" || value_objects.PyStrip(query.Query) == "" {
		// Only return empty if it's not a wildcard search.
		if query.Mode != SearchModeRegex || query.Query != "*" {
			return results, nil
		}
	}

	// Determine levels to search.
	searchLevels := e.expandSearchLevels(query.Levels, query.Scope)

	// Search each level.
	for _, level := range searchLevels {
		levelResults := e.searchLevel(ctx, level, query)
		results = append(results, levelResults...)
	}

	// Sort by relevance score (stable, like Python list.sort).
	sort.SliceStable(results, func(i, j int) bool { return results[i].Score > results[j].Score })

	// Apply pagination.
	start := query.Offset
	end := query.Offset + query.Limit
	results = contextSearchSliceResults(results, start, end)

	// Highlight matches if requested.
	if query.HighlightMatches {
		results = e.highlightMatches(results, query.Query)
	}

	return results, nil
}

// expandSearchLevels mirrors _expand_search_levels. Python returns a set, whose
// iteration order is unspecified; a deterministic canonical order is used here.
func (e *ContextSearchEngine) expandSearchLevels(levels []value_objects.ContextLevel, scope SearchScope) []value_objects.ContextLevel {
	in := map[value_objects.ContextLevel]bool{}
	for _, level := range levels {
		in[level] = true
	}

	switch scope {
	case SearchScopeWithChildren:
		for _, level := range levels {
			switch level {
			case value_objects.ContextLevelGlobal:
				in[value_objects.ContextLevelProject] = true
				in[value_objects.ContextLevelBranch] = true
				in[value_objects.ContextLevelTask] = true
			case value_objects.ContextLevelProject:
				in[value_objects.ContextLevelBranch] = true
				in[value_objects.ContextLevelTask] = true
			case value_objects.ContextLevelBranch:
				in[value_objects.ContextLevelTask] = true
			}
		}
	case SearchScopeWithParents:
		for _, level := range levels {
			switch level {
			case value_objects.ContextLevelTask:
				in[value_objects.ContextLevelBranch] = true
				in[value_objects.ContextLevelProject] = true
				in[value_objects.ContextLevelGlobal] = true
			case value_objects.ContextLevelBranch:
				in[value_objects.ContextLevelProject] = true
				in[value_objects.ContextLevelGlobal] = true
			case value_objects.ContextLevelProject:
				in[value_objects.ContextLevelGlobal] = true
			}
		}
	case SearchScopeAllLevels:
		in = map[value_objects.ContextLevel]bool{}
		for _, level := range value_objects.ContextLevelValues {
			in[level] = true
		}
	}

	out := []value_objects.ContextLevel{}
	for _, level := range value_objects.ContextLevelValues {
		if in[level] {
			out = append(out, level)
		}
	}
	return out
}

// contextSearchContextEntry is one (context_id, context_data) pair from
// _get_contexts_for_level.
type contextSearchContextEntry struct {
	ContextID string
	Data      *entities.OrderedMap[any]
}

// searchLevel mirrors _search_level.
func (e *ContextSearchEngine) searchLevel(ctx context.Context, level value_objects.ContextLevel, query *SearchQuery) []*SearchResult {
	contexts := e.getContextsForLevel(ctx, level, query.UserID, query.ProjectID, query.GitBranchID)

	results := []*SearchResult{}
	for _, entry := range contexts {
		// Apply filters.
		if !e.passesFilters(entry.Data, query) {
			continue
		}

		// Calculate relevance score.
		score, matches := e.calculateRelevance(entry.Data, query.Query, query.Mode)

		if score > 0 {
			created, _ := entry.Data.Get("created_at")
			updated, _ := entry.Data.Get("updated_at")
			var userID any
			if query.UserID != nil {
				userID = *query.UserID
			}
			metadata := entities.NewOrderedMap[any]()
			metadata.Set("created_at", created)
			metadata.Set("updated_at", updated)
			metadata.Set("user_id", userID)
			results = append(results, &SearchResult{
				Level:     level,
				ContextID: entry.ContextID,
				Data:      entry.Data,
				Score:     score,
				Matches:   matches,
				Metadata:  metadata,
			})
		}
	}

	return results
}

// passesFilters mirrors _passes_filters. The Python compares the raw values, which
// raises TypeError when a string is compared with a datetime; here values are
// coerced to a time when possible and the check is skipped when it is not.
func (e *ContextSearchEngine) passesFilters(contextData *entities.OrderedMap[any], query *SearchQuery) bool {
	if query.CreatedAfter != nil {
		if created, ok := contextData.Get("created_at"); ok && value_objects.PyTruthy(created) {
			if t, ok := contextSearchTimeValue(created); ok && t.Before(*query.CreatedAfter) {
				return false
			}
		}
	}
	if query.CreatedBefore != nil {
		if created, ok := contextData.Get("created_at"); ok && value_objects.PyTruthy(created) {
			if t, ok := contextSearchTimeValue(created); ok && t.After(*query.CreatedBefore) {
				return false
			}
		}
	}
	if query.UpdatedAfter != nil {
		if updated, ok := contextData.Get("updated_at"); ok && value_objects.PyTruthy(updated) {
			if t, ok := contextSearchTimeValue(updated); ok && t.Before(*query.UpdatedAfter) {
				return false
			}
		}
	}
	if query.UpdatedBefore != nil {
		if updated, ok := contextData.Get("updated_at"); ok && value_objects.PyTruthy(updated) {
			if t, ok := contextSearchTimeValue(updated); ok && t.After(*query.UpdatedBefore) {
				return false
			}
		}
	}
	return true
}

// contextSearchTimeValue coerces a stored value to a time.Time when possible.
func contextSearchTimeValue(v any) (time.Time, bool) {
	switch t := v.(type) {
	case time.Time:
		return t, true
	case *time.Time:
		if t != nil {
			return *t, true
		}
	case string:
		if parsed, err := value_objects.ParseISO(t); err == nil {
			return parsed, true
		}
	}
	return time.Time{}, false
}

// calculateRelevance mirrors _calculate_relevance.
func (e *ContextSearchEngine) calculateRelevance(data *entities.OrderedMap[any], query string, mode SearchMode) (float64, []*entities.OrderedMap[any]) {
	score := 0.0
	matches := []*entities.OrderedMap[any]{}

	// Convert data to searchable text.
	textContent := e.extractText(data)

	switch mode {
	case SearchModeExact:
		if strings.Contains(value_objects.PyLower(textContent), value_objects.PyLower(query)) {
			score = 1.0
			m := entities.NewOrderedMap[any]()
			m.Set("type", "exact")
			m.Set("field", "full_content")
			m.Set("matched", query)
			matches = append(matches, m)
		}

	case SearchModeContains:
		queryLower := value_objects.PyLower(query)
		textLower := value_objects.PyLower(textContent)

		queryLowerRunes := []rune(queryLower)
		textLowerRunes := []rune(textLower)
		textRunes := []rune(textContent)
		queryRunes := []rune(query)

		count := contextSearchCountRunes(textLowerRunes, queryLowerRunes)
		if count > 0 {
			// Score based on frequency.
			score = math.Min(1.0, float64(count)*0.2)

			// Find all occurrences.
			start := 0
			for {
				index := contextSearchFindRunes(textLowerRunes, queryLowerRunes, start)
				if index == -1 {
					break
				}
				m := entities.NewOrderedMap[any]()
				m.Set("type", "contains")
				m.Set("position", index)
				m.Set("matched", contextSearchSliceRunes(textRunes, index, index+len(queryRunes)))
				matches = append(matches, m)
				start = index + 1
			}
		}

	case SearchModeFuzzy:
		score = e.fuzzyScore(value_objects.PyLower(query), value_objects.PyLower(textContent))
		if score > 0.5 {
			m := entities.NewOrderedMap[any]()
			m.Set("type", "fuzzy")
			m.Set("score", score)
			matches = append(matches, m)
		}

	case SearchModeRegex:
		if query == "*" {
			score = 0.5 // Base score for wildcard match.
			m := entities.NewOrderedMap[any]()
			m.Set("type", "regex")
			m.Set("matched", "all")
			m.Set("wildcard", true)
			matches = append(matches, m)
		} else if pattern, ok := contextSearchCompileRegex(query); ok {
			foundMatches := contextSearchFinditer(pattern, []rune(textContent))
			if len(foundMatches) > 0 {
				score = math.Min(1.0, float64(len(foundMatches))*0.2)
				limit := len(foundMatches)
				if limit > 10 { // Limit matches.
					limit = 10
				}
				for _, found := range foundMatches[:limit] {
					m := entities.NewOrderedMap[any]()
					m.Set("type", "regex")
					m.Set("matched", found.matched)
					m.Set("position", found.position)
					matches = append(matches, m)
				}
			}
		}
		// An invalid pattern is re.error in Python; the except branch is a no-op
		// (the logger call is dropped).

	case SearchModeSemantic:
		// Placeholder for semantic search (logger call is dropped).
	}

	// Boost score for matches in important fields.
	score = e.applyFieldBoosts(data, query, score)

	return score, matches
}

// extractText mirrors _extract_text.
func (e *ContextSearchEngine) extractText(data *entities.OrderedMap[any]) string {
	textParts := []string{}
	contextSearchExtractRecursive(data, &textParts)
	return strings.Join(textParts, " ")
}

// contextSearchExtractRecursive walks dicts/lists in insertion order appending
// str() of every key and scalar.
func contextSearchExtractRecursive(obj any, parts *[]string) {
	switch v := obj.(type) {
	case *entities.OrderedMap[any]:
		for _, key := range v.Keys() {
			*parts = append(*parts, value_objects.PyStr(key))
			value, _ := v.Get(key)
			contextSearchExtractRecursive(value, parts)
		}
	case []any:
		for _, item := range v {
			contextSearchExtractRecursive(item, parts)
		}
	default:
		*parts = append(*parts, value_objects.PyStr(obj))
	}
}

// fuzzyScore mirrors _fuzzy_score.
func (e *ContextSearchEngine) fuzzyScore(query, text string) float64 {
	words := value_objects.PySplit(text)
	maxScore := 0.0
	for _, word := range words {
		score := e.stringSimilarity(query, word)
		if score > maxScore {
			maxScore = score
		}
	}
	return maxScore
}

// stringSimilarity mirrors _string_similarity (0-1).
func (e *ContextSearchEngine) stringSimilarity(s1, s2 string) float64 {
	// Handle empty strings.
	if s1 == "" && s2 == "" {
		return 1.0 // Both empty strings are considered identical.
	}
	if s1 == "" || s2 == "" {
		return 0.0
	}

	// Exact match should return 1.0.
	if s1 == s2 {
		return 1.0
	}

	// Case insensitive comparison.
	s1Lower := value_objects.PyLower(s1)
	s2Lower := value_objects.PyLower(s2)

	// Exact match case insensitive.
	if s1Lower == s2Lower {
		return 1.0
	}

	// For short strings, use character set overlap.
	if utf8.RuneCountInString(s1) <= 5 || utf8.RuneCountInString(s2) <= 5 {
		// Check if one is substring of other.
		if strings.Contains(s1Lower, s2Lower) || strings.Contains(s2Lower, s1Lower) {
			shorter := utf8.RuneCountInString(s1)
			longer := utf8.RuneCountInString(s2)
			if utf8.RuneCountInString(s2) < shorter {
				shorter = utf8.RuneCountInString(s2)
			}
			if utf8.RuneCountInString(s1) > longer {
				longer = utf8.RuneCountInString(s1)
			}
			return float64(shorter) / float64(longer)
		}

		// Character set overlap.
		common, total := contextSearchRuneOverlap(s1Lower, s2Lower)
		if total > 0 {
			return float64(common) / float64(total)
		}
		return 0.0
	}

	// For longer strings, use bigram similarity.
	s1Bigrams := contextSearchBigrams(s1Lower)
	s2Bigrams := contextSearchBigrams(s2Lower)

	// Handle strings with no valid bigrams.
	if len(s1Bigrams) == 0 || len(s2Bigrams) == 0 {
		common, total := contextSearchRuneOverlap(s1Lower, s2Lower)
		if total > 0 {
			return float64(common) / float64(total)
		}
		return 0.0
	}

	intersection := contextSearchSetIntersection(s1Bigrams, s2Bigrams)
	union := len(s1Bigrams) + len(s2Bigrams) - intersection

	if union > 0 {
		return float64(intersection) / float64(union)
	}
	return 0.0
}

// contextSearchRuneOverlap is len(set(s1) & set(s2)) and len(set(s1) | set(s2)).
func contextSearchRuneOverlap(s1, s2 string) (int, int) {
	set1 := map[rune]bool{}
	for _, r := range s1 {
		set1[r] = true
	}
	set2 := map[rune]bool{}
	for _, r := range s2 {
		set2[r] = true
	}
	common := 0
	for r := range set1 {
		if set2[r] {
			common++
		}
	}
	return common, len(set1) + len(set2) - common
}

// contextSearchBigrams is {s[i:i+2] for i in range(len(s)-1)} over code points.
func contextSearchBigrams(s string) map[string]bool {
	runes := []rune(s)
	set := map[string]bool{}
	for i := 0; i < len(runes)-1; i++ {
		set[string(runes[i:i+2])] = true
	}
	return set
}

// contextSearchSetIntersection is len(a & b).
func contextSearchSetIntersection(a, b map[string]bool) int {
	n := 0
	for k := range a {
		if b[k] {
			n++
		}
	}
	return n
}

// applyFieldBoosts mirrors _apply_field_boosts.
func (e *ContextSearchEngine) applyFieldBoosts(data *entities.OrderedMap[any], query string, baseScore float64) float64 {
	boost := 1.0
	queryLower := value_objects.PyLower(query)

	// Boost for matches in important fields.
	importantFields := []string{"title", "name", "description", "summary"}
	for _, field := range importantFields {
		if data.Has(field) {
			fieldValue, _ := data.Get(field)
			if strings.Contains(value_objects.PyLower(value_objects.PyStr(fieldValue)), queryLower) {
				boost *= 1.5
			}
		}
	}

	// Boost for recent updates.
	if updated, ok := data.Get("updated_at"); ok && value_objects.PyTruthy(updated) {
		if updatedTime, ok := contextSearchTimeValue(updated); ok {
			age := time.Now().UTC().Sub(updatedTime)
			if age < 24*time.Hour {
				boost *= 1.3
			} else if age < 7*24*time.Hour {
				boost *= 1.1
			}
		}
	}

	return math.Min(1.0, baseScore*boost)
}

// highlightMatches mirrors _highlight_matches.
func (e *ContextSearchEngine) highlightMatches(results []*SearchResult, query string) []*SearchResult {
	for _, result := range results {
		// Add highlight markers to matched text.
		for _, match := range result.Matches {
			if matched, ok := match.Get("matched"); ok {
				match.Set("highlighted", "**"+value_objects.PyStr(matched)+"**")
			}
		}
	}
	return results
}

// getContextsForLevel mirrors the _get_contexts_for_level placeholder that
// returns [].
func (e *ContextSearchEngine) getContextsForLevel(ctx context.Context, level value_objects.ContextLevel, userID, projectID, gitBranchID *string) []contextSearchContextEntry {
	return []contextSearchContextEntry{}
}

// SearchByPattern mirrors search_by_pattern.
func (e *ContextSearchEngine) SearchByPattern(ctx context.Context, pattern string, levels []value_objects.ContextLevel, userID string) ([]*SearchResult, error) {
	query := NewSearchQuery(pattern, levels)
	query.Mode = SearchModeRegex
	query.UserID = &userID
	query.Scope = SearchScopeCurrentLevel
	return e.Search(ctx, query)
}

// SearchRecent mirrors search_recent.
func (e *ContextSearchEngine) SearchRecent(ctx context.Context, levels []value_objects.ContextLevel, userID string, days, limit int) ([]*SearchResult, error) {
	updatedAfter := time.Now().UTC().Add(-time.Duration(days) * 24 * time.Hour)
	query := NewSearchQuery("*", levels)
	query.Mode = SearchModeRegex
	query.UserID = &userID
	query.UpdatedAfter = &updatedAfter
	query.Limit = limit
	return e.Search(ctx, query)
}

// SearchByTags mirrors search_by_tags.
func (e *ContextSearchEngine) SearchByTags(ctx context.Context, tags []string, levels []value_objects.ContextLevel, userID string) ([]*SearchResult, error) {
	// Build query for tags.
	tagQuery := strings.Join(tags, " OR ")
	query := NewSearchQuery(tagQuery, levels)
	query.Mode = SearchModeContains
	query.UserID = &userID
	return e.Search(ctx, query)
}

// contextSearchCompileRegex compiles a Python pattern. MustCompile panics on an
// invalid pattern (Python's re.error branch); ok is false in that case.
func contextSearchCompileRegex(pattern string) (re *regexp2.Regexp, ok bool) {
	defer func() {
		if recover() != nil {
			re, ok = nil, false
		}
	}()
	return services.PyRegex(pattern, true), true
}

// contextSearchRegexMatch is one re.finditer match (group 0 and its code point
// start index).
type contextSearchRegexMatch struct {
	matched  string
	position int
}

// contextSearchFinditer is list(re.finditer(pattern, text)).
func contextSearchFinditer(re *regexp2.Regexp, runes []rune) []contextSearchRegexMatch {
	var out []contextSearchRegexMatch
	m, _ := re.FindRunesMatch(runes)
	for m != nil {
		out = append(out, contextSearchRegexMatch{m.String(), m.Index})
		m, _ = re.FindNextMatch(m)
	}
	return out
}

// contextSearchCountRunes is str.count (non-overlapping occurrences).
func contextSearchCountRunes(hay, needle []rune) int {
	if len(needle) == 0 {
		return len(hay) + 1
	}
	count := 0
	for i := 0; i+len(needle) <= len(hay); {
		if contextSearchEqualAt(hay, needle, i) {
			count++
			i += len(needle)
		} else {
			i++
		}
	}
	return count
}

// contextSearchFindRunes is str.find(sub, start) over code points.
func contextSearchFindRunes(hay, needle []rune, start int) int {
	if start < 0 {
		start += len(hay)
		if start < 0 {
			start = 0
		}
	}
	if start > len(hay) {
		return -1
	}
	if len(needle) == 0 {
		return start
	}
	for i := start; i+len(needle) <= len(hay); i++ {
		if contextSearchEqualAt(hay, needle, i) {
			return i
		}
	}
	return -1
}

func contextSearchEqualAt(hay, needle []rune, at int) bool {
	for k, r := range needle {
		if hay[at+k] != r {
			return false
		}
	}
	return true
}

// contextSearchSliceRunes is Python's s[a:b] over code points.
func contextSearchSliceRunes(runes []rune, a, b int) string {
	n := len(runes)
	if a < 0 {
		a += n
		if a < 0 {
			a = 0
		}
	} else if a > n {
		a = n
	}
	if b < 0 {
		b += n
		if b < 0 {
			b = 0
		}
	} else if b > n {
		b = n
	}
	if a >= b {
		return ""
	}
	return string(runes[a:b])
}

// contextSearchSliceResults is Python's list[a:b].
func contextSearchSliceResults(results []*SearchResult, a, b int) []*SearchResult {
	n := len(results)
	if a < 0 {
		a += n
		if a < 0 {
			a = 0
		}
	} else if a > n {
		a = n
	}
	if b < 0 {
		b += n
		if b < 0 {
			b = 0
		}
	} else if b > n {
		b = n
	}
	if a >= b {
		return []*SearchResult{}
	}
	return results[a:b]
}
