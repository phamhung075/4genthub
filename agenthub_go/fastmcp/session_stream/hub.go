// Package session_stream ports fastmcp/session_stream (hub.py, repository.py):
// in-process fan-out of stored session events to connected browsers plus the
// user-scoped persistence for streamed sessions.
package session_stream

import (
	"context"
	"sync"

	"agenthub/fastmcp/task_management/domain/entities"
)

// QueueSize is the per-viewer queue bound (QUEUE_SIZE).
const QueueSize = 1000

// Overflow is the marker put on a viewer's queue when it overflows (OVERFLOW).
// It is shared, like the Python module-level dict.
var Overflow = func() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("_overflow", true)
	return m
}()

// Queue mirrors asyncio.Queue with a maxsize. Its values are event dicts.
type Queue struct {
	ch chan any
}

// NewQueue builds a bounded queue (asyncio.Queue(maxsize=maxsize)).
func NewQueue(maxsize int) *Queue { return &Queue{ch: make(chan any, maxsize)} }

// PutNowait is put_nowait: it reports false when the queue is full
// (asyncio.QueueFull).
func (q *Queue) PutNowait(v any) bool {
	select {
	case q.ch <- v:
		return true
	default:
		return false
	}
}

// GetNowait is get_nowait: it reports false when the queue is empty
// (asyncio.QueueEmpty).
func (q *Queue) GetNowait() (any, bool) {
	select {
	case v := <-q.ch:
		return v, true
	default:
		return nil, false
	}
}

// Get is `await q.get()`: it blocks until a value is available or ctx is done.
func (q *Queue) Get(ctx context.Context) (any, bool) {
	select {
	case v := <-q.ch:
		return v, true
	case <-ctx.Done():
		return nil, false
	}
}

// Empty is q.empty().
func (q *Queue) Empty() bool { return len(q.ch) == 0 }

// QSize is q.qsize().
func (q *Queue) QSize() int { return len(q.ch) }

// SessionHub is Python's SessionHub.
type SessionHub struct {
	mu   sync.Mutex
	subs map[string]map[*Queue]struct{}
}

// NewSessionHub builds an empty hub.
func NewSessionHub() *SessionHub {
	return &SessionHub{subs: map[string]map[*Queue]struct{}{}}
}

// Subscribe is subscribe: a new bounded queue for sessionID.
func (h *SessionHub) Subscribe(sessionID string) *Queue {
	q := NewQueue(QueueSize)
	h.mu.Lock()
	defer h.mu.Unlock()
	set := h.subs[sessionID]
	if set == nil {
		set = map[*Queue]struct{}{}
		h.subs[sessionID] = set
	}
	set[q] = struct{}{}
	return q
}

// Unsubscribe is unsubscribe: drop q and the session entry when q was the last
// viewer (Python's defaultdict(set) discard + del).
func (h *SessionHub) Unsubscribe(sessionID string, q *Queue) {
	h.mu.Lock()
	defer h.mu.Unlock()
	set := h.subs[sessionID]
	if len(set) == 0 {
		return
	}
	delete(set, q)
	if len(set) == 0 {
		delete(h.subs, sessionID)
	}
}

// Publish is publish: non-blocking. A slow viewer that overflows is dropped, not
// waited on; it gets the OVERFLOW marker so its handler can close the socket.
func (h *SessionHub) Publish(sessionID string, events []any) {
	h.mu.Lock()
	set := h.subs[sessionID]
	queues := make([]*Queue, 0, len(set))
	for q := range set {
		queues = append(queues, q)
	}
	h.mu.Unlock()

	for _, q := range queues {
		for _, ev := range events {
			if q.PutNowait(ev) {
				continue
			}
			h.Unsubscribe(sessionID, q)
			for {
				if _, ok := q.GetNowait(); !ok {
					break
				}
			}
			q.PutNowait(Overflow)
			break
		}
	}
}

// Hub is the module-level singleton (hub = SessionHub()).
var Hub = NewSessionHub()
