package use_cases

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// GetRuleUseCase ports get_rule.GetRuleUseCase.
type GetRuleUseCase struct {
	ruleRepository repositories.RuleRepository
}

// NewGetRuleUseCase builds the use case.
func NewGetRuleUseCase(ruleRepository repositories.RuleRepository) *GetRuleUseCase {
	return &GetRuleUseCase{ruleRepository: ruleRepository}
}

// Execute returns the rule dict, or an error dict on failure / absence.
func (uc *GetRuleUseCase) Execute(ctx context.Context, rulePath string) *entities.OrderedMap[any] {
	rule, err := uc.ruleRepository.GetRule(ctx, rulePath)
	if err != nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", fmt.Sprintf("Failed to retrieve rule: %s", err.Error()))
		return out
	}
	if rule == nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", fmt.Sprintf("Rule not found at path: %s", rulePath))
		return out
	}

	ruleDict := entities.NewOrderedMap[any]()
	ruleDict.Set("path", rule.Metadata.Path)
	ruleDict.Set("type", rule.Metadata.Type.String())
	ruleDict.Set("format", rule.Metadata.Format.String())
	ruleDict.Set("content", rule.RawContent)
	ruleDict.Set("size", rule.Metadata.Size)
	ruleDict.Set("version", rule.Metadata.Version)
	ruleDict.Set("author", rule.Metadata.Author)
	ruleDict.Set("description", rule.Metadata.Description)
	ruleDict.Set("tags", rule.Metadata.Tags)
	ruleDict.Set("dependencies", rule.Metadata.Dependencies)
	ruleDict.Set("sections", rule.Sections)
	ruleDict.Set("variables", rule.Variables)
	ruleDict.Set("references", rule.References)

	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("rule", ruleDict)
	return out
}
