package entities

import (
	"time"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Port of rule_content.py (only consumer: infrastructure/parsers/rule_content_parser).
// Its RuleMetadata/RuleContent/RuleInheritance repeat names from rule_entity.go and
// carry the RuleContent prefix.

// RuleFormat (rule_content.RuleFormat; distinct from value_objects.RuleFormat).
type RuleFormat string

const (
	RuleFormatMdc  RuleFormat = "mdc"
	RuleFormatMd   RuleFormat = "md"
	RuleFormatJson RuleFormat = "json"
	RuleFormatYaml RuleFormat = "yaml"
	RuleFormatTxt  RuleFormat = "txt"
)

// RuleType (rule_content.RuleType; distinct from value_objects.RuleType).
type RuleType string

const (
	RuleTypeTask    RuleType = "task"
	RuleTypeContext RuleType = "context"
	RuleTypeConfig  RuleType = "config"
	RuleTypeAgent   RuleType = "agent"
	RuleTypeGeneral RuleType = "general"
)

// ConflictResolution (rule_content.ConflictResolution; distinct from value_objects.ConflictResolution).
type ConflictResolution string

const (
	ConflictResolutionOverride ConflictResolution = "override"
	ConflictResolutionMerge    ConflictResolution = "merge"
	ConflictResolutionSkip     ConflictResolution = "skip"
	ConflictResolutionPrompt   ConflictResolution = "prompt"
)

// InheritanceType (rule_content.InheritanceType; distinct from value_objects.InheritanceType).
type InheritanceType string

const (
	InheritanceTypeFull      InheritanceType = "full"
	InheritanceTypePartial   InheritanceType = "partial"
	InheritanceTypeOverride  InheritanceType = "override"
	InheritanceTypeExtension InheritanceType = "extension"
)

// RuleContentRuleMetadata is rule_content.RuleMetadata and describes a rule file.
type RuleContentRuleMetadata struct {
	Path         string
	Format       RuleFormat
	Type         RuleType
	Size         int
	Modified     float64 // unix seconds
	Checksum     string
	Dependencies []string
}

// ModifiedDatetime mirrors datetime.fromtimestamp(modified): a local-time value.
func (m RuleContentRuleMetadata) ModifiedDatetime() time.Time {
	sec := int64(m.Modified)
	return time.Unix(sec, int64((m.Modified-float64(sec))*1e9)).Local()
}

// RuleContentRuleContent is the parsed content of a rule.
type RuleContentRuleContent struct {
	Metadata      *RuleContentRuleMetadata
	RawContent    string
	ParsedContent *OrderedMap[any]
	Sections      *OrderedMap[string]
	References    []string
	Variables     *OrderedMap[any]
}

// NewRuleContentRuleContent validates that content is non-empty and metadata present.
func NewRuleContentRuleContent(metadata *RuleContentRuleMetadata, raw string, parsed *OrderedMap[any], sections *OrderedMap[string],
	references []string, variables *OrderedMap[any]) (*RuleContentRuleContent, error) {
	if raw == "" {
		return nil, value_objects.ValueErrorf("Rule content cannot be empty")
	}
	if metadata == nil {
		return nil, value_objects.ValueErrorf("Rule metadata is required")
	}
	return &RuleContentRuleContent{metadata, raw, parsed, sections, references, variables}, nil
}

// RuleContentRuleInheritance records a parent/child inheritance relationship.
type RuleContentRuleInheritance struct {
	ParentPath        string
	ChildPath         string
	InheritanceType   InheritanceType
	InheritedSections []string
	Conflicts         []string
}

// CompositionResult is the result of composing rules.
type CompositionResult struct {
	Success         bool
	ComposedContent map[string]any
	AppliedRules    []string
	Conflicts       []string
	Errors          []string
}

// RuleConflict describes a conflict between two rules.
type RuleConflict struct {
	Rule1Path       string
	Rule2Path       string
	ConflictSection string
	ConflictType    string
	Resolution      *ConflictResolution
	ResolvedValue   any
}
