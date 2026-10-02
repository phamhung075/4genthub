// Package events ports task_management/infrastructure/events.
package events

import (
	"strconv"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// QueueState enumerates the queue operational states (event_queue.QueueState).
type QueueState string

const (
	QueueStateRunning  QueueState = "running"
	QueueStatePaused   QueueState = "paused"
	QueueStateShutdown QueueState = "shutdown"
)

// QueueMetrics tracks queue performance (event_queue.QueueMetrics).
type QueueMetrics struct {
	TotalEnqueued   int
	TotalDequeued   int
	TotalDropped    int
	TotalErrors     int
	CurrentSize     int
	MaxSizeReached  int
	LastEnqueueTime *time.Time
	LastDequeueTime *time.Time
}

// EventQueue is a thread-safe FIFO queue for async event processing
// (event_queue.EventQueue).
type EventQueue struct {
	stateMu sync.Mutex
	state   QueueState

	metricsMu sync.Mutex
	metrics   QueueMetrics

	mu       sync.Mutex
	notEmpty *sync.Cond
	notFull  *sync.Cond
	items    []any
	maxsize  int
	timeout  float64
}

// NewEventQueue applies the Python constructor defaults (maxsize=10000, timeout=0.1).
func NewEventQueue() *EventQueue { return NewEventQueueWith(10000, 0.1) }

// NewEventQueueWith mirrors EventQueue(maxsize, timeout).
func NewEventQueueWith(maxsize int, timeout float64) *EventQueue {
	q := &EventQueue{state: QueueStateRunning, maxsize: maxsize, timeout: timeout}
	q.notEmpty = sync.NewCond(&q.mu)
	q.notFull = sync.NewCond(&q.mu)
	return q
}

// State returns the current queue state.
func (q *EventQueue) State() QueueState {
	q.stateMu.Lock()
	defer q.stateMu.Unlock()
	return q.state
}

// Put mirrors EventQueue.put. The error is a *value_objects.ValueError when the queue
// is shut down; a full queue (blocking timeout or non-blocking) returns (false, nil)
// after incrementing total_dropped.
func (q *EventQueue) Put(event any, block bool, timeout *float64) (bool, error) {
	state := q.State()
	if state == QueueStateShutdown {
		return false, &value_objects.ValueError{Msg: "Cannot enqueue events: queue is shutdown"}
	}
	if state == QueueStatePaused {
		q.incrementDropped()
		return false, nil
	}

	waitTimeout := q.timeout
	if timeout != nil {
		waitTimeout = *timeout
	}

	if block && q.maxsize > 0 && waitTimeout < 0 {
		// queue.Queue.put raises ValueError("'timeout' must be a non-negative number"), which
		// EventQueue.put catches and counts
		q.incrementErrors()
		return false, nil
	}

	q.mu.Lock()
	if block {
		if q.maxsize > 0 {
			deadline := time.Now().Add(time.Duration(waitTimeout * float64(time.Second)))
			for len(q.items) >= q.maxsize {
				if condWaitTimeout(q.notFull, time.Until(deadline)) {
					q.mu.Unlock()
					q.incrementDropped()
					return false, nil
				}
			}
		}
	} else if q.maxsize > 0 && len(q.items) >= q.maxsize {
		q.mu.Unlock()
		q.incrementDropped()
		return false, nil
	}
	q.items = append(q.items, event)
	q.notEmpty.Signal()
	size := len(q.items)
	q.mu.Unlock()

	q.recordEnqueue(size)
	return true, nil
}

// Get mirrors EventQueue.get; an empty queue (or timeout) returns (nil, nil).
func (q *EventQueue) Get(block bool, timeout *float64) (any, error) {
	state := q.State()
	if state == QueueStateShutdown {
		return nil, &value_objects.ValueError{Msg: "Cannot dequeue events: queue is shutdown"}
	}

	if block && timeout != nil && *timeout < 0 {
		q.incrementErrors()
		return nil, nil
	}

	q.mu.Lock()
	if block {
		if timeout != nil {
			deadline := time.Now().Add(time.Duration(*timeout * float64(time.Second)))
			for len(q.items) == 0 {
				if condWaitTimeout(q.notEmpty, time.Until(deadline)) {
					q.mu.Unlock()
					return nil, nil
				}
			}
		} else {
			for len(q.items) == 0 {
				q.notEmpty.Wait()
			}
		}
	} else if len(q.items) == 0 {
		q.mu.Unlock()
		return nil, nil
	}
	event := q.items[0]
	q.items = q.items[1:]
	q.notFull.Signal()
	size := len(q.items)
	q.mu.Unlock()

	q.recordDequeue(size)
	return event, nil
}

// PutNowait mirrors EventQueue.put_nowait.
func (q *EventQueue) PutNowait(event any) (bool, error) { return q.Put(event, false, nil) }

// GetNowait mirrors EventQueue.get_nowait.
func (q *EventQueue) GetNowait() (any, error) { return q.Get(false, nil) }

// Size mirrors EventQueue.size.
func (q *EventQueue) Size() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	return len(q.items)
}

// IsEmpty mirrors EventQueue.is_empty.
func (q *EventQueue) IsEmpty() bool { return q.Size() == 0 }

// IsFull mirrors EventQueue.is_full (a maxsize <= 0 queue is never full).
func (q *EventQueue) IsFull() bool {
	q.mu.Lock()
	defer q.mu.Unlock()
	return q.maxsize > 0 && len(q.items) >= q.maxsize
}

