package services

import (
	"context"
	"errors"
	"fmt"

	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/task_management/domain/entities"
)

var (
	ErrInvalidOccupant         = errors.New("invalid occupant")
	ErrInvalidPermissionPolicy = errors.New("invalid permission policy")
	ErrRoomNotFound            = errors.New("room not found")
	ErrSeatNotFound            = errors.New("seat not found")

	ErrSeatTypeNotFound       = errors.New("seat type not found")
	ErrInvalidSeatTypeVersion = errors.New("invalid seat type version")
)

// SeatAdminStore is the persistence surface SeatAdminService reads and writes.
type SeatAdminStore interface {
	ListRooms(ctx context.Context, userID string) ([]repositories.Room, error)
	GetRoomBySlug(ctx context.Context, userID, slug string) (*repositories.Room, error)
	ListSeatTypes(ctx context.Context, userID string) ([]repositories.SeatType, error)
	FindSeat(ctx context.Context, userID, roomID, seatKey string) (*repositories.Seat, error)
	ListSeats(ctx context.Context, userID, roomID string) ([]repositories.Seat, error)
	UpdateSeatOccupant(ctx context.Context, userID, seatID, runtime, model string) error
	UpdateSeatPermissionPolicy(ctx context.Context, userID, seatID, permissionPolicy string) error
	GetModuleVersion(ctx context.Context, userID, slug, version string) (*repositories.ModuleVersion, error)
	LatestSeatTypeVersion(ctx context.Context, userID, slug string) (*repositories.SeatTypeVersion, error)
	AddSeatTypeVersion(ctx context.Context, userID, slug, version, defaultRuntime string, refs []resolver.ModuleRef) (*repositories.SeatTypeVersion, error)
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
			views = append(views, SeatView{Seat: seat, RoomSlug: room.Slug, SeatTypeSlug: slugs[seat.SeatTypeID]})
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
	if err := repositories.ValidateOccupant(runtime, model); err != nil {
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

// SetPermissionPolicy changes the permission policy rendered on the seat's member. The next
// rigspec render carries it; a seat already launched keeps the posture it was launched with.
func (s *SeatAdminService) SetPermissionPolicy(ctx context.Context, userID, roomSlug, seatKey, permissionPolicy string) (*SeatView, error) {
	if err := resolver.CheckPermissionPolicy(permissionPolicy); err != nil {
		return nil, fmt.Errorf("%w: %v", ErrInvalidPermissionPolicy, err)
	}
	room, seat, err := s.seat(ctx, userID, roomSlug, seatKey)
	if err != nil {
		return nil, err
	}
	if err := s.store.UpdateSeatPermissionPolicy(ctx, userID, seat.ID, permissionPolicy); err != nil {
		return nil, err
	}
	seat.PermissionPolicy = permissionPolicy
	return s.view(ctx, userID, room, seat)
}

// CreateSeatTypeVersion appends the next patch version (1.0.0 when none) of a seat type with
// the given "slug@version" module refs and default runtime, in one immutable row. Bad input
// and unknown module refs are ErrInvalidSeatTypeVersion, an absent seat type is
// ErrSeatTypeNotFound, and a concurrent writer that took the same version with different
// content is repositories.ErrSeatTypeVersionConflict.
func (s *SeatAdminService) CreateSeatTypeVersion(ctx context.Context, userID, slug string, moduleRefs []string, defaultRuntime string) (*repositories.SeatTypeVersion, error) {
	if err := repositories.ValidateRuntime(defaultRuntime); err != nil {
		return nil, fmt.Errorf("%w: %v", ErrInvalidSeatTypeVersion, err)
	}
	refs := make([]resolver.ModuleRef, 0, len(moduleRefs))
	seen := make(map[string]bool, len(moduleRefs))
	for _, raw := range moduleRefs {
		ref, err := repositories.ParseModuleRef(raw)
		if err != nil {
			return nil, fmt.Errorf("%w: %v", ErrInvalidSeatTypeVersion, err)
		}
		if seen[ref.Slug] {
			return nil, fmt.Errorf("%w: module %q is referenced twice", ErrInvalidSeatTypeVersion, ref.Slug)
		}
		seen[ref.Slug] = true
		refs = append(refs, ref)
	}
	seatTypes, err := s.store.ListSeatTypes(ctx, userID)
	if err != nil {
		return nil, err
	}
	found := false
	for _, st := range seatTypes {
		if st.Slug == slug {
			found = true
			break
		}
	}
	if !found {
		return nil, fmt.Errorf("%w: %q", ErrSeatTypeNotFound, slug)
	}
	for _, ref := range refs {
		module, err := s.store.GetModuleVersion(ctx, userID, ref.Slug, ref.Version)
		if err != nil {
			return nil, err
		}
		if module == nil {
			return nil, fmt.Errorf("%w: module ref %s@%s does not exist", ErrInvalidSeatTypeVersion, ref.Slug, ref.Version)
		}
	}
	version := "1.0.0"
	latest, err := s.store.LatestSeatTypeVersion(ctx, userID, slug)
	if err != nil {
		return nil, err
	}
	if latest != nil {
		if version, err = repositories.NextPatchVersion(latest.Version); err != nil {
			return nil, err
		}
	}
	return s.store.AddSeatTypeVersion(ctx, userID, slug, version, defaultRuntime, refs)
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

// seat finds an existing seat; an absent one is ErrSeatNotFound.
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
	body.Set("permission_policy", seat.PermissionPolicy)
	return body
}
