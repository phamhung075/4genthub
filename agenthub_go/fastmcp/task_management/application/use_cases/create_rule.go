// Package use_cases ports task_management/application/use_cases.
package use_cases

import (
	"context"
	"fmt"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// CreateRuleUseCase ports create_rule.CreateRuleUseCase.
type CreateRuleUseCase struct {
	ruleRepository repositories.RuleRepository
}

// NewCreateRuleUseCase builds the use case.
func NewCreateRuleUseCase(ruleRepository repositories.RuleRepository) *CreateRuleUseCase {
	return &CreateRuleUseCase{ruleRepository: ruleRepository}
}

// Execute creates a rule with validation. Every failure (rule already present,
// save failure, repository error) is returned inside the result dict, matching
// the Python try/except.
func (uc *CreateRuleUseCase) Execute(ctx context.Context, rulePath, content string,
	ruleType value_objects.RuleType, ruleFormat value_objects.RuleFormat,
	metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {

	exists, err := uc.ruleRepository.RuleExists(ctx, rulePath)
	if err != nil {
		return ruleErrorMap("Failed to create rule: " + err.Error())
	}
	if exists {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", fmt.Sprintf("Rule already exists at path: %s", rulePath))
		return out
	}

	ruleMetadata := &entities.RuleMetadata{
		Path:         rulePath,
		Format:       ruleFormat,
		Type:         ruleType,
		Size:         utf8.RuneCountInString(content),
		Modified:     0.0,
		Checksum:     "",
		Dependencies: []string{},
		Version:      ruleMetadataString(metadata, "version", "1.0"),
		Author:       ruleMetadataString(metadata, "author", "rule_creator"),
		Description:  ruleMetadataString(metadata, "description", ""),
		Tags:         ruleMetadataStrings(metadata, "tags"),
	}

	ruleContent := &entities.RuleContent{
		Metadata:      ruleMetadata,
		RawContent:    content,
		ParsedContent: entities.NewOrderedMap[any](),
		Sections:      entities.NewOrderedMap[string](),
		References:    []string{},
		Variables:     entities.NewOrderedMap[any](),
	}

	success, err := uc.ruleRepository.SaveRule(ctx, ruleContent)
	if err != nil {
		return ruleErrorMap("Failed to create rule: " + err.Error())
	}
	if !success {
		return ruleErrorMap("Failed to save rule to repository")
	}

	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("message", fmt.Sprintf("Rule created successfully at %s", rulePath))
	out.Set("rule_path", rulePath)
	out.Set("rule_type", ruleType.String())
	out.Set("rule_format", ruleFormat.String())
	return out
}

func ruleErrorMap(message string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("success", false)
	out.Set("error", message)
	return out
}

// ruleMetadataString mirrors metadata.get(key, def) with the Python truthiness of
// an omitted metadata dict.
func ruleMetadataString(metadata *entities.OrderedMap[any], key, def string) string {
	if metadata == nil {
		return def
	}
	v, ok := metadata.Get(key)
	if !ok || v == nil {
		return def
	}
	if s, ok := v.(string); ok {
		return s
	}
	return value_objects.PyStr(v)
}

// ruleMetadataStrings mirrors metadata.get(key, []) for the tags list.
func ruleMetadataStrings(metadata *entities.OrderedMap[any], key string) []string {
	if metadata == nil {
		return []string{}
	}
	v, ok := metadata.Get(key)
	if !ok || v == nil {
		return []string{}
	}
	return useCasePyStringList(v)
}

// useCasePyStringList converts a Python list value to []string (nil-safe).
func useCasePyStringList(v any) []string {
	switch xs := v.(type) {
	case []string:
		return append([]string{}, xs...)
	case []any:
		out := make([]string, 0, len(xs))
		for _, x := range xs {
			if x == nil {
				out = append(out, "None")
				continue
			}
			out = append(out, value_objects.PyStr(x))
		}
		return out
	}
	return []string{}
}
