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

// TestProgressEventsByTaskIsOneReadForTheWholePage covers the reader the list and search builders use
// to render every row's details. It is ONE call for the page, so it must group by task id, name only
// the progress kind, keep seq order, and answer nothing for a task it was asked about that has no
// events - and nothing for another user's task.
func TestProgressEventsByTaskIsOneReadForTheWholePage(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)
	events := NewTaskEventRepository(sessions, taskRepoTestUserA, branchID)

	withNotes, err := repo.CreateTask(ctx, "Listed with notes", "D", "high", nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	withoutNotes, err := repo.CreateTask(ctx, "Listed without notes", "D", "high", nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	for i, content := range []string{"=== Progress 1 ===\nfirst note", "=== Progress 2 ===\nsecond note"} {
		if _, err := events.Append(ctx, entities.AppendTaskEvent{
			TaskID:    withNotes.ID.Value,
			Kind:      entities.TaskEventKindProgress,
			ActorKind: entities.TaskEventActorHuman,
			ActorID:   "test",
			Payload:   map[string]any{"content": content, "progress_number": i + 1},
		}); err != nil {
			t.Fatal(err)
		}
	}
	// The same task also carries a non-progress event: the reader names one kind, and a list row
	// renders notes, so anything else must not come back as one.
	if _, err := events.Append(ctx, entities.AppendTaskEvent{
		TaskID:    withNotes.ID.Value,
		Kind:      entities.TaskEventKindStatusChanged,
		ActorKind: entities.TaskEventActorHuman,
		ActorID:   "test",
	}); err != nil {
		t.Fatal(err)
	}

	// Another user's ledger, with a note on another user's task. The page is asked for it, and the
	// answer must not carry it: the repository filters by user_id.
	foreignBranch := taskRepoTestBranch(t, sessions, taskRepoTestUserB)
	foreignEvents := NewTaskEventRepository(sessions, taskRepoTestUserB, foreignBranch)
	foreign, err := taskRepoTestNewRepo(t, sessions, taskRepoTestUserB, foreignBranch, false).
		CreateTask(ctx, "Another user's task", "D", "high", nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := foreignEvents.Append(ctx, entities.AppendTaskEvent{
		TaskID:    foreign.ID.Value,
		Kind:      entities.TaskEventKindProgress,
		ActorKind: entities.TaskEventActorHuman,
		ActorID:   "test",
		Payload:   map[string]any{"content": "=== Progress 1 ===\nnot yours", "progress_number": 1},
	}); err != nil {
		t.Fatal(err)
	}

	byTask, err := events.ProgressEventsByTask(ctx, []string{withNotes.ID.Value, withoutNotes.ID.Value, foreign.ID.Value})
	if err != nil {
		t.Fatal(err)
	}
	if len(byTask) != 1 {
		t.Fatalf("reader answered for %d tasks, want 1 (the page's task that HAS notes): %#v", len(byTask), byTask)
	}
	got := byTask[withNotes.ID.Value]
	if len(got) != 2 {
		t.Fatalf("notes = %d, want 2: the status event is not a note", len(got))
	}
	if got[0].Seq >= got[1].Seq {
		t.Fatalf("notes are not in seq order: %d then %d", got[0].Seq, got[1].Seq)
	}
	if content, _ := got[0].Payload["content"].(string); content != "=== Progress 1 ===\nfirst note" {
		t.Fatalf("first note = %q, want the seq-1 content", content)
	}
	if events, ok := byTask[withoutNotes.ID.Value]; ok {
		t.Fatalf("a task with no events answered %#v, want no entry: a row with no notes is empty", events)
	}
	if _, ok := byTask[foreign.ID.Value]; ok {
		t.Fatal("another user's task is in the answer: the read is not user-scoped")
	}
	if empty, err := events.ProgressEventsByTask(ctx, nil); err != nil || len(empty) != 0 {
		t.Fatalf("an empty page answered %#v, %v, want an empty map and no error", empty, err)
	}
}

// TestNextProgressNumberInTxIsReadInsideTheCallersTransaction is the fix for the gate's MINOR: the note
// number's MAX+1 is read INSIDE the caller's transaction and under the SAME advisory lock the append
// takes, never before it. Two writers that each open their own transaction must therefore take
// DIFFERENT numbers for their notes - the property that keeps a reader's merge identity (content plus
// number together) from collapsing two live notes into one.
func TestNextProgressNumberInTxIsReadInsideTheCallersTransaction(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)
	events := NewTaskEventRepository(sessions, taskRepoTestUserA, branchID)

	task, err := repo.CreateTask(ctx, "Numbering subject", "D", "high", nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}

	// Outside a transaction it REFUSES: the number is only safe to read while holding the lock the
	// append takes, and a read that holds nothing is the defect this replaces.
	if _, err := events.NextProgressNumberInTx(ctx, task.ID.Value); err == nil {
		t.Fatal("the number was read outside a transaction: nothing holds the lock, so two writers could share it")
	}

	// A carried note's number is CONTINUED rather than restarted: this is a task whose notes reached 7
	// while the column still held them.
	if _, err := events.Append(ctx, entities.AppendTaskEvent{
		TaskID:    task.ID.Value,
		Kind:      entities.TaskEventKindProgress,
		ActorKind: entities.TaskEventActorHuman,
		ActorID:   "test",
		Payload:   map[string]any{"content": "=== Progress 7 ===\ncarried", "progress_number": 7},
	}); err != nil {
		t.Fatal(err)
	}
	var next int
	if err := sessions.Transaction(ctx, func(ctx context.Context) error {
		var err error
		next, err = events.NextProgressNumberInTx(ctx, task.ID.Value)
		return err
	}); err != nil || next != 8 {
		t.Fatalf("next number = %d, %v, want 8: the sequence continues from the carried tip", next, err)
	}

	// Two writers, each in its own transaction: read the tip, then append its note under it.
	const writers = 2
	numbers := make([]int, writers)
	errs := make([]error, writers)
	var wg sync.WaitGroup
	start := make(chan struct{})
	for i := 0; i < writers; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			<-start
			errs[i] = sessions.Transaction(ctx, func(ctx context.Context) error {
				n, err := events.NextProgressNumberInTx(ctx, task.ID.Value)
				if err != nil {
					return err
				}
				numbers[i] = n
				_, err = events.AppendInTx(ctx, entities.AppendTaskEvent{
					TaskID:    task.ID.Value,
					Kind:      entities.TaskEventKindProgress,
					ActorKind: entities.TaskEventActorHuman,
					ActorID:   "test",
					Payload:   map[string]any{"content": "=== Progress note ===\nconcurrent", "progress_number": n},
				})
				return err
			})
		}(i)
	}
	close(start)
	wg.Wait()
	for i, err := range errs {
		if err != nil {
			t.Fatalf("writer %d: %v", i, err)
		}
	}
	seen := map[int]bool{numbers[0]: true, numbers[1]: true}
	if !seen[8] || !seen[9] {
		t.Fatalf("numbers = %v, want {8, 9}: each writer continues the task's ONE sequence", numbers)
	}
}

