package repositories

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
)

// RuleRepository is the repository interface for rules.
type RuleRepository interface {
	SaveRule(ctx context.Context, rule *entities.RuleContent) (bool, error)
	GetRule(ctx context.Context, rulePath string) (*entities.RuleContent, error)
	GetRuleMetadata(ctx context.Context, rulePath string) (*entities.RuleMetadata, error)
	ListRules(ctx context.Context, filters map[string]any) ([]*entities.RuleContent, error)
	ListRuleMetadata(ctx context.Context, filters map[string]any) ([]*entities.RuleMetadata, error)
	DeleteRule(ctx context.Context, rulePath string) (bool, error)
	RuleExists(ctx context.Context, rulePath string) (bool, error)
	GetRulesByType(ctx context.Context, ruleType string) ([]*entities.RuleContent, error)
	GetRulesByTag(ctx context.Context, tag string) ([]*entities.RuleContent, error)
	GetRuleDependencies(ctx context.Context, rulePath string) ([]string, error)
	GetDependentRules(ctx context.Context, rulePath string) ([]string, error)
	SaveRuleInheritance(ctx context.Context, inheritance *entities.RuleInheritance) (bool, error)
	GetRuleInheritance(ctx context.Context, childPath string) (*entities.RuleInheritance, error)
	GetRuleHierarchy(ctx context.Context, rulePath string) ([]*entities.RuleInheritance, error)
	BackupRules(ctx context.Context, backupPath string) (bool, error)
	RestoreRules(ctx context.Context, backupPath string) (bool, error)
	ValidateRuleIntegrity(ctx context.Context) (map[string]any, error)
	CleanupObsoleteRules(ctx context.Context) ([]string, error)
	GetRuleStatistics(ctx context.Context) (map[string]any, error)
}
