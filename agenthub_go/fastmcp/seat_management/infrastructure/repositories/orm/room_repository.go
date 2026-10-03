package orm

import (
	"context"
	"sort"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// ORMRoomRepository is the ORM RoomRepository over rooms.
type ORMRoomRepository struct {
	*baserepo.ORMRepository[seatdb.RoomORM]
}

var _ domainrepo.RoomRepository = (*ORMRoomRepository)(nil)

// NewORMRoomRepository builds the repository over rooms.
func NewORMRoomRepository(sessions *database.SessionManager) (*ORMRoomRepository, error) {
	base, err := baserepo.NewORMRepository[seatdb.RoomORM]("rooms", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMRoomRepository{ORMRepository: base}, nil
}

// Save get-or-creates the room by user_id + slug.
func (r *ORMRoomRepository) Save(ctx context.Context, userID string, room domainrepo.Room) (*domainrepo.Room, error) {
	row, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "slug", room.Slug))
	if err != nil {
		return nil, err
	}
	if row != nil {
		return roomToDomain(row), nil
	}
	created, err := r.Create(ctx, baserepo.NewKwargs("user_id", userID, "slug", room.Slug, "name", room.Name))
	if err != nil {
		return nil, err
	}
	return roomToDomain(created), nil
}

// GetBySlug returns the room with the slug, or nil when absent.
func (r *ORMRoomRepository) GetBySlug(ctx context.Context, userID, slug string) (*domainrepo.Room, error) {
	row, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "slug", slug))
	if err != nil || row == nil {
		return nil, err
	}
	return roomToDomain(row), nil
}

// GetByID returns the room with the id, or nil when absent.
func (r *ORMRoomRepository) GetByID(ctx context.Context, userID, roomID string) (*domainrepo.Room, error) {
	row, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "id", roomID))
	if err != nil || row == nil {
		return nil, err
	}
	return roomToDomain(row), nil
}

// List returns the user's rooms ordered by slug.
func (r *ORMRoomRepository) List(ctx context.Context, userID string) ([]domainrepo.Room, error) {
	rows, err := r.FindBy(ctx, baserepo.NewKwargs("user_id", userID))
	if err != nil {
		return nil, err
	}
	out := make([]domainrepo.Room, 0, len(rows))
	for _, row := range rows {
		out = append(out, *roomToDomain(row))
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Slug < out[j].Slug })
	return out, nil
}
