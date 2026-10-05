package services

import (
	"crypto/md5"
	"encoding/hex"
	"errors"
	"os"
	"regexp"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// iruleParserServiceMethod patterns. MDC is essentially markdown with metadata.
var (
	ruleImportRe   = regexp.MustCompile(`(?i)@import\s+["']([^"']+)["']`)
	ruleIncludeRe  = regexp.MustCompile(`(?i)@include\s+["']([^"']+)["']`)
	ruleImport2Re  = regexp.MustCompile(`(?i)import\s+["']([^"']+)["']`)
	ruleRequireRe  = regexp.MustCompile(`(?i)require\s+["']([^"']+)["']`)
	ruleFileRefRe  = regexp.MustCompile(`(?i)(?:file|path):\s*["']([^"']+)["']`)
	wikiRefRe      = regexp.MustCompile(`\[\[([^\]]+)\]\]`)
	mustache2Re    = regexp.MustCompile(`\{\{([^}]+)\}\}`)
	hashtagRe      = regexp.MustCompile(`#(\w+)`)
	varAssignRe    = regexp.MustCompile(`^(\w+)\s*=\s*(.+)$`)
	frontmatterDel = "---"
)

// RuleParserService is rule_parser_service.RuleParserService.
type RuleParserService struct{}

// NewRuleParserService builds the service (Python's __init__ only installs handlers).
func NewRuleParserService() *RuleParserService { return &RuleParserService{} }

// ParseRuleFile is RuleParserService.parse_rule_file.
func (s *RuleParserService) ParseRuleFile(filePath string) (*entities.RuleContent, error) {
	if _, err := os.Stat(filePath); err != nil {
		return nil, errors.New("Rule file not found: " + filePath)
	}
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, &value_objects.ValueError{Msg: "Failed to read rule file " + filePath + ": " + err.Error()}
	}
	raw := string(data)

	formatType := s.DetectFormat(filePath)
	metadata := s.generateMetadata(filePath, formatType, raw)
	parsed, err := s.parseByFormat(formatType, raw)
	if err != nil {
		return nil, err
	}
	return &entities.RuleContent{
		Metadata:      metadata,
		RawContent:    raw,
		ParsedContent: asOrderedMapAny(parsed.content),
		Sections:      asOrderedMapString(parsed.sections),
		References:    parsed.references,
		Variables:     asOrderedMapAny(parsed.variables),
	}, nil
}

// DetectFormat is RuleParserService.detect_format.
func (s *RuleParserService) DetectFormat(filePath string) value_objects.RuleFormat {
	switch lowerSuffix(filePath) {
	case ".mdc":
		return value_objects.RuleFormatMdc
	case ".md", ".markdown":
		return value_objects.RuleFormatMd
	case ".json":
		return value_objects.RuleFormatJson
	case ".yaml", ".yml":
		return value_objects.RuleFormatYaml
	case ".txt":
		return value_objects.RuleFormatTxt
	}
	return value_objects.RuleFormatTxt
}

func lowerSuffix(path string) string {
	i := strings.LastIndex(path, ".")
	if i < 0 {
		return ""
	}
	return strings.ToLower(path[i:])
}

type ruleParseResult struct {
	content    any
	sections   any
	references []string
	variables  any
}

func (s *RuleParserService) parseByFormat(format value_objects.RuleFormat, raw string) (ruleParseResult, error) {
	switch format {
	case value_objects.RuleFormatMdc:
		return s.parseMDC(raw), nil
	case value_objects.RuleFormatMd:
		return s.parseMarkdown(raw), nil
	case value_objects.RuleFormatJson:
		return s.parseJSON(raw)
	case value_objects.RuleFormatYaml:
		return s.parseYAML(raw)
	}
	return s.parseText(raw), nil
}

