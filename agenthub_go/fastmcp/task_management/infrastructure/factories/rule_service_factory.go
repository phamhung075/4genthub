// Package factories ports task_management/infrastructure/factories.
package factories

import (
	"agenthub/fastmcp/task_management/application/services"
	domainrepositories "agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// RuleServiceFactory mirrors RuleServiceFactory.
type RuleServiceFactory struct {
	ruleRepository domainrepositories.RuleRepository
}

// NewRuleServiceFactory mirrors RuleServiceFactory.__init__.
func NewRuleServiceFactory(ruleRepository domainrepositories.RuleRepository) *RuleServiceFactory {
	return &RuleServiceFactory{ruleRepository: ruleRepository}
}

// CreateRuleApplicationService mirrors create_rule_application_service.
func (f *RuleServiceFactory) CreateRuleApplicationService() (*services.RuleApplicationService, error) {
	if f.ruleRepository == nil {
		return nil, &value_objects.ValueError{Msg: "RuleRepository is required for creating RuleApplicationService"}
	}
	return services.NewRuleApplicationService(f.ruleRepository, nil), nil
}

// SetRuleRepository mirrors set_rule_repository.
func (f *RuleServiceFactory) SetRuleRepository(ruleRepository domainrepositories.RuleRepository) {
	f.ruleRepository = ruleRepository
}

// GetRuleRepository mirrors get_rule_repository.
func (f *RuleServiceFactory) GetRuleRepository() domainrepositories.RuleRepository {
	return f.ruleRepository
}
