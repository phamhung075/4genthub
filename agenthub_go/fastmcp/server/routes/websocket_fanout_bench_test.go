package routes

import (
	"context"
	"fmt"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities"
)

// PERF-04 (ai_docs/core-architecture/nfr-register.md): one broadcast of a ~2 KB task event to
// N registered sockets, through the production path - RegisterConnection for the registry,
// BroadcastDataChange for the fan-out (authorization per socket, one frame marshal per socket, one
// SendText hand-off each). The wire and the browser are not measured; this is server-side fan-out.

// fanoutSocket is a wslib.WebSocket that counts frames instead of keeping them: the benchmark must
// not grow a slice per iteration, and the count is the tautology guard - a loop that dead-ends on a
// closed or unregistered socket measures nothing.
type fanoutSocket struct {
	frames atomic.Int64
	bytes  atomic.Int64
}

func (f *fanoutSocket) Accept(context.Context) error             { return nil }
func (f *fanoutSocket) Close(context.Context, int, string) error { return nil }
func (f *fanoutSocket) SendText(_ context.Context, data string) error {
	f.frames.Add(1)
	f.bytes.Add(int64(len(data)))
	return nil
}
func (f *fanoutSocket) ReceiveText(context.Context) (string, error) { return "", nil }

// benchTaskData is a TaskData of about 2 KB, the size PERF-05's claim describes.
func benchTaskData() *entities.OrderedMap[any] {
	data := entities.NewOrderedMap[any]()
	data.Set("id", "task-bench")
	data.Set("title", "realtime fan-out benchmark")
	data.Set("status", "in_progress")
	data.Set("assignees", []any{"@go-dev"})
	data.Set("labels", []any{"nfr", "PERF-04"})
	data.Set("description", strings.Repeat("x", 1800))
	return data
}

func BenchmarkRealtimeFanout(b *testing.B) {
	const (
		userID   = "user-bench-fanout"
		taskID   = "task-bench"
		ceilingN = 100
	)
	// The measured ceiling, PERF-04's threshold: one fan-out to 100 sockets in under 500 ms.
	const ceiling = 500 * time.Millisecond
	ctx := context.Background()
	data := benchTaskData()

	for _, sockets := range []int{1, 10, 100} {
		b.Run(fmt.Sprintf("sockets=%d", sockets), func(b *testing.B) {
			made := make([]*fanoutSocket, sockets)
			for index := range made {
				made[index] = &fanoutSocket{}
				RegisterConnection(made[index], &authdomain.User{ID: strPtr(userID)}, fmt.Sprintf("bench-%d-%d", sockets, index))
			}
			b.Cleanup(func() {
				for _, ws := range made {
					UnregisterConnection(ws)
				}
			})

			b.ReportAllocs()
			b.ResetTimer()
			for b.Loop() {
				// The success path deletes the queue entry it made, so this delete is bookkeeping
				// the next broadcast of the same (entity, user) would otherwise accumulate - the
				// same per-iteration reset BenchmarkTaskEventDelta does for its duplicate cache.
				messageQueueMu.Lock()
				delete(userMessageQueues, userID)
				messageQueueMu.Unlock()

				// The triggering user owns every socket, so rule 1 authorizes each one without a
				// repository read: this measures fan-out, not the ownership port.
				if err := BroadcastDataChange(ctx, "updated", "task", taskID, userID, data, nil); err != nil {
					b.Fatalf("BroadcastDataChange: %v", err)
				}
			}
			b.StopTimer()

			for index, ws := range made {
				if got := ws.frames.Load(); got != int64(b.N) {
					b.Fatalf("socket %d received %d frames over %d broadcasts: every socket must get exactly one per broadcast", index, got, b.N)
				}
			}
			elapsed := b.Elapsed()
			perSend := float64(elapsed.Nanoseconds()) / float64(b.N)
			perSocket := perSend / float64(sockets)
			b.ReportMetric(perSocket, "ns/socket")
			if sockets == ceilingN && time.Duration(perSend) > ceiling {
				b.Fatalf("one fan-out to %d sockets took %s against the %s ceiling", sockets, time.Duration(perSend), ceiling)
			}
		})
	}
}
