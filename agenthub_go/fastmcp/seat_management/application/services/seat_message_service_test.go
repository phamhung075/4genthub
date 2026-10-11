package services

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/seat_management/domain/repositories"
)

// fakeSeatMessageStore is the store the service talks to, in memory, and it holds the two behaviours
// the contract names: a stored message is PENDING, and an acked one is gone from the pending set.
// The SQL semantics behind them (the keyset page, the delivered_at IS NULL update) are the real
// repository's, and are covered where a database is available.
type fakeSeatMessageStore struct {
	pending []repositories.SeatMessage
	created []repositories.SeatMessage
	acked   []string

	listAfter   time.Time
	listAfterID string
	listLimit   int
	lastMachine string
}

func (f *fakeSeatMessageStore) Create(_ context.Context, message repositories.SeatMessage) (*repositories.SeatMessage, error) {
	message.ID = fmt.Sprintf("m%d", len(f.created)+1)
	f.created = append(f.created, message)
	f.pending = append(f.pending, message)
	stored := message
	return &stored, nil
}

func (f *fakeSeatMessageStore) ListPending(_ context.Context, _, room, seat string, afterCreatedAt time.Time, afterID string, limit int) ([]repositories.SeatMessage, error) {
	f.listAfter, f.listAfterID, f.listLimit = afterCreatedAt, afterID, limit
	out := []repositories.SeatMessage{}
	for _, m := range f.pending {
		if m.Room != room || m.Seat != seat {
			continue
		}
		// The keyset the repository uses, minus its id tiebreak: these fixtures use distinct instants.
		if !afterCreatedAt.IsZero() && !m.CreatedAt.After(afterCreatedAt) {
			continue
		}
		out = append(out, m)
	}
	if len(out) > limit {
		out = out[:limit]
	}
	return out, nil
}

func (f *fakeSeatMessageStore) Ack(_ context.Context, _, room, seat, id, machineID string, _ time.Time) (bool, error) {
	f.lastMachine = machineID
	for i, m := range f.pending {
		if m.ID == id && m.Room == room && m.Seat == seat {
			f.pending = append(f.pending[:i], f.pending[i+1:]...)
			f.acked = append(f.acked, id)
			return true, nil
		}
	}
	return false, nil
}

var seatMessageServiceNow = time.Date(2026, 10, 10, 9, 0, 0, 0, time.UTC)

// The send is trimmed, the identifiers are the caller's, and the stored row is the one the answer
// carries — the same instant, because the service is handed the clock rather than reading its own.
func TestSeatMessageSendStoresTheTrimmedText(t *testing.T) {
	store := &fakeSeatMessageStore{}
	stored, err := NewSeatMessageService(store).Send(context.Background(), "u1",
		SeatMessageInput{Room: "dev", Seat: "coder", Text: "  hello  "}, seatMessageServiceNow)
	if err != nil {
		t.Fatalf("Send: %v", err)
	}
	if stored.Text != "hello" || stored.UserID != "u1" || stored.Room != "dev" || stored.Seat != "coder" {
		t.Errorf("stored = %+v, want the trimmed text under the caller's tenant and URL pair", stored)
	}
	if !stored.CreatedAt.Equal(seatMessageServiceNow) || !stored.Pending() {
		t.Errorf("stored = %+v, want the supplied instant and a pending row", stored)
	}
}

// THE RULED OBLIGATION: the chat window is where an operator pastes a token, so the scan runs before
// anything is stored, the rejection NAMES THE FIELD, and the credential never reaches the store.
func TestSeatMessageSendRefusesACredentialAndNamesTheField(t *testing.T) {
	const secret = "ghp_0123456789012345678901234567890123"
	store := &fakeSeatMessageStore{}
	_, err := NewSeatMessageService(store).Send(context.Background(), "u1",
		SeatMessageInput{Room: "dev", Seat: "coder", Text: "the call failed with " + secret + " in the header"},
		seatMessageServiceNow)

	var rejection *SeatMessageRejection
	if !errors.As(err, &rejection) {
		t.Fatalf("err = %v, want a SeatMessageRejection", err)
	}
	if rejection.SecretField != "text" || rejection.Message != "secret detected in field text" {
		t.Errorf("rejection = %+v, want the field named as text", rejection)
	}
	if strings.Contains(rejection.Message, secret) {
		t.Errorf("the rejection repeats the credential: %q", rejection.Message)
	}
	if len(store.created) != 0 {
		t.Errorf("a refused message was stored: %+v", store.created)
	}
}

// The write contract's other refusals, each with the sentence the window renders.
func TestSeatMessageSendRefusesBadNamesAndBadText(t *testing.T) {
	cases := []struct {
		name  string
		input SeatMessageInput
		want  string
	}{
		{"empty text", SeatMessageInput{Room: "dev", Seat: "coder", Text: "   "}, "text must not be empty"},
		{"a room that is not a name", SeatMessageInput{Room: "dev/../etc", Seat: "coder", Text: "x"}, "room slug"},
		{"a seat that is not a name", SeatMessageInput{Room: "dev", Seat: ".", Text: "x"}, "seat key"},
		{
			"text past the bound",
			SeatMessageInput{Room: "dev", Seat: "coder", Text: strings.Repeat("x", SeatMessageMaxText+1)},
			"cannot exceed",
		},
	}
	for _, c := range cases {
		store := &fakeSeatMessageStore{}
		_, err := NewSeatMessageService(store).Send(context.Background(), "u1", c.input, seatMessageServiceNow)
		var rejection *SeatMessageRejection
		if !errors.As(err, &rejection) || !strings.Contains(rejection.Message, c.want) {
			t.Errorf("%s: err = %v, want a rejection mentioning %q", c.name, err, c.want)
		}
		if rejection != nil && rejection.SecretField != "" {
			t.Errorf("%s: wrote a field name for a reason that is not a credential: %+v", c.name, rejection)
		}
		if len(store.created) != 0 {
			t.Errorf("%s: a refused message was stored", c.name)
		}
	}
}

