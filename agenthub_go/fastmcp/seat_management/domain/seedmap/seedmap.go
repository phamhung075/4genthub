// Package seedmap maps 4genthub agent templates into seat-type seed modules.
package seedmap

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"

	amentities "agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/seat_management/domain/resolver"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"

	"gopkg.in/yaml.v3"
)

const (
	seedVersion    = "1.0.0"
	defaultRuntime = "claude-code"
)

type SeedModule struct {
	Slug    string
	Kind    resolver.ModuleKind
	Version string
	Content string
}

type Seed struct {
	Modules        []SeedModule
	SeatTypeSlug   string
	SeatTypeName   string
	Description    string
	DefaultRuntime string
	Version        string
	ModuleRefs     []resolver.ModuleRef
}

var ruleNameSeparator = regexp.MustCompile(`[^a-z0-9]+`)

// normaliseRuleName lowercases a rule name and collapses non [a-z0-9] runs to one dash.
func normaliseRuleName(name string) string {
	return strings.Trim(ruleNameSeparator.ReplaceAllString(strings.ToLower(name), "-"), "-")
}

// Map turns one agent template into a seat-type seed: a role instruction module, one
// instruction module per rule, and the output format as a document module.
func Map(template *amentities.AgentTemplate) (Seed, error) {
	if template == nil {
		return Seed{}, tmvo.ValueErrorf("template is nil")
	}
	if template.DefaultConfiguration == nil {
		return Seed{}, tmvo.ValueErrorf("template %q has no default configuration", template.Slug)
	}
	config := template.DefaultConfiguration
	prompt := strings.TrimSpace(config.SystemPrompt)
	if prompt == "" {
		return Seed{}, tmvo.ValueErrorf("template %q has an empty system prompt", template.Slug)
	}

	seed := Seed{
		SeatTypeSlug:   template.Slug,
		SeatTypeName:   template.Name,
		Description:    template.Description,
		DefaultRuntime: defaultRuntime,
		Version:        template.Version,
	}
	seed.Modules = append(seed.Modules, SeedModule{
		Slug: template.Slug + "-role", Kind: resolver.KindInstruction, Version: seedVersion, Content: prompt,
	})

	seenRules := make(map[string]bool, len(config.Rules))
	for _, raw := range config.Rules {
		name, body, err := decodeRule(raw)
		if err != nil {
			return Seed{}, fmt.Errorf("template %q: %w", template.Slug, err)
		}
		normalised := normaliseRuleName(name)
		if normalised == "" {
			return Seed{}, tmvo.ValueErrorf("template %q: rule %q has an empty name", template.Slug, name)
		}
		if seenRules[normalised] {
			return Seed{}, tmvo.ValueErrorf("template %q: duplicate rule name %q", template.Slug, normalised)
		}
		seenRules[normalised] = true
		seed.Modules = append(seed.Modules, SeedModule{
			Slug:    template.Slug + "-rule-" + normalised,
			Kind:    resolver.KindInstruction,
			Version: seedVersion,
			Content: "### " + name + "\n\n```yaml\n" + body + "```\n",
		})
	}

	if config.OutputFormat != nil && config.OutputFormat.Len() > 0 {
		body, err := orderedMapToYAML(config.OutputFormat)
		if err != nil {
			return Seed{}, fmt.Errorf("template %q: output format: %w", template.Slug, err)
		}
		seed.Modules = append(seed.Modules, SeedModule{
			Slug: template.Slug + "-output-format", Kind: resolver.KindDocument, Version: seedVersion,
			Content: "```yaml\n" + body + "```\n",
		})
	}

	// Tool modules are Claude settings JSON merged by the renderer, not content derived
	// from the agent's tools list, so the seed deliberately creates none.

	seed.ModuleRefs = make([]resolver.ModuleRef, len(seed.Modules))
	for i, module := range seed.Modules {
		seed.ModuleRefs[i] = resolver.ModuleRef{Slug: module.Slug, Version: module.Version}
	}
	return seed, nil
}

// MapAll maps every template, failing on the first error and on any module slug shared
// by two seeds.
func MapAll(templates []*amentities.AgentTemplate) ([]Seed, error) {
	seeds := make([]Seed, 0, len(templates))
	owner := make(map[string]string)
	for _, template := range templates {
		slug := "<nil>"
		if template != nil {
			slug = template.Slug
		}
		seed, err := Map(template)
		if err != nil {
			return nil, fmt.Errorf("map agent template %q: %w", slug, err)
		}
		for _, module := range seed.Modules {
			if previous, ok := owner[module.Slug]; ok {
				return nil, fmt.Errorf("duplicate module slug %q produced by seat types %q and %q", module.Slug, previous, seed.SeatTypeSlug)
			}
			owner[module.Slug] = seed.SeatTypeSlug
		}
		seeds = append(seeds, seed)
	}
	return seeds, nil
}

// decodeRule and orderedMapToYAML are minimal re-implementations of the renderer's
// unexported helpers (the renderer stays untouched) and must stay byte-compatible.
func decodeRule(raw string) (name, body string, err error) {
	var rule struct {
		Name    string `json:"name"`
		Content any    `json:"content"`
	}
	if err := json.Unmarshal([]byte(raw), &rule); err != nil {
		return "", "", fmt.Errorf("decode rule: %w", err)
	}
	encoded, err := yaml.Marshal(rule.Content)
	if err != nil {
		return "", "", fmt.Errorf("encode rule %q: %w", rule.Name, err)
	}
	return rule.Name, string(encoded), nil
}

func orderedMapToYAML(m any) (string, error) {
	encoded, err := tmvo.PyJSONDumpsCompact(m)
	if err != nil {
		return "", err
	}
	var decoded any
	if err := json.Unmarshal([]byte(encoded), &decoded); err != nil {
		return "", err
	}
	out, err := yaml.Marshal(decoded)
	if err != nil {
		return "", err
	}
	return string(out), nil
}
