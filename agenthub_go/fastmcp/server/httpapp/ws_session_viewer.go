// ws_session_viewer.go serves WS /ws/sessions/{id}, the browser side of the session
// stream (server/routes/session_stream_routes.py session_viewer): replay the stored
// events after after_seq, then follow the live events the connector publishes.
package httpapp

import (
	"context"
	"net/http"
	"strconv"

	"agenthub/fastmcp/auth"
	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/session_stream"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

const (
	// wsReplayPage is the page size of the replay (500 in session_viewer).
	wsReplayPage = 500
	// wsCloseTryAgain is the close code of a viewer the hub dropped as too slow.
	wsCloseTryAgain = 1013
	wsCloseInternal = 1011
)

// sessionViewerStore is what the viewer reads: the caller's own session and its stored
// events. sessionStreamStore is the production implementation.
type sessionViewerStore interface {
	GetSessionForUser(ctx context.Context, userID, sessionID string) (*entities.OrderedMap[any], error)
	ListEvents(ctx context.Context, userID, sessionID string, afterSeq, limit int64) ([]*entities.OrderedMap[any], error)
}

type sessionStreamStore struct{ sessions *database.SessionManager }

func (s sessionStreamStore) GetSessionForUser(ctx context.Context, userID, sessionID string) (*entities.OrderedMap[any], error) {
	return session_stream.GetSessionForUser(ctx, s.sessions, userID, sessionID)
}

func (s sessionStreamStore) ListEvents(ctx context.Context, userID, sessionID string, afterSeq, limit int64) ([]*entities.OrderedMap[any], error) {
	return session_stream.ListEvents(ctx, s.sessions, userID, sessionID, afterSeq, limit)
}

// handleSessionViewer authenticates from ?token=, then answers a session that is
// missing and a session that belongs to someone else with the same 4004 close so ids
// cannot be probed.
func handleSessionViewer(store sessionViewerStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		result := auth.ValidateTokenUniversal(r.Context(), r.URL.Query().Get("token"), nil)
		if !result.Valid || result.UserID == nil || *result.UserID == "" {
			http.Error(w, "Authentication required", http.StatusForbidden)
			return
		}
		conn, err := wsUpgrade(w, r)
		if err != nil {
			return
		}
		ctx := context.Background()
		code, reason := serveSessionViewer(ctx, conn, store, *result.UserID, r.PathValue("id"), afterSeqParam(r))
		_ = conn.Close(ctx, code, reason)
	}
}

// afterSeqParam is int(query["after_seq"]), 0 when absent or not an integer.
func afterSeqParam(r *http.Request) int {
	n, err := strconv.Atoi(r.URL.Query().Get("after_seq"))
	if err != nil {
		return 0
	}
	return n
}

// serveSessionViewer streams the session to conn and returns the close code and
// reason to end the socket with.
func serveSessionViewer(ctx context.Context, conn *wsConn, store sessionViewerStore, userID, sessionID string, after int) (int, string) {
	row, err := store.GetSessionForUser(ctx, userID, sessionID)
	if err != nil {
		return wsCloseInternal, "internal error"
	}
	if row == nil {
		return routes.SessionStreamNotFoundCode, "Session not found"
	}

	// Subscribe before the replay so no event published meanwhile is missed.
	q := session_stream.Hub.Subscribe(sessionID)
	defer session_stream.Hub.Unsubscribe(sessionID, q)

	last := after
	for {
		batch, err := store.ListEvents(ctx, userID, sessionID, int64(last), wsReplayPage)
		if err != nil {
			return wsCloseInternal, "internal error"
		}
		for _, ev := range batch {
			if err := wsSend(ctx, conn, ev); err != nil {
				return 1000, ""
			}
			seq, _ := ev.Get("seq")
			last = wsInt(seq)
		}
		if len(batch) < wsReplayPage {
			break
		}
	}

	// Read the socket while idle: without a pending read a viewer whose browser went
	// away would never be noticed and would keep its hub subscription. Whatever the
	// browser sends (a ping, say) is ignored; only a failed read ends the stream.
	liveCtx, stop := context.WithCancel(ctx)
	defer stop()
	go func() {
		defer stop()
		for {
			if _, err := conn.ReceiveText(liveCtx); err != nil {
				return
			}
		}
	}()

	for {
		v, ok := q.Get(liveCtx)
		if !ok {
			return 1000, ""
		}
		ev, isEvent := v.(*entities.OrderedMap[any])
		if !isEvent {
			continue
		}
		if ev == session_stream.Overflow {
			return wsCloseTryAgain, "Too slow, reconnect"
		}
		seqValue, _ := ev.Get("seq")
		seq := wsInt(seqValue)
		if seq <= last { // already replayed
			continue
		}
		if err := wsSend(ctx, conn, ev); err != nil {
			return 1000, ""
		}
		last = seq
	}
}
