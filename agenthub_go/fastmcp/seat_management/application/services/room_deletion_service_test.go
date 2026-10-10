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

func (f *fakeRoomDeletionStore) DeleteMachineEdgesForRoom(_ context.Context, _, roomSlug string) error {
	return f.record("edges:" + roomSlug)
}

func (f *fakeRoomDeletionStore) DeleteSeatMessagesForSeat(_ context.Context, _, roomSlug, seatKey string) error {
	return f.record("messages:" + roomSlug + "/" + seatKey)
}

func (f *fakeRoomDeletionStore) DeleteSeatMessagesForRoom(_ context.Context, _, roomSlug string) error {
	return f.record("messages:" + roomSlug)
}

func (f *fakeRoomDeletionStore) DeleteRoom(_ context.Context, _, roomID string) error {
	return f.record("room:" + roomID)
}

func (f *fakeRoomDeletionStore) InTransaction(ctx context.Context, fn func(ctx context.Context) error) error {
	f.calls = append(f.calls, "tx-begin")
	err := fn(ctx)
	f.calls = append(f.calls, "tx-end")
	return err
}

// A room that still holds seats is refused, naming how many, and not one dependent row is
// touched: deleting a room never cascades its seats away.
func TestDeleteRoomRefusesARoomThatHoldsSeats(t *testing.T) {
	store := &fakeRoomDeletionStore{
		room:  &repositories.Room{ID: "r1", Slug: "dev"},
		seats: []repositories.Seat{{ID: "s1"}, {ID: "s2"}},
	}
	err := NewRoomDeletionService(store).DeleteRoom(context.Background(), "u", "dev")
	if !errors.Is(err, ErrRoomNotEmpty) {
		t.Fatalf("err = %v, want ErrRoomNotEmpty", err)
	}
	if !strings.Contains(err.Error(), `room "dev" still holds 2 seat(s)`) {
		t.Errorf("err = %q, want it to name the count", err)
	}
	for _, call := range store.calls {
		if call != "tx-begin" && call != "tx-end" {
			t.Errorf("a refused delete touched rows: %v", store.calls)
		}
	}
}

// An empty room deletes its room overlay, its reported statuses, its undelivered seat messages, its
// reported topology edges and itself, in one transaction, and nothing else.
//
// THE MESSAGE DELETE IS THE RULED OBLIGATION, and it is on this path rather than left to a CASCADE
// because this schema has none: text addressed to a seat the room no longer has can never be
// delivered, so it goes with the room rather than waiting forever.
func TestDeleteRoomDeletesAnEmptyRoom(t *testing.T) {
	store := &fakeRoomDeletionStore{room: &repositories.Room{ID: "r1", Slug: "dev"}}
	if err := NewRoomDeletionService(store).DeleteRoom(context.Background(), "u", "dev"); err != nil {
		t.Fatalf("DeleteRoom: %v", err)
	}
	want := "tx-begin,room-overlay:r1,status:dev,messages:dev,edges:dev,room:r1,tx-end"
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

// A failing delete in the empty-room transaction stops the remaining deletes and propagates, so
// InTransaction rolls back whatever came before and the room row is never removed.
func TestDeleteRoomStopsAtFirstFailure(t *testing.T) {
	boom := errors.New("boom")
	for _, failOn := range []string{"room-overlay:r1", "status:dev", "messages:dev"} {
		store := &fakeRoomDeletionStore{
			room:   &repositories.Room{ID: "r1", Slug: "dev"},
			failOn: failOn, failErr: boom,
		}
		if err := NewRoomDeletionService(store).DeleteRoom(context.Background(), "u", "dev"); !errors.Is(err, boom) {
			t.Fatalf("fail on %s: err = %v, want boom", failOn, err)
		}
		for _, call := range store.calls {
			if call == "room:r1" {
				t.Errorf("fail on %s: the room row was deleted after a failure: %v", failOn, store.calls)
			}
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
	want := "tx-begin,links:s2,overlay:s2,resolved:s2,seat:s2,status:dev/bob,messages:dev/bob,tx-end"
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

// A failing delete inside RemoveSeat's transaction stops the remaining deletes and returns the
// error, which is what makes InTransaction roll every earlier delete back.
func TestRemoveSeatFailureInTheTransactionStopsAndPropagates(t *testing.T) {
	boom := errors.New("boom")
	for _, failOn := range []string{"links:s2", "overlay:s2", "resolved:s2", "seat:s2", "status:dev/bob", "messages:dev/bob"} {
		store := &fakeRoomDeletionStore{
			room:   &repositories.Room{ID: "r1", Slug: "dev"},
			seats:  []repositories.Seat{{ID: "s2", SeatKey: "bob"}},
			failOn: failOn, failErr: boom,
		}
		err := NewRoomDeletionService(store).RemoveSeat(context.Background(), "u", "dev", "bob")
		if !errors.Is(err, boom) {
			t.Fatalf("fail on %s: err = %v, want boom", failOn, err)
		}
		if store.calls[0] != "tx-begin" || store.calls[len(store.calls)-1] != "tx-end" || store.calls[len(store.calls)-2] != failOn {
			t.Errorf("fail on %s: calls = %v, want every delete inside the transaction, ending at the failing one", failOn, store.calls)
		}
	}
}
