package entities

import "agenthub/fastmcp/task_management/domain/value_objects"

// Port of rule_entity.py. Its types own the plain names (consumers: rule_repository,
// rule_composition_service, create_rule, rule_parser_service, rule_value_objects);
// rule_content.go repeats them with the RuleContent prefix.

func containsStr(list []string, s string) bool {
	for _, x := range list {
		if x == s {
			return true
		}
	}
	return false
}

func removeStr(list []string, s string) []string {
	for i, x := range list {
		if x == s {
			return append(list[:i], list[i+1:]...)
		}
	}
	return list
}

// RuleMetadata is rule_entity.RuleMetadata (uses the value_objects enums).
type RuleMetadata struct {
	Path         string
	Format       value_objects.RuleFormat
	Type         value_objects.RuleType
	Size         int
	Modified     float64
	Checksum     string
	Dependencies []string
	Author       string // default "system"
	Version      string // default "1.0"
	Description  string
	Tags         []string
}

// NewRuleMetadata applies the Python defaults (author "system", version "1.0", empty tags).
func NewRuleMetadata(path string, format value_objects.RuleFormat, typ value_objects.RuleType,
	size int, modified float64, checksum string, dependencies []string) *RuleMetadata {
	return &RuleMetadata{Path: path, Format: format, Type: typ, Size: size, Modified: modified,
		Checksum: checksum, Dependencies: dependencies, Author: "system", Version: "1.0", Tags: []string{}}
}

func (m *RuleMetadata) AddTag(tag string) {
	if !containsStr(m.Tags, tag) {
		m.Tags = append(m.Tags, tag)
	}
}
func (m *RuleMetadata) RemoveTag(tag string)   { m.Tags = removeStr(m.Tags, tag) }
func (m *RuleMetadata) HasTag(tag string) bool { return containsStr(m.Tags, tag) }
func (m *RuleMetadata) AddDependency(d string) {
	if !containsStr(m.Dependencies, d) {
		m.Dependencies = append(m.Dependencies, d)
	}
}
func (m *RuleMetadata) RemoveDependency(d string) {
	m.Dependencies = removeStr(m.Dependencies, d)
}
func (m *RuleMetadata) HasDependency(d string) bool { return containsStr(m.Dependencies, d) }

// RuleContent is rule_entity.RuleContent (no validation).
type RuleContent struct {
	Metadata      *RuleMetadata
	RawContent    string
	ParsedContent *OrderedMap[any]    // Python dict: insertion order is observable
	Sections      *OrderedMap[string] // section name -> content, in insertion order
	References    []string
	Variables     *OrderedMap[any]
}

// GetSection returns a section, or false when absent.
func (c *RuleContent) GetSection(name string) (string, bool) {
	return c.Sections.Get(name)
}
func (c *RuleContent) SetSection(name, content string) { c.Sections.Set(name, content) }
func (c *RuleContent) HasSection(name string) bool     { return c.Sections.Has(name) }

// GetVariable returns a variable or def when absent.
func (c *RuleContent) GetVariable(name string, def any) any {
	if v, ok := c.Variables.Get(name); ok {
		return v
	}
	return def
}
func (c *RuleContent) SetVariable(name string, v any) { c.Variables.Set(name, v) }
func (c *RuleContent) HasVariable(name string) bool   { return c.Variables.Has(name) }
func (c *RuleContent) AddReference(ref string) {
	if !containsStr(c.References, ref) {
		c.References = append(c.References, ref)
	}
}
func (c *RuleContent) RemoveReference(ref string) {
	c.References = removeStr(c.References, ref)
}
func (c *RuleContent) HasReference(ref string) bool         { return containsStr(c.References, ref) }
func (c *RuleContent) RulePath() string                     { return c.Metadata.Path }
func (c *RuleContent) RuleType() value_objects.RuleType     { return c.Metadata.Type }
func (c *RuleContent) RuleFormat() value_objects.RuleFormat { return c.Metadata.Format }

// RuleInheritance is rule_entity.RuleInheritance.
type RuleInheritance struct {
	ParentPath         string
	ChildPath          string
	InheritanceType    value_objects.InheritanceType
	InheritedSections  []string
	OverriddenSections []string
	MergedVariables    map[string]any
	InheritanceDepth   int
	Conflicts          []string
}

// NewRuleInheritance applies the Python defaults (empty collections, depth 0).
func NewRuleInheritance(parent, child string, t value_objects.InheritanceType) *RuleInheritance {
	return &RuleInheritance{ParentPath: parent, ChildPath: child, InheritanceType: t,
		InheritedSections: []string{}, OverriddenSections: []string{}, MergedVariables: map[string]any{}, Conflicts: []string{}}
}

func (r *RuleInheritance) AddInheritedSection(s string) {
	if !containsStr(r.InheritedSections, s) {
		r.InheritedSections = append(r.InheritedSections, s)
	}
}
func (r *RuleInheritance) AddOverriddenSection(s string) {
	if !containsStr(r.OverriddenSections, s) {
		r.OverriddenSections = append(r.OverriddenSections, s)
	}
}
func (r *RuleInheritance) AddConflict(c string) {
	if !containsStr(r.Conflicts, c) {
		r.Conflicts = append(r.Conflicts, c)
	}
}
func (r *RuleInheritance) HasConflicts() bool { return len(r.Conflicts) > 0 }
func (r *RuleInheritance) IsSectionInherited(s string) bool {
	return containsStr(r.InheritedSections, s)
}
func (r *RuleInheritance) IsSectionOverridden(s string) bool {
	return containsStr(r.OverriddenSections, s)
}
func (r *RuleInheritance) MergeVariable(key string, v any) { r.MergedVariables[key] = v }
func (r *RuleInheritance) GetMergedVariable(key string, def any) any {
	if v, ok := r.MergedVariables[key]; ok {
		return v
	}
	return def
}

// Rule pairs metadata with optional content and inheritance.
type Rule struct {
	Metadata    *RuleMetadata
	Content     *RuleContent
	Inheritance *RuleInheritance
}

// NewRule creates an empty content object when content is nil (Python __post_init__).
func NewRule(metadata *RuleMetadata, content *RuleContent, inheritance *RuleInheritance) *Rule {
	if content == nil {
		content = &RuleContent{Metadata: metadata, ParsedContent: NewOrderedMap[any](), Sections: NewOrderedMap[string](),
			References: []string{}, Variables: NewOrderedMap[any]()}
	}
	return &Rule{metadata, content, inheritance}
}
