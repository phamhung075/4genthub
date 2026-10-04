package httpapp

import (
	"bufio"
	"context"
	"encoding/binary"
	"net"
	"net/http"
	"net/http/httptest"
	"net/url"
	"sync"
	"testing"
	"time"

	"agenthub/fastmcp/session_stream"
	"agenthub/fastmcp/task_management/domain/entities"
)

const (
	viewerUser  = "user-1" // the user wsTestToken signs for
	viewerOther = "user-2"
	viewerSID   = "session-1"
)

// viewerStore is an in-memory sessionViewerStore. gate, when set, blocks every
// ListEvents until it is closed, which freezes the viewer between its subscription
// and its replay.
type viewerStore struct {
	mu       sync.Mutex
	owner    map[string]string // session id -> owning user id
	events   []*entities.OrderedMap[any]
	limits   []int64
	gate     chan struct{}
	gateOnce sync.Once
}

func newViewerStore(eventCount int) *viewerStore {
	st := &viewerStore{owner: map[string]string{viewerSID: viewerUser}}
	for seq := 1; seq <= eventCount; seq++ {
		st.events = append(st.events, viewerEvent(seq))
	}
	return st
}

func viewerEvent(seq int) *entities.OrderedMap[any] {
	ev := entities.NewOrderedMap[any]()
	ev.Set("seq", seq)
	ev.Set("type", "output")
	ev.Set("payload", "p")
	return ev
}

func (s *viewerStore) GetSessionForUser(_ context.Context, userID, sessionID string) (*entities.OrderedMap[any], error) {
	if s.owner[sessionID] != userID {
		return nil, nil
	}
	row := entities.NewOrderedMap[any]()
	row.Set("id", sessionID)
	return row, nil
}

