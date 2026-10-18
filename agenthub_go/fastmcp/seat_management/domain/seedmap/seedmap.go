// Package seedmap builds seat-type seed modules from a seat-type spec.
package seedmap

import (
	"regexp"
	"strings"

	"agenthub/fastmcp/seat_management/domain/resolver"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// seedVersion is bumped whenever a seed's module set changes: a stored seat type version is
// immutable, so a changed module set needs a new version. 1.4.15 makes the comm-guard deny list bind unaudited routes only - `4genteam input`, `tmux send-keys`, `tmux paste-buffer` - and allows `4genteam send` by name, because that is the audited path the guard skill names and denying it denied the only route a seat may send over. 1.4.14 states guide-common.md's queue-row caps as the CLI enforces them - summary at most 120 characters, body at most 600, where the rule read as one 600-character row - and drops seat-friction-loop.md's `4genteam sync rig`, which no longer exists: the runtime installs the resolved skill tree under the seat's own `skills/` at every start. 1.4.13 restores guide-common.md's loop step 4 to the commit form the owner ruled fleet-wide: commit by pathspec and do not stage first, with git add -N only for a new file. 1.4.12 cuts shared-modules/guide-common.md to a short index (the loop, the five rules, stuck handling), drops its shared-tree commit, approval-gate, pytest and task-ritual sections, and moves the reviewer verdict into the task or queue row (no GATE file, no vite build). 1.4.11 moves the runtime-neutral note rule out
// of guide-writer.md and into shared-modules/guide-common.md's writing section, where every seat reads it:
// the rule covers every seat that writes a note, and guide-common.md is the cross-seat container, so
// guide-writer.md returns to its pre-1.4.10 content. 1.4.10 rehomes the rule the architect guide
// carried inside its tool list - "write notes that read the same to any runtime" - into guide-writer as
// its own workflow line; it had no other home in the shelf. 1.4.9 is the architect guide without the
// stale seating line ("You are the only seat here on claude-code; the rest run omp"): the room runs
// every seat on omp, so both halves were false, and a seating fact about one room does not belong in
// a role-scoped block. 1.4.8 names the `short-output` skill in the seat guide's output rule, so a seat loads the skill the client delivers. 1.4.7 is the owner's short-pointers
// rule, added to the seat guide beside the work-first rule: a seat thinks in short pointers and
// gives the result first, then at most five short lines, and pastes no large tool output or whole
// file into a thought or a row. 1.4.6 is the owner's work-first rule
// written into the seat guide: the work is build, improve and fix; the queue carries an idea, a
// finding, a ruling and a status; `CHANGELOG/` and `TEST-CHANGELOG.md` are written once, when a
// task is done, beside the code they describe; and a doc sweep is not a task unless the owner asks
// for one. 1.4.5 is the retirement of the checker's send verb: the comm-guard allow list drops its
// entry for it and the guard skill now names `4genteam send`. The deny list and
// `Bash(4genteam whoami:*)` are unchanged.
const seedVersion = "1.4.17"

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
