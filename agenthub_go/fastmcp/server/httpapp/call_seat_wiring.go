package httpapp

import (
	"context"
	"fmt"
	"os"
	"strings"

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
// does, so an unset AGENTHUB_PUBLIC_URL is a tool-call failure with that reason
// rather than a failure to start the server.
func newCallSeatController(sessions *database.SessionManager) *seatcontrollers.CallSeatController {
	return seatcontrollers.NewCallSeatController(authservices.NewAuthenticationService(),
		seatResolverFunc(func(ctx context.Context, userID, roomSlug, seatKey string) (*repositories.ResolvedSeat, error) {
			mcpURL := strings.TrimRight(os.Getenv(publicURLEnv), "/")
			if mcpURL == "" {
				return nil, fmt.Errorf("%s is not set; it is required to render a seat's MCP fragment", publicURLEnv)
			}
			source, err := newSeatSource(sessions, mcpURL+"/mcp")
			if err != nil {
				return nil, err
			}
			return source.ResolveSeat(ctx, userID, roomSlug, seatKey)
		}))
}