// TestTaskEventAppendTakesTheNextTaskSeqAcrossTwoWriterIdentities is the regression for the
// 2026-10-15 defect: `manage_task(action=update)` answered
// `duplicate key value violates unique constraint "uq_task_event_seq"` (SQLSTATE 23505)
// deterministically on a freshly created task, and get showed the row unchanged because the whole
// update transaction rolled back.
//
// WHAT IT PINS. The task-level context event was appended through a repository built with user_id ""
// while the task's own status event was appended under the caller, so ONE task carried two spellings of
// its writer's rows. The seq is unique over (task_id, seq) - the TASK, not (user, task) - so computing
// it over the narrower domain handed the second writer a number already taken. Here the two identities
// are two users, which is what a second identity IS; the first append is the context event's position,
// the second is the task's own, and it must take the NEXT number rather than collide.
func TestTaskEventAppendTakesTheNextTaskSeqAcrossTwoWriterIdentities(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)
	firstWriter := NewTaskEventRepository(sessions, taskRepoTestUserB, branchID)
	secondWriter := NewTaskEventRepository(sessions, taskRepoTestUserA, branchID)

	task, err := repo.CreateTask(ctx, "Two writer identities, one task", "D", "high", []string{"agent-x"}, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	taskID := task.ID.Value

	first, err := firstWriter.Append(ctx, entities.AppendTaskEvent{
		TaskID:    taskID,
		Kind:      entities.TaskEventKindContextUpdated,
		ActorKind: entities.TaskEventActorSeat,
		ActorID:   "context",
	})
	if err != nil {
		t.Fatalf("the first writer: %v", err)
	}
	second, err := secondWriter.Append(ctx, entities.AppendTaskEvent{
		TaskID:    taskID,
		Kind:      entities.TaskEventKindStatusChanged,
		ActorKind: entities.TaskEventActorHuman,
		ActorID:   "test",
	})
	if err != nil {
		t.Fatalf("the second writer must take the task's next seq, not collide: %v", err)
	}
	if second.Seq != first.Seq+1 {
		t.Fatalf("seq = %d after %d, want the next number: the seq is the TASK's", second.Seq, first.Seq)
	}

	// The reader is scoped to its own user, so this one assertion covers two properties: the caller
	// sees the entry it just wrote, and it does NOT see the other identity's - which is why a row
	// written under a different spelling of the same caller is a row the caller's history loses.
	own, err := secondWriter.ListAfter(ctx, taskID, 0, 100)
	if err != nil {
		t.Fatal(err)
	}
	if len(own) != 1 || own[0].Seq != second.Seq {
		t.Fatalf("the caller's own ledger read must hold exactly its entry at seq %d, got %#v", second.Seq, own)
	}
}
