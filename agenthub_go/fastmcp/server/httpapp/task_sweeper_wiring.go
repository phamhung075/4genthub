package httpapp

// The task lifecycle sweep as THIS app composes it: the read side over the tasks table, the write
// side over the SAME task facade the routes write through, the audit trail over its own table, and
// the advisory lock over a session of its own.
//
// WHY THE WRITES GO THROUGH THE FACADE RATHER THAN THE REPOSITORY. The owner's ruling is that every
// escalation, block and delete reaches the audit trail AND publishes the normal task events; the
// facade's update and delete use cases are what produce those events, the status_changed and
// progress entries in the ledger, the cascading delete and the websocket frames, so the sweep drives
// them rather than the repository beneath them. The priority and status moves inside them are the
// entity's own UpdatePriority/UpdateStatus, which keeps the domain's transition rules in charge.

import (
	"context"
	"fmt"
	"strings"
	"time"

	"agenthub/fastmcp/auth/middleware"
	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/application/factories"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// NewTaskLifecycleSweeper composes the periodic sweep.
//
// IT READS ITS SCHEDULE HERE, and a malformed interval is returned as an error rather than
// swallowed: cmd/agenthub/main.go refuses to start on it, which is what the guide's constraint asks
// for (a missing variable takes its documented default, a malformed one fails startup).
func NewTaskLifecycleSweeper(ctx context.Context, sessions *database.SessionManager) (*services.TaskLifecycleSweeper, error) {
	cfg, err := services.TaskSweepConfigFromEnv()
	if err != nil {
		return nil, fmt.Errorf("task lifecycle sweep schedule: %w", err)
	}
	ctxFactory, err := factories.NewUnifiedContextFacadeFactory(ctx, sessions)
	if err != nil {
		return nil, fmt.Errorf("task lifecycle sweep context factory: %w", err)
	}
	provider := taskFacadeProvider{
		sessions:   sessions,
		ctxFactory: ctxFactory,
		notifier:   newTaskNotifier(sessions),
	}
	return services.NewTaskLifecycleSweeper(
		sweepTaskSource{sessions: sessions},
		newSweepWriter(provider),
		infrarepos.NewTaskAuditRecordRepository(sessions),
		sweepLock{sessions: sessions},
		cfg,
	), nil
}

// sweepUserContext stamps the task's OWNER onto the context the facade writes under. A facade with
// no user on the context stamps its notification "system", and a "system" stamp is refused wherever
// the ownership of the resource cannot be established - so without this the UI would not learn about
// the sweep's changes at all.
func sweepUserContext(ctx context.Context, userID string) context.Context {
	if userID == "" {
		return ctx
	}
	return middleware.WithRequestAuthContext(ctx, &middleware.RequestAuthContext{UserID: new(userID)})
}

// sweepFacadeError turns a facade result into the error the sweep logs. The facade answers with
// {"success": false, "error"|"message": "..."} rather than an error value, so the message the
// caller would have seen is what the sweep reports.
func sweepFacadeError(action string, result *entities.OrderedMap[any]) error {
	if success, ok := result.Get("success"); ok {
		if done, isBool := success.(bool); isBool && done {
			return nil
		}
	}
	for _, key := range []string{"error", "message"} {
		if v, ok := result.Get(key); ok && v != nil {
			return fmt.Errorf("%s: %s", action, value_objects.PyStr(v))
		}
	}
	return fmt.Errorf("%s: the application layer reported no success", action)
}

// sweepTaskSource is the sweep's read side, over the tasks table itself.
//
// IT IS NOT USER-SCOPED, and that is the difference between it and every repository in
// infrastructure/repositories: the sweep is one platform actor with every user's tasks to enforce
// the ruling over, so the filter here is the STATUS SET the rule names and nothing else. It is a
// read model rather than the Task entity because the entity's own repositories are user-scoped and
// because the age a rule measures - completed_at else updated_at - is not on the entity.
type sweepTaskSource struct{ sessions *database.SessionManager }

// sweepTaskColumns is the read model's column list, in the order readSweepTask scans it.
const sweepTaskColumns = `"id", "user_id", "title", "status", "priority", "created_at", "updated_at", "completed_at", "completion_summary"`

// Completed returns every task in a completed state (done, cancelled, archived).
func (src sweepTaskSource) Completed(ctx context.Context) ([]services.SweepTask, error) {
	return src.statesIn(ctx, value_objects.TaskStatusDone, value_objects.TaskStatusCancelled, value_objects.TaskStatusArchived)
}

// Open returns every task in an open state (todo, in_progress, review, testing). Blocked is NOT
// here: a blocked task is never pruned or escalated, so the sweep has nothing to do with it.
func (src sweepTaskSource) Open(ctx context.Context) ([]services.SweepTask, error) {
	return src.statesIn(ctx, value_objects.TaskStatusTodo, value_objects.TaskStatusInProgress,
		value_objects.TaskStatusReview, value_objects.TaskStatusTesting)
}

// statesIn reads the tasks in the given states, oldest update first. The statuses are spelled from
// the value objects rather than as SQL literals, so a status renamed there is a status this query
// follows.
func (src sweepTaskSource) statesIn(ctx context.Context, states ...value_objects.TaskStatusEnum) ([]services.SweepTask, error) {
	placeholders := make([]string, len(states))
	args := make([]any, len(states))
	for i, state := range states {
		placeholders[i] = fmt.Sprintf("$%d", i+1)
		args[i] = string(state)
	}
	query := `SELECT ` + sweepTaskColumns + ` FROM tasks WHERE "status" IN (` + strings.Join(placeholders, ", ") + `) ORDER BY "updated_at"`
	var out []services.SweepTask
	err := src.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx, query, args...)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			task, err := readSweepTask(rows)
			if err != nil {
				return err
			}
			out = append(out, task)
		}
		return rows.Err()
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// readSweepTask scans one row in sweepTaskColumns order. The timestamps are taken as the driver
// hands them back, exactly as the ORM repository takes them for the entity: the columns hold UTC and
// the driver reads a `timestamp without time zone` back in UTC, so the age the sweep measures is
// measured against the same instant the rest of the codebase reads.
func readSweepTask(rows interface{ Scan(...any) error }) (services.SweepTask, error) {
	var (
		task              services.SweepTask
		createdAt         time.Time
		updatedAt         time.Time
		completedAt       *time.Time
		completionSummary *string
	)
	if err := rows.Scan(&task.ID, &task.UserID, &task.Title, &task.Status, &task.Priority,
		&createdAt, &updatedAt, &completedAt, &completionSummary); err != nil {
		return services.SweepTask{}, err
	}
	task.CreatedAt = createdAt
	task.UpdatedAt = updatedAt
	task.CompletedAt = completedAt
	if completionSummary != nil {
		task.CompletionSummary = *completionSummary
	}
	return task, nil
}

