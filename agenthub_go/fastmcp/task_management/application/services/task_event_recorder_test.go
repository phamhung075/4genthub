package services

import (
	"context"
	"errors"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// ledgerSpy is the ledger as the recorder needs it. It records the entry it is HANDED, so a case
// reads what the recorder decided rather than what some caller passed in.
type ledgerSpy struct {
	appended []entities.AppendTaskEvent
}

func (s *ledgerSpy) AppendInTx(_ context.Context, in entities.AppendTaskEvent) (*entities.TaskEvent, error) {
	s.appended = append(s.appended, in)
	return &entities.TaskEvent{TaskID: in.TaskID, Kind: in.Kind}, nil
}

func (s *ledgerSpy) StatusOf(context.Context, string) (string, error) { return "todo", nil }

// WHO a status write is attributed to is the recorder's decision, taken from the request rather
// than from a name each caller had to invent: a request that named a seat through the MCP header is
// that SEAT acting on the caller's behalf, a request that named no seat belongs to the user whose
// recorder this is, and a recorder built with NEITHER refuses rather than stamping something
// anonymous - an unattributable write is the one thing this ledger exists to prevent, so the third
// case asserts a refusal AND that nothing reached the ledger.
func TestRecorderAttributesAStatusWrite(t *testing.T) {
	cases := []struct {
		name    string
		seatID  string
		user    string
		want    entities.TaskEventActorKind
		wantID  string
		wantErr error
	}{
		{name: "the request named a seat", seatID: "alpha/beta", user: "user-1",
			want: entities.TaskEventActorSeat, wantID: "alpha/beta"},
		{name: "the request named no seat", user: "user-1",
			want: entities.TaskEventActorHuman, wantID: "user-1"},
		{name: "no actor anywhere", wantErr: ErrNoActor},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			spy := &ledgerSpy{}
			ctx := context.Background()
			if tc.seatID != "" {
				ctx = WithActor(ctx, SeatActor(tc.seatID))
			}
			_, err := NewTaskEventRecorder(spy, tc.user).RecordStatusChange(ctx, "task-1", "todo", "in_progress")
			if tc.wantErr != nil {
				if !errors.Is(err, tc.wantErr) {
					t.Fatalf("err = %v, want %v: a write with no actor must be REFUSED rather than attributed", err, tc.wantErr)
				}
				if len(spy.appended) != 0 {
					t.Fatalf("entries written = %d, want 0: the refusal must not reach the ledger", len(spy.appended))
				}
				t.Logf("OBSERVED refusal = %v (seat=%q user=%q)", err, tc.seatID, tc.user)
				return
			}
			if err != nil {
				t.Fatalf("RecordStatusChange: %v", err)
			}
			if len(spy.appended) != 1 {
				t.Fatalf("entries written = %d, want exactly 1", len(spy.appended))
			}
			got := spy.appended[0]
			t.Logf("OBSERVED actor = %s/%q (seat=%q user=%q)", got.ActorKind, got.ActorID, tc.seatID, tc.user)
			if got.ActorKind != tc.want || got.ActorID != tc.wantID {
				t.Fatalf("actor = %s/%q, want %s/%q", got.ActorKind, got.ActorID, tc.want, tc.wantID)
			}
			if got.Payload["old"] != "todo" || got.Payload["new"] != "in_progress" {
				t.Fatalf("payload = %v, want the transition it recorded", got.Payload)
			}
		})
	}
}
