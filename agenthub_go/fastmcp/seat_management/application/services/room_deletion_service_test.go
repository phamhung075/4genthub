package services

import (
	"context"
	"errors"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/repositories"
)

type fakeRoomDeletionStore struct {
	room    *repositories.Room
	seats   []repositories.Seat
	calls   []string
	failOn  string
	failErr error
}

func (f *fakeRoomDeletionStore) record(call string) error {
	f.calls = append(f.calls, call)
	if call == f.failOn {
		return f.failErr
	}
	return nil
}

func (f *fakeRoomDeletionStore) GetRoomBySlug(context.Context, string, string) (*repositories.Room, error) {
	return f.room, nil
}

func (f *fakeRoomDeletionStore) FindSeat(_ context.Context, _, _, seatKey string) (*repositories.Seat, error) {
	for i := range f.seats {
		if f.seats[i].SeatKey == seatKey {
			return &f.seats[i], nil
		}
	}
	return nil, nil
}

func (f *fakeRoomDeletionStore) ListSeats(context.Context, string, string) ([]repositories.Seat, error) {
	return f.seats, nil
}

func (f *fakeRoomDeletionStore) DeleteSeatLinksOfSeat(_ context.Context, _, seatID string) error {
	return f.record("links:" + seatID)
}

func (f *fakeRoomDeletionStore) DeleteSeatOverlay(_ context.Context, _, seatID string) error {
	return f.record("overlay:" + seatID)
}

func (f *fakeRoomDeletionStore) DeleteResolvedSeats(_ context.Context, _, seatID string) error {
	return f.record("resolved:" + seatID)
}

func (f *fakeRoomDeletionStore) DeleteSeat(_ context.Context, _, seatID string) error {
	return f.record("seat:" + seatID)
}

func (f *fakeRoomDeletionStore) DeleteRoomOverlay(_ context.Context, _, roomID string) error {
	return f.record("room-overlay:" + roomID)
}

func (f *fakeRoomDeletionStore) DeleteSeatStatusForRoom(_ context.Context, _, roomSlug string) error {
	return f.record("status:" + roomSlug)
}

func (f *fakeRoomDeletionStore) DeleteSeatStatusForSeat(_ context.Context, _, roomSlug, seatKey string) error {
	return f.record("status:" + roomSlug + "/" + seatKey)
}

func (f *fakeRoomDeletionStore) DeleteRoom(_ context.Context, _, roomID string) error {
	return f.record("room:" + roomID)
}

func (f *fakeRoomDeletionStore) InTransaction(ctx context.Context, fn func(ctx context.Context) error) error {
	return fn(ctx)
}

func TestDeleteRoomRemovesDependentsBeforeParents(t *testing.T) {
	store := &fakeRoomDeletionStore{
		room:  &repositories.Room{ID: "r1", Slug: "dev"},
		seats: []repositories.Seat{{ID: "s1"}, {ID: "s2"}},
	}
	if err := NewRoomDeletionService(store).DeleteRoom(context.Background(), "u", "dev"); err != nil {
		t.Fatalf("DeleteRoom: %v", err)
	}
	want := "links:s1,overlay:s1,resolved:s1,seat:s1,links:s2,overlay:s2,resolved:s2,seat:s2,room-overlay:r1,status:dev,room:r1"
	if got := strings.Join(store.calls, ","); got != want {
		t.Errorf("calls = %s\nwant    %s", got, want)
	}
}

func TestDeleteRoomAbsentRoom(t *testing.T) {
	store := &fakeRoomDeletionStore{}
	err := NewRoomDeletionService(store).DeleteRoom(context.Background(), "u", "ghost")
	if !errors.Is(err, ErrRoomNotFound) || len(store.calls) != 0 {
		t.Errorf("err = %v, calls = %v, want ErrRoomNotFound and no deletes", err, store.calls)
	}
}

func TestDeleteRoomStopsAtFirstFailure(t *testing.T) {
	boom := errors.New("boom")
	store := &fakeRoomDeletionStore{
		room:   &repositories.Room{ID: "r1"},
		seats:  []repositories.Seat{{ID: "s1"}},
		failOn: "seat:s1", failErr: boom,
	}
	if err := NewRoomDeletionService(store).DeleteRoom(context.Background(), "u", "dev"); !errors.Is(err, boom) {
		t.Fatalf("err = %v, want boom", err)
	}
	for _, call := range store.calls {
		if strings.HasPrefix(call, "room") {
			t.Errorf("room rows deleted after a failure: %v", store.calls)
		}
	}
}

func TestRemoveSeatDeletesOnlyThatSeatsRows(t *testing.T) {
	store := &fakeRoomDeletionStore{
		room:  &repositories.Room{ID: "r1", Slug: "dev"},
		seats: []repositories.Seat{{ID: "s1", SeatKey: "alice"}, {ID: "s2", SeatKey: "bob"}},
	}
	if err := NewRoomDeletionService(store).RemoveSeat(context.Background(), "u", "dev", "bob"); err != nil {
		t.Fatalf("RemoveSeat: %v", err)
	}
	want := "links:s2,overlay:s2,resolved:s2,seat:s2,status:dev/bob"
	if got := strings.Join(store.calls, ","); got != want {
		t.Errorf("calls = %s\nwant    %s", got, want)
	}
}

func TestRemoveSeatAbsentRoomOrSeat(t *testing.T) {
	noRoom := &fakeRoomDeletionStore{}
	if err := NewRoomDeletionService(noRoom).RemoveSeat(context.Background(), "u", "ghost", "alice"); !errors.Is(err, ErrRoomNotFound) || len(noRoom.calls) != 0 {
		t.Errorf("absent room: err = %v, calls = %v", err, noRoom.calls)
	}
	noSeat := &fakeRoomDeletionStore{room: &repositories.Room{ID: "r1", Slug: "dev"}}
	if err := NewRoomDeletionService(noSeat).RemoveSeat(context.Background(), "u", "dev", "ghost"); !errors.Is(err, ErrSeatNotFound) || len(noSeat.calls) != 0 {
		t.Errorf("absent seat: err = %v, calls = %v", err, noSeat.calls)
	}
}
