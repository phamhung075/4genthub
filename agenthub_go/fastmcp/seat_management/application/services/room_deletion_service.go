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
	ListSeats(ctx context.Context, userID, roomID string) ([]repositories.Seat, error)
	DeleteSeatLinksOfSeat(ctx context.Context, userID, seatID string) error
	DeleteSeatOverlay(ctx context.Context, userID, seatID string) error
	DeleteResolvedSeats(ctx context.Context, userID, seatID string) error
	DeleteSeat(ctx context.Context, userID, seatID string) error
	DeleteRoomOverlay(ctx context.Context, userID, roomID string) error
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

// DeleteRoom hard-deletes the room and everything under it, including seats already
// marked removed, in one transaction. An absent room is ErrRoomNotFound.
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
		for _, seat := range seats {
			if err := s.store.DeleteSeatLinksOfSeat(ctx, userID, seat.ID); err != nil {
				return err
			}
			if err := s.store.DeleteSeatOverlay(ctx, userID, seat.ID); err != nil {
				return err
			}
			if err := s.store.DeleteResolvedSeats(ctx, userID, seat.ID); err != nil {
				return err
			}
			if err := s.store.DeleteSeat(ctx, userID, seat.ID); err != nil {
				return err
			}
		}
		if err := s.store.DeleteRoomOverlay(ctx, userID, room.ID); err != nil {
			return err
		}
		return s.store.DeleteRoom(ctx, userID, room.ID)
	})
}
