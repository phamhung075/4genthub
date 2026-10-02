// Package parsers ports task_management/infrastructure/parsers.
package parsers

import (
	"crypto/md5"
	"encoding/hex"
	"os"
	"regexp"
	"strconv"
	"strings"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/utilities/pyyaml"
)

var (
	// Python keeps the first spelling of a string in a set; stringSet preserves insertion order.
	mdcRefRe    = regexp.MustCompile(`\[([^\]]+)\]\(mdc:([^)]+)\)`)
	importRe    = regexp.MustCompile(`@import\s+"([^"]+)"`)
	includeRe   = regexp.MustCompile(`include:\s*([^\n]+)`)
	dependsOnRe = regexp.MustCompile(`depends_on:\s*\[([^\]]+)\]`)
	mdRefRe     = regexp.MustCompile(`\[([^\]]+)\]\(([^)]+)\)`)
	mustacheRe  = regexp.MustCompile(`\{\{([^}]+)\}\}`)

	configSectionRes = []*regexp.Regexp{
		regexp.MustCompile(`(?m)^\s*config:`),
		regexp.MustCompile(`(?m)^\s*configuration:`),
		regexp.MustCompile(`(?m)^\s*\[?config\]?\s*$`),
		regexp.MustCompile(`(?m)^\s*\[?configuration\]?\s*$`),
	}

	textURLRe  = regexp.MustCompile(`https?://[^\s]+`)
	textFileRe = regexp.MustCompile(`file://[^\s]+`)
	textNameRe = regexp.MustCompile(`[a-zA-Z0-9_-]+\.[a-zA-Z]{2,4}`)
	textVarRe  = regexp.MustCompile(`\$\{([^}]+)\}`)
)

// RuleContentParser is rule_content_parser.RuleContentParser: an advanced parser for rule
// content with format detection and validation.
type RuleContentParser struct{}

// NewRuleContentParser builds a parser (Python's __init__ only installs handlers).
func NewRuleContentParser() *RuleContentParser { return &RuleContentParser{} }

// ParseRuleFile is RuleContentParser.parse_rule_file.
func (p *RuleContentParser) ParseRuleFile(filePath string) (*entities.RuleContentRuleContent, error) {
	formatType := p.DetectFormat(filePath)

	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}
	// open(..., encoding="utf-8") in text mode: invalid UTF-8 fails, and universal newlines
	// turn "\r\n" and lone "\r" into "\n" before anything else sees the text.
	if !utf8.Valid(data) {
		return nil, &UnicodeDecodeError{Msg: "'utf-8' codec can't decode bytes"}
	}
	raw := strings.ReplaceAll(strings.ReplaceAll(string(data), "\r\n", "\n"), "\r", "\n")

	metadata, err := p.generateMetadata(filePath, formatType, raw)
	if err != nil {
		return nil, err
	}

	parsed := p.parseByFormat(formatType, raw)

	if parsed.err != nil {
		return nil, parsed.err
	}
	return entities.NewRuleContentRuleContent(metadata, raw, asOrderedMap(parsed.content), asStringMap(parsed.sections),
		parsed.references, asOrderedMap(parsed.variables))
}

// DetectFormat is RuleContentParser._detect_format.
func (p *RuleContentParser) DetectFormat(filePath string) entities.RuleFormat {
	switch lowerExt(filePath) {
	case ".mdc":
		return entities.RuleFormatMdc
	case ".md":
		return entities.RuleFormatMd
	case ".json":
		return entities.RuleFormatJson
	case ".yaml", ".yml":
		return entities.RuleFormatYaml
	case ".txt":
		return entities.RuleFormatTxt
	}
	return entities.RuleFormatTxt
}

// parseResult is the tuple returned by the format handlers; content is a
// *OrderedMap[any] for the parsers that build a dict and the raw decoded value for the
// JSON/YAML parsers (a root sequence is not representable in the entity's field).
type parseResult struct {
	content    any
	sections   any
	references []string
	variables  any
	err        error // an exception that escapes the Python handler
}

func (p *RuleContentParser) parseByFormat(format entities.RuleFormat, raw string) parseResult {
	switch format {
	case entities.RuleFormatMdc:
		return p.parseMDC(raw)
	case entities.RuleFormatMd:
		return p.parseMarkdown(raw)
	case entities.RuleFormatJson:
		return p.parseJSON(raw)
	case entities.RuleFormatYaml:
		return p.parseYAML(raw)
	}
	return p.parseText(raw)
}

func lowerExt(path string) string {
	i := strings.LastIndex(path, ".")
	if i < 0 {
		return ""
	}
	return strings.ToLower(path[i:])
}

