package routes

// The 'updated' task frame is the one the operator's browser never received: the facade stamped it
// "system". WHAT REFUSES IT IS OWNERSHIP, NOT THE STAMP. With the checker assigned (httpapp/
// ownership_wiring.go, via NewApp) a system-stamped frame reaches the connection whose user owns the
// resource and is refused for one that does not - pinned by TestTheOwnershipCheckerDecidesASystemStampedFrame
// and, under both environment strings, by TestTheEnvironmentStringDoesNotDecideWhenTheCheckerAnswers
// in websocket_ownership_checker_test.go. The case below is the other half of the delivery contract:
// the acting user receives its own task's frame, with the keys the client contract needs intact.
//
// THE CASE THIS FILE NO LONGER CARRIES, because a claim like it would be false of the shipped runtime:
// what a system-stamped frame does when NO checker is assigned and no check can be made. Then the
// answer is the ENVIRONMENT string - development delivers, production refuses - so a case asserting
// refusal there is green only because the ambient ENVIRONMENT is not development, and it FAILS under
// ENVIRONMENT=development with the frame delivered - MEASURED at the gate on 67af511f, which is what
// made the name false rather than merely optimistic.
// TestSystemStampedTaskUpdateIsRefusedForEveryConnection
// was exactly that: its name and header claimed a property of the stamp, and its green came from the
// environment. It was deleted by the gate on 67af511f rather than renamed around, and its one unique
// assertion - that the refusing connection is TOLD, rather than silently dropped - moved to the
// not-owned cases above, where the checker is installed.

import (
	"context"
	"strings"
	"testing"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities"
)

func TestTaskUpdatedFrameReachesTheActingUsersSocket(t *testing.T) {
	actor, other := &fakeWS{}, &fakeWS{}
	connectionsMu.Lock()
	connections[actor] = &WebSocketConnection{
		Websocket: actor,
		User:      &authdomain.User{ID: strPtr("u-actor")},
		ClientID:  "c1",
	}
	connections[other] = &WebSocketConnection{
		Websocket: other,
		User:      &authdomain.User{ID: strPtr("u-other")},
		ClientID:  "c2",
	}
	connectionsMu.Unlock()
	defer func() {
		connectionsMu.Lock()
		delete(connections, actor)
		delete(connections, other)
		connectionsMu.Unlock()
	}()

	data := entities.NewOrderedMap[any]()
	data.Set("id", "task-1")
	data.Set("status", "in_progress")

	// The frame the facade emits for a status change: EventType "updated", stamped with the user
	// who made it.
	if err := BroadcastDataChange(context.Background(), "updated", "task", "task-1", "u-actor", data, nil); err != nil {
		t.Fatalf("BroadcastDataChange: %v", err)
	}

	if len(actor.sent) != 1 {
		t.Fatalf("the acting user received %d frames, want 1: %v", len(actor.sent), actor.sent)
	}
	body := string(actor.sent[0])
	// The client contract: metadata.version/type select the handler, payload.entity routes it, and
	// payload.data.primary IS the task dict the hook caches. Keep all three as they are.
	for _, want := range []string{
		`"version":"2.0"`, `"type":"update"`,
		`"entity":"task"`, `"action":"updated"`,
		`"userId":"u-actor"`, `"source":"user"`,
		`"id":"task-1"`, `"status":"in_progress"`,
	} {
		if !strings.Contains(body, want) {
			t.Fatalf("the delivered frame is missing %s: %s", want, body)
		}
	}
	if len(other.sent) == 0 || !strings.Contains(string(other.sent[0]), "authorization_denied") {
		t.Fatalf("the second user was not told the event was denied: %v", other.sent)
	}
}
