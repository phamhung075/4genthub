// Orchestrator Router - application layer orchestrator access.
//
// Ports task_management/application/orchestration/orchestrator_router.py.
package orchestration

import (
	"agenthub/fastmcp/task_management/domain/entities"
)

// GetOrchestrator is the factory function to get the application layer
// orchestrator (Python get_orchestrator).
func GetOrchestrator(strategy OrchestrationStrategy) *ProjectOrchestrator {
	// Python: logger.debug("Using application layer orchestrator")
	return NewProjectOrchestrator(strategy)
}

// OrchestratorRouter delegates to the application layer orchestrator
// (Python OrchestratorRouter).
type OrchestratorRouter struct {
	orchestrator *ProjectOrchestrator
}

// NewOrchestratorRouter initializes the router with the application layer
// orchestrator (Python OrchestratorRouter.__init__).
func NewOrchestratorRouter(strategy OrchestrationStrategy) *OrchestratorRouter {
	// Python: logger.debug("OrchestratorRouter initialized with application layer implementation")
	return &OrchestratorRouter{orchestrator: GetOrchestrator(strategy)}
}

// OrchestrateProject orchestrates work distribution for a project.
func (r *OrchestratorRouter) OrchestrateProject(project *entities.Project) (map[string]any, error) {
	return r.orchestrator.OrchestrateProject(project)
}

// CoordinateCrossTreeDependencies coordinates and validates cross-tree
// dependencies.
func (r *OrchestratorRouter) CoordinateCrossTreeDependencies(project *entities.Project) []map[string]any {
	return r.orchestrator.CoordinateCrossTreeDependencies(project)
}

// BalanceWorkload balances workload across agents.
func (r *OrchestratorRouter) BalanceWorkload(project *entities.Project) (map[string]any, error) {
	return r.orchestrator.BalanceWorkload(project)
}

// OrchestrateProject is the convenience function for quick orchestration
// (Python module-level orchestrate_project).
func OrchestrateProject(project *entities.Project, strategy OrchestrationStrategy) (map[string]any, error) {
	orchestrator := GetOrchestrator(strategy)
	return orchestrator.OrchestrateProject(project)
}
