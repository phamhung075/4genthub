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
				Kind:      entities.TaskEventKindCreated,
				ActorKind: entities.TaskEventActorSystem,
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
		ActorKind: entities.TaskEventActorSystem,
		ActorID:   "test",
	}); err == nil {
		t.Fatal("kind='bogus' was accepted; the database must refuse a value outside the vocabulary")
	}
}
