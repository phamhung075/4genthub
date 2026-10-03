package services

import (
	"context"
	"errors"
	"fmt"

	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/entities"
)

var (
	ErrInvalidOccupant = errors.New("invalid occupant")
	ErrRoomNotFound    = errors.New("room not found")
	ErrSeatNotFound    = errors.New("seat not found")
	ErrSeatRemoved     = errors.New("seat removed")
)

// SeatAdminStore is the persistence surface SeatAdminService reads and writes.
type SeatAdminStore interface {
	ListRooms(ctx context.Context, userID string) ([]repositories.Room, error)
	GetRoomBySlug(ctx context.Context, userID, slug string) (*repositories.Room, error)
	ListSeatTypes(ctx context.Context, userID string) ([]repositories.SeatType, error)
	FindSeat(ctx context.Context, userID, roomID, seatKey string) (*repositories.Seat, error)
	ListSeats(ctx context.Context, userID, roomID string) ([]repositories.Seat, error)
	UpdateSeatOccupant(ctx context.Context, userID, seatID, runtime, model string) error
}

// SeatView is a seat with the slugs of its room and seat type.
type SeatView struct {
	Seat         repositories.Seat
	RoomSlug     string
	SeatTypeSlug string
}

// SeatAdminService reads seats and switches the LLM (runtime and model) of a seat.
type SeatAdminService struct {
	store SeatAdminStore
}

// NewSeatAdminService builds the service over store.
func NewSeatAdminService(store SeatAdminStore) *SeatAdminService {
	return &SeatAdminService{store: store}
}

// ListSeats returns the active seats of one room, or of every room when roomSlug is empty.
func (s *SeatAdminService) ListSeats(ctx context.Context, userID, roomSlug string) ([]SeatView, error) {
	var rooms []repositories.Room
	if roomSlug == "" {
		all, err := s.store.ListRooms(ctx, userID)
		if err != nil {
			return nil, err
		}
		rooms = all
	} else {
		room, err := s.room(ctx, userID, roomSlug)
		if err != nil {
			return nil, err
		}
		rooms = []repositories.Room{*room}
	}
	slugs, err := s.seatTypeSlugs(ctx, userID)
	if err != nil {
		return nil, err
	}
	views := []SeatView{}
	for _, room := range rooms {
		seats, err := s.store.ListSeats(ctx, userID, room.ID)
		if err != nil {
			return nil, err
		}
		for _, seat := range seats {
			if seat.Status != "removed" {
				views = append(views, SeatView{Seat: seat, RoomSlug: room.Slug, SeatTypeSlug: slugs[seat.SeatTypeID]})
			}
		}
	}
	return views, nil
}

// GetSeat returns one active seat.
func (s *SeatAdminService) GetSeat(ctx context.Context, userID, roomSlug, seatKey string) (*SeatView, error) {
	room, seat, err := s.seat(ctx, userID, roomSlug, seatKey)
	if err != nil {
		return nil, err
	}
	return s.view(ctx, userID, room, seat)
}

// SetOccupant switches the seat to runtime and model. The seat keeps its pinned seat type
// version; the next resolve renders the new runtime into a new snapshot.
func (s *SeatAdminService) SetOccupant(ctx context.Context, userID, roomSlug, seatKey, runtime, model string) (*SeatView, error) {
	if err := repositories.ValidateRuntime(runtime); err != nil {
		return nil, fmt.Errorf("%w: %v", ErrInvalidOccupant, err)
	}
	if err := repositories.ValidateModel(model); err != nil {
		return nil, fmt.Errorf("%w: %v", ErrInvalidOccupant, err)
	}
	room, seat, err := s.seat(ctx, userID, roomSlug, seatKey)
	if err != nil {
		return nil, err
	}
	if err := s.store.UpdateSeatOccupant(ctx, userID, seat.ID, runtime, model); err != nil {
		return nil, err
	}
	seat.Runtime, seat.Model = runtime, model
	return s.view(ctx, userID, room, seat)
}

func (s *SeatAdminService) room(ctx context.Context, userID, slug string) (*repositories.Room, error) {
	room, err := s.store.GetRoomBySlug(ctx, userID, slug)
	if err != nil {
		return nil, err
	}
	if room == nil {
		return nil, fmt.Errorf("%w: room %q", ErrRoomNotFound, slug)
	}
	return room, nil
}

// seat finds an existing seat; a removed seat is ErrSeatRemoved, an absent one ErrSeatNotFound.
func (s *SeatAdminService) seat(ctx context.Context, userID, roomSlug, seatKey string) (*repositories.Room, *repositories.Seat, error) {
	room, err := s.room(ctx, userID, roomSlug)
	if err != nil {
		return nil, nil, err
	}
	seat, err := s.store.FindSeat(ctx, userID, room.ID, seatKey)
	if err != nil {
		return nil, nil, err
	}
	if seat == nil {
		return nil, nil, fmt.Errorf("%w: seat %q", ErrSeatNotFound, seatKey)
	}
	if seat.Status == "removed" {
		return nil, nil, fmt.Errorf("%w: seat %q", ErrSeatRemoved, seatKey)
	}
	return room, seat, nil
}

func (s *SeatAdminService) view(ctx context.Context, userID string, room *repositories.Room, seat *repositories.Seat) (*SeatView, error) {
	slugs, err := s.seatTypeSlugs(ctx, userID)
	if err != nil {
		return nil, err
	}
	return &SeatView{Seat: *seat, RoomSlug: room.Slug, SeatTypeSlug: slugs[seat.SeatTypeID]}, nil
}

func (s *SeatAdminService) seatTypeSlugs(ctx context.Context, userID string) (map[string]string, error) {
	seatTypes, err := s.store.ListSeatTypes(ctx, userID)
	if err != nil {
		return nil, err
	}
	slugs := make(map[string]string, len(seatTypes))
	for _, st := range seatTypes {
		slugs[st.ID] = st.Slug
	}
	return slugs, nil
}

// SeatBody is the JSON shape of a seat in every seat response.
func SeatBody(seat *repositories.Seat, seatTypeSlug string) *entities.OrderedMap[any] {
	body := entities.NewOrderedMap[any]()
	body.Set("id", seat.ID)
	body.Set("room_id", seat.RoomID)
	body.Set("seat_key", seat.SeatKey)
	body.Set("seat_type_id", seat.SeatTypeID)
	body.Set("seat_type", seatTypeSlug)
	if seat.PinnedVersion == nil {
		body.Set("pinned_version", nil)
	} else {
		body.Set("pinned_version", *seat.PinnedVersion)
	}
	body.Set("runtime", seat.Runtime)
	body.Set("model", seat.Model)
	body.Set("status", seat.Status)
	return body
}
