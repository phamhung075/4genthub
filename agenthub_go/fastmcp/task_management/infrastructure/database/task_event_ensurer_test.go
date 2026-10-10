package database_test

// Integration tests for the task_events.user_seq ensurer: the column and its per-user unique ship
// on two paths (the TableDef for a fresh database, this ensurer for one that already holds the
// table), and these are the three cases that decide whether the second path is safe.
//
// WHY AN OLD SHAPE, NOT A FRESH DATABASE: a fresh database gets the column by construction, so a
// test that starts fresh cannot see the failure this exists for - production's task_events predates
// the column, the boot called createAll, which skips a table that is absent... and the table was
// not absent. The failure lives in the UPGRADE path.
//
// They need AGENTHUB_TEST_PG_URL (see tools/testpg/start.sh) and skip loudly without it.

import (
	"context"
	"database/sql"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/repositories"
)

// oldShapeColumnsDDL is the shape P1 met: the table exists, WITHOUT user_seq, client_event_id and
// the two per-user uniques, under the CURRENT closed vocabularies - the wave that renamed the actor
// classes and widened the kinds ran before P1's columns, so this is the shape whose only gap is the
// columns. The foreign key to tasks is left out because nothing in these cases depends on it.
const oldShapeColumnsDDL = `CREATE TABLE task_events (
	id UUID NOT NULL,
	task_id UUID NOT NULL,
	subtask_id UUID,
	user_id VARCHAR(64) NOT NULL,
	seq INTEGER NOT NULL,
	kind VARCHAR(32) NOT NULL,
	actor_kind VARCHAR(16) NOT NULL,
	actor_id VARCHAR(255) NOT NULL,
	payload JSONB,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_task_event_seq UNIQUE (task_id, seq),
	CONSTRAINT ck_task_event_kind CHECK (kind IN ('assigned', 'claimed', 'delivered', 'context_loaded', 'progress', 'status_changed', 'evidence_submitted', 'gate_verdict', 'escalated', 'human_decision', 'handover', 'context_updated')),
	CONSTRAINT ck_task_event_actor_kind CHECK (actor_kind IN ('seat', 'client', 'gate', 'human'))
)`

// legacyVocabularyDDL is the shape BEFORE the vocabulary wave: five kinds, three actor classes. The
// ensurer must widen it - the recorder stamps actor_kind 'seat', which this check refuses - and that
// widening validates every existing row, so it is the shape where a populated table cannot reach the
// definition without a value migration (a data move) while an empty one can.
const legacyVocabularyDDL = `CREATE TABLE task_events (
	id UUID NOT NULL,
	task_id UUID NOT NULL,
	subtask_id UUID,
	user_id VARCHAR(64) NOT NULL,
	seq INTEGER NOT NULL,
	kind VARCHAR(32) NOT NULL,
	actor_kind VARCHAR(16) NOT NULL,
	actor_id VARCHAR(255) NOT NULL,
	payload JSONB,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_task_event_seq UNIQUE (task_id, seq),
	CONSTRAINT ck_task_event_kind CHECK (kind IN ('created', 'updated', 'status_changed', 'completed', 'deleted')),
	CONSTRAINT ck_task_event_actor_kind CHECK (actor_kind IN ('user', 'system', 'agent'))
)`

func newEnsurerTestDB(t *testing.T) *sql.DB {
	t.Helper()
	db, err := database.PgxOpener(newTestDatabase(t), database.EngineOptions{PoolSize: 2, MaxOverflow: 2, PoolRecycle: 60})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return db
}

