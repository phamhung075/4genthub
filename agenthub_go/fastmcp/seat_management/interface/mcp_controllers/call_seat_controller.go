// Package mcp_controllers holds the MCP tool controllers of seat_management.
package mcp_controllers

import (
	"context"

	"agenthub/fastmcp/seat_management/domain/repositories"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

// CallSeatToolName is the MCP tool name of CallSeatController.
//
// It is call_seat and not call_agent on purpose: the seat is the durable position
// 4genthub stores, the occupant is the brain that sits in it, and the name should
// say which layer this reaches.
const CallSeatToolName = "call_seat"

// CallSeatToolDescription is read by LLM seats.
const CallSeatToolDescription = "Resolve one exact seat by room and seat key. Returns the seat's runtime, model, permission policy, resolved snapshot hash and its rendered context files. 4genthub stores the seat and its context, OpenRig runs the seat, and the brain is the occupant."

// SeatResolver resolves a seat and renders it to its immutable snapshot.
// SeatResolutionService is the production implementation.
type SeatResolver interface {
	ResolveSeat(ctx context.Context, userID, roomSlug, seatKey string) (*repositories.ResolvedSeat, error)
}

// CallSeatController is the call_seat MCP tool over a SeatResolver.
type CallSeatController struct {
	auth     AuthenticationService
	resolver SeatResolver
}

// NewCallSeatController creates the controller.
func NewCallSeatController(auth AuthenticationService, resolver SeatResolver) *CallSeatController {
	return &CallSeatController{auth: auth, resolver: resolver}
}

// CallSeat resolves the seat for the authenticated user; every failure is a success=false response.
func (c *CallSeatController) CallSeat(ctx context.Context, room, seat *string, userID *string) *tmentities.OrderedMap[any] {
	uid, err := c.auth.GetAuthenticatedUserID(ctx, userID, CallSeatToolName)
	if err != nil {
		return seatFailure(err.Error())
	}
	if deref(room) == "" || deref(seat) == "" {
		return seatFailure("room and seat are required")
	}
	resolved, err := c.resolver.ResolveSeat(ctx, uid, deref(room), deref(seat))
	if err != nil {
		return seatFailure(err.Error())
	}

	resp := seatSuccess()
	resp.Set("room", deref(room))
	resp.Set("seat", deref(seat))
	resp.Set("hash", resolved.Hash)
	resp.Set("runtime", resolved.Runtime)
	resp.Set("policy", resolved.Policy)
	files := make([]any, 0, len(resolved.Files))
	for _, f := range resolved.Files {
		entry := tmentities.NewOrderedMap[any]()
		entry.Set("path", f.Path)
		entry.Set("content", f.Content)
		files = append(files, entry)
	}
	resp.Set("files", files)
	return resp
}

// RegisterTools registers the call_seat tool with an MCP server instance.
func (c *CallSeatController) RegisterTools(server FastMCPServer) {
	if server == nil {
		return
	}
	server.Tool(CallSeatToolName, CallSeatToolDescription,
		func(ctx context.Context, room, seat, userID *string) *tmentities.OrderedMap[any] {
			return c.CallSeat(ctx, room, seat, userID)
		})
}

// CallSeatInputSchema is the inputSchema of the call_seat tool.
func CallSeatInputSchema() *tmentities.OrderedMap[any] {
	properties := tmentities.NewOrderedMap[any]()
	properties.Set("room", seatParam("Room", "[REQUIRED] Room slug, for example 4genthub-dev", false))
	properties.Set("seat", seatParam("Seat", "[REQUIRED] Seat key, for example lead", false))
	properties.Set("user_id", seatParam("User Id", "[OPTIONAL] ", true))

	schema := tmentities.NewOrderedMap[any]()
	schema.Set("properties", properties)
	schema.Set("required", []any{"room", "seat"})
	schema.Set("type", "object")
	return schema
}
