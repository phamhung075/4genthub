package orm

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"testing"
	"time"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// The message store against REAL SQL, which is where the ruled behaviours actually live: the keyset
// page that must not skip or repeat a row, and the `delivered_at IS NULL` update that is what makes a
// redelivery impossible once a client has acknowledged a message and possible until then.
//
// Gated exactly like its neighbour: without SEAT_TEST_DATABASE_URL it skips rather than pretending. The
// route and service tests cover the ordering and the refusals against a fake store; this file covers the
// statements the fake cannot.
func TestSeatMessageRepositoryIntegration(t *testing.T) {
	url := os.Getenv("SEAT_TEST_DATABASE_URL")
	if url == "" {
		t.Skip("SEAT_TEST_DATABASE_URL not set")
	}
	db, err := sql.Open("pgx", url)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx := context.Background()
	if err := db.PingContext(ctx); err != nil {
		t.Fatalf("ping: %v", err)
	}
	if _, err := db.ExecContext(ctx, seatIntegrationSchema(t)); err != nil {
		t.Fatalf("apply schema: %v", err)
	}
	sessions := database.NewSessionManager(&database.DatabaseConfig{Engine: &database.Engine{DB: db}})
	userID := fmt.Sprintf("seat-msg-it-%d", time.Now().UnixNano())
	other := fmt.Sprintf("seat-msg-it-other-%d", time.Now().UnixNano())

	messages, err := NewORMSeatMessageRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	base := time.Now().UTC().Truncate(time.Microsecond)
	store := func(user, room, seat, text string, at time.Time) domainrepo.SeatMessage {
		t.Helper()
		stored, err := messages.Create(ctx, domainrepo.SeatMessage{
			UserID: user, Room: room, Seat: seat, Text: text, CreatedAt: at,
		})
		if err != nil {
			t.Fatalf("Create(%s): %v", text, err)
		}
		if stored.ID == "" || !stored.Pending() {
			t.Fatalf("created row = %+v, want an id and a pending state", stored)
		}
		return *stored
	}

	// TWO MESSAGES IN THE SAME INSTANT: the id tiebreak is what keeps the page stable, so this is the
	// case an ORDER BY created_at alone would answer non-deterministically.
	first := store(userID, "dev", "coder", "first", base)
	tie := store(userID, "dev", "coder", "tie", base)
	third := store(userID, "dev", "coder", "third", base.Add(time.Second))
	// Another seat and another tenant, both of which every read below must leave alone.
	store(userID, "dev", "reviewer", "other seat", base)
	store(other, "dev", "coder", "other tenant", base)

	page, err := messages.ListPending(ctx, userID, "dev", "coder", time.Time{}, "", 10)
	if err != nil {
		t.Fatalf("ListPending: %v", err)
	}
	if len(page) != 3 {
		t.Fatalf("pending = %d rows, want the seat's 3 (not the other seat's, not the other tenant's)", len(page))
	}
	if page[0].Text != "first" || page[1].Text != "tie" || page[2].Text != "third" {
		t.Fatalf("order = %q,%q,%q, want oldest first with the same-instant pair ordered by id",
			page[0].Text, page[1].Text, page[2].Text)
	}
	if page[0].CreatedAt.After(page[1].CreatedAt) || page[1].CreatedAt.After(page[2].CreatedAt) {
		t.Fatalf("instants are not non-decreasing: %v", page)
	}

	// THE KEYSET WALKS THE SAME SET, and a message that lands WHILE the walk is in progress must not
	// make the next page skip or repeat a row: that is what the cursor pair is for, and an offset would
	// fail exactly here.
	firstPage, err := messages.ListPending(ctx, userID, "dev", "coder", time.Time{}, "", 2)
	if err != nil {
		t.Fatal(err)
	}
	if len(firstPage) != 2 {
		t.Fatalf("first page = %d rows, want 2", len(firstPage))
	}
	store(userID, "dev", "coder", "arrived mid-walk", base.Add(time.Millisecond))
	cursor := firstPage[len(firstPage)-1]
	secondPage, err := messages.ListPending(ctx, userID, "dev", "coder", cursor.CreatedAt, cursor.ID, 10)
	if err != nil {
		t.Fatal(err)
	}
	seen := map[string]bool{}
	for _, m := range append(append([]domainrepo.SeatMessage{}, firstPage...), secondPage...) {
		if seen[m.ID] {
			t.Fatalf("the walk repeated %s across its pages", m.ID)
		}
		seen[m.ID] = true
	}
	for _, m := range page {
		if !seen[m.ID] {
			t.Errorf("the walk skipped %s (%q)", m.ID, m.Text)
		}
	}

	// THE ACK IS WHAT STOPS A REDELIVERY, and a second ack finds nothing: the row keeps the first
	// machine and instant that took it.
	acked, err := messages.Ack(ctx, userID, "dev", "coder", first.ID, "pc-home", base.Add(2*time.Second))
	if err != nil || !acked {
		t.Fatalf("Ack = %v (%v), want true", acked, err)
	}
	if again, err := messages.Ack(ctx, userID, "dev", "coder", first.ID, "pc-two", base.Add(3*time.Second)); err != nil || again {
		t.Fatalf("second Ack = %v (%v), want false", again, err)
	}
	if wrongSeat, err := messages.Ack(ctx, userID, "dev", "reviewer", third.ID, "pc-home", base); err != nil || wrongSeat {
		t.Fatalf("Ack through another seat = %v (%v), want false", wrongSeat, err)
	}
	if otherTenant, err := messages.Ack(ctx, other, "dev", "coder", third.ID, "pc-home", base); err != nil || otherTenant {
		t.Fatalf("Ack through another tenant = %v (%v), want false", otherTenant, err)
	}
	remaining, err := messages.ListPending(ctx, userID, "dev", "coder", time.Time{}, "", 10)
	if err != nil {
		t.Fatal(err)
	}
	for _, m := range remaining {
		if m.ID == first.ID {
			t.Fatalf("the acknowledged message came back: %+v", m)
		}
	}
	if tied, err := messages.ListPending(ctx, userID, "dev", "coder", tie.CreatedAt, tie.ID, 10); err != nil || len(tied) == 0 || tied[0].Text == "first" {
		t.Fatalf("the cursor past the first row returned %+v (%v), want the rows after it", tied, err)
	}

	// THE DELETES ARE THE APPLICATION-LAYER CASCADE, and they are scoped by the names they are given:
	// the seat's own rows go, the neighbouring seat's and the other tenant's stay.
	if err := messages.DeleteForSeat(ctx, userID, "dev", "coder"); err != nil {
		t.Fatal(err)
	}
	if left, err := messages.ListPending(ctx, userID, "dev", "coder", time.Time{}, "", 10); err != nil || len(left) != 0 {
		t.Fatalf("after DeleteForSeat: %d rows (%v), want none", len(left), err)
	}
	if kept, err := messages.ListPending(ctx, userID, "dev", "reviewer", time.Time{}, "", 10); err != nil || len(kept) != 1 {
		t.Fatalf("the neighbouring seat lost its row: %d (%v)", len(kept), err)
	}
	if kept, err := messages.ListPending(ctx, other, "dev", "coder", time.Time{}, "", 10); err != nil || len(kept) != 1 {
		t.Fatalf("the other tenant lost its row: %d (%v)", len(kept), err)
	}
	if err := messages.DeleteForRoom(ctx, userID, "dev"); err != nil {
		t.Fatal(err)
	}
	if kept, err := messages.ListPending(ctx, other, "dev", "coder", time.Time{}, "", 10); err != nil || len(kept) != 1 {
		t.Fatalf("DeleteForRoom crossed the tenant boundary: %d rows left for the other user (%v)", len(kept), err)
	}
	_ = third
}
