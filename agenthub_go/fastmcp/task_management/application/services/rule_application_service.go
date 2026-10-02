package services

// Port of
// agenthub_main/src/fastmcp/task_management/application/services/rule_application_service.py
//
// DDD application service for rule management operations.

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// zpRuleApplicationUserScoped is the minimal optional interface mirroring the
// Python `hasattr(repository, "with_user")` branch. Concrete Go repositories do
// not currently implement it, so the repository is returned unchanged.
type zpRuleApplicationUserScoped interface {
	WithUser(userID string) repositories.RuleRepository
}

// RuleApplicationService mirrors the Python class.
type RuleApplicationService struct {
	ruleRepository repositories.RuleRepository
	userID         *string

	createRuleUseCase   *use_cases.CreateRuleUseCase
	getRuleUseCase      *use_cases.GetRuleUseCase
	listRulesUseCase    *use_cases.ListRulesUseCase
	updateRuleUseCase   *use_cases.UpdateRuleUseCase
	deleteRuleUseCase   *use_cases.DeleteRuleUseCase
	validateRuleUseCase *use_cases.ValidateRuleUseCase
}

// NewRuleApplicationService mirrors __init__(rule_repository, user_id=None).
func NewRuleApplicationService(ruleRepository repositories.RuleRepository, userID *string) *RuleApplicationService {
	s := &RuleApplicationService{ruleRepository: ruleRepository, userID: userID}
	repo := s.userScopedRepository(ruleRepository)
	s.createRuleUseCase = use_cases.NewCreateRuleUseCase(repo)
	s.getRuleUseCase = use_cases.NewGetRuleUseCase(repo)
	s.listRulesUseCase = use_cases.NewListRulesUseCase(repo)
	s.updateRuleUseCase = use_cases.NewUpdateRuleUseCase(repo)
	s.deleteRuleUseCase = use_cases.NewDeleteRuleUseCase(repo)
	s.validateRuleUseCase = use_cases.NewValidateRuleUseCase(repo)
	return s
}

// userScopedRepository mirrors _get_user_scoped_repository. Only the
// `with_user` branch is representable; the `user_id`/`session` reconstruction
// branch has no Go analog and returns the repository unchanged.
func (s *RuleApplicationService) userScopedRepository(repository repositories.RuleRepository) repositories.RuleRepository {
	if repository == nil {
		return repository
	}
	if s.userID != nil {
		if scoped, ok := repository.(zpRuleApplicationUserScoped); ok {
			return scoped.WithUser(*s.userID)
		}
	}
	return repository
}

// WithUser mirrors with_user.
func (s *RuleApplicationService) WithUser(userID string) *RuleApplicationService {
	return NewRuleApplicationService(s.ruleRepository, &userID)
}

// CreateRule mirrors create_rule.
func (s *RuleApplicationService) CreateRule(ctx context.Context, rulePath, content string,
	ruleType value_objects.RuleType, ruleFormat value_objects.RuleFormat,
	metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return s.createRuleUseCase.Execute(ctx, rulePath, content, ruleType, ruleFormat, metadata)
}

// GetRule mirrors get_rule.
func (s *RuleApplicationService) GetRule(ctx context.Context, rulePath string) *entities.OrderedMap[any] {
	return s.getRuleUseCase.Execute(ctx, rulePath)
}

// ListRules mirrors list_rules.
func (s *RuleApplicationService) ListRules(ctx context.Context, filters map[string]any, metadataOnly bool) *entities.OrderedMap[any] {
	return s.listRulesUseCase.Execute(ctx, filters, metadataOnly)
}

// UpdateRule mirrors update_rule.
func (s *RuleApplicationService) UpdateRule(ctx context.Context, rulePath string, content *string, metadataUpdates *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return s.updateRuleUseCase.Execute(ctx, rulePath, content, metadataUpdates)
}

// DeleteRule mirrors delete_rule.
func (s *RuleApplicationService) DeleteRule(ctx context.Context, rulePath string, force bool) *entities.OrderedMap[any] {
	return s.deleteRuleUseCase.Execute(ctx, rulePath, force)
}

// ValidateRule mirrors validate_rule(rule_path=None).
func (s *RuleApplicationService) ValidateRule(ctx context.Context, rulePath *string) *entities.OrderedMap[any] {
	return s.validateRuleUseCase.Execute(ctx, rulePath)
}

// BackupRules mirrors backup_rules.
func (s *RuleApplicationService) BackupRules(ctx context.Context, backupPath string) *entities.OrderedMap[any] {
	repo := s.userScopedRepository(s.ruleRepository)
	success, err := repo.BackupRules(ctx, backupPath)
	out := entities.NewOrderedMap[any]()
	if err != nil {
		out.Set("success", false)
		out.Set("error", "Failed to backup rules: "+err.Error())
		return out
	}
	if success {
		out.Set("success", true)
		out.Set("message", "Rules backed up successfully to "+backupPath)
		out.Set("backup_path", backupPath)
		return out
	}
	out.Set("success", false)
	out.Set("error", "Failed to backup rules")
	return out
}

