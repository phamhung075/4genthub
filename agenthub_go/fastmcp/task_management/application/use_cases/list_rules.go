package use_cases

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// ListRulesUseCase ports list_rules.ListRulesUseCase.
type ListRulesUseCase struct {
	ruleRepository repositories.RuleRepository
}

// NewListRulesUseCase mirrors __init__(rule_repository).
func NewListRulesUseCase(ruleRepository repositories.RuleRepository) *ListRulesUseCase {
	return &ListRulesUseCase{ruleRepository: ruleRepository}
}

// listRulesError builds {"success": False, "error": "Failed to list rules: ..."}.
func listRulesError(err error) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", "Failed to list rules: "+err.Error())
	return m
}

// Execute mirrors ListRulesUseCase.execute; filters nil means Python None.
func (u *ListRulesUseCase) Execute(ctx context.Context, filters map[string]any, metadataOnly bool) *entities.OrderedMap[any] {
	rules := []any{}

	if metadataOnly {
		metadataList, err := u.ruleRepository.ListRuleMetadata(ctx, filters)
		if err != nil {
			return listRulesError(err)
		}
		for _, metadata := range metadataList {
			m := entities.NewOrderedMap[any]()
			m.Set("path", metadata.Path)
			m.Set("type", string(metadata.Type))
			m.Set("format", string(metadata.Format))
			m.Set("size", metadata.Size)
			m.Set("version", metadata.Version)
			m.Set("author", metadata.Author)
			m.Set("description", metadata.Description)
			m.Set("tags", metadata.Tags)
			m.Set("dependencies", metadata.Dependencies)
			m.Set("modified", metadata.Modified)
			m.Set("checksum", metadata.Checksum)
			rules = append(rules, m)
		}
	} else {
		ruleList, err := u.ruleRepository.ListRules(ctx, filters)
		if err != nil {
			return listRulesError(err)
		}
		for _, rule := range ruleList {
			m := entities.NewOrderedMap[any]()
			m.Set("path", rule.Metadata.Path)
			m.Set("type", string(rule.Metadata.Type))
			m.Set("format", string(rule.Metadata.Format))
			m.Set("content", rule.RawContent)
			m.Set("size", rule.Metadata.Size)
			m.Set("version", rule.Metadata.Version)
			m.Set("author", rule.Metadata.Author)
			m.Set("description", rule.Metadata.Description)
			m.Set("tags", rule.Metadata.Tags)
			m.Set("dependencies", rule.Metadata.Dependencies)
			m.Set("sections", rule.Sections)
			m.Set("variables", rule.Variables)
			m.Set("references", rule.References)
			m.Set("modified", rule.Metadata.Modified)
			m.Set("checksum", rule.Metadata.Checksum)
			rules = append(rules, m)
		}
	}

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("rules", rules)
	result.Set("count", len(rules))
	if filters != nil {
		result.Set("filters_applied", filters)
	} else {
		result.Set("filters_applied", map[string]any{})
	}
	result.Set("metadata_only", metadataOnly)
	return result
}
