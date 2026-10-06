package mcp_controllers

// submit_feedback_controller.go is the MCP submission path of the seat friction channel: a seat
// whose runtime has MCP reports friction with this tool, and a runtime without MCP uses the shell
// command instead. Both reach SeatFeedbackService, so the channel has one writer contract and not
// two — this tool does not open a socket back into the server, and it does not touch storage.

import (
	"context"
	"time"

	seatservices "agenthub/fastmcp/seat_management/application/services"
	"agenthub/fastmcp/seat_management/domain/feedback"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

// SubmitFeedbackToolName is the MCP tool name of SubmitFeedbackController.
const SubmitFeedbackToolName = "submit_feedback"

// SubmitFeedbackToolDescription is read by LLM seats.
const SubmitFeedbackToolDescription = "Report friction you hit while working: the layer it is in (runtime, openrig, cloud, seat-context, workspace, other), the room and seat you are, and what happened. The owner reads these grouped by layer."

// SubmitFeedbackController is the submit_feedback MCP tool over SeatFeedbackService.
type SubmitFeedbackController struct {
	auth    AuthenticationService
	service *seatservices.SeatFeedbackService
}

// NewSubmitFeedbackController creates the controller.
func NewSubmitFeedbackController(auth AuthenticationService, service *seatservices.SeatFeedbackService) *SubmitFeedbackController {
	return &SubmitFeedbackController{auth: auth, service: service}
}

// SubmitFeedback stores one friction report for the authenticated user. Every failure is a
// success=false response, like the seat tools.
//
// The machine is empty here: a tool call arrives with the caller's user token, so the row is
// attributed to the user and to no bridge. That is the one thing the two submission paths do not
// share, and it is a fact about the transport rather than a second contract.
func (c *SubmitFeedbackController) SubmitFeedback(ctx context.Context, room, seat, session, layer, text string, userID *string) *tmentities.OrderedMap[any] {
	uid, err := c.auth.GetAuthenticatedUserID(ctx, userID, SubmitFeedbackToolName)
	if err != nil {
		return seatFailure(err.Error())
	}
	stored, err := c.service.Submit(ctx, seatservices.SeatFeedbackPoster{UserID: uid}, seatservices.SeatFeedbackInput{
		Room:    room,
		Seat:    seat,
		Session: session,
		Layer:   layer,
		Text:    text,
	}, time.Now().UTC())
	if err != nil {
		return seatFailure(err.Error())
	}
	resp := seatSuccess()
	resp.Set("id", stored.ID)
	resp.Set("layer", stored.Layer)
	return resp
}

// RegisterTools registers the submit_feedback tool with an MCP server instance.
func (c *SubmitFeedbackController) RegisterTools(server FastMCPServer) {
	if server == nil {
		return
	}
	server.Tool(SubmitFeedbackToolName, SubmitFeedbackToolDescription,
		func(ctx context.Context, room, seat, session, layer, text string, userID *string) *tmentities.OrderedMap[any] {
			return c.SubmitFeedback(ctx, room, seat, session, layer, text, userID)
		})
}

// SubmitFeedbackInputSchema is the inputSchema of the submit_feedback tool. The layer's enum is
// built from the domain vocabulary, so the tool can never advertise a layer the writer refuses.
func SubmitFeedbackInputSchema() *tmentities.OrderedMap[any] {
	properties := tmentities.NewOrderedMap[any]()
	properties.Set("room", seatParam("Room", "[REQUIRED] Room slug you are in", false))
	properties.Set("seat", seatParam("Seat", "[REQUIRED] Seat key you are", false))
	properties.Set("session", seatParam("Session", "[OPTIONAL] Your full session name, e.g. room-seat@room", true))
	properties.Set("layer", layerParam())
	properties.Set("text", textParam())
	properties.Set("user_id", seatParam("User Id", "[OPTIONAL] ", true))

	schema := tmentities.NewOrderedMap[any]()
	schema.Set("properties", properties)
	schema.Set("required", []any{"room", "seat", "layer", "text"})
	schema.Set("type", "object")
	return schema
}

// layerParam is the layer property, with the accepted values spelled out in the description and
// as an enum so a seat is told the vocabulary instead of guessing it.
func layerParam() *tmentities.OrderedMap[any] {
	param := seatParam("Layer", "[REQUIRED] The layer the friction is in. One of: "+feedback.List(), false)
	values := make([]any, 0, len(feedback.Layers))
	for _, layer := range feedback.Layers {
		values = append(values, string(layer))
	}
	param.Set("enum", values)
	return param
}

func textParam() *tmentities.OrderedMap[any] {
	param := seatParam("Text", "[REQUIRED] What happened, and what you expected instead", false)
	param.Set("maxLength", seatservices.SeatFeedbackMaxText)
	return param
}
