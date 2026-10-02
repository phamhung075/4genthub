// Package services ports agent_management/application/services (the application-layer
// services; the domain services live in domain/services).
package services

import (
	"os"
	"path/filepath"
	"sort"
	"strings"

	amentities "agenthub/fastmcp/agent_management/domain/entities"
	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// YAMLAgentTemplateLoader loads agent templates from agent-library YAML files.
type YAMLAgentTemplateLoader struct {
	AgentLibraryPath string
	AgentsPath       string
}

// NewYAMLAgentTemplateLoader validates that the agents directory exists.
func NewYAMLAgentTemplateLoader(agentLibraryPath string) (*YAMLAgentTemplateLoader, error) {
	loader := &YAMLAgentTemplateLoader{
		AgentLibraryPath: agentLibraryPath,
		AgentsPath:       filepath.Join(agentLibraryPath, "agents"),
	}
	if _, err := os.Stat(loader.AgentsPath); err != nil {
		return nil, tmvo.ValueErrorf("Agent library path not found: %s", loader.AgentsPath)
	}
	return loader, nil
}

// LoadAllAgents loads every agent directory, skipping directories that fail to load.
func (l *YAMLAgentTemplateLoader) LoadAllAgents() []*amentities.AgentTemplate {
	templates := []*amentities.AgentTemplate{}
	entries, err := os.ReadDir(l.AgentsPath)
	if err != nil {
		return templates
	}
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		template, err := l.LoadAgent(filepath.Join(l.AgentsPath, entry.Name()))
		if err != nil {
			continue
		}
		templates = append(templates, template)
	}
	return templates
}

// LoadAgent loads a single agent template from its directory.
func (l *YAMLAgentTemplateLoader) LoadAgent(agentDir string) (*amentities.AgentTemplate, error) {
	configData := l.loadYAML(filepath.Join(agentDir, "config.yaml"), false)
	agentInfo := nestedMap(configData, "agent_info")
	capabilitiesData := l.loadYAML(filepath.Join(agentDir, "capabilities.yaml"), false)

	slugValue, _ := agentInfo.Get("slug")
	slug, ok := slugValue.(string)
	if !ok {
		return nil, tmvo.TypeErrorf("'NoneType' object has no attribute 'replace'")
	}
	slugUnderscored := strings.ReplaceAll(slug, "-", "_")
	instructionsData := l.loadYAML(filepath.Join(agentDir, "contexts", slugUnderscored+"_instructions.yaml"), false)
	systemPrompt := mapStringDefault(instructionsData, "custom_instructions", "")

	rules := l.LoadRules(filepath.Join(agentDir, "rules"))

	outputFormatFile := filepath.Join(agentDir, "output_format", "output_specification.yaml")
	var outputFormat *tmentities.OrderedMap[any]
	if _, err := os.Stat(outputFormatFile); err == nil {
		outputFormatData := l.loadYAML(outputFormatFile, false)
		if v, ok := outputFormatData.Get("output_specification"); ok {
			if m, isMap := v.(*tmentities.OrderedMap[any]); isMap {
				outputFormat = m
			}
		}
	}

	metadataData := l.loadYAML(filepath.Join(agentDir, "metadata.yaml"), true)
	tools := extractTools(capabilitiesData)
	capabilitiesObj := buildCapabilitiesObject(capabilitiesData)

	// Python passes the list of rule dicts into a tuple[str, ...] field (no runtime
	// check). The Go AgentConfiguration.Rules is []string, so each rule dict is
	// JSON-encoded to a string; this is the one place the data shape diverges.
	rulesForConfig := make([]string, 0, len(rules))
	for _, rule := range rules {
		encoded, err := tmvo.PyJSONDumpsCompact(rule)
		if err != nil {
			return nil, err
		}
		rulesForConfig = append(rulesForConfig, encoded)
	}
	configuration, err := amvo.NewAgentConfiguration(systemPrompt, tools, capabilitiesObj, rulesForConfig, outputFormat, metadataData)
	if err != nil {
		return nil, err
	}

	templateMetadata := tmentities.NewOrderedMap[any]()
	templateMetadata.Set("source", "agent-library")
	templateMetadata.Set("migration_date", mapValueOrNil(agentInfo, "migration_date"))
	templateMetadata.Set("usage_scenarios", mapValueOrNil(agentInfo, "usage_scenarios"))
	templateMetadata.Set("author", mapStringDefault(agentInfo, "author", "agenthub"))
	if metadataData != nil {
		for _, k := range metadataData.Keys() {
			v, _ := metadataData.Get(k)
			templateMetadata.Set(k, v)
		}
	}

	templateID := amvo.GenerateNewAgentTemplateId()
	template := amentities.DefaultAgentTemplate()
	template.ID = &templateID
	template.Slug = slug
	template.Name = mapStringDefault(agentInfo, "name", slug)
	template.Description = mapStringDefault(agentInfo, "description", "")
	template.Category = mapStringDefault(agentInfo, "category", "general")
	template.Version = mapStringDefault(agentInfo, "version", "1.0.0")
	template.DefaultConfiguration = &configuration
	template.Metadata = templateMetadata
	return amentities.NewAgentTemplate(template)
}