// oldShapeWithRows builds the pre-P1 table and writes two events for each of two users, in seq
// order, so the backfill has something to number.
func oldShapeWithRows(t *testing.T, db *sql.DB) {
	t.Helper()
	ctx := context.Background()
	if _, err := db.ExecContext(ctx, oldShapeColumnsDDL); err != nil {
		t.Fatal(err)
	}
	rows := []struct {
		id, taskID, userID, kind, actorKind, actorID string
		seq                                          int
	}{
		// actor_kind 'seat' is what the recorder stamps, and it is in the fixture's vocabulary (the
		// wave that renamed the actor classes ran before P1's columns).
		{"11111111-1111-1111-1111-111111111111", "aaaaaaaa-0000-0000-0000-000000000001", "user-1", "status_changed", "seat", "room/one", 1},
		{"22222222-2222-2222-2222-222222222222", "aaaaaaaa-0000-0000-0000-000000000001", "user-1", "status_changed", "seat", "room/one", 2},
		{"33333333-3333-3333-3333-333333333333", "bbbbbbbb-0000-0000-0000-000000000002", "user-2", "status_changed", "seat", "room/two", 1},
		{"44444444-4444-4444-4444-444444444444", "bbbbbbbb-0000-0000-0000-000000000002", "user-2", "status_changed", "seat", "room/two", 2},
	}
	for _, r := range rows {
		if _, err := db.ExecContext(ctx,
			`INSERT INTO task_events (id, task_id, user_id, seq, kind, actor_kind, actor_id)
			 VALUES ($1, $2, $3, $4, $5, $6, $7)`,
			r.id, r.taskID, r.userID, r.seq, r.kind, r.actorKind, r.actorID); err != nil {
			t.Fatal(err)
		}
	}
}

func userSeqState(t *testing.T, db *sql.DB) (exists bool, notNull bool, constraint bool) {
	t.Helper()
	if err := db.QueryRowContext(context.Background(),
		`SELECT count(*) > 0,
		        COALESCE(bool_or(is_nullable = 'NO'), false)
		   FROM information_schema.columns
		  WHERE table_name = 'task_events' AND column_name = 'user_seq'`).Scan(&exists, &notNull); err != nil {
		t.Fatal(err)
	}
	if err := db.QueryRowContext(context.Background(),
		`SELECT count(*) > 0 FROM pg_constraint WHERE conname = 'uq_task_event_user_seq'`).Scan(&constraint); err != nil {
		t.Fatal(err)
	}
	return exists, notNull, constraint
}

func userSeqPairs(t *testing.T, db *sql.DB) map[string]int64 {
	t.Helper()
	got := map[string]int64{}
	rows, err := db.QueryContext(context.Background(),
		`SELECT id::text, user_seq FROM task_events ORDER BY id`)
	if err != nil {
		t.Fatal(err)
	}
	defer rows.Close()
	for rows.Next() {
		var id string
		var seq int64
		if err := rows.Scan(&id, &seq); err != nil {
			t.Fatal(err)
		}
		got[id] = seq
	}
	if err := rows.Err(); err != nil {
		t.Fatal(err)
	}
	return got
}

// (a) A FRESH database already has the column and the unique, because CreateTables runs createAll
// first. A plain ADD COLUMN or ADD CONSTRAINT here would fail every boot; this case is what pins
// the guarded shapes.
func TestTaskEventEnsurerLeavesAFreshDatabaseAlone(t *testing.T) {
	db := newEnsurerTestDB(t)
	ctx := context.Background()
	cfg := &database.DatabaseConfig{Engine: &database.Engine{DB: db}}
	if err := cfg.CreateTables(ctx); err != nil {
		t.Fatal(err)
	}
	before := userSeqPairs(t, db)
	if err := database.EnsureTaskEventColumns(ctx, db); err != nil {
		t.Fatalf("the ensurer failed on a database createAll had already migrated: %v", err)
	}
	exists, notNull, constraint := userSeqState(t, db)
	if !exists || !notNull || !constraint {
		t.Fatalf("after the ensurer: column exists=%v notNull=%v constraint=%v, want all true", exists, notNull, constraint)
	}
	after := userSeqPairs(t, db)
	if len(before) != len(after) {
		t.Fatalf("the ensurer changed the row count on a fresh database: %d then %d", len(before), len(after))
	}
}

