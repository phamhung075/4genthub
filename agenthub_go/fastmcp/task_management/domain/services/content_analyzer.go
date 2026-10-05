package services

import (
	"fmt"
	"strings"
	"unicode"

	"github.com/dlclark/regexp2"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AnalysisType is the type of content analysis.
type AnalysisType string

const (
	AnalysisKeyword            AnalysisType = "keyword"
	AnalysisFileReference      AnalysisType = "file_reference"
	AnalysisEntityExtraction   AnalysisType = "entity_extraction"
	AnalysisTemporalPattern    AnalysisType = "temporal_pattern"
	AnalysisSemanticSimilarity AnalysisType = "semantic_similarity"
)

// ContentFeature is a feature extracted from task content. Position is a code point index.
type ContentFeature struct {
	FeatureType AnalysisType
	Value       string
	Confidence  float64
	Position    int
	Context     string
	Metadata    map[string]any
}

// EntityMatch is a matched entity between tasks.
type EntityMatch struct {
	Entity       string
	SourceTaskID string
	TargetTaskID string
	MatchType    string
	Confidence   float64
	Evidence     []string
}

type patternSpec struct {
	key        string // the Python pattern / name, reported in metadata
	re         *regexp2.Regexp
	confidence float64
}

const (
	wordClass  = `\p{L}\p{N}_`              // chars Python's \w matches (str.isalnum or "_")
	spaceClass = `\s\x1c-\x1f`              // chars Python's \s matches
	notWordBeh = `(?<![` + wordClass + `])` // Python \b before a word character
	notWordAhd = `(?![` + wordClass + `])`  // Python \b after a word character
)

// pyFoldExtras are the non-ASCII characters Python's re.IGNORECASE (Unicode patterns)
// treats as equal to ASCII letters: a-z / A-Z ranges match all four, literal s, k and
// i match the listed ones.
const pyFoldExtras = "\u0130\u0131\u017f\u212a"

var pyFoldLiteral = map[rune]string{'s': "\u017f", 'k': "\u212a", 'i': "\u0130\u0131"}

func isASCIILetter(c rune) bool { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') }

// pyRegex translates a Python (re, str pattern) expression to a regexp2 expression with the
// same Unicode semantics: \w, \s, \d and \b are redefined because .NET's differ from
// Python's (combining marks count as word characters in .NET), and IGNORECASE is
// expanded explicitly because the two engines fold different characters. A leading \b
// becomes a look-behind and a trailing \b a look-ahead; every pattern here has a word
// character on the inner side of each \b.
func pyRegex(pattern string, ignoreCase bool) *regexp2.Regexp {
	var b strings.Builder
	rs := []rune(pattern)
	inClass, classHasLetterRange := false, false
	for i := 0; i < len(rs); i++ {
		c := rs[i]
		switch {
		case c == '\\' && i+1 < len(rs):
			n := rs[i+1]
			i++
			switch {
			case n == 'w' && inClass:
				b.WriteString(wordClass)
			case n == 'w':
				b.WriteString("[" + wordClass + "]")
			case n == 's' && inClass:
				b.WriteString(spaceClass)
			case n == 's':
				b.WriteString("[" + spaceClass + "]")
			case n == 'd':
				b.WriteString(`\p{Nd}`)
			case n == 'b' && i == 1:
				b.WriteString(notWordBeh)
			case n == 'b':
				b.WriteString(notWordAhd)
			default:
				b.WriteRune('\\')
				b.WriteRune(n)
			}
		case c == '[' && !inClass:
			inClass, classHasLetterRange = true, false
			b.WriteRune(c)
		case c == ']' && inClass:
			if ignoreCase && classHasLetterRange {
				b.WriteString("a-zA-Z" + pyFoldExtras)
			}
			inClass = false
			b.WriteRune(c)
		case inClass:
			if ignoreCase && isASCIILetter(c) && i+2 < len(rs) && rs[i+1] == '-' && isASCIILetter(rs[i+2]) {
				classHasLetterRange = true
			}
			b.WriteRune(c)
		case ignoreCase && isASCIILetter(c):
			lc := unicode.ToLower(c)
			b.WriteString("[" + string(lc) + string(unicode.ToUpper(c)) + pyFoldLiteral[lc] + "]")
		default:
			b.WriteRune(c)
		}
	}
	return regexp2.MustCompile(b.String(), regexp2.None)
}

type namedPattern struct {
	name    string
	pattern string
}

var dependencyPatterns = []struct {
	pattern    string
	confidence float64
}{
	{`\b(?:requires?|needs?|depends?\s+on)\s+(?:the\s+)?([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\b`, 0.9},
	{`\b(?:after|following)\s+(?:the\s+)?([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\b`, 0.8},
	{`\b(?:before|preceding)\s+(?:the\s+)?([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\b`, 0.8},
	{`\b(?:blocks?|blocked\s+by)\s+(?:the\s+)?([A-Za-z][a-zA-Z]*(?:\s+[a-zA-Z]+)*)\b`, 1.0},
	{`\b(?:prerequisite|prerequist)\s+(?:the\s+)?([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\b`, 0.9},
	{`\b(?:implements?|implementation\s+of)\s+(["\']?[\w\s\-]+["\']?)`, 0.7},
	{`\b(?:extends?|extension\s+of)\s+(["\']?[\w\s\-]+["\']?)`, 0.7},
	{`\b(?:inherits?\s+from|based\s+on)\s+(["\']?[\w\s\-]+["\']?)`, 0.6},
	{`\b(?:uses?|utilizes?)\s+(["\']?[\w\s\-]+["\']?)`, 0.5},
	{`\b(?:first|initially|start\s+with)\s+(["\']?[\w\s\-]+["\']?)`, 0.7},
	{`\b(?:then|next|followed\s+by)\s+(["\']?[\w\s\-]+["\']?)`, 0.8},
	{`\b(?:finally|last|end\s+with)\s+(["\']?[\w\s\-]+["\']?)`, 0.6},
}

var filePatterns = []namedPattern{
	{"source_code", `(?:src/|source/)?[\w\-/]+\.(?:py|js|ts|tsx|jsx|java|cpp|c|h|php|rb|go|rs|swift|kt)`},
	{"config_files", `(?:config/|conf/)?[\w\-/]+\.(?:json|yaml|yml|toml|ini|cfg|properties)`},
	{"documentation", `(?:docs?/|documentation/)?[\w\-/]+\.(?:md|rst|txt|adoc)`},
	{"database", `(?:migrations?/|schema/|db/)?[\w\-/]+\.(?:sql|migration|schema)`},
	{"tests", `(?:tests?/|spec/|__tests__/)?[\w\-/]+\.(?:test|spec)\.(?:py|js|ts|java|cpp)`},
	{"static_assets", `(?:static/|assets/|public/)?[\w\-/]+\.(?:css|scss|less|png|jpg|jpeg|svg|ico)`},
	{"templates", `(?:templates?/|views?/)?[\w\-/]+\.(?:html|jinja|tpl|blade|erb)`},
}

var technicalEntities = []namedPattern{
	{"database_objects", `\b(?:table|view|procedure|function|trigger|index)\s+([a-z_][a-z0-9_]*)\b`},
	{"api_endpoints", `\b(?:GET|POST|PUT|DELETE|PATCH)\s+([/\w\-{}]+)`},
	{"api_routes", `(?:route|endpoint|path)[\s:]+([/\w\-{}]+)`},
	{"class_references", `\bclass\s+([A-Z][a-zA-Z0-9_]*)\b`},
	{"function_references", `\bfunction\s+([a-z_][a-zA-Z0-9_]*)\b`},
	{"method_references", `\.([a-z_][a-zA-Z0-9_]*)\s*\(`},
	{"module_imports", `\b(?:import|from)\s+([\w\.]+)`},
	{"component_names", `\b([A-Z][a-zA-Z0-9]*Component)\b`},
	{"service_names", `\b([A-Z][a-zA-Z0-9]*Service)\b`},
	{"model_names", `\b([A-Z][a-zA-Z0-9]*Model)\b`},
	{"entity_names", `\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)+)\b`},
}

var entityConfidence = map[string]float64{
	"database_objects": 0.9, "api_endpoints": 0.8, "class_references": 0.7, "function_references": 0.6,
	"module_imports": 0.8, "component_names": 0.7, "service_names": 0.7, "model_names": 0.7, "entity_names": 0.6,
}

var temporalPatterns = []struct {
	pattern    string
	confidence float64
}{
	{`\bstep\s+(\d+)`, 0.8},
	{`\bphase\s+(\d+)`, 0.7},
	{`\bstage\s+(\d+)`, 0.7},
	{`\border\s*:\s*(\d+)`, 0.6},
	{`\bsequence\s*:\s*(\d+)`, 0.6},
	{`\b(first|second|third|fourth|fifth|last)\s+step`, 0.7},
}

// ContentAnalyzer analyzes task content to identify dependencies.
type ContentAnalyzer struct {
	keyword  []patternSpec
	files    []patternSpec
	entities []patternSpec
	temporal []patternSpec
}

func NewContentAnalyzer() *ContentAnalyzer {
	a := &ContentAnalyzer{}
	for _, p := range dependencyPatterns {
		a.keyword = append(a.keyword, patternSpec{p.pattern, pyRegex(p.pattern, true), p.confidence})
	}
	for _, p := range filePatterns {
		a.files = append(a.files, patternSpec{p.name, pyRegex(p.pattern, true), 0})
	}
	for _, p := range technicalEntities {
		a.entities = append(a.entities, patternSpec{p.name, pyRegex(p.pattern, p.name != "entity_names"), entityConfidenceFor(p.name)})
	}
	for _, p := range temporalPatterns {
		a.temporal = append(a.temporal, patternSpec{p.pattern, pyRegex(p.pattern, true), p.confidence})
	}
	return a
}

type reMatch struct {
	start, end int
	full, g1   string
}

// finditer returns the non-overlapping matches of re over runes (code point offsets).
func finditer(re *regexp2.Regexp, runes []rune) []reMatch {
	var out []reMatch
	m, _ := re.FindRunesMatch(runes)
	for m != nil {
		g := ""
		if gs := m.Groups(); len(gs) > 1 {
			g = gs[1].String()
		} else {
			g = m.String()
		}
		out = append(out, reMatch{m.Index, m.Index + m.Length, m.String(), g})
		m, _ = re.FindNextMatch(m)
	}
	return out
}

// pySlice is Python's s[max(0, a):b] over code points.
func pySlice(runes []rune, a, b int) string {
	if a < 0 {
		a = 0
	}
	if b > len(runes) {
		b = len(runes)
	}
	if a >= b {
		return ""
	}
	return string(runes[a:b])
}

// ExtractFeatures extracts all features from task content.
func (a *ContentAnalyzer) ExtractFeatures(content string) []ContentFeature {
	var out []ContentFeature
	out = append(out, a.extractKeywordFeatures(content)...)
	out = append(out, a.extractFileFeatures(content)...)
	out = append(out, a.extractEntityFeatures(content)...)
	return append(out, a.extractTemporalFeatures(content)...)
}

func (a *ContentAnalyzer) extractKeywordFeatures(content string) []ContentFeature {
	var out []ContentFeature
	original := []rune(content)
	lower := []rune(value_objects.PyLower(content))
	for _, p := range a.keyword {
		for _, m := range finditer(p.re, lower) {
			out = append(out, ContentFeature{FeatureType: AnalysisKeyword, Value: strings.Trim(m.g1, "'\""),
				Confidence: p.confidence, Position: m.start, Context: pySlice(original, m.start-50, m.end+50),
				Metadata: map[string]any{"pattern": p.key, "full_match": m.full}})
		}
	}
	return out
}

func (a *ContentAnalyzer) extractFileFeatures(content string) []ContentFeature {
	var out []ContentFeature
	runes := []rune(content)
	for _, p := range a.files {
		for _, m := range finditer(p.re, runes) {
			confidence := 0.6
			switch p.key {
			case "source_code", "config_files", "database":
				confidence = 0.8
			case "tests":
				confidence = 0.7
			}
			ext := ""
			if strings.Contains(m.full, ".") {
				ext = m.full[strings.LastIndex(m.full, ".")+1:]
			}
			out = append(out, ContentFeature{FeatureType: AnalysisFileReference, Value: m.full, Confidence: confidence,
				Position: m.start, Context: pySlice(runes, m.start-30, m.end+30),
				Metadata: map[string]any{"file_type": p.key, "extension": ext}})
		}
	}
	return out
}

func (a *ContentAnalyzer) extractEntityFeatures(content string) []ContentFeature {
	var out []ContentFeature
	runes := []rune(content)
	for _, p := range a.entities {
		for _, m := range finditer(p.re, runes) {
			out = append(out, ContentFeature{FeatureType: AnalysisEntityExtraction, Value: m.g1, Confidence: p.confidence,
				Position: m.start, Context: pySlice(runes, m.start-40, m.end+40),
				Metadata: map[string]any{"entity_type": p.key, "full_match": m.full}})
		}
	}
	return out
}

func isDigitString(s string) bool {
	if s == "" {
		return false
	}
	for _, r := range s {
		if !unicode.IsDigit(r) {
			return false
		}
	}
	return true
}

func (a *ContentAnalyzer) extractTemporalFeatures(content string) []ContentFeature {
	var out []ContentFeature
	runes := []rune(content)
	for _, p := range a.temporal {
		for _, m := range finditer(p.re, runes) {
			seq := "sequential"
			if isDigitString(m.g1) {
				seq = "ordered"
			}
			out = append(out, ContentFeature{FeatureType: AnalysisTemporalPattern, Value: m.g1, Confidence: p.confidence,
				Position: m.start, Context: pySlice(runes, m.start-30, m.end+30),
				Metadata: map[string]any{"pattern": p.key, "sequence_type": seq}})
		}
	}
	return out
}

// FindContentMatches finds matches between source features and the features of target content.
func (a *ContentAnalyzer) FindContentMatches(source []ContentFeature, targetContent string) []EntityMatch {
	matches := []EntityMatch{}
	targets := a.ExtractFeatures(targetContent)
	for _, s := range source {
		for _, t := range targets {
			if m := a.calculateFeatureMatch(s, t); m != nil && m.Confidence > 0.3 {
				matches = append(matches, *m)
			}
		}
	}
	return matches
}

func compatibleTypes(t AnalysisType, target AnalysisType) bool {
	switch t {
	case AnalysisKeyword, AnalysisEntityExtraction:
		return target == AnalysisKeyword || target == AnalysisEntityExtraction
	case AnalysisFileReference:
		return target == AnalysisFileReference
	case AnalysisTemporalPattern:
		return target == AnalysisTemporalPattern
	}
	return false
}

func (a *ContentAnalyzer) calculateFeatureMatch(s, t ContentFeature) *EntityMatch {
	if !compatibleTypes(s.FeatureType, t.FeatureType) {
		return nil
	}
	similarity := calculateStringSimilarity(s.Value, t.Value)
	minThreshold := 0.5
	if s.FeatureType == AnalysisKeyword || t.FeatureType == AnalysisKeyword || s.Confidence > 0.7 || t.Confidence > 0.7 {
		minThreshold = 0.3
	}
	if similarity < minThreshold {
		return nil
	}
	confidence := float64((s.Confidence+t.Confidence)/2) * similarity
	if similarity >= 0.95 {
		confidence *= 1.2
	}
	if confidence > 0.95 {
		confidence = 0.95
	}
	return &EntityMatch{Entity: s.Value, MatchType: string(s.FeatureType) + "_" + string(t.FeatureType),
		Confidence: confidence, Evidence: []string{
			"Source: " + pySlice([]rune(s.Context), 0, 100),
			"Target: " + pySlice([]rune(t.Context), 0, 100),
			fmt.Sprintf("Similarity: %.2f", similarity)}}
}

func splitTokens(s string) map[string]struct{} {
	set := map[string]struct{}{}
	start := 0
	rs := []rune(s)
	i := 0
	for i < len(rs) {
		if value_objects.PyIsSpace(rs[i]) || rs[i] == '_' || rs[i] == '-' {
			set[string(rs[start:i])] = struct{}{}
			for i < len(rs) && (value_objects.PyIsSpace(rs[i]) || rs[i] == '_' || rs[i] == '-') {
				i++
			}
			start = i
			continue
		}
		i++
	}
	set[string(rs[start:])] = struct{}{}
	return set
}

func calculateStringSimilarity(a, b string) float64 {
	a, b = value_objects.PyStrip(value_objects.PyLower(a)), value_objects.PyStrip(value_objects.PyLower(b))
	if a == b {
		return 1.0
	}
	la, lb := runeLen(a), runeLen(b)
	if strings.Contains(b, a) || strings.Contains(a, b) {
		shorter, longer := la, lb
		if lb < la {
			shorter, longer = lb, la
		}
		return float64(shorter) / float64(longer)
	}
	t1, t2 := splitTokens(a), splitTokens(b)
	inter := 0
	for k := range t1 {
		if _, ok := t2[k]; ok {
			inter++
		}
	}
	union := len(t1) + len(t2) - inter
	if sim := float64(inter) / float64(union); sim > 0.3 {
		return sim
	}
	if la <= 20 && lb <= 20 {
		return simpleEditDistanceSimilarity(a, b)
	}
	return 0.0
}

func simpleEditDistanceSimilarity(a, b string) float64 {
	if a == "" || b == "" {
		return 0.0
	}
	common := 0
	for _, c := range a {
		if strings.ContainsRune(b, c) {
			common++
		}
	}
	maxLen := runeLen(a)
	if l := runeLen(b); l > maxLen {
		maxLen = l
	}
	return float64(common) / float64(maxLen)
}

// AnalyzeTaskRelationships matches every task's features against every other task's content.
func (a *ContentAnalyzer) AnalyzeTaskRelationships(taskContents *entities.OrderedMap[string]) *entities.OrderedMap[[]EntityMatch] {
	relationships := entities.NewOrderedMap[[]EntityMatch]()
	features := map[string][]ContentFeature{}
	ids := taskContents.Keys()
	for _, id := range ids {
		content, _ := taskContents.Get(id)
		features[id] = a.ExtractFeatures(content)
	}
	for i, src := range ids {
		matches := []EntityMatch{}
		for j, tgt := range ids {
			if i == j {
				continue
			}
			target, _ := taskContents.Get(tgt)
			for _, m := range a.FindContentMatches(features[src], target) {
				m.SourceTaskID, m.TargetTaskID = src, tgt
				matches = append(matches, m)
			}
		}
		relationships.Set(src, matches)
	}
	return relationships
}

// AnalysisSummary is the result of GetAnalysisSummary.
type AnalysisSummary struct {
	TotalFeatures          int
	FeatureTypes           *entities.OrderedMap[int]
	HighConfidenceFeatures int
	AvgConfidence          float64
	ExtractedEntities      []string
	FileReferences         []string
}

// GetAnalysisSummary generates summary statistics for content analysis.
func (a *ContentAnalyzer) GetAnalysisSummary(features []ContentFeature) AnalysisSummary {
	s := AnalysisSummary{TotalFeatures: len(features), FeatureTypes: entities.NewOrderedMap[int](),
		ExtractedEntities: []string{}, FileReferences: []string{}}
	if len(features) == 0 {
		return s
	}
	confidences := make([]float64, 0, len(features))
	for _, f := range features {
		n, _ := s.FeatureTypes.Get(string(f.FeatureType))
		s.FeatureTypes.Set(string(f.FeatureType), n+1)
		if f.Confidence > 0.7 {
			s.HighConfidenceFeatures++
		}
		switch f.FeatureType {
		case AnalysisEntityExtraction:
			s.ExtractedEntities = append(s.ExtractedEntities, f.Value)
		case AnalysisFileReference:
			s.FileReferences = append(s.FileReferences, f.Value)
		}
		confidences = append(confidences, f.Confidence)
	}
	s.AvgConfidence = value_objects.PySum(confidences) / float64(len(features))
	return s
}

// entityConfidenceFor is confidence_map.get(entity_type, 0.5).
func entityConfidenceFor(name string) float64 {
	if c, ok := entityConfidence[name]; ok {
		return c
	}
	return 0.5
}

// PyRegex exposes pyRegex to the intelligence subpackage.
func PyRegex(pattern string, ignoreCase bool) *regexp2.Regexp { return pyRegex(pattern, ignoreCase) }
