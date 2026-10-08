package routes

import (
	"context"
	"testing"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	taskdomain "agenthub/fastmcp/task_management/domain/entities"

	"agenthub/fastmcp/auth"
)

// fakeTaskController answers GetTask with whatever the test decided. It embeds the interface so the
// methods this test never reaches do not have to be written out.
type fakeTaskController struct {
	UserTaskController
	result UserTaskResult
	calls  int
}

func (f *fakeTaskController) GetTask(ctx context.Context, taskID, userID string) (UserTaskResult, error) {
	f.calls++
	return f.result, nil
}

// recordingEventReader records whether it was reached. THE ASSERTION THAT MATTERS IS THAT IT WAS
// NOT: a task the caller cannot see must be refused before the ledger is read, so a bug that read
// first and filtered later could not pass this test.
type recordingEventReader struct {
	called bool
	events []*taskdomain.TaskEvent
}

func (r *recordingEventReader) ListTaskEvents(ctx context.Context, taskID string, afterSeq int, userID string) ([]*taskdomain.TaskEvent, error) {
	r.called = true
	return r.events, nil
}

// TestGetTaskEventsRefusesAnInvisibleTaskWithoutReadingTheLedger is one of O1a's acceptance
// negatives, and it needs no database: the 404 comes from the same !Success branch GetUserTask
// uses, and the reader must never run. A real pass on this box rather than a skip.
func TestGetTaskEventsRefusesAnInvisibleTaskWithoutReadingTheLedger(t *testing.T) {
	notFound := "Task not found"
	tasks := &fakeTaskController{result: UserTaskResult{Success: false, Error: &notFound}}
	events := &recordingEventReader{}

	body, err := GetTaskEvents(context.Background(), "task-1", 7, &authdomain.User{}, tasks, events)

	if err == nil {
		t.Fatal("a task the caller cannot see must return an error rather than a body")
	}
	// The 404 itself, not merely an error: the acceptance asks for the same branch GetUserTask
	// uses, so the status is the claim and an error of any kind would not satisfy it.
	if exc, ok := err.(*auth.HTTPException); !ok || exc.StatusCode != 404 {
		t.Fatalf("expected a 404 HTTPException, got %#v", err)
	}
	if body != nil {
		t.Fatalf("no body on refusal, got %#v", body)
	}
	if tasks.calls != 1 {
		t.Fatalf("the task lookup must run exactly once, ran %d", tasks.calls)
	}
	if events.called {
		t.Fatal("THE LEDGER WAS READ FOR A TASK THE CALLER CANNOT SEE - isolation must come from the task check, not from filtering afterwards")
	}
}

// TestGetTaskEventsPassesAfterSeqAndReturnsEvents covers the positive direction: the ledger's rows
// reach the response, and after_seq travels through to the reader rather than being dropped, which
// is the whole point of a resumable read.
func TestGetTaskEventsPassesAfterSeqAndReturnsEvents(t *testing.T) {
	tasks := &fakeTaskController{result: UserTaskResult{Success: true}}
	events := &recordingEventReader{events: []*taskdomain.TaskEvent{
		{ID: "e1", TaskID: "task-1", Seq: 8, Kind: "updated", ActorKind: "system", ActorID: "x"},
		{ID: "e2", TaskID: "task-1", Seq: 9, Kind: "completed", ActorKind: "user", ActorID: "y"},
	}}

	body, err := GetTaskEvents(context.Background(), "task-1", 7, &authdomain.User{}, tasks, events)
	if err != nil {
		t.Fatal(err)
	}
	if !events.called {
		t.Fatal("the ledger must be read once the task is visible")
	}
	got, _ := body.Get("count")
	if got != 2 {
		t.Fatalf("count: got %v", got)
	}
	if after, _ := body.Get("after_seq"); after != 7 {
		t.Fatalf("after_seq must travel through: got %v", after)
	}
}