// (b) THE CASE THE INCIDENT WAS. Rows exist with no user_seq at all; the ensurer must give every
// one of them a value that is gapless per user and ordered by seq, then make the column NOT NULL
// and the unique live.
func TestTaskEventEnsurerBackfillsAnOldShapeWithRows(t *testing.T) {
	db := newEnsurerTestDB(t)
	ctx := context.Background()
	oldShapeWithRows(t, db)

	if err := database.EnsureTaskEventColumns(ctx, db); err != nil {
		t.Fatalf("the ensurer failed on the pre-P1 shape: %v", err)
	}
	exists, notNull, constraint := userSeqState(t, db)
	if !exists || !notNull {
		t.Fatalf("column exists=%v notNull=%v, want both true", exists, notNull)
	}
	if !constraint {
		t.Fatal("uq_task_event_user_seq was not created")
	}
	want := map[string]int64{
		"11111111-1111-1111-1111-111111111111": 1,
		"22222222-2222-2222-2222-222222222222": 2,
		"33333333-3333-3333-3333-333333333333": 1,
		"44444444-4444-4444-4444-444444444444": 2,
	}
	got := userSeqPairs(t, db)
	for id, w := range want {
		if got[id] != w {
			t.Errorf("row %s has user_seq %d, want %d (numbering is per user, in seq order)", id, got[id], w)
		}
	}
	// The unique is live, not merely present: a duplicate (user_id, user_seq) must be refused.
	if _, err := db.ExecContext(ctx,
		`INSERT INTO task_events (id, task_id, user_id, seq, user_seq, kind, actor_kind, actor_id)
		 VALUES ('55555555-5555-5555-5555-555555555555', 'aaaaaaaa-0000-0000-0000-000000000003',
		         'user-1', 9, 1, 'status_changed', 'seat', 'room/one')`); err == nil {
		t.Error("a duplicate (user_id, user_seq) was accepted: the constraint is not enforcing")
	}
	// And the property the policy is about, stated directly: every (user_id, user_seq) pair the
	// backfill produced is distinct - one pair per row, four rows.
	var pairs int
	if err := db.QueryRowContext(ctx,
		`SELECT count(*) FROM (SELECT DISTINCT user_id, user_seq FROM task_events) d`).Scan(&pairs); err != nil {
		t.Fatal(err)
	}
	if pairs != len(want) {
		t.Errorf("(user_id, user_seq) has %d distinct pairs over %d rows: the backfill collided", pairs, len(want))
	}
}

// (c) A SECOND RUN APPLIES NOTHING. The numbers are the evidence: a re-run that renumbered rows
// would move them, and a re-run that re-added the constraint would fail.
func TestTaskEventEnsurerIsIdempotentOnASecondRun(t *testing.T) {
	db := newEnsurerTestDB(t)
	ctx := context.Background()
	oldShapeWithRows(t, db)

	if err := database.EnsureTaskEventColumns(ctx, db); err != nil {
		t.Fatal(err)
	}
	first := userSeqPairs(t, db)
	if err := database.EnsureTaskEventColumns(ctx, db); err != nil {
		t.Fatalf("the second run failed: %v", err)
	}
	second := userSeqPairs(t, db)
	if len(first) != len(second) {
		t.Fatalf("the second run changed the row count: %d then %d", len(first), len(second))
	}
	for id, seq := range first {
		if second[id] != seq {
			t.Errorf("the second run renumbered %s: %d then %d", id, seq, second[id])
		}
	}
	exists, notNull, constraint := userSeqState(t, db)
	if !exists || !notNull || !constraint {
		t.Fatalf("after the second run: column exists=%v notNull=%v constraint=%v, want all true", exists, notNull, constraint)
	}
}

