package httpapp

import (
	amfacades "agenthub/fastmcp/agent_management/application/facades"
	amorm "agenthub/fastmcp/agent_management/infrastructure/repositories/orm"
	amcontrollers "agenthub/fastmcp/agent_management/interface/mcp_controllers"
	"agenthub/fastmcp/task_management/infrastructure/database"
	authservices "agenthub/fastmcp/task_management/interface/mcp_controllers/auth_helper/services"
)

// newCallAgentController is CallAgentMCPController(): the authentication service plus
// the agent management facade over the ORM template and instance repositories.
func newCallAgentController(sessions *database.SessionManager) (*amcontrollers.CallAgentMCPController, error) {
	templateRepo, err := amorm.NewORMAgentTemplateRepository(sessions)
	if err != nil {
		return nil, err
	}
	instanceRepo, err := amorm.NewORMUserAgentInstanceRepository(sessions)
	if err != nil {
		return nil, err
	}
	facade := amfacades.NewAgentManagementFacade(templateRepo, instanceRepo, nil, nil)
	return amcontrollers.NewCallAgentMCPController(authservices.NewAuthenticationService(), facade), nil
}