// Evidence reads the task's evidence from the ledger, BEFORE the prune deletes it: the ledger
// `evidence_submitted` entries are the only place a task's evidence is stored, and the delete
// cascade removes them with the task.
//
// The repository is built for the task's OWN user, because the ledger is per user and every entry
// of a task was written under its owner; a repository built once for "the system" would read no
// entries at all.
func (src sweepTaskSource) Evidence(ctx context.Context, task services.SweepTask) ([]map[string]any, error) {
	events, err := infrarepos.NewTaskEventRepository(src.sessions, task.UserID, "").Events(ctx, task.ID)
	if err != nil {
		return nil, err
	}
	var evidence []map[string]any
	for _, event := range events {
		if event.Kind != entities.TaskEventKindEvidenceSubmitted {
			continue
		}
		evidence = append(evidence, event.Payload)
	}
	return evidence, nil
}

// sweepAdvisoryLockKey names the sweep's lock. It is a fixed string rather than a user id or a task
// id, hashed by the database into the same one-argument key space the ledger's per-user lock uses
// (pg_advisory_xact_lock(hashtext($1))), and it is deliberately its own key: two instances of THIS
// sweep contend for it and nothing else does.
const sweepAdvisoryLockKey = "task_lifecycle_sweeper"

// sweepLock is the sweep's advisory lock, taken on a session of its own.
type sweepLock struct{ sessions *database.SessionManager }