func (p *RuleContentParser) generateMetadata(filePath string, formatType entities.RuleFormat, content string) (*entities.RuleContentRuleMetadata, error) {
	stat, err := os.Stat(filePath)
	if err != nil {
		return nil, err
	}
	sum := md5.Sum([]byte(content))
	meta := &entities.RuleContentRuleMetadata{
		Path:         filePath,
		Format:       formatType,
		Type:         p.classifyRuleType(filePath, content),
		Size:         int(stat.Size()),
		Modified:     float64(stat.ModTime().UnixNano()) / 1e9,
		Checksum:     hex.EncodeToString(sum[:]),
		Dependencies: p.extractDependencies(content),
	}
	return meta, nil
}

// extractDependencies is RuleContentParser._extract_dependencies.
func (p *RuleContentParser) extractDependencies(content string) []string {
	set := newStringSet()
	add := func(s string) { set.add(s) }
	addMatches := func(re *regexp.Regexp, group int) {
		for _, m := range re.FindAllStringSubmatch(content, -1) {
			if group < len(m) {
				add(m[group])
			}
		}
	}
	addMatches(mdcRefRe, 2)
	addMatches(importRe, 1)
	addMatches(includeRe, 1)

	// depends_on values are not split, matching Python's findall result verbatim.
	addMatches(dependsOnRe, 1)
	return set.items
}

// classifyRuleType is RuleContentParser._classify_rule_type.
func (p *RuleContentParser) classifyRuleType(filePath, content string) entities.RuleType {
	pathStr := value_objects.PyLower(filePath)
	contentLower := value_objects.PyLower(content)

	if strings.Contains(pathStr, "task") || strings.Contains(contentLower, "task") {
		return entities.RuleTypeTask
	}
	if strings.Contains(pathStr, "context") || strings.Contains(contentLower, "context") {
		return entities.RuleTypeContext
	}
	if strings.Contains(pathStr, "agent") {
		return entities.RuleTypeAgent
	}
	if strings.Contains(contentLower, "agent") {
		if !strings.Contains(pathStr, "config") && !strings.Contains(pathStr, "configuration") &&
			!strings.Contains(contentLower, "config") && !strings.Contains(contentLower, "configuration") {
			return entities.RuleTypeAgent
		}
	}
	if strings.Contains(pathStr, "config") || strings.Contains(pathStr, "configuration") {
		return entities.RuleTypeConfig
	}
	for _, re := range configSectionRes {
		if re.MatchString(contentLower) {
			return entities.RuleTypeConfig
		}
	}
	return entities.RuleTypeGeneral
}

// parseMDC is RuleContentParser._parse_mdc (MDC uses the markdown structure).
func (p *RuleContentParser) parseMDC(content string) parseResult {
	return p.parseMarkdown(content)
}

// parseMarkdown is RuleContentParser._parse_markdown.
func (p *RuleContentParser) parseMarkdown(content string) parseResult {
	sections := newOrderedAny()
	references := []string{}
	variables := newOrderedAny()

	lines := strings.Split(content, "\n")
	currentSection := "content"
	var current []string

	for _, line := range lines {
		if strings.HasPrefix(line, "#") {
			if len(current) > 0 {
				sections.Set(currentSection, strings.Join(current, "\n"))
			}
			// line.strip("# ").lower().replace(" ", "_")
			currentSection = strings.ReplaceAll(value_objects.PyLower(strings.Trim(line, "# ")), " ", "_")
			current = nil
			continue
		}
		current = append(current, line)
		for _, m := range mdRefRe.FindAllStringSubmatch(line, -1) {
			references = append(references, m[2])
		}
		for _, m := range mustacheRe.FindAllStringSubmatch(line, -1) {
			variables.Set(m[1], m[1])
		}
	}
	if len(current) > 0 {
		sections.Set(currentSection, strings.Join(current, "\n"))
	}

	parsed := newOrderedAny()
	parsed.Set("type", "markdown")
	parsed.Set("sections", sections)
	parsed.Set("references", references)
	parsed.Set("variables", variables)

	return parseResult{content: parsed, sections: sections, references: references, variables: variables}
}

