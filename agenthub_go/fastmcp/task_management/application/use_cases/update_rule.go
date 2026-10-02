package use_cases

import (
	"context"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// UpdateRuleUseCase ports update_rule.UpdateRuleUseCase.
type UpdateRuleUseCase struct {
	ruleRepository repositories.RuleRepository
}

// NewUpdateRuleUseCase builds the use case.
func NewUpdateRuleUseCase(ruleRepository repositories.RuleRepository) *UpdateRuleUseCase {
	return &UpdateRuleUseCase{ruleRepository: ruleRepository}
}

// Execute ports execute(); metadataUpdates keys apply in the same order.
func (uc *UpdateRuleUseCase) Execute(ctx context.Context, rulePath string, content *string, metadataUpdates *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	existingRule, err := uc.ruleRepository.GetRule(ctx, rulePath)
	if err != nil {
		return updateRuleError("Failed to update rule: " + err.Error())
	}
	if existingRule == nil {
		return updateRuleError("Rule not found at path: " + rulePath)
	}

	if content != nil {
		existingRule.RawContent = *content
		if existingRule.Metadata != nil {
			existingRule.Metadata.Size = utf8.RuneCountInString(*content)
		}
	}

	if metadataUpdates != nil && metadataUpdates.Len() > 0 {
		applyRuleMetadataUpdates(existingRule, metadataUpdates)
	}

	success, err := uc.ruleRepository.SaveRule(ctx, existingRule)
	if err != nil {
		return updateRuleError("Failed to update rule: " + err.Error())
	}
	if success {
		result := entities.NewOrderedMap[any]()
		result.Set("success", true)
		result.Set("message", "Rule updated successfully at "+rulePath)
		result.Set("rule_path", rulePath)
		updatesApplied := entities.NewOrderedMap[any]()
		updatesApplied.Set("content_updated", content != nil)
		updatesApplied.Set("metadata_updated", metadataUpdates != nil)
		result.Set("updates_applied", updatesApplied)
		return result
	}
	return updateRuleError("Failed to save updated rule to repository")
}

func updateRuleError(msg string) *entities.OrderedMap[any] {
	result := entities.NewOrderedMap[any]()
	result.Set("success", false)
	result.Set("error", msg)
	return result
}

func applyRuleMetadataUpdates(rule *entities.RuleContent, updates *entities.OrderedMap[any]) {
	if rule.Metadata == nil {
		return
	}
	if v, ok := updates.Get("version"); ok {
		if s, ok := v.(string); ok {
			rule.Metadata.Version = s
		}
	}
	if v, ok := updates.Get("author"); ok {
		if s, ok := v.(string); ok {
			rule.Metadata.Author = s
		}
	}
	if v, ok := updates.Get("description"); ok {
		if s, ok := v.(string); ok {
			rule.Metadata.Description = s
		}
	}
	if v, ok := updates.Get("tags"); ok {
		if list, ok := anyToStringSlice(v); ok {
			rule.Metadata.Tags = list
		}
	}
	if v, ok := updates.Get("dependencies"); ok {
		if list, ok := anyToStringSlice(v); ok {
			rule.Metadata.Dependencies = list
		}
	}
	if v, ok := updates.Get("sections"); ok {
		if m, ok := v.(*entities.OrderedMap[string]); ok {
			rule.Sections = m
		}
	}
	if v, ok := updates.Get("variables"); ok {
		if m, ok := v.(*entities.OrderedMap[any]); ok {
			rule.Variables = m
		}
	}
	if v, ok := updates.Get("references"); ok {
		if list, ok := anyToStringSlice(v); ok {
			rule.References = list
		}
	}
}

func anyToStringSlice(v any) ([]string, bool) {
	switch x := v.(type) {
	case []string:
		return x, true
	case []any:
		out := make([]string, 0, len(x))
		for _, item := range x {
			s, ok := item.(string)
			if !ok {
				return nil, false
			}
			out = append(out, s)
		}
		return out, true
	}
	return nil, false
}
