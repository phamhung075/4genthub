// Package mcp_controllers holds the MCP tool controllers of seat_management.
package mcp_controllers

import (
	"context"

	seatservices "agenthub/fastmcp/seat_management/application/services"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

// ManageSeatToolName is the MCP tool name of ManageSeatController.
const ManageSeatToolName = "manage_seat"

// ManageSeatToolDescription is read by LLM seats.
const ManageSeatToolDescription = "Manage seats: list, get, set_occupant (switch the LLM of a seat: runtime claude-code|codex|agy|omp and model id)"

// FastMCPServer is the minimal FastMCP server interface for tool registration.
type FastMCPServer interface {
	Tool(name string, description string, fn any)
}

// AuthenticationService resolves the tenant of a tool call.
type AuthenticationService interface {
	GetAuthenticatedUserID(ctx context.Context, providedUserID *string, operationName string) (string, error)
}

// ManageSeatController is the manage_seat MCP tool over SeatAdminService.
type ManageSeatController struct {
	auth    AuthenticationService
	service *seatservices.SeatAdminService
}

// NewManageSeatController creates the controller.
func NewManageSeatController(auth AuthenticationService, service *seatservices.SeatAdminService) *ManageSeatController {
	return &ManageSeatController{auth: auth, service: service}
}

// ManageSeat runs action for the authenticated user; every failure is a success=false response.
func (c *ManageSeatController) ManageSeat(ctx context.Context, action string, room, seat, runtime, model, userID *string) *tmentities.OrderedMap[any] {
	uid, err := c.auth.GetAuthenticatedUserID(ctx, userID, ManageSeatToolName)
	if err != nil {
		return seatFailure(err.Error())
	}
	switch action {
	case "list":
		views, err := c.service.ListSeats(ctx, uid, deref(room))
		if err != nil {
			return seatFailure(err.Error())
		}
		seats := make([]any, 0, len(views))
		for i := range views {
			seats = append(seats, seatEntry(&views[i]))
		}
		resp := seatSuccess()
		resp.Set("seats", seats)
		return resp
	case "get":
		if deref(room) == "" || deref(seat) == "" {
			return seatFailure("room and seat are required for get")
		}
		view, err := c.service.GetSeat(ctx, uid, deref(room), deref(seat))
		return seatResult(view, err)
	case "set_occupant":
		if deref(room) == "" || deref(seat) == "" || deref(runtime) == "" {
			return seatFailure("room, seat and runtime are required for set_occupant")
		}
		view, err := c.service.SetOccupant(ctx, uid, deref(room), deref(seat), deref(runtime), deref(model))
		return seatResult(view, err)
	}
	return seatFailure("unknown action \"" + action + "\"; use list, get or set_occupant")
}

// RegisterTools registers the manage_seat tool with an MCP server instance.
func (c *ManageSeatController) RegisterTools(server FastMCPServer) {
	if server == nil {
		return
	}
	server.Tool(ManageSeatToolName, ManageSeatToolDescription,
		func(ctx context.Context, action string, room, seat, runtime, model, userID *string) *tmentities.OrderedMap[any] {
			return c.ManageSeat(ctx, action, room, seat, runtime, model, userID)
		})
}

// ManageSeatInputSchema is the inputSchema of the manage_seat tool.
func ManageSeatInputSchema() *tmentities.OrderedMap[any] {
	properties := tmentities.NewOrderedMap[any]()
	properties.Set("action", seatParam("Action", "list | get | set_occupant", false))
	properties.Set("room", seatParam("Room", "[OPTIONAL for list, REQUIRED for get and set_occupant] Room slug", true))
	properties.Set("seat", seatParam("Seat", "[REQUIRED for get and set_occupant] Seat key", true))
	properties.Set("runtime", seatParam("Runtime", "[REQUIRED for set_occupant] claude-code, codex, agy or omp", true))
	properties.Set("model", seatParam("Model", "[OPTIONAL for set_occupant] Model id. Empty means TWO DIFFERENT THINGS depending on the action: on UPDATE it is IGNORED - the stored model is kept unchanged and no error is returned, so an empty value cannot be used to reset a model; on CREATE it is stored AS GIVEN, because nothing in this service substitutes a default - whether the runtime then supplies one of its own is the runtime's behaviour, NOT established here", true))
	properties.Set("user_id", seatParam("User Id", "[OPTIONAL] ", true))

	schema := tmentities.NewOrderedMap[any]()
	schema.Set("properties", properties)
	schema.Set("required", []any{"action"})
	schema.Set("type", "object")
	return schema
}

func seatParam(title, description string, optional bool) *tmentities.OrderedMap[any] {
	param := tmentities.NewOrderedMap[any]()
	if optional {
		param.Set("default", nil)
	}
	param.Set("description", description)
	param.Set("title", title)
	param.Set("type", "string")
	return param
}

func seatEntry(view *seatservices.SeatView) *tmentities.OrderedMap[any] {
	entry := seatservices.SeatBody(&view.Seat, view.SeatTypeSlug)
	entry.Set("room", view.RoomSlug)
	return entry
}

func seatResult(view *seatservices.SeatView, err error) *tmentities.OrderedMap[any] {
	if err != nil {
		return seatFailure(err.Error())
	}
	resp := seatSuccess()
	resp.Set("seat", seatEntry(view))
	return resp
}

func seatSuccess() *tmentities.OrderedMap[any] {
	resp := tmentities.NewOrderedMap[any]()
	resp.Set("success", true)
	return resp
}

func seatFailure(message string) *tmentities.OrderedMap[any] {
	resp := tmentities.NewOrderedMap[any]()
	resp.Set("success", false)
	resp.Set("error", message)
	return resp
}

func deref(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}
