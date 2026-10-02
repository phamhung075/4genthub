package use_cases

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// DeleteRuleUseCase ports delete_rule.DeleteRuleUseCase.
type DeleteRuleUseCase struct {
	ruleRepository repositories.RuleRepository
}

// NewDeleteRuleUseCase mirrors __init__(rule_repository).
func NewDeleteRuleUseCase(ruleRepository repositories.RuleRepository) *DeleteRuleUseCase {
	return &DeleteRuleUseCase{ruleRepository: ruleRepository}
}

// deleteRuleError builds {"success": False, "error": msg}.
func deleteRuleError(msg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", msg)
	return m
}

// Execute mirrors DeleteRuleUseCase.execute (force default false).
func (u *DeleteRuleUseCase) Execute(ctx context.Context, rulePath string, force bool) *entities.OrderedMap[any] {
	exists, err := u.ruleRepository.RuleExists(ctx, rulePath)
	if err != nil {
		return deleteRuleError("Failed to delete rule: " + err.Error())
	}
	if !exists {
		return deleteRuleError(fmt.Sprintf("Rule not found at path: %s", rulePath))
	}

	if !force {
		dependentRules, err := u.ruleRepository.GetDependentRules(ctx, rulePath)
		if err != nil {
			return deleteRuleError("Failed to delete rule: " + err.Error())
		}
		if len(dependentRules) > 0 {
			m := entities.NewOrderedMap[any]()
			m.Set("success", false)
			m.Set("error", fmt.Sprintf("Cannot delete rule: %d dependent rules found", len(dependentRules)))
			m.Set("dependent_rules", dependentRules)
			m.Set("suggestion", "Use force=True to delete anyway or remove dependencies first")
			return m
		}
	}

	success, err := u.ruleRepository.DeleteRule(ctx, rulePath)
	if err != nil {
		return deleteRuleError("Failed to delete rule: " + err.Error())
	}
	if success {
		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("message", fmt.Sprintf("Rule deleted successfully from %s", rulePath))
		m.Set("rule_path", rulePath)
		m.Set("forced", force)
		return m
	}
	return deleteRuleError("Failed to delete rule from repository")
}