// generateMetadata is RuleParserService._generate_metadata (static parser service).
func (s *RuleParserService) generateMetadata(filePath string, formatType value_objects.RuleFormat, content string) *entities.RuleMetadata {
	stat, err := os.Stat(filePath)
	size := 0
	modified := 0.0
	if err == nil {
		size = int(stat.Size())
		modified = float64(stat.ModTime().UnixNano()) / 1e9
	}
	sum := md5.Sum([]byte(content))
	return &entities.RuleMetadata{
		Path:         filePath,
		Format:       formatType,
		Type:         s.classifyRuleType(filePath, content),
		Size:         size,
		Modified:     modified,
		Checksum:     hex.EncodeToString(sum[:]),
		Dependencies: s.extractDependencies(content),
		Version:      "1.0",
		Author:       "rule_parser",
		Description:  s.extractDescription(content),
		Tags:         s.extractTags(content),
	}
}

// extractDependencies is RuleParserService._extract_dependencies.
func (s *RuleParserService) extractDependencies(content string) []string {
	set := newSet()
	for _, re := range []*regexp.Regexp{ruleImportRe, ruleIncludeRe, ruleImport2Re, ruleRequireRe, ruleFileRefRe} {
		for _, m := range re.FindAllStringSubmatch(content, -1) {
			set.add(m[1])
		}
	}
	return set.items
}

// classifyRuleType is RuleParserService._classify_rule_type.
func (s *RuleParserService) classifyRuleType(filePath, content string) value_objects.RuleType {
	pathStr := value_objects.PyLower(filePath)
	contentLower := value_objects.PyLower(content)

	switch {
	case strings.Contains(pathStr, "core") || strings.Contains(pathStr, "system"):
		return value_objects.RuleTypeCore
	case strings.Contains(pathStr, "workflow") || strings.Contains(pathStr, "process"):
		return value_objects.RuleTypeWorkflow
	case strings.Contains(pathStr, "agent"):
		return value_objects.RuleTypeAgent
	case strings.Contains(pathStr, "project"):
		return value_objects.RuleTypeProject
	case strings.Contains(pathStr, "context"):
		return value_objects.RuleTypeContext
	}

	switch {
	case containsWord(contentLower, "core", "system", "essential"):
		return value_objects.RuleTypeCore
	case containsWord(contentLower, "workflow", "process", "pipeline"):
		return value_objects.RuleTypeWorkflow
	case containsWord(contentLower, "agent", "bot", "assistant"):
		return value_objects.RuleTypeAgent
	case containsWord(contentLower, "project", "repository"):
		return value_objects.RuleTypeProject
	case containsWord(contentLower, "context", "environment"):
		return value_objects.RuleTypeContext
	}
	return value_objects.RuleTypeCustom
}

func containsWord(haystack string, words ...string) bool {
	for _, w := range words {
		if strings.Contains(haystack, w) {
			return true
		}
	}
	return false
}

// extractDescription is RuleParserService._extract_description.
func (s *RuleParserService) extractDescription(content string) string {
	lines := strings.Split(content, "\n")
	if strings.HasPrefix(content, frontmatterDel) {
		for _, line := range lines[1:] {
			if value_objects.PyStrip(line) == frontmatterDel {
				break
			}
			if strings.HasPrefix(value_objects.PyStrip(line), "description:") {
				parts := strings.SplitN(line, ":", 2)
				if len(parts) == 2 {
					return strings.Trim(value_objects.PyStrip(parts[1]), "\"'")
				}
			}
		}
	}
	for _, rawLine := range lines {
		line := value_objects.PyStrip(rawLine)
		if line != "" && !strings.HasPrefix(line, "#") && !strings.HasPrefix(line, "//") {
			if len(line) > 20 {
				if len([]rune(line)) > 200 {
					return string([]rune(line)[:200]) + "..."
				}
				return line
			}
		}
	}
	return ""
}

