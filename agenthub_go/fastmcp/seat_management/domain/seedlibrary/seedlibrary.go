// Package seedlibrary loads the seat types embedded in the binary.
package seedlibrary

import (
	"bytes"
	"embed"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"regexp"
	"sort"
	"strings"

	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/seedmap"

	"gopkg.in/yaml.v3"
)

//go:embed seat-types/*.yaml shared-modules/*
var embedded embed.FS

const (
	seatTypesDir     = "seat-types"
	sharedModulesDir = "shared-modules"
)

// sharedModuleFiles lists the modules every seat type carries: slug, kind and the file in
// shared-modules/ that holds the content. comm-guard is the Claude settings fragment that
// denies direct messaging commands; comm-guard-skill tells the seat what to use instead.
var sharedModuleFiles = []struct {
	slug string
	kind resolver.ModuleKind
	file string
}{
	{"comm-guard", resolver.KindTool, "comm-guard.json"},
	{"comm-guard-skill", resolver.KindSkill, "comm-guard-skill.md"},
}

var (
	slugPattern = regexp.MustCompile(`^[a-z][a-z0-9-]*$`)
	runtimes    = map[string]bool{"claude-code": true, "codex": true}
)

type ruleFile struct {
	Name    string `yaml:"name"`
	Content string `yaml:"content"`
}

type seatTypeFile struct {
	Slug           string     `yaml:"slug"`
	Name           string     `yaml:"name"`
	Description    string     `yaml:"description"`
	DefaultRuntime string     `yaml:"default_runtime"`
	Role           string     `yaml:"role"`
	Rules          []ruleFile `yaml:"rules"`
	OutputFormat   string     `yaml:"output_format"`
}

// Load returns the seeds of the embedded seat types, sorted by slug.
func Load() ([]seedmap.Seed, error) {
	return LoadFS(embedded)
}

// LoadFS parses every seat-types/*.yaml of fsys; slugs must be unique across files.
func LoadFS(fsys fs.FS) ([]seedmap.Seed, error) {
	names, err := fs.Glob(fsys, seatTypesDir+"/*.yaml")
	if err != nil {
		return nil, err
	}
	shared, err := loadSharedModules(fsys)
	if err != nil {
		return nil, err
	}
	seeds := make([]seedmap.Seed, 0, len(names))
	owner := make(map[string]string, len(names))
	for _, name := range names {
		data, err := fs.ReadFile(fsys, name)
		if err != nil {
			return nil, err
		}
		seed, err := Parse(name, data, shared)
		if err != nil {
			return nil, err
		}
		if previous, ok := owner[seed.SeatTypeSlug]; ok {
			return nil, fmt.Errorf("%s: slug %q already defined in %s", name, seed.SeatTypeSlug, previous)
		}
		owner[seed.SeatTypeSlug] = name
		seeds = append(seeds, seed)
	}
	sort.Slice(seeds, func(i, j int) bool { return seeds[i].SeatTypeSlug < seeds[j].SeatTypeSlug })
	return seeds, nil
}

func loadSharedModules(fsys fs.FS) ([]seedmap.SeedModule, error) {
	modules := make([]seedmap.SeedModule, 0, len(sharedModuleFiles))
	for _, f := range sharedModuleFiles {
		data, err := fs.ReadFile(fsys, sharedModulesDir+"/"+f.file)
		if err != nil {
			return nil, err
		}
		modules = append(modules, seedmap.SeedModule{Slug: f.slug, Kind: f.kind, Content: string(data)})
	}
	return modules, nil
}

// Parse decodes one seat-type file strictly and builds its seed, which also carries the shared
// modules; errors name the file and field.
func Parse(name string, data []byte, shared []seedmap.SeedModule) (seedmap.Seed, error) {
	var file seatTypeFile
	decoder := yaml.NewDecoder(bytes.NewReader(data))
	decoder.KnownFields(true)
	if err := decoder.Decode(&file); err != nil {
		if errors.Is(err, io.EOF) {
			return seedmap.Seed{}, fmt.Errorf("%s: file is empty", name)
		}
		return seedmap.Seed{}, fmt.Errorf("%s: %w", name, err)
	}
	if !slugPattern.MatchString(file.Slug) {
		return seedmap.Seed{}, fmt.Errorf("%s: field slug %q must match %s", name, file.Slug, slugPattern)
	}
	if strings.TrimSpace(file.Name) == "" {
		return seedmap.Seed{}, fmt.Errorf("%s: field name is empty", name)
	}
	if !runtimes[file.DefaultRuntime] {
		return seedmap.Seed{}, fmt.Errorf("%s: field default_runtime %q must be claude-code or codex", name, file.DefaultRuntime)
	}
	spec := seedmap.Spec{
		Slug: file.Slug, Name: file.Name, Description: file.Description, DefaultRuntime: file.DefaultRuntime,
		Role: file.Role, OutputFormat: file.OutputFormat, Shared: shared,
	}
	for i, rule := range file.Rules {
		if strings.TrimSpace(rule.Content) == "" {
			return seedmap.Seed{}, fmt.Errorf("%s: field rules[%d].content is empty", name, i)
		}
		spec.Rules = append(spec.Rules, seedmap.Rule{Name: rule.Name, Content: rule.Content})
	}
	seed, err := seedmap.FromSpec(spec)
	if err != nil {
		return seedmap.Seed{}, fmt.Errorf("%s: %w", name, err)
	}
	return seed, nil
}
