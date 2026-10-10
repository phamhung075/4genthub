package services

import (
	"context"
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
// an agent acting on the caller's behalf, a request that named no seat belongs to the user whose
// recorder this is, and only a recorder built with no user at all falls back to the system.
//
// The seat class is spelled `agent` because that is the landed task_events vocabulary; the
// architecture names this identity `seat` (section 2.5) and P1 lands that spelling. The deviation
// is named here, in the commit and in the changelog rather than left to be rediscovered.
func TestRecorderAttributesAStatusWrite(t *testing.T) {
	cases := []struct {
		name   string
		seatID string
		user   string
		want   entities.TaskEventActorKind
		wantID string
	}{
		{name: "the request named a seat", seatID: "alpha/beta", user: "user-1",
			want: entities.TaskEventActorAgent, wantID: "alpha/beta"},
		{name: "the request named no seat", user: "user-1",
			want: entities.TaskEventActorUser, wantID: "user-1"},
		{name: "no acting user at all",
			want: entities.TaskEventActorSystem, wantID: entities.TaskEventActorSystemID},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			spy := &ledgerSpy{}
			ctx := context.Background()
			if tc.seatID != "" {
				ctx = WithActor(ctx, SeatActor(tc.seatID))
			}
			if _, err := NewTaskEventRecorder(spy, tc.user).RecordStatusChange(ctx, "task-1", "todo", "in_progress"); err != nil {
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
