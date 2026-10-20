package orm

import (
	"context"
	"database/sql/driver"
	"strings"
	"testing"
	"time"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
)

// TestUpdateOccupantRecordsTheChange pins the write half of the occupant trail: the previous
// pair comes from the locked row and the new pair from the call, both in one record.
func TestUpdateOccupantRecordsTheChange(t *testing.T) {
	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		if strings.Contains(q, `FROM "seats"`) && strings.Contains(q, `FOR UPDATE`) {
			return []string{"runtime", "model"}, [][]driver.Value{fakeRow("claude-code", "sonnet")}, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMSeatRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	if err := repo.UpdateOccupant(context.Background(), testUser, testSeatID, "codex", "gpt-5.1", testUser); err != nil {
		t.Fatalf("UpdateOccupant: %v", err)
	}

	lockedSelect, seatUpdate := false, false
	for _, q := range f.recorded() {
		switch {
		case strings.Contains(q, `FROM "seats"`) && strings.Contains(q, `FOR UPDATE`):
			lockedSelect = true
		case strings.Contains(q, `UPDATE "seats"`) && strings.Contains(q, `"runtime" = $1, "model" = $2`):
			seatUpdate = true
		}
	}
	if !lockedSelect {
		t.Fatalf("no locked SELECT of the current occupant: %v", f.recorded())
	}
	if !seatUpdate {
		t.Fatalf("no seat overwrite: %v", f.recorded())
	}

	var insert *fakeExec
	for _, rec := range f.execRecords() {
		if strings.Contains(rec.query, `INSERT INTO "seat_occupant_changes"`) {
			found := rec
			insert = &found
		}
	}
	if insert == nil {
		t.Fatalf("no occupant change recorded: %v", f.recorded())
	}
	if len(insert.args) != 9 {
		t.Fatalf("occupant change args = %d, want 9: %v", len(insert.args), insert.args)
	}
	if args := insert.args; args[1] != testUser || args[2] != testSeatID || args[3] != testUser {
		t.Fatalf("record carries (user_id, seat_id, actor) = (%v, %v, %v), want (%s, %s, %s)",
			args[1], args[2], args[3], testUser, testSeatID, testUser)
	}
	at, ok := insert.args[4].(time.Time)
	if !ok || at.IsZero() {
		t.Fatalf("recorded at = %v, want a non-zero time", insert.args[4])
	}
	if insert.args[5] != "claude-code" || insert.args[6] != "sonnet" {
		t.Fatalf("from = (%v, %v), want (claude-code, sonnet) from the locked row", insert.args[5], insert.args[6])
	}
	if insert.args[7] != "codex" || insert.args[8] != "gpt-5.1" {
		t.Fatalf("to = (%v, %v), want (codex, gpt-5.1) from the call", insert.args[7], insert.args[8])
	}
}

// TestUpdateOccupantSkipsTheRecordForANoOp pins the idempotent retry: writing the stored values
// moves neither updated_at nor the trail.
func TestUpdateOccupantSkipsTheRecordForANoOp(t *testing.T) {
	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		if strings.Contains(q, `FROM "seats"`) && strings.Contains(q, `FOR UPDATE`) {
			return []string{"runtime", "model"}, [][]driver.Value{fakeRow("codex", "gpt-5.1")}, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMSeatRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	if err := repo.UpdateOccupant(context.Background(), testUser, testSeatID, "codex", "gpt-5.1", testUser); err != nil {
		t.Fatalf("UpdateOccupant(no-op): %v", err)
	}
	assertNoStatement(t, f, `UPDATE "seats"`)
	assertNoStatement(t, f, `INSERT INTO "seat_occupant_changes"`)
}

// TestListOccupantChangesIsTenantScoped pins the read: both tenant filters and newest first.
func TestListOccupantChangesIsTenantScoped(t *testing.T) {
	at := time.Date(2026, 10, 20, 19, 1, 34, 0, time.UTC)
	const changeID = "66666666-6666-4666-8666-666666666666"

	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		if strings.Contains(q, `FROM "seat_occupant_changes"`) {
			return []string{"id", "user_id", "seat_id", "actor", "at", "from_runtime", "from_model", "to_runtime", "to_model"},
				[][]driver.Value{fakeRow(changeID, testUser, testSeatID, "actor-9", at, "claude-code", "sonnet", "codex", "gpt-5.1")}, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMSeatRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	got, err := repo.ListOccupantChanges(context.Background(), testUser, testSeatID)
	if err != nil {
		t.Fatalf("ListOccupantChanges: %v", err)
	}
	want := domainrepo.OccupantChange{
		ID: changeID, UserID: testUser, SeatID: testSeatID, Actor: "actor-9", At: at,
		FromRuntime: "claude-code", FromModel: "sonnet", ToRuntime: "codex", ToModel: "gpt-5.1",
	}
	if len(got) != 1 || got[0] != want {
		t.Fatalf("ListOccupantChanges = %+v, want one %+v", got, want)
	}

	found := false
	for _, q := range f.recorded() {
		if !strings.Contains(q, `FROM "seat_occupant_changes"`) {
			continue
		}
		found = true
		for _, scope := range []string{`"user_id" = $1`, `"seat_id" = $2`, `ORDER BY "at" DESC`} {
			if !strings.Contains(q, scope) {
				t.Fatalf("occupant change query lacks %q: %s", scope, q)
			}
		}
	}
	if !found {
		t.Fatalf("no occupant change query recorded: %v", f.recorded())
	}
}