// parseJSON is RuleContentParser._parse_json. Invalid JSON returns empty results, as the
// Python logs and returns ({}, {}, [], {}).
func (p *RuleContentParser) parseJSON(content string) parseResult {
	decoded, err := entities.DecodeJSON([]byte(content))
	if err != nil {
		return parseResult{content: newOrderedAny(), sections: newOrderedAny(), variables: newOrderedAny()}
	}
	// Python calls parsed.items() on the decoded value; any non-object raises AttributeError.
	if _, isDict := decoded.(*entities.OrderedMap[any]); !isDict {
		return parseResult{err: &AttributeError{Msg: "'" + pyTypeName(decoded) + "' object has no attribute 'items'"}}
	}
	sections := newOrderedAny()
	references := []string{}
	variables := newOrderedAny()

	var extractRefs func(obj any, path string)
	extractRefs = func(obj any, path string) {
		switch v := obj.(type) {
		case *entities.OrderedMap[any]:
			for _, key := range v.Keys() {
				value, _ := v.Get(key)
				newPath := key
				if path != "" {
					newPath = path + "." + key
				}
				if key == "reference" {
					if s, ok := value.(string); ok {
						references = append(references, s)
						continue
					}
				}
				if key == "variables" {
					if om, ok := value.(*entities.OrderedMap[any]); ok {
						for _, k := range om.Keys() {
							val, _ := om.Get(k)
							variables.Set(k, val)
						}
						continue
					}
				}
				extractRefs(value, newPath)
			}
		case []any:
			for i, item := range v {
				extractRefs(item, path+"["+strconv.Itoa(i)+"]")
			}
		}
	}
	extractRefs(decoded, "")

	if root, ok := decoded.(*entities.OrderedMap[any]); ok {
		for _, key := range root.Keys() {
			value, _ := root.Get(key)
			switch value.(type) {
			case *entities.OrderedMap[any], []any:
				if dumped, err := value_objects.PyJSONDumps(value, 2); err == nil {
					sections.Set(key, dumped)
				}
			default:
				sections.Set(key, value_objects.PyStr(value))
			}
		}
	}
	return parseResult{content: decoded, sections: sections, references: references, variables: variables}
}

// parseYAML is RuleContentParser._parse_yaml. Invalid YAML returns empty results.
func (p *RuleContentParser) parseYAML(content string) parseResult {
	parsed, err := entities.LoadYAML([]byte(content))
	if err != nil {
		return parseResult{content: newOrderedAny(), sections: newOrderedAny(), variables: newOrderedAny()}
	}
	sections := newOrderedAny()
	references := []string{}
	variables := newOrderedAny()

	var extractRefs func(obj any)
	extractRefs = func(obj any) {
		switch v := obj.(type) {
		case *entities.OrderedMap[any]:
			for _, key := range v.Keys() {
				value, _ := v.Get(key)
				if key == "reference" {
					if s, ok := value.(string); ok {
						references = append(references, s)
						continue
					}
				}
				if key == "variables" {
					if om, ok := value.(*entities.OrderedMap[any]); ok {
						for _, k := range om.Keys() {
							val, _ := om.Get(k)
							variables.Set(k, val)
						}
						continue
					}
				}
				extractRefs(value)
			}
		case []any:
			for _, item := range v {
				extractRefs(item)
			}
		}
	}

	root, isMap := parsed.(*entities.OrderedMap[any])
	if isMap {
		extractRefs(root)
		for _, key := range root.Keys() {
			value, _ := root.Get(key)
			switch value.(type) {
			case *entities.OrderedMap[any], []any:
				dumped, err := pyyaml.Dump(value, true)
				if err != nil {
					return parseResult{err: err}
				}
				sections.Set(key, dumped)
			default:
				sections.Set(key, value_objects.PyStr(value))
			}
		}
	}

	if !value_objects.PyTruthy(parsed) {
		parsed = newOrderedAny()
	}
	return parseResult{content: parsed, sections: sections, references: references, variables: variables}
}

// parseText is RuleContentParser._parse_text.
func (p *RuleContentParser) parseText(content string) parseResult {
	sections := newOrderedAny()
	sections.Set("content", content)
	references := []string{}
	variables := newOrderedAny()

	for _, re := range []*regexp.Regexp{textURLRe, textFileRe, textNameRe} {
		references = append(references, re.FindAllString(content, -1)...)
	}
	for _, m := range textVarRe.FindAllStringSubmatch(content, -1) {
		variables.Set(m[1], m[1])
	}

	parsed := newOrderedAny()
	parsed.Set("type", "text")
	parsed.Set("content", content)
	parsed.Set("lines", len(strings.Split(content, "\n")))
	parsed.Set("characters", len([]rune(content)))

	return parseResult{content: parsed, sections: sections, references: references, variables: variables}
}

func asOrderedMap(v any) *entities.OrderedMap[any] {
	if om, ok := v.(*entities.OrderedMap[any]); ok {
		return om
	}
	return newOrderedAny()
}

func asStringMap(v any) *entities.OrderedMap[string] {
	om := entities.NewOrderedMap[string]()
	if src, ok := v.(*entities.OrderedMap[any]); ok {
		for _, k := range src.Keys() {
			val, _ := src.Get(k)
			if s, ok := val.(string); ok {
				om.Set(k, s)
			}
		}
	}
	return om
}

// stringSet reproduces Python's list(set(...)) observable result; only membership
// matters, so insertion order is kept.
type stringSet struct{ items []string }

func newStringSet() *stringSet { return &stringSet{} }

func (s *stringSet) add(v string) {
	for _, x := range s.items {
		if x == v {
			return
		}
	}
	s.items = append(s.items, v)
}

// newOrderedAny is a helper for building the dict-shaped results.
func newOrderedAny() *entities.OrderedMap[any] { return entities.NewOrderedMap[any]() }
