// Package seedmap builds seat-type seed modules from a seat-type spec.
package seedmap

import (
	"regexp"
	"strings"

	"agenthub/fastmcp/seat_management/domain/resolver"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// seedVersion is bumped whenever a seed's module set changes: a stored seat type version is
// immutable, so a changed module set needs a new version. 1.4.7 is the owner's short-pointers
// rule, added to the seat guide beside the work-first rule: a seat thinks in short pointers and
// gives the result first, then at most five short lines, and pastes no large tool output or whole
// file into a thought or a row. 1.4.6 is the owner's work-first rule
// written into the seat guide: the work is build, improve and fix; the queue carries an idea, a
// finding, a ruling and a status; `CHANGELOG/` and `TEST-CHANGELOG.md` are written once, when a
// task is done, beside the code they describe; and a doc sweep is not a task unless the owner asks
// for one. 1.4.5 is the retirement of the checker's send verb: the comm-guard allow list drops its
// entry for it and the guard skill now names `4genteam send`. The deny list and
// `Bash(4genteam whoami:*)` are unchanged.
const seedVersion = "1.4.7"

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
	// Shared modules are appended to the seat type's own modules, whatever its default runtime:
	// the runtime of the seat decides at render time which of them apply.
	Shared []SeedModule
	// Blocks are the MCP server blocks this seat type mounts, appended after the shared
	// modules. A block is content of kind mcp; a seat with no block mounts no server.
	Blocks []SeedModule
	// ExtraRefs are module refs the seat type version carries but the seed does not author:
	// the curated catalog skills the seat is composed from. They are appended to ModuleRefs
	// after the refs of the modules above, so the seat arrives with its skills attached.
	ExtraRefs []resolver.ModuleRef
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

	for _, shared := range spec.Shared {
		shared.Version = seedVersion
		seed.Modules = append(seed.Modules, shared)
	}

	for _, block := range spec.Blocks {
		block.Version = seedVersion
		seed.Modules = append(seed.Modules, block)
	}

	seed.ModuleRefs = make([]resolver.ModuleRef, len(seed.Modules))
	for i, module := range seed.Modules {
		seed.ModuleRefs[i] = resolver.ModuleRef{Slug: module.Slug, Version: module.Version}
	}
	seed.ModuleRefs = append(seed.ModuleRefs, spec.ExtraRefs...)
	return seed, nil
}