// RestoreRules mirrors restore_rules.
func (s *RuleApplicationService) RestoreRules(ctx context.Context, backupPath string) *entities.OrderedMap[any] {
	repo := s.userScopedRepository(s.ruleRepository)
	success, err := repo.RestoreRules(ctx, backupPath)
	out := entities.NewOrderedMap[any]()
	if err != nil {
		out.Set("success", false)
		out.Set("error", "Failed to restore rules: "+err.Error())
		return out
	}
	if success {
		out.Set("success", true)
		out.Set("message", "Rules restored successfully from "+backupPath)
		out.Set("backup_path", backupPath)
		return out
	}
	out.Set("success", false)
	out.Set("error", "Failed to restore rules")
	return out
}

// CleanupObsoleteRules mirrors cleanup_obsolete_rules.
func (s *RuleApplicationService) CleanupObsoleteRules(ctx context.Context) *entities.OrderedMap[any] {
	repo := s.userScopedRepository(s.ruleRepository)
	cleanedPaths, err := repo.CleanupObsoleteRules(ctx)
	out := entities.NewOrderedMap[any]()
	if err != nil {
		out.Set("success", false)
		out.Set("error", "Failed to cleanup obsolete rules: "+err.Error())
		return out
	}
	out.Set("success", true)
	out.Set("message", fmt.Sprintf("Cleaned up %d obsolete rules", len(cleanedPaths)))
	out.Set("cleaned_paths", cleanedPaths)
	return out
}

// GetRuleStatistics mirrors get_rule_statistics.
func (s *RuleApplicationService) GetRuleStatistics(ctx context.Context) *entities.OrderedMap[any] {
	repo := s.userScopedRepository(s.ruleRepository)
	stats, err := repo.GetRuleStatistics(ctx)
	out := entities.NewOrderedMap[any]()
	if err != nil {
		out.Set("success", false)
		out.Set("error", "Failed to get rule statistics: "+err.Error())
		return out
	}
	out.Set("success", true)
	out.Set("statistics", stats)
	return out
}

// GetRuleDependencies mirrors get_rule_dependencies.
func (s *RuleApplicationService) GetRuleDependencies(ctx context.Context, rulePath string) *entities.OrderedMap[any] {
	repo := s.userScopedRepository(s.ruleRepository)
	dependencies, err := repo.GetRuleDependencies(ctx, rulePath)
	out := entities.NewOrderedMap[any]()
	if err != nil {
		out.Set("success", false)
		out.Set("error", "Failed to get rule dependencies: "+err.Error())
		return out
	}
	out.Set("success", true)
	out.Set("rule_path", rulePath)
	out.Set("dependencies", dependencies)
	return out
}

// GetDependentRules mirrors get_dependent_rules.
func (s *RuleApplicationService) GetDependentRules(ctx context.Context, rulePath string) *entities.OrderedMap[any] {
	repo := s.userScopedRepository(s.ruleRepository)
	dependentRules, err := repo.GetDependentRules(ctx, rulePath)
	out := entities.NewOrderedMap[any]()
	if err != nil {
		out.Set("success", false)
		out.Set("error", "Failed to get dependent rules: "+err.Error())
		return out
	}
	out.Set("success", true)
	out.Set("rule_path", rulePath)
	out.Set("dependent_rules", dependentRules)
	return out
}

// GetRulesByType mirrors get_rules_by_type.
func (s *RuleApplicationService) GetRulesByType(ctx context.Context, ruleType string) *entities.OrderedMap[any] {
	repo := s.userScopedRepository(s.ruleRepository)
	rules, err := repo.GetRulesByType(ctx, ruleType)
	out := entities.NewOrderedMap[any]()
	if err != nil {
		out.Set("success", false)
		out.Set("error", "Failed to get rules by type: "+err.Error())
		return out
	}
	out.Set("success", true)
	out.Set("rule_type", ruleType)
	out.Set("rules", zpRuleApplicationSummaries(rules))
	return out
}

// GetRulesByTag mirrors get_rules_by_tag.
func (s *RuleApplicationService) GetRulesByTag(ctx context.Context, tag string) *entities.OrderedMap[any] {
	repo := s.userScopedRepository(s.ruleRepository)
	rules, err := repo.GetRulesByTag(ctx, tag)
	out := entities.NewOrderedMap[any]()
	if err != nil {
		out.Set("success", false)
		out.Set("error", "Failed to get rules by tag: "+err.Error())
		return out
	}
	out.Set("success", true)
	out.Set("tag", tag)
	out.Set("rules", zpRuleApplicationSummaries(rules))
	return out
}

// zpRuleApplicationSummaries builds the Python list comprehension
// {path, type, format, description, tags} preserving insertion order.
func zpRuleApplicationSummaries(rules []*entities.RuleContent) []any {
	out := make([]any, 0, len(rules))
	for _, rule := range rules {
		entry := entities.NewOrderedMap[any]()
		entry.Set("path", rule.Metadata.Path)
		entry.Set("type", rule.Metadata.Type.String())
		entry.Set("format", rule.Metadata.Format.String())
		entry.Set("description", rule.Metadata.Description)
		entry.Set("tags", rule.Metadata.Tags)
		out = append(out, entry)
	}
	return out
}
