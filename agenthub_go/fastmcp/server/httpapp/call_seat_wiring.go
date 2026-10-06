package httpapp

import (
	"context"
	"fmt"

	"agenthub/fastmcp/seat_management/domain/repositories"
	seatcontrollers "agenthub/fastmcp/seat_management/interface/mcp_controllers"
	"agenthub/fastmcp/task_management/infrastructure/database"
	authservices "agenthub/fastmcp/task_management/interface/mcp_controllers/auth_helper/services"
)

// seatResolverFunc adapts a function to seatcontrollers.SeatResolver.
type seatResolverFunc func(ctx context.Context, userID, roomSlug, seatKey string) (*repositories.ResolvedSeat, error)

func (f seatResolverFunc) ResolveSeat(ctx context.Context, userID, roomSlug, seatKey string) (*repositories.ResolvedSeat, error) {
	return f(ctx, userID, roomSlug, seatKey)
}

// newCallSeatController is the call_seat tool over the same resolution source the
// resolved-seat REST route uses. The source is built per call, exactly as the route
// does, with the same public URL: AGENTHUB_PUBLIC_URL when pinned, else the origin of
// the MCP request this tool call arrived on (dispatchMCPTool puts it on ctx), so a
// self-hosted stack without the variable renders the caller's own URL rather than
// failing.
func newCallSeatController(sessions *database.SessionManager) *seatcontrollers.CallSeatController {
	return seatcontrollers.NewCallSeatController(authservices.NewAuthenticationService(),
		seatResolverFunc(func(ctx context.Context, userID, roomSlug, seatKey string) (*repositories.ResolvedSeat, error) {
			mcpURL := seatMCPURL(nil, ctx)
			if mcpURL == "" {
				return nil, fmt.Errorf("%s is not set and the MCP request origin is unknown; it is required to render a seat's MCP fragment", publicURLEnv)
			}
			source, err := newSeatSource(sessions, mcpURL)
			if err != nil {
				return nil, err
			}
			return source.ResolveSeat(ctx, userID, roomSlug, seatKey)
		}))
}
