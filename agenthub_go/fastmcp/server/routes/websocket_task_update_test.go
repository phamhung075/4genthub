package routes

// The 'updated' task frame is the one the operator's browser never received: the facade stamped it
// "system", and this gate refuses that stamp for every connection, because Rule 1 needs the ids to
// be equal and Rule 2's ownership checker has no implementation. These two cases are the delivery
// contract the new stamp must satisfy - the acting user receives its own task's frame, and the
// "system" stamp stays REFUSED rather than being exempted.

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

// TestSystemStampedTaskUpdateIsRefusedForEveryConnection pins the shortcut that is FORBIDDEN on this
// row: exempting a "system" stamp would deliver the frame without fixing who acted. The ownership
// checker Rule 2 falls back to does not exist, so the stamp had to change instead.
func TestSystemStampedTaskUpdateIsRefusedForEveryConnection(t *testing.T) {
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
	if len(actor.sent) != 1 || !strings.Contains(string(actor.sent[0]), "notification_blocked") {
		t.Fatalf("a system-stamped task update reached a connection instead of being refused: %v", actor.sent)
	}
}
