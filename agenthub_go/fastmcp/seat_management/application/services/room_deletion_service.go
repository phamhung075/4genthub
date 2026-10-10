package services

import (
	"context"
	"fmt"

	"agenthub/fastmcp/seat_management/domain/repositories"
)

// RoomDeletionStore is the persistence surface RoomDeletionService writes. There are no
// foreign-key cascades, so the service removes every dependent row itself.
type RoomDeletionStore interface {
	GetRoomBySlug(ctx context.Context, userID, slug string) (*repositories.Room, error)
	FindSeat(ctx context.Context, userID, roomID, seatKey string) (*repositories.Seat, error)
	ListSeats(ctx context.Context, userID, roomID string) ([]repositories.Seat, error)
	DeleteSeatLinksOfSeat(ctx context.Context, userID, seatID string) error
	DeleteSeatOverlay(ctx context.Context, userID, seatID string) error
	DeleteResolvedSeats(ctx context.Context, userID, seatID string) error
	DeleteSeat(ctx context.Context, userID, seatID string) error
	DeleteRoomOverlay(ctx context.Context, userID, roomID string) error
	DeleteSeatStatusForRoom(ctx context.Context, userID, roomSlug string) error
	DeleteSeatStatusForSeat(ctx context.Context, userID, roomSlug, seatKey string) error
	DeleteMachineEdgesForRoom(ctx context.Context, userID, roomSlug string) error
	// The message store's two, and they are the reason this service exists rather than a CASCADE:
	// undelivered text addressed to a seat that is going away can never be delivered, so it goes with
	// the seat (and with an emptied room) EXPLICITLY. Silence here would leave rows no client can ever
	// reach.
	DeleteSeatMessagesForSeat(ctx context.Context, userID, roomSlug, seatKey string) error
	DeleteSeatMessagesForRoom(ctx context.Context, userID, roomSlug string) error
	DeleteRoom(ctx context.Context, userID, roomID string) error
	// InTransaction runs fn so that all its store calls commit or roll back together.
	InTransaction(ctx context.Context, fn func(ctx context.Context) error) error
}

// RoomDeletionService deletes a room with its seats, links, overlays and snapshots.
type RoomDeletionService struct {
	store RoomDeletionStore
}

// NewRoomDeletionService builds the service over store.
func NewRoomDeletionService(store RoomDeletionStore) *RoomDeletionService {
	return &RoomDeletionService{store: store}
}

// DeleteRoom hard-deletes an empty room: its room overlay, its reported seat statuses, its
// reported topology edges and the room row, in one transaction. A room that still holds seats is
// refused with ErrRoomNotEmpty naming how many remain, so seats are never cascaded away; remove
// them with RemoveSeat first.
// An absent room is ErrRoomNotFound.
func (s *RoomDeletionService) DeleteRoom(ctx context.Context, userID, roomSlug string) error {
	room, err := s.store.GetRoomBySlug(ctx, userID, roomSlug)
	if err != nil {
		return err
	}
	if room == nil {
		return fmt.Errorf("%w: room %q", ErrRoomNotFound, roomSlug)
	}
	return s.store.InTransaction(ctx, func(ctx context.Context) error {
		seats, err := s.store.ListSeats(ctx, userID, room.ID)
		if err != nil {
			return err
		}
		if len(seats) > 0 {
			return fmt.Errorf("%w: room %q still holds %d seat(s); remove them first", ErrRoomNotEmpty, roomSlug, len(seats))
		}
		if err := s.store.DeleteRoomOverlay(ctx, userID, room.ID); err != nil {
			return err
		}
		if err := s.store.DeleteSeatStatusForRoom(ctx, userID, room.Slug); err != nil {
			return err
		}
		// The room's undelivered messages go with it: they are addressed to seats this room no longer
		// has, so no client could ever deliver them, and leaving them would be rows no one can reach.
		if err := s.store.DeleteSeatMessagesForRoom(ctx, userID, room.Slug); err != nil {
			return err
		}
		// The reported topology edges of the room go with it: machine_edges carries the room
		// slug, not a foreign key, so nothing else would remove them.
		if err := s.store.DeleteMachineEdgesForRoom(ctx, userID, room.Slug); err != nil {
			return err
		}
		return s.store.DeleteRoom(ctx, userID, room.ID)
	})
}

// RemoveSeat hard-deletes one seat with its links (both directions), overlay, resolved
// snapshots and reported statuses in one transaction, so the seat key can be added again from
// scratch. An absent room is ErrRoomNotFound and an absent seat ErrSeatNotFound.
func (s *RoomDeletionService) RemoveSeat(ctx context.Context, userID, roomSlug, seatKey string) error {
	room, err := s.store.GetRoomBySlug(ctx, userID, roomSlug)
	if err != nil {
		return err
	}
	if room == nil {
		return fmt.Errorf("%w: room %q", ErrRoomNotFound, roomSlug)
	}
	seat, err := s.store.FindSeat(ctx, userID, room.ID, seatKey)
	if err != nil {
		return err
	}
	if seat == nil {
		return fmt.Errorf("%w: seat %q", ErrSeatNotFound, seatKey)
	}
	return s.store.InTransaction(ctx, func(ctx context.Context) error {
		if err := s.deleteSeatRows(ctx, userID, seat.ID); err != nil {
			return err
		}
		if err := s.store.DeleteSeatStatusForSeat(ctx, userID, room.Slug, seat.SeatKey); err != nil {
			return err
		}
		// And the seat's messages, delivered or not: they are addressed to a seat key that is about to
		// not exist, so nothing could ever deliver what is left — and this service's own promise is that
		// the seat key can be added again FROM SCRATCH, which means without inheriting the previous
		// seat's inbox.
		return s.store.DeleteSeatMessagesForSeat(ctx, userID, room.Slug, seat.SeatKey)
	})
}

// deleteSeatRows removes the seat and the rows that reference it by seat id.
func (s *RoomDeletionService) deleteSeatRows(ctx context.Context, userID, seatID string) error {
	if err := s.store.DeleteSeatLinksOfSeat(ctx, userID, seatID); err != nil {
		return err
	}
	if err := s.store.DeleteSeatOverlay(ctx, userID, seatID); err != nil {
		return err
	}
	if err := s.store.DeleteResolvedSeats(ctx, userID, seatID); err != nil {
		return err
	}
	return s.store.DeleteSeat(ctx, userID, seatID)
}
