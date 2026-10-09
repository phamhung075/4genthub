package routes

// Row 0413a1ce, the behaviour half. routes.Ownership is the checker Rule 2 consults for a frame the
// server stamped "system"; the wiring row assigns it in production. What must hold once it is
// assigned is that the CHECKER decides the frame - the connection's user owns the resource and
// receives it, or does not and is refused - with no dependence on the ENVIRONMENT string, which is
// only the reference's answer when the check cannot be made at all.

import (
	"context"
	"strings"
	"testing"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities"
)

// stubOwnership is a checker with one answer for every entity type.
type stubOwnership struct{ owned bool }

func (s stubOwnership) TaskOwnedBy(context.Context, string, string) (bool, error) {
	return s.owned, nil
}

func (s stubOwnership) SubtaskParentOwnedBy(context.Context, string, string) (bool, error) {
	return s.owned, nil
}

func (s stubOwnership) BranchOwnedBy(context.Context, string, string) (bool, error) {
	return s.owned, nil
}

func (s stubOwnership) ProjectOwnedBy(context.Context, string, string) (bool, error) {
	return s.owned, nil
}

func TestTheOwnershipCheckerDecidesASystemStampedFrame(t *testing.T) {
	previous := Ownership
	t.Cleanup(func() { Ownership = previous })

	for _, tc := range []struct {
		name          string
		owned         bool
		wantDelivered bool
	}{
		{"the resource owner receives the frame", true, true},
		{"a connection that does not own it is refused", false, false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			Ownership = stubOwnership{owned: tc.owned}
			actor := &fakeWS{}
			connectionsMu.Lock()
			connections[actor] = &WebSocketConnection{
				Websocket: actor,
				User:      &authdomain.User{ID: strPtr("u-actor")},
				ClientID:  "c1",
			}
			connectionsMu.Unlock()
			defer func() {
				connectionsMu.Lock()
				delete(connections, actor)
				connectionsMu.Unlock()
			}()

			data := entities.NewOrderedMap[any]()
			data.Set("id", "task-1")
			if err := BroadcastDataChange(context.Background(), "updated", "task", "task-1", "system", data, nil); err != nil {
				t.Fatalf("BroadcastDataChange: %v", err)
			}

			delivered := false
			for _, frame := range actor.sent {
				if strings.Contains(string(frame), `"action":"updated"`) {
					delivered = true
				}
			}
			if delivered != tc.wantDelivered {
				t.Fatalf("delivered=%v, want %v with the checker answering owned=%v: %v",
					delivered, tc.wantDelivered, tc.owned, actor.sent)
			}
			// A refusal must not be silent: this is the assertion the deleted
			// TestSystemStampedTaskUpdateIsRefusedForEveryConnection carried, moved here so it runs
			// with the checker installed rather than on an ambient environment string.
			if len(actor.sent) == 0 {
				t.Fatalf("the connection was told nothing at all with owned=%v", tc.owned)
			}
		})
	}
}

// TestTheEnvironmentStringDoesNotDecideWhenTheCheckerAnswers is the sharp edge of the row: the
// fallback reads ENVIRONMENT, so the checker's answer must be taken BEFORE it - in every environment,
// including the one where the fallback would have delivered the frame.
func TestTheEnvironmentStringDoesNotDecideWhenTheCheckerAnswers(t *testing.T) {
	previous := Ownership
	t.Cleanup(func() { Ownership = previous })

	for _, environment := range []string{"development", "production"} {
		t.Run(environment, func(t *testing.T) {
			t.Setenv("ENVIRONMENT", environment)
			// The checker says NOT owned. development would deliver the frame on its own, so a
			// delivery here means the environment string decided instead of the checker.
			Ownership = stubOwnership{owned: false}
			actor := &fakeWS{}
			connectionsMu.Lock()
			connections[actor] = &WebSocketConnection{
				Websocket: actor,
				User:      &authdomain.User{ID: strPtr("u-actor")},
				ClientID:  "c1",
			}
			connectionsMu.Unlock()
			defer func() {
				connectionsMu.Lock()
				delete(connections, actor)
				connectionsMu.Unlock()
			}()

			data := entities.NewOrderedMap[any]()
			data.Set("id", "task-1")
			if err := BroadcastDataChange(context.Background(), "updated", "task", "task-1", "system", data, nil); err != nil {
				t.Fatalf("BroadcastDataChange: %v", err)
			}

			for _, frame := range actor.sent {
				if strings.Contains(string(frame), `"action":"updated"`) {
					t.Fatalf("ENVIRONMENT=%s decided the frame while the checker said not-owned: %s",
						environment, frame)
				}
			}
			// A silent drop is not a refusal: without this the loop above passes vacuously on an
			// empty send, which is how a "not delivered" claim can be true for the wrong reason.
			if len(actor.sent) == 0 {
				t.Fatalf("ENVIRONMENT=%s: the connection was told nothing at all", environment)
			}
		})
	}
}
