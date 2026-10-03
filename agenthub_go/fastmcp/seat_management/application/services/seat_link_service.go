package services

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/rigspec"
)

// ErrLinkCycle is a link that would close a delegates_to/spawned_by launch cycle.
var ErrLinkCycle = errors.New("link would create a launch cycle")

// SeatLinkStore is the persistence surface SeatLinkService reads and writes.
type SeatLinkStore interface {
	ListSeats(ctx context.Context, userID, roomID string) ([]repositories.Seat, error)
	ListSeatLinks(ctx context.Context, userID, seatID string) ([]repositories.SeatLink, error)
	UpsertSeatLink(ctx context.Context, userID string, link repositories.SeatLink) (*repositories.SeatLink, error)
}

// SeatLinkService stores seat links.
type SeatLinkService struct {
	store SeatLinkStore
}

// NewSeatLinkService builds the service over store.
func NewSeatLinkService(store SeatLinkStore) *SeatLinkService {
	return &SeatLinkService{store: store}
}

// UpsertSeatLink stores a link between two seats of the room. A link that `rig up` would render
// (allowed) must not close a delegates_to/spawned_by launch cycle with the room's other allowed
// links: that is ErrLinkCycle naming the cycle. Links of the descriptive kinds and links with
// Allow false never cycle.
func (s *SeatLinkService) UpsertSeatLink(ctx context.Context, userID, roomID string, link repositories.SeatLink) (*repositories.SeatLink, error) {
	if link.Allow {
		if err := s.checkLaunchCycle(ctx, userID, roomID, link); err != nil {
			return nil, err
		}
	}
	return s.store.UpsertSeatLink(ctx, userID, link)
}

func (s *SeatLinkService) checkLaunchCycle(ctx context.Context, userID, roomID string, link repositories.SeatLink) error {
	seats, err := s.store.ListSeats(ctx, userID, roomID)
	if err != nil {
		return err
	}
	keys := make(map[string]string, len(seats))
	for _, seat := range seats {
		if seat.Status != "removed" {
			keys[seat.ID] = seat.SeatKey
		}
	}
	var edges []rigspec.Edge
	for _, seat := range seats {
		if _, active := keys[seat.ID]; !active {
			continue
		}
		links, err := s.store.ListSeatLinks(ctx, userID, seat.ID)
		if err != nil {
			return err
		}
		for _, l := range links {
			replaced := l.FromSeatID == link.FromSeatID && l.ToSeatID == link.ToSeatID && l.Kind == link.Kind
			to, toActive := keys[l.ToSeatID]
			if l.Allow && !replaced && toActive {
				edges = append(edges, rigspec.Edge{Kind: l.Kind, From: keys[l.FromSeatID], To: to})
			}
		}
	}
	edges = append(edges, rigspec.Edge{Kind: link.Kind, From: keys[link.FromSeatID], To: keys[link.ToSeatID]})
	if cycle := rigspec.FindLaunchCycle(edges); cycle != nil {
		return fmt.Errorf("%w: %s", ErrLinkCycle, strings.Join(cycle, " -> "))
	}
	return nil
}
