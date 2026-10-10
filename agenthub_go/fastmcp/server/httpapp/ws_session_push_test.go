package httpapp

// The browser push half of rigd-boundaries.md 2.3a: every `session` frame that registers a NEW
// (user_id, connector_id, session_key) emits one `agent_session` frame with action `created`; a
// later frame that changes the seat_state or the status emits `updated`; a frame that changes
// neither emits nothing; and MarkOffline emits one `updated` frame per session it marks.
//
// The frames are observed through the same package-level seam style the seat routes use
// (seatBroadcastFn in seat_admin_mount.go): the socket path calls agentSessionBroadcastFn, and a
// test replaces it, so the contract is checked without a live realtime socket. The cases read the
// database, so they run on the Postgres named by AGENTHUB_TEST_PG_URL (recipe in
// session_stream/testdb) and skip without it.

import (
	"context"
	"sync"
	"testing"
	"time"

	"agenthub/fastmcp/session_stream"
	"agenthub/fastmcp/task_management/domain/entities"
)

// recordedAgentSessionFrame is one frame the socket path handed to the seam.
type recordedAgentSessionFrame struct {
	action, entity, id, userID string
	seatState, status          any
}

// agentSessionFrameRecorder collects the frames emitted while a test holds the seam.
type agentSessionFrameRecorder struct {
	mu     sync.Mutex
	frames []recordedAgentSessionFrame
}

// installAgentSessionFrames swaps the seam and restores it when the test ends.
func installAgentSessionFrames(t *testing.T) *agentSessionFrameRecorder {
	t.Helper()
	rec := &agentSessionFrameRecorder{}
	previous := agentSessionBroadcastFn
	agentSessionBroadcastFn = func(_ context.Context, action, entity, id, userID string, data *entities.OrderedMap[any]) error {
		seatState, _ := data.Get("seat_state")
		status, _ := data.Get("status")
		rec.mu.Lock()
		rec.frames = append(rec.frames, recordedAgentSessionFrame{action, entity, id, userID, seatState, status})
		rec.mu.Unlock()
		return nil
	}
	t.Cleanup(func() { agentSessionBroadcastFn = previous })
	return rec
}

func (r *agentSessionFrameRecorder) snapshot() []recordedAgentSessionFrame {
	r.mu.Lock()
	defer r.mu.Unlock()
	out := make([]recordedAgentSessionFrame, len(r.frames))
	copy(out, r.frames)
	return out
}

func (r *agentSessionFrameRecorder) reset() {
	r.mu.Lock()
	r.frames = nil
	r.mu.Unlock()
}

