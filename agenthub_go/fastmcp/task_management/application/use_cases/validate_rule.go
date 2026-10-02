package use_cases

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// ValidateRuleUseCase ports validate_rule.ValidateRuleUseCase.
type ValidateRuleUseCase struct {
	ruleRepository repositories.RuleRepository
}

// NewValidateRuleUseCase builds the use case.
func NewValidateRuleUseCase(ruleRepository repositories.RuleRepository) *ValidateRuleUseCase {
	return &ValidateRuleUseCase{ruleRepository: ruleRepository}
}

// Execute ports execute().
func (uc *ValidateRuleUseCase) Execute(ctx context.Context, rulePath *string) *entities.OrderedMap[any] {
	var (
		result *entities.OrderedMap[any]
		err    error
	)
	if rulePath != nil && *rulePath != "" {
		result, err = uc.validateSingleRule(ctx, *rulePath)
	} else {
		result, err = uc.validateAllRules(ctx)
	}
	if err != nil {
		return validateRuleError("Failed to validate rules: " + err.Error())
	}
	return result
}

func validateRuleError(msg string) *entities.OrderedMap[any] {
	result := entities.NewOrderedMap[any]()
	result.Set("success", false)
	result.Set("error", msg)
	return result
}

func (uc *ValidateRuleUseCase) validateSingleRule(ctx context.Context, rulePath string) (*entities.OrderedMap[any], error) {
	exists, err := uc.ruleRepository.RuleExists(ctx, rulePath)
	if err != nil {
		return nil, err
	}
	if !exists {
		return validateRuleError("Rule not found at path: " + rulePath), nil
	}

	rule, err := uc.ruleRepository.GetRule(ctx, rulePath)
	if err != nil {
		return nil, err
	}
	if rule == nil {
		return validateRuleError("Failed to retrieve rule content for: " + rulePath), nil
	}

	validationResults := []any{}
	if rule.Metadata != nil {
		for _, dependency := range rule.Metadata.Dependencies {
			found, err := uc.ruleRepository.RuleExists(ctx, dependency)
			if err != nil {
				return nil, err
			}
			if !found {
				validationResults = append(validationResults, validationResultEntry("dependency_error", "Dependency not found: "+dependency))
			}
		}
	}
	for _, reference := range rule.References {
		found, err := uc.ruleRepository.RuleExists(ctx, reference)
		if err != nil {
			return nil, err
		}
		if !found {
			validationResults = append(validationResults, validationResultEntry("reference_error", "Reference not found: "+reference))
		}
	}

	circular, err := uc.hasCircularDependency(ctx, rulePath, nil)
	if err != nil {
		return nil, err
	}
	if circular {
		validationResults = append(validationResults, validationResultEntry("circular_dependency", "Circular dependency detected for rule: "+rulePath))
	}

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("rule_path", rulePath)
	result.Set("is_valid", len(validationResults) == 0)
	result.Set("validation_results", validationResults)
	return result, nil
}

func validationResultEntry(typ, message string) *entities.OrderedMap[any] {
	entry := entities.NewOrderedMap[any]()
	entry.Set("type", typ)
	entry.Set("message", message)
	return entry
}

func (uc *ValidateRuleUseCase) validateAllRules(ctx context.Context) (*entities.OrderedMap[any], error) {
	integrityResults, err := uc.ruleRepository.ValidateRuleIntegrity(ctx)
	if err != nil {
		return nil, err
	}
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("validation_type", "all_rules")
	result.Set("integrity_results", orderedMapFromSortedMap(integrityResults))
	return result, nil
}

func (uc *ValidateRuleUseCase) hasCircularDependency(ctx context.Context, rulePath string, visited map[string]bool) (bool, error) {
	if visited == nil {
		visited = map[string]bool{}
	}
	if visited[rulePath] {
		return true, nil
	}
	visited[rulePath] = true

	dependencies, err := uc.ruleRepository.GetRuleDependencies(ctx, rulePath)
	if err != nil {
		return false, err
	}
	for _, dependency := range dependencies {
		visitedCopy := make(map[string]bool, len(visited))
		for k, v := range visited {
			visitedCopy[k] = v
		}
		circular, err := uc.hasCircularDependency(ctx, dependency, visitedCopy)
		if err != nil {
			return false, err
		}
		if circular {
			return true, nil
		}
	}
	return false, nil
}
