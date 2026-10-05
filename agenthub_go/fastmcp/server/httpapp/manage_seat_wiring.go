package httpapp

import (
	seatservices "agenthub/fastmcp/seat_management/application/services"
	seatcontrollers "agenthub/fastmcp/seat_management/interface/mcp_controllers"
	"agenthub/fastmcp/task_management/infrastructure/database"
	authservices "agenthub/fastmcp/task_management/interface/mcp_controllers/auth_helper/services"
)

// newManageSeatController is the manage_seat tool over the same seat source the REST
// routes use.
func newManageSeatController(sessions *database.SessionManager) (*seatcontrollers.ManageSeatController, error) {
	source, err := newSeatAdminSource(sessions)
	if err != nil {
		return nil, err
	}
	return seatcontrollers.NewManageSeatController(authservices.NewAuthenticationService(), seatservices.NewSeatAdminService(source)), nil
}