// WithLock runs fn while this instance holds the sweep lock on a pinned session.
//
// TRY, NOT THE BLOCKING FORM: a second instance must SKIP the interval, not queue a second sweep
// behind the first - two sweeps run one after the other are still two sweeps, and the blocking form
// would deliver exactly that.
//
// XACT, NOT THE SESSION FORM: pg_advisory_xact_lock is released when the transaction that took it
// ends, and WithSession's transaction ends when fn returns - including on a panic, which rolls it
// back. A session-scoped lock would instead have to be unlocked by hand and would survive a
// connection handed back to the pool, which is the one way this lock could outlive its sweep and
// stop every later one.
//
// WHAT THE SWEEP'S OWN WRITES DO WITH THIS TRANSACTION: nothing. WithSession hands fn a session
// WITHOUT putting its transaction on the context, so each application-layer write inside fn opens a
// transaction of its own and commits - and publishes its websocket frame - like any other change.
// Running the whole sweep in this transaction would hold the same lock and would make a single
// failed task roll back every change the interval had made.
func (l sweepLock) WithLock(ctx context.Context, fn func() error) (bool, error) {
	ran := false
	err := l.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var acquired bool
		if err := s.QueryRowContext(ctx, `SELECT pg_try_advisory_xact_lock(hashtext($1))`, sweepAdvisoryLockKey).Scan(&acquired); err != nil {
			return err
		}
		if !acquired {
			return nil
		}
		ran = true
		return fn()
	})
	return ran, err
}

// sweepWriter drives the sweep's writes through the application layer's own use cases, with ONE
// facade per user.
//
// WHY PER USER RATHER THAN ONE SYSTEM FACADE. A facade carries the user its repositories and its
// status ledger write under: the ledger is per-user (its user_seq cursor and its read path are
// scoped to a user id), so a facade built with no user would write the sweep's ledger entries under
// an empty id - entries the owner's own events read would never show, sitting in a cursor nobody
// follows. The facades are cached by user id because one user usually owns several tasks of one
// sweep, and building one is the same work the routes do per request.
type sweepWriter struct {
	provider taskFacadeProvider
	facades  map[string]*facades.TaskApplicationFacade
}

func newSweepWriter(provider taskFacadeProvider) *sweepWriter {
	return &sweepWriter{provider: provider, facades: map[string]*facades.TaskApplicationFacade{}}
}

// facadeFor returns the facade for the task's owner, building it on first use. A task that carries no
// user id falls back to the unscoped facade, which is the only shape left for a row that names no
// owner.
func (w *sweepWriter) facadeFor(ctx context.Context, userID string) (*facades.TaskApplicationFacade, error) {
	if facade, ok := w.facades[userID]; ok {
		return facade, nil
	}
	var user *string
	if userID != "" {
		user = new(userID)
	}
	facade, err := w.provider.TaskFacade(ctx, user, nil, nil)
	if err != nil {
		return nil, err
	}
	w.facades[userID] = facade
	return facade, nil
}

// Escalate raises the priority to the one level the sweep already chose and writes the note that
// names the step - the note reaches the ledger as this update's progress entry, through the same
// status ledger a manual update's note goes through.
func (w *sweepWriter) Escalate(ctx context.Context, task services.SweepTask, to value_objects.Priority, note string) error {
	return w.update(ctx, task, dtostask.UpdateTaskRequest{TaskID: task.ID, Priority: new(to.Value), Details: new(note)})
}

// Block moves the task to blocked and carries the blocker text as the note, so the words a human
// needs are in the task's own history rather than only in the audit trail.
func (w *sweepWriter) Block(ctx context.Context, task services.SweepTask, blocker string) error {
	status := string(value_objects.TaskStatusBlocked)
	return w.update(ctx, task, dtostask.UpdateTaskRequest{TaskID: task.ID, Status: new(status), Details: new(blocker)})
}

// update is the ONE update call both lifecycle moves make, and it exists so the two cannot come to
// attribute or scope their write differently.
func (w *sweepWriter) update(ctx context.Context, task services.SweepTask, request dtostask.UpdateTaskRequest) error {
	facade, err := w.facadeFor(ctx, task.UserID)
	if err != nil {
		return err
	}
	return sweepFacadeError("update", facade.UpdateTask(sweepUserContext(ctx, task.UserID), request))
}

// Delete deletes the task through the delete use case, whose cascade removes the subtasks,
// assignees, contexts, dependencies, labels and ledger entries the schema does not cascade - which
// is why the sweep does not issue a DELETE of its own.
func (w *sweepWriter) Delete(ctx context.Context, task services.SweepTask) error {
	facade, err := w.facadeFor(ctx, task.UserID)
	if err != nil {
		return err
	}
	var owner *string
	if task.UserID != "" {
		owner = new(task.UserID)
	}
	return sweepFacadeError("delete", facade.DeleteTask(sweepUserContext(ctx, task.UserID), task.ID, owner))
}