// Clear mirrors EventQueue.clear and returns the number of events removed.
func (q *EventQueue) Clear() int {
	q.mu.Lock()
	count := len(q.items)
	q.items = nil
	q.notFull.Broadcast()
	q.mu.Unlock()

	q.metricsMu.Lock()
	q.metrics.CurrentSize = 0
	q.metricsMu.Unlock()
	return count
}

// Pause mirrors EventQueue.pause.
func (q *EventQueue) Pause() {
	q.stateMu.Lock()
	q.state = QueueStatePaused
	q.stateMu.Unlock()
}

// Resume mirrors EventQueue.resume.
func (q *EventQueue) Resume() {
	q.stateMu.Lock()
	if q.state == QueueStatePaused {
		q.state = QueueStateRunning
	}
	q.stateMu.Unlock()
}

// Shutdown mirrors EventQueue.shutdown; when drain is false the remaining events are
// dropped and their count returned.
func (q *EventQueue) Shutdown(drain bool) int {
	q.stateMu.Lock()
	q.state = QueueStateShutdown
	q.stateMu.Unlock()

	remaining := q.Size()
	if !drain && remaining > 0 {
		return q.Clear()
	}
	return remaining
}

// GetMetrics mirrors EventQueue.get_metrics.
func (q *EventQueue) GetMetrics() *entities.OrderedMap[any] {
	q.metricsMu.Lock()
	defer q.metricsMu.Unlock()

	var utilization any = 0
	if q.maxsize > 0 {
		utilization = float64(q.metrics.CurrentSize) / float64(q.maxsize) * 100
	}
	var dropRate any = 0
	denom := q.metrics.TotalEnqueued + q.metrics.TotalDropped
	if denom > 0 {
		dropRate = float64(q.metrics.TotalDropped) / float64(denom) * 100
	}
	lastEnqueue := any(nil)
	if q.metrics.LastEnqueueTime != nil {
		lastEnqueue = value_objects.IsoFormat(*q.metrics.LastEnqueueTime)
	}
	lastDequeue := any(nil)
	if q.metrics.LastDequeueTime != nil {
		lastDequeue = value_objects.IsoFormat(*q.metrics.LastDequeueTime)
	}
	out := entities.NewOrderedMap[any]()
	out.Set("state", q.State())
	out.Set("current_size", q.metrics.CurrentSize)
	out.Set("maxsize", q.maxsize)
	out.Set("total_enqueued", q.metrics.TotalEnqueued)
	out.Set("total_dequeued", q.metrics.TotalDequeued)
	out.Set("total_dropped", q.metrics.TotalDropped)
	out.Set("total_errors", q.metrics.TotalErrors)
	out.Set("max_size_reached", q.metrics.MaxSizeReached)
	out.Set("utilization_percent", utilization)
	out.Set("drop_rate_percent", dropRate)
	out.Set("last_enqueue_time", lastEnqueue)
	out.Set("last_dequeue_time", lastDequeue)
	return out
}

// ResetMetrics mirrors EventQueue.reset_metrics.
func (q *EventQueue) ResetMetrics() {
	q.metricsMu.Lock()
	q.metrics = QueueMetrics{}
	q.metricsMu.Unlock()
}

func (q *EventQueue) incrementErrors() {
	q.metricsMu.Lock()
	q.metrics.TotalErrors++
	q.metricsMu.Unlock()
}

func (q *EventQueue) incrementDropped() {
	q.metricsMu.Lock()
	q.metrics.TotalDropped++
	q.metricsMu.Unlock()
}

func (q *EventQueue) recordEnqueue(size int) {
	q.metricsMu.Lock()
	q.metrics.TotalEnqueued++
	q.metrics.CurrentSize = size
	now := time.Now().UTC().Truncate(time.Microsecond)
	q.metrics.LastEnqueueTime = &now
	if size > q.metrics.MaxSizeReached {
		q.metrics.MaxSizeReached = size
	}
	q.metricsMu.Unlock()
}

func (q *EventQueue) recordDequeue(size int) {
	q.metricsMu.Lock()
	q.metrics.TotalDequeued++
	q.metrics.CurrentSize = size
	now := time.Now().UTC().Truncate(time.Microsecond)
	q.metrics.LastDequeueTime = &now
	q.metricsMu.Unlock()
}

// String is EventQueue.__repr__.
func (q *EventQueue) String() string {
	q.metricsMu.Lock()
	enqueued := q.metrics.TotalEnqueued
	dropped := q.metrics.TotalDropped
	q.metricsMu.Unlock()
	return "EventQueue(state=" + string(q.State()) +
		", size=" + strconv.Itoa(q.Size()) + "/" + strconv.Itoa(q.maxsize) +
		", enqueued=" + strconv.Itoa(enqueued) + ", dropped=" + strconv.Itoa(dropped) + ")"
}

// condWaitTimeout waits on c until it is signalled or d elapses, reporting whether it
// timed out.
func condWaitTimeout(c *sync.Cond, d time.Duration) bool {
	if d <= 0 {
		return true
	}
	// the callback takes the lock so the broadcast cannot fire between AfterFunc and Wait
	// enlisting (the waiter holds c.L until Wait releases it atomically)
	timer := time.AfterFunc(d, func() {
		c.L.Lock()
		c.Broadcast()
		c.L.Unlock()
	})
	c.Wait()
	return !timer.Stop()
}