// waitFor polls until the recorder holds at least n frames, or fails. MarkOffline's frames come
// from the server goroutine that noticed the closed socket, so there is no ack to barrier on.
func (r *agentSessionFrameRecorder) waitFor(t *testing.T, n int) {
	t.Helper()
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		if len(r.snapshot()) >= n {
			return
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatalf("waited 3s for %d frame(s), got %d", n, len(r.snapshot()))
}

// sendSession sends one `session` frame and returns its session_ack. The ack is the barrier: the
// handler emits the push before it answers, so a received ack means the frame (if any) is recorded.
func (c *streamConn) sendSession(t *testing.T, key, name, state string) map[string]any {
	t.Helper()
	frame := map[string]any{"type": "session", "session_key": key, "name": name}
	if state != "" {
		frame["state"] = state
	}
	c.send(frame)
	ack := c.recv()
	if ack["type"] != "session_ack" {
		t.Fatalf("session answered %v", ack)
	}
	return ack
}

// Case 1: the first frame for a new session emits `created` once, carrying the row id, the frame's
// user and the row the browser will read back.
func TestAgentSessionPushCreatedOnceForANewSession(t *testing.T) {
	env := newPGStreamEnv(t)
	rec := installAgentSessionFrames(t)

	c := env.connector(t, "user-push")
	c.hello("conn-push")
	ack := c.sendSession(t, "k1", "coder", "running")

	got := rec.snapshot()
	if len(got) != 1 {
		t.Fatalf("frames = %d (%v), want exactly one `created` for the first session frame", len(got), got)
	}
	f := got[0]
	if f.action != "created" || f.entity != "agent_session" {
		t.Errorf("frame = %s/%s, want created/agent_session", f.action, f.entity)
	}
	if want := session_stream.SessionIDFor("user-push", "conn-push", "k1"); f.id != want {
		t.Errorf("frame id = %q, want the session id %q", f.id, want)
	}
	if ackID, _ := ack["session_id"].(string); f.id != ackID {
		t.Errorf("frame id = %q, want the ack's session_id %q", f.id, ackID)
	}
	if f.userID != "user-push" {
		t.Errorf("frame userID = %q, want the frame's user", f.userID)
	}
	if f.seatState != "running" || f.status != "active" {
		t.Errorf("frame data seat_state/status = %v/%v, want running/active", f.seatState, f.status)
	}
}

// Case 2: a frame that reports the same seat_state and leaves the status alone emits nothing.
func TestAgentSessionPushSilentWhenNothingChanged(t *testing.T) {
	env := newPGStreamEnv(t)
	rec := installAgentSessionFrames(t)

	c := env.connector(t, "user-push")
	c.hello("conn-push")
	c.sendSession(t, "k1", "coder", "running")
	rec.reset()

	c.sendSession(t, "k1", "coder", "running")

	if n := len(rec.snapshot()); n != 0 {
		t.Fatalf("the unchanged re-registration emitted %d frame(s): %v", n, rec.snapshot())
	}
}

// Case 3: a seat_state change emits `updated`, and the row still reports the connection as active.
func TestAgentSessionPushUpdatedOnSeatStateChange(t *testing.T) {
	env := newPGStreamEnv(t)
	rec := installAgentSessionFrames(t)

	c := env.connector(t, "user-push")
	c.hello("conn-push")
	c.sendSession(t, "k1", "coder", "running")
	rec.reset()

	c.sendSession(t, "k1", "coder", "stopped")

	got := rec.snapshot()
	if len(got) != 1 {
		t.Fatalf("frames = %d (%v), want exactly one `updated` for a seat_state change", len(got), got)
	}
	f := got[0]
	if f.action != "updated" || f.entity != "agent_session" {
		t.Errorf("frame = %s/%s, want updated/agent_session", f.action, f.entity)
	}
	if f.seatState != "stopped" || f.status != "active" {
		t.Errorf("frame data seat_state/status = %v/%v, want stopped/active", f.seatState, f.status)
	}
}

// Case 4: MarkOffline emits ONE frame per session it marks. Two sessions on the connector are two
// frames, both `updated`, both reporting status offline and keeping the last seat_state.
func TestAgentSessionPushOfflineEmitsOneFramePerSession(t *testing.T) {
	env := newPGStreamEnv(t)
	rec := installAgentSessionFrames(t)

	c := env.connector(t, "user-push")
	c.hello("conn-push")
	ack1 := c.sendSession(t, "k1", "coder", "running")
	ack2 := c.sendSession(t, "k2", "coder", "running")
	rec.reset()

	// Closing the socket is what makes the server run MarkOffline for the connector.
	_ = c.conn.Close()
	rec.waitFor(t, 2)

	got := rec.snapshot()
	if len(got) != 2 {
		t.Fatalf("MarkOffline emitted %d frame(s), want one per marked session (2): %v", len(got), got)
	}
	ids := map[string]bool{}
	for _, f := range got {
		if f.action != "updated" || f.entity != "agent_session" {
			t.Errorf("offline frame = %s/%s, want updated/agent_session", f.action, f.entity)
		}
		if f.status != "offline" {
			t.Errorf("offline frame status = %v, want offline", f.status)
		}
		if f.seatState != "running" {
			t.Errorf("offline frame seat_state = %v, want the last reported running", f.seatState)
		}
		if f.userID != "user-push" {
			t.Errorf("offline frame userID = %q, want the frame's user", f.userID)
		}
		ids[f.id] = true
	}
	for _, ack := range []map[string]any{ack1, ack2} {
		if id, _ := ack["session_id"].(string); !ids[id] {
			t.Errorf("no offline frame for session %q: got ids %v", id, ids)
		}
	}
}

// Case 5: the userID handed to the seam is the frame's own user, so a frame can never reach
// another user's realtime subscribers - even with the same connector_id and session_key.
func TestAgentSessionPushCarriesTheFramesUser(t *testing.T) {
	env := newPGStreamEnv(t)
	rec := installAgentSessionFrames(t)

	a := env.connector(t, "user-a")
	a.hello("conn")
	ackA := a.sendSession(t, "k", "coder", "running")

	b := env.connector(t, "user-b")
	b.hello("conn")
	ackB := b.sendSession(t, "k", "coder", "running")

	got := rec.snapshot()
	if len(got) != 2 {
		t.Fatalf("frames = %d (%v), want one per user", len(got), got)
	}
	byID := map[string]string{}
	for _, f := range got {
		if f.action != "created" {
			t.Errorf("frame action = %q, want created", f.action)
		}
		byID[f.id] = f.userID
	}
	for _, c := range []struct {
		ack  map[string]any
		user string
	}{{ackA, "user-a"}, {ackB, "user-b"}} {
		id, _ := c.ack["session_id"].(string)
		if byID[id] != c.user {
			t.Errorf("frame for session %q carried userID %q, want %q", id, byID[id], c.user)
		}
	}

	// MarkOffline for one user's connector must not emit a frame for the other user's session.
	rec.reset()
	_ = a.conn.Close()
	rec.waitFor(t, 1)
	time.Sleep(100 * time.Millisecond)
	offline := rec.snapshot()
	if len(offline) != 1 {
		t.Fatalf("closing user-a's socket emitted %d frame(s), want 1 (user-b's session is untouched): %v", len(offline), offline)
	}
	if offline[0].userID != "user-a" {
		t.Errorf("offline frame userID = %q, want user-a", offline[0].userID)
	}
}
