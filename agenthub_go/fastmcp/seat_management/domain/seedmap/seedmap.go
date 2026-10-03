// Package seedmap builds seat-type seed modules from a seat-type spec.
package seedmap

import (
	"regexp"
	"strings"

	"agenthub/fastmcp/seat_management/domain/resolver"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

const seedVersion = "1.0.0"

type SeedModule struct {
	Slug    string
	Kind    resolver.ModuleKind
	Version string
	Content string
}

// Rule is one named rule of a seat type.
type Rule struct {
	Name    string
	Content string
}

// Spec is the declarative definition of a seat type.
type Spec struct {
	Slug           string
	Name           string
	Description    string
	DefaultRuntime string
	Role           string
	Rules          []Rule
	OutputFormat   string
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

// FromSpec turns a seat-type spec into a seed: a role instruction module, one
// instruction module per rule, and the output format as a document module.
func FromSpec(spec Spec) (Seed, error) {
	role := strings.TrimSpace(spec.Role)
	if role == "" {
		return Seed{}, tmvo.ValueErrorf("seat type %q has an empty role", spec.Slug)
	}
	outputFormat := strings.TrimSpace(spec.OutputFormat)
	if outputFormat == "" {
		return Seed{}, tmvo.ValueErrorf("seat type %q has an empty output format", spec.Slug)
	}

	seed := Seed{
		SeatTypeSlug:   spec.Slug,
		SeatTypeName:   spec.Name,
		Description:    spec.Description,
		DefaultRuntime: spec.DefaultRuntime,
		Version:        seedVersion,
	}
	seed.Modules = append(seed.Modules, SeedModule{
		Slug: spec.Slug + "-role", Kind: resolver.KindInstruction, Version: seedVersion, Content: role,
	})

	seenRules := make(map[string]bool, len(spec.Rules))
	for _, rule := range spec.Rules {
		normalised := normaliseRuleName(rule.Name)
		if normalised == "" {
			return Seed{}, tmvo.ValueErrorf("seat type %q: rule %q has an empty name", spec.Slug, rule.Name)
		}
		if seenRules[normalised] {
			return Seed{}, tmvo.ValueErrorf("seat type %q: duplicate rule name %q", spec.Slug, normalised)
		}
		seenRules[normalised] = true
		seed.Modules = append(seed.Modules, SeedModule{
			Slug:    spec.Slug + "-rule-" + normalised,
			Kind:    resolver.KindInstruction,
			Version: seedVersion,
			Content: "### " + rule.Name + "\n\n" + strings.TrimSpace(rule.Content) + "\n",
		})
	}

	seed.Modules = append(seed.Modules, SeedModule{
		Slug: spec.Slug + "-output-format", Kind: resolver.KindDocument, Version: seedVersion, Content: outputFormat + "\n",
	})

	// Tool modules are Claude settings JSON merged by the renderer, so the seed creates none.

	seed.ModuleRefs = make([]resolver.ModuleRef, len(seed.Modules))
	for i, module := range seed.Modules {
		seed.ModuleRefs[i] = resolver.ModuleRef{Slug: module.Slug, Version: module.Version}
	}
	return seed, nil
}