// extractTags is RuleParserService._extract_tags.
func (s *RuleParserService) extractTags(content string) []string {
	set := newSet()
	if strings.HasPrefix(content, frontmatterDel) {
		lines := strings.Split(content, "\n")
		frontmatterEnd := -1
		for i, line := range lines[1:] {
			if value_objects.PyStrip(line) == frontmatterDel {
				frontmatterEnd = i + 1
				break
			}
		}
		if frontmatterEnd > 0 {
			frontmatterContent := strings.Join(lines[1:frontmatterEnd], "\n")
			if parsed, err := entities.LoadYAML([]byte(frontmatterContent)); err == nil {
				if m, ok := parsed.(*entities.OrderedMap[any]); ok {
					if tagsValue, ok := m.Get("tags"); ok {
						switch tv := tagsValue.(type) {
						case []any:
							for _, item := range tv {
								set.add(value_objects.PyStr(item))
							}
						case string:
							set.add(tv)
						}
					}
				}
			}
		}
	}
	for _, m := range hashtagRe.FindAllStringSubmatch(content, -1) {
		set.add(m[1])
	}
	return set.items
}

// parseMDC is RuleParserService._parse_mdc (MDC is markdown with metadata).
func (s *RuleParserService) parseMDC(content string) ruleParseResult {
	return s.parseMarkdown(content)
}

// parseMarkdown is RuleParserService._parse_markdown, including the YAML frontmatter.
func (s *RuleParserService) parseMarkdown(content string) ruleParseResult {
	parsedContent := newOrderedAny()
	sections := newOrderedAny()
	references := []string{}
	variables := newOrderedAny()

	lines := strings.Split(content, "\n")

	if strings.HasPrefix(content, frontmatterDel) {
		frontmatterEnd := -1
		for i, line := range lines[1:] {
			if value_objects.PyStrip(line) == frontmatterDel {
				frontmatterEnd = i + 1
				break
			}
		}
		if frontmatterEnd > 0 {
			frontmatterContent := strings.Join(lines[1:frontmatterEnd], "\n")
			if parsed, err := entities.LoadYAML([]byte(frontmatterContent)); err == nil {
				if m, ok := parsed.(*entities.OrderedMap[any]); ok {
					for _, key := range m.Keys() {
						value, _ := m.Get(key)
						parsedContent.Set(key, value)
					}
					if v, ok := m.Get("variables"); ok {
						if vm, ok := v.(*entities.OrderedMap[any]); ok {
							for _, key := range vm.Keys() {
								value, _ := vm.Get(key)
								variables.Set(key, value)
							}
						}
					}
				}
			}
			if frontmatterEnd+1 <= len(lines) {
				lines = lines[frontmatterEnd+1:]
			} else {
				lines = nil
			}
		}
	}

	currentSection := ""
	var currentContent []string
	for _, line := range lines {
		if strings.HasPrefix(line, "#") {
			if currentSection != "" {
				sections.Set(currentSection, value_objects.PyStrip(strings.Join(currentContent, "\n")))
			}
			currentSection = value_objects.PyStrip(strings.TrimLeft(line, "#"))
			currentContent = nil
			continue
		}
		if currentSection != "" {
			currentContent = append(currentContent, line)
		}
		if strings.Contains(line, "[[") && strings.Contains(line, "]]") {
			for _, m := range wikiRefRe.FindAllStringSubmatch(line, -1) {
				references = append(references, m[1])
			}
		}
		if strings.Contains(line, "{{") && strings.Contains(line, "}}") {
			for _, m := range mustache2Re.FindAllStringSubmatch(line, -1) {
				varName := value_objects.PyStrip(m[1])
				if !variables.Has(varName) {
					variables.Set(varName, nil)
				}
			}
		}
	}
	if currentSection != "" {
		sections.Set(currentSection, value_objects.PyStrip(strings.Join(currentContent, "\n")))
	}
	if sections.Len() == 0 {
		sections.Set("content", content)
	}

	parsedContent.Set("sections", sections)
	parsedContent.Set("variables", variables)
	return ruleParseResult{content: parsedContent, sections: sections, references: references, variables: variables}
}

