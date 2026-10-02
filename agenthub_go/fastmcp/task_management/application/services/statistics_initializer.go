package services

import (
	domainServices "agenthub/fastmcp/task_management/domain/services"
)

// StatisticsInitializer is the application service that initializes branch statistics
// tracking on startup (Python application/services/statistics_initializer.py). Logging
// is dropped.
type StatisticsInitializer struct{}

// statsInitInitialized is the class-level flag (Python StatisticsInitializer._initialized).
var statsInitInitialized bool

// Initialize initializes the statistics tracking system. It should be called once
// during application startup; repeated calls are a no-op.
func (StatisticsInitializer) Initialize() error {
	if statsInitInitialized {
		return nil
	}
	provider := RepositoryProviderService{}.GetInstance()
	taskRepo, err := provider.GetTaskRepository(nil, nil, nil, nil)
	if err != nil {
		return err
	}
	branchRepo, err := provider.GetGitBranchRepository(nil, nil)
	if err != nil {
		return err
	}
	GetBranchStatisticsIntegrationService(taskRepo, branchRepo)
	statsInitInitialized = true
	return nil
}

// RecalculateAllBranches recalculates statistics for all branches, optionally limited
// to one project (Python project_id=None).
func (StatisticsInitializer) RecalculateAllBranches(projectID *string) (map[string]domainServices.BranchStatistics, error) {
	provider := RepositoryProviderService{}.GetInstance()
	taskRepo, err := provider.GetTaskRepository(nil, nil, nil, nil)
	if err != nil {
		return nil, err
	}
	branchRepo, err := provider.GetGitBranchRepository(nil, nil)
	if err != nil {
		return nil, err
	}
	integrationService := GetBranchStatisticsIntegrationService(taskRepo, branchRepo)
	return integrationService.RecalculateAllBranches(projectID)
}

// IsInitialized reports whether the statistics system is initialized.
func (StatisticsInitializer) IsInitialized() bool {
	return statsInitInitialized
}
