package agent

// RegisterAgentResponse is the response DTO for agent registration.
type RegisterAgentResponse struct {
	Success bool
	Agent   *AgentResponse
	Message *string
	Error   *string
}

// NewRegisterAgentResponseSuccess mirrors success_response; a nil message uses
// the Python default.
func NewRegisterAgentResponseSuccess(agent *AgentResponse, message *string) *RegisterAgentResponse {
	msg := "Agent registered successfully"
	if message != nil {
		msg = *message
	}
	return &RegisterAgentResponse{Success: true, Agent: agent, Message: &msg}
}

// NewRegisterAgentResponseError mirrors error_response.
func NewRegisterAgentResponseError(err string) *RegisterAgentResponse {
	return &RegisterAgentResponse{Success: false, Error: &err}
}