// THE PAGE HAS ONE SOURCE OF TRUTH: the caller's limit is clamped by the service, and the cursor is
// the store's keyset rendered as an opaque string the caller only echoes back.
func TestSeatMessagePullClampsThePageAndEchoesAnOpaqueCursor(t *testing.T) {
	store := &fakeSeatMessageStore{}
	svc := NewSeatMessageService(store)
	first := seatMessageServiceNow
	second := seatMessageServiceNow.Add(time.Second)
	if _, err := svc.Send(context.Background(), "u1", SeatMessageInput{Room: "dev", Seat: "coder", Text: "one"}, first); err != nil {
		t.Fatal(err)
	}
	if _, err := svc.Send(context.Background(), "u1", SeatMessageInput{Room: "dev", Seat: "coder", Text: "two"}, second); err != nil {
		t.Fatal(err)
	}

	messages, cursor, err := svc.Pull(context.Background(), "u1", "dev", "coder", "", 1)
	if err != nil {
		t.Fatalf("Pull: %v", err)
	}
	if len(messages) != 1 || messages[0].Text != "one" {
		t.Fatalf("page = %+v, want the first message alone", messages)
	}
	if store.listLimit != 1 {
		t.Errorf("store limit = %d, want the caller's 1", store.listLimit)
	}
	if cursor == "" || !strings.Contains(cursor, "|") {
		t.Fatalf("cursor = %q, want an opaque pair", cursor)
	}

	// The cursor is what continues the walk, and it is echoed rather than composed by the caller.
	next, _, err := svc.Pull(context.Background(), "u1", "dev", "coder", cursor, SeatMessageMaxLimit+50)
	if err != nil {
		t.Fatalf("Pull after cursor: %v", err)
	}
	if len(next) != 1 || next[0].Text != "two" {
		t.Fatalf("second page = %+v, want the second message alone", next)
	}
	if store.listLimit != SeatMessageMaxLimit {
		t.Errorf("store limit = %d, want the clamp %d", store.listLimit, SeatMessageMaxLimit)
	}
	if store.listAfter.IsZero() {
		t.Error("the store was asked for the first page again: the cursor did not reach it")
	}
}

// The default limit applies when the caller names none, and a cursor that is not one of ours is a
// rejection rather than an empty page: an empty page would read as "nothing is waiting" and drop the
// backlog the caller cannot see.
func TestSeatMessagePullDefaultsAndRefusesAMangledCursor(t *testing.T) {
	store := &fakeSeatMessageStore{}
	svc := NewSeatMessageService(store)
	if _, _, err := svc.Pull(context.Background(), "u1", "dev", "coder", "", 0); err != nil {
		t.Fatalf("Pull: %v", err)
	}
	if store.listLimit != SeatMessageDefaultLimit {
		t.Errorf("store limit = %d, want the default %d", store.listLimit, SeatMessageDefaultLimit)
	}
	for _, after := range []string{"not-a-cursor", "2026-10-10T09:00:00Z", "|missing-instant"} {
		_, _, err := svc.Pull(context.Background(), "u1", "dev", "coder", after, 10)
		var rejection *SeatMessageRejection
		if !errors.As(err, &rejection) {
			t.Errorf("after %q: err = %v, want a rejection", after, err)
		}
	}
}

// THE DELIVERY CONTRACT, in two halves: an ack takes the message out of the pending set so the next
// pull does not hand it out again, and a SECOND ack of the same id is refused rather than counted as a
// second delivery. This is what makes at-least-once safe — an unacked message comes back, an acked one
// does not.
func TestSeatMessageAckIsTheSecondHalfOfDelivery(t *testing.T) {
	store := &fakeSeatMessageStore{}
	svc := NewSeatMessageService(store)
	stored, err := svc.Send(context.Background(), "u1", SeatMessageInput{Room: "dev", Seat: "coder", Text: "hello"}, seatMessageServiceNow)
	if err != nil {
		t.Fatal(err)
	}

	// Unacked, the message is still handed out: an interruption before the ack means redelivery
	// rather than loss.
	messages, _, err := svc.Pull(context.Background(), "u1", "dev", "coder", "", 10)
	if err != nil || len(messages) != 1 {
		t.Fatalf("unacked pull = %+v (%v), want the message again", messages, err)
	}

	if err := svc.Ack(context.Background(), "u1", "dev", "coder", stored.ID, "pc-home", seatMessageServiceNow); err != nil {
		t.Fatalf("Ack: %v", err)
	}
	if store.lastMachine != "pc-home" {
		t.Errorf("the ack recorded machine %q, want the machine that delivered it", store.lastMachine)
	}
	messages, _, err = svc.Pull(context.Background(), "u1", "dev", "coder", "", 10)
	if err != nil || len(messages) != 0 {
		t.Fatalf("pull after ack = %+v (%v), want nothing redelivered", messages, err)
	}
	if err := svc.Ack(context.Background(), "u1", "dev", "coder", stored.ID, "pc-home", seatMessageServiceNow); !errors.Is(err, ErrSeatMessageNotPending) {
		t.Errorf("second ack err = %v, want ErrSeatMessageNotPending", err)
	}
	// An id that was never this seat's is the same refusal, so a caller cannot use the ack to probe
	// another seat's ids.
	if err := svc.Ack(context.Background(), "u1", "dev", "other", "m1", "pc-home", seatMessageServiceNow); !errors.Is(err, ErrSeatMessageNotPending) {
		t.Errorf("ack for another seat err = %v, want ErrSeatMessageNotPending", err)
	}
}