// parseJSON is RuleParserService._parse_json. Invalid JSON is a ValueError.
func (s *RuleParserService) parseJSON(content string) (ruleParseResult, error) {
	parsed, err := entities.DecodeJSON([]byte(content))
	if err != nil {
		return ruleParseResult{}, &value_objects.ValueError{Msg: "Invalid JSON content: " + err.Error()}
	}
	root := asOrderedMapAny(parsed).Copy()
	sections := newOrderedAny()
	if v, ok := root.Get("sections"); ok {
		sections = asOrderedMapAny(v).Copy()
	}
	variables := newOrderedAny()
	if v, ok := root.Get("variables"); ok {
		variables = asOrderedMapAny(v).Copy()
	}
	references := []string{}

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
				extractRefs(value, newPath)
			}
		case []any:
			for _, item := range v {
				extractRefs(item, path)
			}
		case string:
			if strings.Contains(v, "[[") && strings.Contains(v, "]]") {
				for _, m := range wikiRefRe.FindAllStringSubmatch(v, -1) {
					references = append(references, m[1])
				}
			}
		}
	}
	extractRefs(parsed, "")

	return ruleParseResult{content: root, sections: sections, references: references, variables: variables}, nil
}

// parseYAML is RuleParserService._parse_yaml. Invalid YAML is a ValueError.
func (s *RuleParserService) parseYAML(content string) (ruleParseResult, error) {
	parsed, err := entities.LoadYAML([]byte(content))
	if err != nil {
		return ruleParseResult{}, &value_objects.ValueError{Msg: "Invalid YAML content: " + err.Error()}
	}
	root, isMap := parsed.(*entities.OrderedMap[any])
	if !isMap {
		root = entities.NewOrderedMap[any]()
		root.Set("content", parsed)
	}

	sections := newOrderedAny()
	if v, ok := root.Get("sections"); ok {
		sections = asOrderedMapAny(v).Copy()
	}
	variables := newOrderedAny()
	if v, ok := root.Get("variables"); ok {
		variables = asOrderedMapAny(v).Copy()
	}
	references := []string{}

	var extractRefs func(obj any)
	extractRefs = func(obj any) {
		switch v := obj.(type) {
		case *entities.OrderedMap[any]:
			for _, key := range v.Keys() {
				value, _ := v.Get(key)
				extractRefs(value)
			}
		case []any:
			for _, item := range v {
				extractRefs(item)
			}
		case string:
			if strings.Contains(v, "[[") && strings.Contains(v, "]]") {
				for _, m := range wikiRefRe.FindAllStringSubmatch(v, -1) {
					references = append(references, m[1])
				}
			}
		}
	}
	extractRefs(root)

	return ruleParseResult{content: root, sections: sections, references: references, variables: variables}, nil
}

// parseText is RuleParserService._parse_text.
func (s *RuleParserService) parseText(content string) ruleParseResult {
	parsedContent := newOrderedAny()
	parsedContent.Set("content", content)
	sections := newOrderedAny()
	sections.Set("content", content)
	references := []string{}
	variables := newOrderedAny()

	if strings.Contains(content, "[[") && strings.Contains(content, "]]") {
		for _, m := range wikiRefRe.FindAllStringSubmatch(content, -1) {
			references = append(references, m[1])
		}
	}
	for _, line := range strings.Split(content, "\n") {
		if m := varAssignRe.FindStringSubmatch(value_objects.PyStrip(line)); m != nil {
			variables.Set(m[1], strings.Trim(value_objects.PyStrip(m[2]), "\"'"))
		}
	}
	return ruleParseResult{content: parsedContent, sections: sections, references: references, variables: variables}
}

// set is a small insertion-ordered string set matching list(set(...)) membership.
type set struct{ items []string }

func newSet() *set { return &set{} }

func (s *set) add(v string) {
	for _, x := range s.items {
		if x == v {
			return
		}
	}
	s.items = append(s.items, v)
}

func asOrderedMapAny(v any) *entities.OrderedMap[any] {
	if om, ok := v.(*entities.OrderedMap[any]); ok {
		return om
	}
	return entities.NewOrderedMap[any]()
}

// newOrderedAny is a helper for building the dict-shaped results.
func newOrderedAny() *entities.OrderedMap[any] { return entities.NewOrderedMap[any]() }

func asOrderedMapString(v any) *entities.OrderedMap[string] {
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