// LoadRules loads rules/*.yaml (sorted by filename) as {"name","content"} dicts; nil when
// the directory is missing or empty.
func (l *YAMLAgentTemplateLoader) LoadRules(rulesDir string) []any {
	if _, err := os.Stat(rulesDir); err != nil {
		return nil
	}
	entries, err := os.ReadDir(rulesDir)
	if err != nil {
		return nil
	}
	names := []string{}
	for _, entry := range entries {
		if !entry.IsDir() && strings.HasSuffix(entry.Name(), ".yaml") {
			names = append(names, entry.Name())
		}
	}
	sort.Strings(names)
	rules := []any{}
	for _, name := range names {
		ruleData := l.loadYAML(filepath.Join(rulesDir, name), false)
		rule := tmentities.NewOrderedMap[any]()
		rule.Set("name", strings.TrimSuffix(name, ".yaml"))
		rule.Set("content", ruleData)
		rules = append(rules, rule)
	}
	if len(rules) == 0 {
		return nil
	}
	return rules
}

// loadYAML returns {} on a missing file or parse error, like the Python loader.
func (l *YAMLAgentTemplateLoader) loadYAML(filePath string, multiDocument bool) *tmentities.OrderedMap[any] {
	raw, err := os.ReadFile(filePath)
	if err != nil {
		return tmentities.NewOrderedMap[any]()
	}
	if multiDocument {
		raw = firstYAMLDocument(raw)
	}
	loaded, err := tmentities.LoadYAML(raw)
	if err != nil || loaded == nil {
		return tmentities.NewOrderedMap[any]()
	}
	if m, ok := loaded.(*tmentities.OrderedMap[any]); ok {
		return m
	}
	return tmentities.NewOrderedMap[any]()
}

// firstYAMLDocument returns the first document of a multi-document YAML file.
func firstYAMLDocument(raw []byte) []byte {
	lines := strings.Split(string(raw), "\n")
	first := []string{}
	for _, line := range lines {
		if strings.TrimSpace(line) == "---" {
			if len(first) > 0 {
				break
			}
			continue
		}
		first = append(first, line)
	}
	return []byte(strings.Join(first, "\n"))
}

// extractTools reads mcp_tools.tools (a list of strings).
func extractTools(capabilitiesData *tmentities.OrderedMap[any]) []string {
	v, ok := capabilitiesData.Get("mcp_tools")
	if !ok {
		return []string{}
	}
	mcpTools, ok := v.(*tmentities.OrderedMap[any])
	if !ok {
		return []string{}
	}
	toolsValue, ok := mcpTools.Get("tools")
	if !ok {
		return []string{}
	}
	list, ok := toolsValue.([]any)
	if !ok {
		return []string{}
	}
	tools := make([]string, 0, len(list))
	for _, item := range list {
		if s, isStr := item.(string); isStr {
			tools = append(tools, s)
		}
	}
	return tools
}

// buildCapabilitiesObject builds the structured capabilities dict in Python key order.
func buildCapabilitiesObject(capabilitiesData *tmentities.OrderedMap[any]) *tmentities.OrderedMap[any] {
	out := tmentities.NewOrderedMap[any]()
	for _, key := range []string{"file_operations", "command_execution", "mcp_tools", "collaboration"} {
		out.Set(key, mapValueOrEmpty(capabilitiesData, key))
	}
	return out
}

func nestedMap(m *tmentities.OrderedMap[any], key string) *tmentities.OrderedMap[any] {
	if v, ok := m.Get(key); ok {
		if child, isMap := v.(*tmentities.OrderedMap[any]); isMap {
			return child
		}
	}
	return tmentities.NewOrderedMap[any]()
}

// mapValueOrEmpty is Python m.get(key, {}).
func mapValueOrEmpty(m *tmentities.OrderedMap[any], key string) any {
	if m == nil {
		return tmentities.NewOrderedMap[any]()
	}
	if v, ok := m.Get(key); ok {
		return v
	}
	return tmentities.NewOrderedMap[any]()
}

// mapValueOrNil is Python m.get(key) (missing -> None).
func mapValueOrNil(m *tmentities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	if v, ok := m.Get(key); ok {
		return v
	}
	return nil
}

func mapStringDefault(m *tmentities.OrderedMap[any], key, def string) string {
	if m == nil {
		return def
	}
	if v, ok := m.Get(key); ok {
		if s, isStr := v.(string); isStr {
			return s
		}
	}
	return def
}
