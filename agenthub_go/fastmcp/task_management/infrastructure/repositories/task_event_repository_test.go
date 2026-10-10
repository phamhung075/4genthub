package repositories

import (
	"context"
	"sync"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// TestTaskEventAppendAssignsGaplessSeq is the O1a acceptance test, written BEFORE the
// implementation so the red run is evidence rather than a claim. Two concurrent Appends on ONE
// task must get seq 1 and seq 2 - never a duplicate, never a gap.
//
// It is PostgreSQL-gated through newTestRepoEnv, like its siblings: with no AGENTHUB_TEST_PG_URL
// it SKIPS, and a skip is not a pass.
func TestTaskEventAppendAssignsGaplessSeq(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)
	events := NewTaskEventRepository(sessions, taskRepoTestUserA, branchID)

	task, err := repo.CreateTask(ctx, "Ledger subject", "D", "high", []string{"agent-x"}, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	taskID := task.ID.Value

	const writers = 2
	seqs := make([]int, writers)
	errs := make([]error, writers)
	var wg sync.WaitGroup
	start := make(chan struct{})
	for i := 0; i < writers; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			<-start
			ev, err := events.Append(ctx, entities.AppendTaskEvent{
				TaskID:    taskID,
				Kind:      entities.TaskEventKindProgress,
				ActorKind: entities.TaskEventActorHuman,
				ActorID:   "test",
			})
			if err != nil {
				errs[i] = err
				return
			}
			seqs[i] = ev.Seq
		}(i)
	}
	close(start)
	wg.Wait()

	for i, err := range errs {
		if err != nil {
			t.Fatalf("writer %d: %v", i, err)
		}
	}
	if seqs[0] == seqs[1] {
		t.Fatalf("concurrent appends produced the SAME seq %d - a duplicate is a lost event", seqs[0])
	}
	seen := map[int]bool{}
	for _, s := range seqs {
		seen[s] = true
	}
	if !seen[1] || !seen[2] {
		t.Fatalf("gapless per-task sequence expected {1,2}, got %v", seqs)
	}

	// after_seq returns only what comes after it - the third acceptance negative.
	afterFirst, err := events.ListAfter(ctx, taskID, 1, 100)
	if err != nil {
		t.Fatal(err)
	}
	if len(afterFirst) != 1 || afterFirst[0].Seq != 2 {
		t.Fatalf("after_seq=1 must return only seq>1, got %#v", afterFirst)
	}
}

// TestTaskEventAppendRefusesBogusKind is acceptance negative (i): the closed vocabulary is
// enforced by the database, not by Go, so a value that skips the Go constants is still refused.
func TestTaskEventAppendRefusesBogusKind(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)
	events := NewTaskEventRepository(sessions, taskRepoTestUserA, branchID)

	task, err := repo.CreateTask(ctx, "Bogus kind subject", "D", "high", nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := events.Append(ctx, entities.AppendTaskEvent{
		TaskID:    task.ID.Value,
		Kind:      entities.TaskEventKind("bogus"),
		ActorKind: entities.TaskEventActorHuman,
		ActorID:   "test",
	}); err == nil {
		t.Fatal("kind='bogus' was accepted; the database must refuse a value outside the vocabulary")
	}
}

// TestTaskEventAppendGivesOneGaplessUserCursorAndRefusesAResend is P1's acceptance test.
//
// `user_seq` is the cursor the WHOLE ledger is read by, so two appends for one user - on DIFFERENT
// tasks, which is the case a per-task lock cannot cover - must never share a number and never leave
// a gap. And a resend carrying a client_event_id already stored must be REFUSED by the unique
// constraint rather than landing a second row: the outbox retries after a reconnect, and "exactly
// once" is that constraint's job, not a rule the client has to remember.
//
// It also pins the actor vocabulary where it lands - at the table - by inserting a value that skips
// the Go constants entirely and requiring the database to refuse it.
func TestTaskEventAppendGivesOneGaplessUserCursorAndRefusesAResend(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)
	events := NewTaskEventRepository(sessions, taskRepoTestUserA, branchID)

	first, err := repo.CreateTask(ctx, "Cursor one", "D", "high", nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	second, err := repo.CreateTask(ctx, "Cursor two", "D", "high", nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}

	// One append per task, concurrently: the per-USER lock is what serializes them, and a per-task
	// lock would let both take the same user_seq because their tasks differ.
	taskIDs := []string{first.ID.Value, second.ID.Value}
	const writers = 2
	userSeqs := make([]int64, writers)
	taskSeqs := make([]int, writers)
	errs := make([]error, writers)
	var wg sync.WaitGroup
	start := make(chan struct{})
	for i := 0; i < writers; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			<-start
			ev, err := events.Append(ctx, entities.AppendTaskEvent{
				TaskID:    taskIDs[i],
				Kind:      entities.TaskEventKindProgress,
				ActorKind: entities.TaskEventActorHuman,
				ActorID:   "test",
			})
			if err != nil {
				errs[i] = err
				return
			}
			userSeqs[i] = ev.UserSeq
			taskSeqs[i] = ev.Seq
		}(i)
	}
	close(start)
	wg.Wait()
	for i, err := range errs {
		if err != nil {
			t.Fatalf("writer %d: %v", i, err)
		}
	}
	t.Logf("OBSERVED user_seq across two tasks = %v, per-task seq = %v", userSeqs, taskSeqs)

	if userSeqs[0] == userSeqs[1] {
		t.Fatalf("two appends for one user took the SAME user_seq %d - a reader that has passed it would miss a row", userSeqs[0])
	}
	seenUser := map[int64]bool{}
	for _, s := range userSeqs {
		seenUser[s] = true
	}
	if !seenUser[1] || !seenUser[2] {
		t.Fatalf("gapless per-user cursor expected {1,2}, got %v", userSeqs)
	}
	// The per-task sequence is still the task's own: each of these is that task's first entry.
	for i, s := range taskSeqs {
		if s != 1 {
			t.Fatalf("task %d's first entry has seq %d, want 1: the per-task sequence must not be shared", i, s)
		}
	}

	// A resend is refused, and the ledger keeps exactly one row for the key.
	const key = "9f1c2d3e-4a5b-4c6d-8e7f-001122334455"
	if _, err := events.Append(ctx, entities.AppendTaskEvent{
		TaskID: taskIDs[0], Kind: entities.TaskEventKindProgress,
		ActorKind: entities.TaskEventActorHuman, ActorID: "test", ClientEventID: key,
	}); err != nil {
		t.Fatalf("first keyed append: %v", err)
	}
	if _, err := events.Append(ctx, entities.AppendTaskEvent{
		TaskID: taskIDs[0], Kind: entities.TaskEventKindProgress,
		ActorKind: entities.TaskEventActorHuman, ActorID: "test", ClientEventID: key,
	}); err == nil {
		t.Fatal("the same client_event_id was accepted twice: the unique constraint must refuse a resend")
	}

	// The actor class is refused where the bytes land, by the CHECK, for a value Go never offers.
	if _, err := events.Append(ctx, entities.AppendTaskEvent{
		TaskID: taskIDs[0], Kind: entities.TaskEventKindProgress,
		ActorKind: entities.TaskEventActorKind("bogus"), ActorID: "test",
	}); err == nil {
		t.Fatal("actor_kind='bogus' was accepted; the database must refuse a value outside the vocabulary")
	}
}
