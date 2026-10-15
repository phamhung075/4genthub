package services

import (
	"context"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// The owner's ruling (2026-10-15): a task must end done or blocked after it is created, and the
// server enforces it with ONE periodic sweep - nothing depends on a seat remembering. This file is
// that sweep: the three age rules, the audit trail that keeps a pruned task's evidence, and the
// ports it reads and writes through.
//
// WHAT THE SWEEP IS NOT. It is not a second write path: every escalation, block and delete goes
// through the same application use cases the routes use (SweepWriter's implementation drives the
// task facade), so the events, the ledger entries and the websocket frames a lifecycle change
// produces are the ones every other change produces - and the priority and status moves are made by
// the ENTITY's own UpdatePriority/UpdateStatus, so the transition rules stay the domain's to keep.

// Environment variables the sweep's schedule is read from. Every interval the sweep measures comes
// from one of these; no number is hard-coded except the documented defaults below.
const (
	TaskSweepIntervalEnv = "TASK_SWEEP_INTERVAL"
	TaskPruneAfterEnv    = "TASK_PRUNE_AFTER"
	TaskEscalateAfterEnv = "TASK_ESCALATE_AFTER"
	TaskBlockAfterEnv    = "TASK_BLOCK_AFTER"
)

// The documented defaults: the values a deployment that sets nothing gets.
const (
	DefaultTaskSweepInterval = time.Hour
	DefaultTaskPruneAfter    = 7 * 24 * time.Hour
	DefaultTaskEscalateAfter = 24 * time.Hour
	DefaultTaskBlockAfter    = 7 * 24 * time.Hour
)

// TaskSweepConfig is the sweep's whole schedule: how often it runs, and the three ages its rules
// turn on.
type TaskSweepConfig struct {
	// Interval is TASK_SWEEP_INTERVAL (default 1h): how often one sweep runs.
	Interval time.Duration
	// PruneAfter is TASK_PRUNE_AFTER (default 7d): the age at which a done, cancelled or archived
	// task is deleted.
	PruneAfter time.Duration
	// EscalateAfter is TASK_ESCALATE_AFTER (default 24h): the age at which an open task's priority
	// climbs one level.
	EscalateAfter time.Duration
	// BlockAfter is TASK_BLOCK_AFTER (default 7d): the age at which an open task that is already
	// critical becomes blocked.
	BlockAfter time.Duration
}

// TaskSweepConfigFromEnv reads the schedule from the environment.
//
// A MISSING VARIABLE TAKES ITS DOCUMENTED DEFAULT; A MALFORMED ONE IS AN ERROR, and the caller is
// expected to refuse to start on it (cmd/agenthub/main.go does). The two halves are deliberately
// different: a deployment that sets nothing gets the documented behaviour, while a deployment that
// meant to set `TASK_PRUNE_AFTER=7 days` and misspelled it must not be quietly served the default -
// an enforcement age nobody chose is worse than a server that will not boot.
func TaskSweepConfigFromEnv() (TaskSweepConfig, error) {
	interval, err := taskSweepEnvDuration(TaskSweepIntervalEnv, DefaultTaskSweepInterval)
	if err != nil {
		return TaskSweepConfig{}, err
	}
	pruneAfter, err := taskSweepEnvDuration(TaskPruneAfterEnv, DefaultTaskPruneAfter)
	if err != nil {
		return TaskSweepConfig{}, err
	}
	escalateAfter, err := taskSweepEnvDuration(TaskEscalateAfterEnv, DefaultTaskEscalateAfter)
	if err != nil {
		return TaskSweepConfig{}, err
	}
	blockAfter, err := taskSweepEnvDuration(TaskBlockAfterEnv, DefaultTaskBlockAfter)
	if err != nil {
		return TaskSweepConfig{}, err
	}
	return TaskSweepConfig{
		Interval:      interval,
		PruneAfter:    pruneAfter,
		EscalateAfter: escalateAfter,
		BlockAfter:    blockAfter,
	}, nil
}

// taskSweepEnvDuration reads one environment duration: an absent or blank variable takes def, and
// anything else is parsed as a Go duration plus the day suffix the guide spells its ages with
// ("7d"). A value that is neither - "abc", "7x", "0", "-3h" - is an error rather than a quiet
// default, and the error names the variable so the operator knows which one to look at.
func taskSweepEnvDuration(key string, def time.Duration) (time.Duration, error) {
	raw, ok := os.LookupEnv(key)
	if !ok || strings.TrimSpace(raw) == "" {
		return def, nil
	}
	value := strings.TrimSpace(raw)
	parsed, err := taskSweepParseDuration(value)
	if err != nil {
		return 0, fmt.Errorf("%s: %q is not a duration (spell it as seconds, minutes or days: 90m, 24h, 7d): %w", key, raw, err)
	}
	if parsed <= 0 {
		return 0, fmt.Errorf("%s: %q is not a positive duration", key, raw)
	}
	return parsed, nil
}

// taskSweepParseDuration parses the two spellings the schedule accepts: a Go duration ("24h",
// "90m") and whole days ("7d"), which time.ParseDuration does not know.
func taskSweepParseDuration(value string) (time.Duration, error) {
	if days, ok := strings.CutSuffix(value, "d"); ok {
		n, err := strconv.Atoi(days)
		if err != nil {
			return 0, err
		}
		return time.Duration(n) * 24 * time.Hour, nil
	}
	return time.ParseDuration(value)
}

// SweepTask is what the sweep reads about one task: the fields the three rules turn on, plus the
// summary a prune has to keep. It is a read model rather than the entity on purpose - the sweep is a
// platform actor that sees every user's tasks, and the entity's user-scoped repositories are for the
// application layer's own writes, which the sweep reaches through SweepWriter instead.
type SweepTask struct {
	ID                string
	UserID            string
	Title             string
	Status            string
	Priority          string
	CompletionSummary string
	CreatedAt         time.Time
	UpdatedAt         time.Time
	CompletedAt       *time.Time
}

// Age is the age the rules measure: completed_at when the row has one, updated_at otherwise, and
// both against the instant the sweep is running at.
func (t SweepTask) Age(now time.Time) time.Duration {
	at := t.UpdatedAt
	if t.CompletedAt != nil {
		at = *t.CompletedAt
	}
	return now.Sub(at)
}

// SweepTaskSource is the sweep's read side: the tasks it has to consider, and the evidence a prune
// has to keep.
//
// THE AGES ARE NOT FILTERED HERE. Completed and Open hand over the candidate sets, and every rule
// about how old is old enough is applied by the sweep, so the rules can be driven against a fake
// clock rather than buried in SQL. The sets are small by construction: a task is expected to end
// done, cancelled, archived or blocked, so the open set is the work actually in flight, and the
// completed set is what the prune age has not yet taken.
type SweepTaskSource interface {
	// Completed returns every task in a completed state (done, cancelled, archived).
	Completed(ctx context.Context) ([]SweepTask, error)
	// Open returns every task in an open state (todo, in_progress, review, testing). Blocked is not
	// an open state for these rules: a blocked task is never pruned or escalated, and the sweep
	// leaves it alone.
	Open(ctx context.Context) ([]SweepTask, error)
	// Evidence returns the task's evidence - one entry per evidence_submitted ledger entry, verbatim -
	// read BEFORE the task is deleted, because the delete cascade removes the ledger rows with it.
	Evidence(ctx context.Context, task SweepTask) ([]map[string]any, error)
}

// SweepWriter is the application layer as the sweep writes through it.
//
// EVERY METHOD IS A USE CASE CALL, not a SQL statement: the implementation drives the task facade,
// so an escalation and a block publish the task_updated frames and write the status_changed and
// progress entries a normal update writes, and a delete runs the same cascade every other delete
// runs. The status and priority moves themselves are the entity's own UpdateStatus/UpdatePriority,
// so the domain's transition rules still decide what is reachable.
type SweepWriter interface {
	// Escalate raises the task's priority to `to`, exactly the one level the caller already chose,
	// and writes the progress note that names the step.
	Escalate(ctx context.Context, task SweepTask, to value_objects.Priority, note string) error
	// Block moves the task to blocked and carries the blocker text as the note the record keeps.
	Block(ctx context.Context, task SweepTask, blocker string) error
	// Delete deletes the task through the application layer, cascade and event included.
	Delete(ctx context.Context, task SweepTask) error
}

// TaskAuditTrail is the append-only audit trail the sweep records into: one record per escalation,
// block and prune. The trail is NEVER pruned by the sweep.
type TaskAuditTrail interface {
	Record(ctx context.Context, record entities.TaskAuditRecord) error
}

// SweepLock is the exclusive gate a sweep run passes through, so two server instances never sweep
// twice.
//
// WITHLOCK RATHER THAN A LOCK VALUE, because the lock's lifetime must be the RUN's: the
// implementation holds it while fn executes and releases it when fn returns, and fn returning false
// is what tells the sweep it must skip the interval rather than queue a second sweep behind the
// first.
type SweepLock interface {
	WithLock(ctx context.Context, fn func() error) (ran bool, err error)
}

// taskSweepNow is the clock the sweep reads when nothing else is set (datetime.now(UTC), truncated
// as the rest of this codebase truncates timestamps).
var taskSweepNow = func() time.Time { return time.Now().UTC().Truncate(time.Microsecond) }

// TaskLifecycleSweeper is the periodic sweep: one pass per interval over the completed and open
// tasks, applying the three age rules.
type TaskLifecycleSweeper struct {
	source SweepTaskSource
	writer SweepWriter
	audit  TaskAuditTrail
	lock   SweepLock
	cfg    TaskSweepConfig

	now  func() time.Time
	logf func(string, ...any)
}

// NewTaskLifecycleSweeper builds the sweep over its four ports and the schedule it runs on.
func NewTaskLifecycleSweeper(source SweepTaskSource, writer SweepWriter, audit TaskAuditTrail,
	lock SweepLock, cfg TaskSweepConfig) *TaskLifecycleSweeper {
	return &TaskLifecycleSweeper{
		source: source,
		writer: writer,
		audit:  audit,
		lock:   lock,
		cfg:    cfg,
		now:    taskSweepNow,
		logf:   log.Printf,
	}
}

// WithClock sets the clock every age is measured against. It is the seam the tests drive: no test
// sleeps on wall time, and the clock is the only thing that decides what "6 days old" means.
func (s *TaskLifecycleSweeper) WithClock(now func() time.Time) *TaskLifecycleSweeper {
	s.now = now
	return s
}

// WithLogger sets where the sweep reports what it did.
func (s *TaskLifecycleSweeper) WithLogger(logf func(string, ...any)) *TaskLifecycleSweeper {
	s.logf = logf
	return s
}

// SweepReport is what one sweep did, for the caller's log line and for a test to read.
type SweepReport struct {
	// Locked is true when another instance held the sweep lock, so this run did nothing at all.
	Locked bool

	Pruned    int
	Escalated int
	Blocked   int
	// Refused counts the tasks the sweep could not block because the DOMAIN refuses the transition
	// (todo, review and testing may not reach blocked - value_objects.taskStatusTransitions). They
	// stay critical for the next interval rather than being forced into a state the domain forbids.
	Refused int
	// Failed counts the tasks the sweep could not act on: the work is logged and retried next
	// interval, and one task's failure never stops the others.
	Failed int
}

// Run sweeps once, then once per interval, until ctx is cancelled.
//
// THE FIRST SWEEP RUNS IMMEDIATELY rather than one interval after boot: the intervals are hours, a
// server restart is common, and a schedule that only started counting at boot would let a restart
// loop postpone enforcement indefinitely. It is still one sweep per interval after that.
func (s *TaskLifecycleSweeper) Run(ctx context.Context) {
	ticker := time.NewTicker(s.cfg.Interval)
	defer ticker.Stop()
	for {
		if report, err := s.SweepOnce(ctx); err != nil {
			if ctx.Err() != nil {
				return
			}
			s.logf("task lifecycle sweep failed: %v", err)
		} else if report.Locked {
			s.logf("task lifecycle sweep skipped: another instance holds the sweep lock")
		} else {
			s.logf("task lifecycle sweep: pruned %d, escalated %d, blocked %d, refused-to-block %d, failed %d",
				report.Pruned, report.Escalated, report.Blocked, report.Refused, report.Failed)
		}
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
	}
}

// SweepOnce runs one sweep behind the advisory lock. A run that could not take the lock reports
// Locked and touches nothing: the other instance is doing this interval's work.
func (s *TaskLifecycleSweeper) SweepOnce(ctx context.Context) (SweepReport, error) {
	var report SweepReport
	ran, err := s.lock.WithLock(ctx, func() error {
		var sweepErr error
		report, sweepErr = s.sweep(ctx)
		return sweepErr
	})
	if err != nil {
		return SweepReport{}, err
	}
	if !ran {
		return SweepReport{Locked: true}, nil
	}
	return report, nil
}

// sweep is one pass of the three rules, in the order the table states them.
func (s *TaskLifecycleSweeper) sweep(ctx context.Context) (SweepReport, error) {
	now := s.now()
	var report SweepReport

	completed, err := s.source.Completed(ctx)
	if err != nil {
		return report, fmt.Errorf("read the completed tasks: %w", err)
	}
	for _, task := range completed {
		if task.Age(now) <= s.cfg.PruneAfter {
			continue
		}
		if err := s.prune(ctx, task, now); err != nil {
			report.Failed++
			s.logf("task lifecycle sweep: %s (%s) was not pruned: %v", task.ID, task.Status, err)
			continue
		}
		report.Pruned++
	}

	open, err := s.source.Open(ctx)
	if err != nil {
		return report, fmt.Errorf("read the open tasks: %w", err)
	}
	for _, task := range open {
		age := task.Age(now)
		// The source does not hand over blocked tasks; the check is here because the rule that a
		// blocked task is never pruned or escalated is the sweep's, not the query's.
		if task.Status == string(value_objects.TaskStatusBlocked) {
			continue
		}
		if task.Priority == value_objects.PriorityCritical().Value {
			// Already at the top of the ladder: one more interval changes nothing, and the block age
			// is the whole of what is left to wait for.
			if age <= s.cfg.BlockAfter {
				continue
			}
			if err := s.block(ctx, task, age, now); err != nil {
				if err == errBlockRefused {
					report.Refused++
					s.logf("task lifecycle sweep: %s (%s, critical) is past the block age, but the domain refuses %s -> blocked; it stays critical", task.ID, task.Status, task.Status)
					continue
				}
				report.Failed++
				s.logf("task lifecycle sweep: %s (%s, critical) was not blocked: %v", task.ID, task.Status, err)
				continue
			}
			report.Blocked++
			continue
		}
		if age <= s.cfg.EscalateAfter {
			continue
		}
		if err := s.escalate(ctx, task, age, now); err != nil {
			report.Failed++
			s.logf("task lifecycle sweep: %s (%s, %s) was not escalated: %v", task.ID, task.Status, task.Priority, err)
			continue
		}
		report.Escalated++
	}
	return report, nil
}

// taskSweepRecord is the part of a record that describes the TASK itself, carried by every kind so
// that a reader of the trail finds the same shape whatever the sweep did - and so that the facts a
// prune would otherwise take with the row (the summary, the timestamps) are in every record.
//
// Status and Priority are set to the task's CURRENT values and the caller overrides the one the
// write moves, so each record states the state its own change left behind.
func taskSweepRecord(task SweepTask, kind entities.TaskAuditKind, now time.Time) entities.TaskAuditRecord {
	return entities.TaskAuditRecord{
		TaskID:            task.ID,
		UserID:            task.UserID,
		Kind:              kind,
		Title:             task.Title,
		Status:            task.Status,
		Priority:          task.Priority,
		CompletionSummary: task.CompletionSummary,
		CreatedAt:         now,
		TaskCreatedAt:     task.CreatedAt,
		TaskUpdatedAt:     task.UpdatedAt,
		TaskCompletedAt:   task.CompletedAt,
	}
}

// prune keeps the evidence and deletes the task.
//
// THE AUDIT RECORD COMES FIRST, and that ordering is the whole of "evidence is kept": the delete
// cascade removes the task's ledger rows - the only place its evidence lives - so a record written
// after the delete would have nothing left to hold. The delete itself goes through the application
// layer (SweepWriter.Delete -> the delete use case and its cascade), never a SQL DELETE here, so the
// subtasks, assignees, contexts and ledger rows the schema does not cascade are removed as they are
// for any other delete.
func (s *TaskLifecycleSweeper) prune(ctx context.Context, task SweepTask, now time.Time) error {
	evidence, err := s.source.Evidence(ctx, task)
	if err != nil {
		return fmt.Errorf("read the evidence: %w", err)
	}
	record := taskSweepRecord(task, entities.TaskAuditKindPruned, now)
	record.Evidence = evidence
	record.Detail = fmt.Sprintf("pruned after %s in %s", taskSweepAgeText(task.Age(now)), task.Status)
	if err := s.audit.Record(ctx, record); err != nil {
		return fmt.Errorf("write the audit record: %w", err)
	}
	if err := s.writer.Delete(ctx, task); err != nil {
		return fmt.Errorf("delete through the application layer: %w", err)
	}
	return nil
}

// escalate raises the priority exactly one level and writes the progress note that names the step.
//
// ONE LEVEL PER RUN, NEVER SEVERAL: the step is the next rung of value_objects.PriorityLevels, and
// the write advances the task's updated_at, so the next interval measures the age again from the
// escalation rather than climbing the rest of the ladder in one pass.
func (s *TaskLifecycleSweeper) escalate(ctx context.Context, task SweepTask, age time.Duration, now time.Time) error {
	next, ok := taskSweepNextPriority(task.Priority)
	if !ok {
		return nil
	}
	note := fmt.Sprintf("escalated to %s: no progress for %s (task lifecycle sweep)", next.Value, taskSweepAgeText(age))
	record := taskSweepRecord(task, entities.TaskAuditKindEscalated, now)
	record.Priority = next.Value
	record.Detail = note
	if err := s.audit.Record(ctx, record); err != nil {
		return fmt.Errorf("write the audit record: %w", err)
	}
	if err := s.writer.Escalate(ctx, task, next, note); err != nil {
		return fmt.Errorf("escalate through the application layer: %w", err)
	}
	return nil
}

// errBlockRefused is the sweep's own answer to a transition the DOMAIN refuses: todo, review and
// testing may not reach blocked (value_objects.taskStatusTransitions), so the sweep leaves the task
// where it is and says so, rather than forcing a state the domain's rules do not allow.
var errBlockRefused = fmt.Errorf("the domain refuses this transition to blocked")

// block hands a critical task to a human: the status becomes blocked and the blocker text - "no
// progress for N days at critical priority" - is written as the note and carried in the record, so
// the reason is readable after the task stops moving.
func (s *TaskLifecycleSweeper) block(ctx context.Context, task SweepTask, age time.Duration, now time.Time) error {
	current, err := value_objects.NewTaskStatus(task.Status)
	if err != nil {
		return err
	}
	if !current.CanTransitionTo(string(value_objects.TaskStatusBlocked)) {
		return errBlockRefused
	}
	blocker := fmt.Sprintf("no progress for %d days at critical priority", int(age/(24*time.Hour)))
	record := taskSweepRecord(task, entities.TaskAuditKindBlocked, now)
	record.Status = string(value_objects.TaskStatusBlocked)
	record.Detail = blocker
	if err := s.audit.Record(ctx, record); err != nil {
		return fmt.Errorf("write the audit record: %w", err)
	}
	if err := s.writer.Block(ctx, task, blocker); err != nil {
		return fmt.Errorf("block through the application layer: %w", err)
	}
	return nil
}

// taskSweepNextPriority is one rung up the priority ladder, and the second return is false when the
// task is already at the top. The rung order is read from value_objects.PriorityLevels rather than
// restated here, so a level added to the ladder is a level the climb reaches.
func taskSweepNextPriority(current string) (value_objects.Priority, bool) {
	for i, level := range value_objects.PriorityLevels {
		if level.Label != current {
			continue
		}
		if i+1 >= len(value_objects.PriorityLevels) {
			return value_objects.Priority{}, false
		}
		next, err := value_objects.NewPriority(value_objects.PriorityLevels[i+1].Label)
		if err != nil {
			return value_objects.Priority{}, false
		}
		return next, true
	}
	return value_objects.Priority{}, false
}

// taskSweepAgeText renders an age the way the sweep's own words state it: whole days when it is a
// day or more, whole hours below that.
func taskSweepAgeText(age time.Duration) string {
	if age >= 24*time.Hour {
		days := int(age / (24 * time.Hour))
		if days == 1 {
			return "1 day"
		}
		return strconv.Itoa(days) + " days"
	}
	hours := int(age / time.Hour)
	if hours == 1 {
		return "1 hour"
	}
	return strconv.Itoa(hours) + " hours"
}