func (s *viewerStore) ListEvents(_ context.Context, userID, sessionID string, afterSeq, limit int64) ([]*entities.OrderedMap[any], error) {
	if s.gate != nil {
		<-s.gate
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	s.limits = append(s.limits, limit)
	out := []*entities.OrderedMap[any]{}
	if s.owner[sessionID] != userID {
		return out, nil
	}
	for _, ev := range s.events {
		seq, _ := ev.Get("seq")
		if int64(seq.(int)) > afterSeq && int64(len(out)) < limit {
			out = append(out, ev)
		}
	}
	return out, nil
}

func (s *viewerStore) openGate() { s.gateOnce.Do(func() { close(s.gate) }) }

// dialViewer starts the viewer handler on a test server and connects to sessionID.
// Reads on the returned connection fail after 5s instead of hanging.
func dialViewer(t *testing.T, store sessionViewerStore, sessionID, query string) (net.Conn, *bufio.Reader) {
	t.Helper()
	mux := http.NewServeMux()
	mux.HandleFunc("GET /ws/sessions/{id}", handleSessionViewer(store))
	server := httptest.NewServer(mux)
	t.Cleanup(server.Close)
	token := wsTestToken(t, nil)
	conn, br := wsTestDial(t, server.URL, "/ws/sessions/"+sessionID+"?token="+url.QueryEscape(token)+query)
	t.Cleanup(func() { _ = conn.Close() })
	_ = conn.SetReadDeadline(time.Now().Add(5 * time.Second))
	return conn, br
}

func readEventSeq(t *testing.T, br *bufio.Reader) int {
	t.Helper()
	opcode, payload := wsTestReadFrame(t, br)
	if opcode != wsOpText {
		t.Fatalf("opcode = %d (payload %q), want a text event", opcode, payload)
	}
	return int(wsTestJSON(t, payload)["seq"].(float64))
}

func readClose(t *testing.T, br *bufio.Reader) (int, string) {
	t.Helper()
	opcode, payload := wsTestReadFrame(t, br)
	if opcode != wsOpClose || len(payload) < 2 {
		t.Fatalf("frame = opcode %d payload %q, want a close frame with a code", opcode, payload)
	}
	return int(binary.BigEndian.Uint16(payload[:2])), string(payload[2:])
}

func waitFor(t *testing.T, what string, cond func() bool) {
	t.Helper()
	deadline := time.Now().Add(3 * time.Second)
	for !cond() {
		if time.Now().After(deadline) {
			t.Fatalf("timed out waiting for %s", what)
		}
		time.Sleep(5 * time.Millisecond)
	}
}

func TestSessionViewerReplaysAfterSeqThenFollowsLiveEvents(t *testing.T) {
	_, br := dialViewer(t, newViewerStore(3), viewerSID, "&after_seq=1")

	if got := []int{readEventSeq(t, br), readEventSeq(t, br)}; got[0] != 2 || got[1] != 3 {
		t.Fatalf("replayed seqs = %v, want [2 3]", got)
	}
	waitFor(t, "the viewer to follow the hub", func() bool { return session_stream.Hub.Subscribers(viewerSID) == 1 })
	// A live event the replay already covered is skipped; the next one is sent.
	session_stream.Hub.Publish(viewerSID, []any{viewerEvent(3), viewerEvent(4)})
	if seq := readEventSeq(t, br); seq != 4 {
		t.Fatalf("live seq = %d, want 4 (seq 3 was already replayed)", seq)
	}
}

func TestSessionViewerMissingAndForeignSessionCloseIdentically(t *testing.T) {
	store := newViewerStore(1)
	store.owner["someone-elses"] = viewerOther

	_, missing := dialViewer(t, store, "no-such-id", "")
	_, foreign := dialViewer(t, store, "someone-elses", "")

	missingCode, missingReason := readClose(t, missing)
	foreignCode, foreignReason := readClose(t, foreign)
	if missingCode != 4004 || foreignCode != 4004 {
		t.Fatalf("close codes = %d and %d, want 4004 for both", missingCode, foreignCode)
	}
	if missingReason != foreignReason {
		t.Fatalf("close reasons differ: %q vs %q, ids could be probed", missingReason, foreignReason)
	}
}

func TestSessionViewerDoesNotLoseAnEventPublishedDuringTheReplay(t *testing.T) {
	store := newViewerStore(3)
	store.gate = make(chan struct{})
	t.Cleanup(store.openGate)
	_, br := dialViewer(t, store, viewerSID, "")

	// The viewer is subscribed and stuck before its first replay page.
	waitFor(t, "the viewer to subscribe", func() bool { return session_stream.Hub.Subscribers(viewerSID) == 1 })
	session_stream.Hub.Publish(viewerSID, []any{viewerEvent(4)})
	store.openGate()

	for want := 1; want <= 4; want++ {
		if got := readEventSeq(t, br); got != want {
			t.Fatalf("seq = %d, want %d", got, want)
		}
	}
}

func TestSessionViewerTellsAnOverflowingViewerToReconnect(t *testing.T) {
	store := newViewerStore(0)
	store.gate = make(chan struct{})
	t.Cleanup(store.openGate)
	_, br := dialViewer(t, store, viewerSID, "")
	waitFor(t, "the viewer to subscribe", func() bool { return session_stream.Hub.Subscribers(viewerSID) == 1 })

	// The viewer reads nothing while the replay is gated, so its queue overflows.
	events := make([]any, session_stream.QueueSize+1)
	for i := range events {
		events[i] = viewerEvent(i + 1)
	}
	session_stream.Hub.Publish(viewerSID, events)
	store.openGate()

	code, reason := readClose(t, br)
	if code != 1013 || reason != "Too slow, reconnect" {
		t.Fatalf("close = %d %q, want 1013 \"Too slow, reconnect\"", code, reason)
	}
	if n := session_stream.Hub.Subscribers(viewerSID); n != 0 {
		t.Fatalf("%d subscriptions left after the overflow", n)
	}
}

func TestSessionViewerLeavesNoSubscriptionWhenAnIdleClientCloses(t *testing.T) {
	conn, br := dialViewer(t, newViewerStore(1), viewerSID, "")
	if seq := readEventSeq(t, br); seq != 1 {
		t.Fatalf("seq = %d, want 1", seq)
	}
	waitFor(t, "the viewer to go idle on the hub", func() bool { return session_stream.Hub.Subscribers(viewerSID) == 1 })

	_ = conn.Close()

	waitFor(t, "the subscription to be released", func() bool { return session_stream.Hub.Subscribers(viewerSID) == 0 })
}

func TestSessionViewerIgnoresWhatTheBrowserSends(t *testing.T) {
	conn, br := dialViewer(t, newViewerStore(0), viewerSID, "")
	waitFor(t, "the viewer to go idle on the hub", func() bool { return session_stream.Hub.Subscribers(viewerSID) == 1 })

	wsTestWriteText(t, conn, []byte(`{"type":"ping"}`))
	session_stream.Hub.Publish(viewerSID, []any{viewerEvent(1)})

	if seq := readEventSeq(t, br); seq != 1 {
		t.Fatalf("seq = %d, want the stream to go on after a client message", seq)
	}
}

func TestSessionViewerReplaysInPagesOf500(t *testing.T) {
	for _, tc := range []struct {
		name  string
		total int
		pages int
	}{
		{"1203 events", 1203, 3},
		{"1000 events end on a full page, so one empty page follows", 1000, 3},
	} {
		t.Run(tc.name, func(t *testing.T) {
			store := newViewerStore(tc.total)
			_, br := dialViewer(t, store, viewerSID, "")

			for want := 1; want <= tc.total; want++ {
				if got := readEventSeq(t, br); got != want {
					t.Fatalf("seq = %d, want %d", got, want)
				}
			}
			waitFor(t, "the replay to finish", func() bool { return session_stream.Hub.Subscribers(viewerSID) == 1 })
			store.mu.Lock()
			limits := append([]int64(nil), store.limits...)
			store.mu.Unlock()
			if len(limits) != tc.pages {
				t.Fatalf("%d page reads, want %d", len(limits), tc.pages)
			}
			for _, l := range limits {
				if l != 500 {
					t.Fatalf("page limit %d, want 500", l)
				}
			}
		})
	}
}
