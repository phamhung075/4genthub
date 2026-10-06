package httpapp

import (
	seatcontrollers "agenthub/fastmcp/seat_management/interface/mcp_controllers"
	"agenthub/fastmcp/task_management/infrastructure/database"
	authservices "agenthub/fastmcp/task_management/interface/mcp_controllers/auth_helper/services"
)

// newSubmitFeedbackController is the submit_feedback MCP tool over the SAME service seam the REST
// route uses (newSeatFeedbackService): one writer contract, two transports.
func newSubmitFeedbackController(sessions *database.SessionManager) (*seatcontrollers.SubmitFeedbackController, error) {
	service, err := newSeatFeedbackService(sessions)
	if err != nil {
		return nil, err
	}
	return seatcontrollers.NewSubmitFeedbackController(
		authservices.NewAuthenticationService(),
		service,
	), nil
}