// (d) THE SCHEMA BEING RIGHT AND THE WRITE PATH BEING USABLE ARE TWO CLAIMS. This case makes the
// second one: on the pre-P1 shape, after the ensurer runs, the writes that need user_seq must
// SUCCEED and read back - a status change, which is the one that answered `column "user_seq" does
// not exist` while /health kept answering, and a progress entry, which is where progress lives now
// that the column pair is on its way out.
func TestTaskEventEnsurerRestoresTheWritePathForBothShapes(t *testing.T) {
	db := newEnsurerTestDB(t)
	ctx := context.Background()
	oldShapeWithRows(t, db)
	if err := database.EnsureTaskEventColumns(ctx, db); err != nil {
		t.Fatal(err)
	}

	sessions := database.NewSessionManager(&database.DatabaseConfig{Engine: &database.Engine{DB: db}})
	const taskID = "cccccccc-0000-0000-0000-000000000003"
	recorder := services.NewTaskEventRecorder(repositories.NewTaskEventRepository(sessions, "user-1", ""), "user-1")

	if err := sessions.Transaction(ctx, func(ctx context.Context) error {
		_, err := recorder.RecordStatusChange(ctx, taskID, "todo", "in_progress")
		return err
	}); err != nil {
		t.Fatalf("a status change still fails after the ensurer: %v", err)
	}
	if err := sessions.Transaction(ctx, func(ctx context.Context) error {
		_, err := recorder.Record(ctx, taskID, entities.TaskEventKindProgress, entities.TaskEventActorSeat,
			"room/one", map[string]any{"content": "=== Progress 1 ==="})
		return err
	}); err != nil {
		t.Fatalf("a progress entry still fails after the ensurer: %v", err)
	}

	sequences := map[string]int64{}
	rows, err := db.QueryContext(ctx,
		`SELECT kind, user_seq FROM task_events WHERE task_id = $1 ORDER BY user_seq`, taskID)
	if err != nil {
		t.Fatal(err)
	}
	defer rows.Close()
	for rows.Next() {
		var kind string
		var seq int64
		if err := rows.Scan(&kind, &seq); err != nil {
			t.Fatal(err)
		}
		sequences[kind] = seq
	}
	if err := rows.Err(); err != nil {
		t.Fatal(err)
	}
	status, progress := sequences[string(entities.TaskEventKindStatusChanged)], sequences[string(entities.TaskEventKindProgress)]
	if status == 0 || progress == 0 {
		t.Fatalf("entries did not read back: status=%d progress=%d", status, progress)
	}
	if status == progress {
		t.Errorf("both entries carry user_seq %d: the per-user sequence is not advancing", status)
	}
}

// (e) AN EMPTY TABLE UNDER THE OLD VOCABULARY REACHES THE DEFINITION. This is the shape the real
// ledger had - nothing wrote task_events before P1's reader landed - so the widening must apply, and
// afterwards a 'seat' actor and a 'progress' kind must be accepted, which the old checks refused.
func TestTaskEventEnsurerWidensTheVocabularyOnAnEmptyOldTable(t *testing.T) {
	db := newEnsurerTestDB(t)
	ctx := context.Background()
	if _, err := db.ExecContext(ctx, legacyVocabularyDDL); err != nil {
		t.Fatal(err)
	}
	if err := database.EnsureTaskEventColumns(ctx, db); err != nil {
		t.Fatalf("the ensurer failed on an empty table with the old vocabulary: %v", err)
	}
	if _, err := db.ExecContext(ctx,
		`INSERT INTO task_events (id, task_id, user_id, seq, user_seq, kind, actor_kind, actor_id)
		 VALUES ('66666666-6666-6666-6666-666666666666', 'aaaaaaaa-0000-0000-0000-000000000004',
		         'user-1', 1, 1, 'progress', 'seat', 'room/one')`); err != nil {
		t.Fatalf("a seat actor and a progress kind were refused after the widening: %v", err)
	}
}

// (f) A POPULATED TABLE UNDER THE OLD VOCABULARY CANNOT REACH IT WITHOUT A VALUE MIGRATION, and the
// ensurer must say so rather than pretend: the columns still land (they can go on any table), and the
// widening fails with the constraint's own message naming what violates it. Rewriting those actor
// values is a data move, which is the owner's call and not this ensurer's.
func TestTaskEventEnsurerNamesTheValueMigrationAPopulatedOldTableNeeds(t *testing.T) {
	db := newEnsurerTestDB(t)
	ctx := context.Background()
	if _, err := db.ExecContext(ctx, legacyVocabularyDDL); err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(ctx,
		`INSERT INTO task_events (id, task_id, user_id, seq, kind, actor_kind, actor_id)
		 VALUES ('77777777-7777-7777-7777-777777777777', 'aaaaaaaa-0000-0000-0000-000000000005',
		         'user-1', 1, 'status_changed', 'agent', 'room/one')`); err != nil {
		t.Fatal(err)
	}
	err := database.EnsureTaskEventColumns(ctx, db)
	if err == nil {
		t.Fatal("the widening succeeded over a row carrying an actor the new vocabulary does not have")
	}
	if !strings.Contains(err.Error(), "ck_task_event_actor_kind") {
		t.Errorf("the failure does not name the constraint an operator has to look at: %v", err)
	}
	exists, notNull, constraint := userSeqState(t, db)
	if !exists || !notNull || !constraint {
		t.Fatalf("the columns did not land even though the widening failed: exists=%v notNull=%v unique=%v", exists, notNull, constraint)
	}
}
