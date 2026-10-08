package repositories

// ORM Task Repository (Python infrastructure/repositories/orm/task_repository.py): the
// SQLAlchemy task repository ported over database/sql + pgx.
//
// The selective-field methods go through the small TaskRepoFieldSelector interface
// declared here (nil when none is configured). Logging and the cache/performance-cache
// side effects are dropped; the performance-mode query shape (selectinload) does not change
// results. Relationship eager-loading (joinedload/selectinload) is reproduced with explicit
// queries; the per-relationship try/except in _model_to_entity degrades every failed
// relationship load to empty, exactly like Python.

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/exceptions"
	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// TaskRepoFieldSelector is the subset of ContextFieldSelector used by ORMTaskRepository's
// selective-field methods; a concrete implementation supplies these methods.
type TaskRepoFieldSelector interface {
	// GetTaskFields is get_task_fields.
	GetTaskFields(taskID string, fields any) *entities.OrderedMap[any]
	// GetCachedFields is get_cached_fields (nil when nothing is cached).
	GetCachedFields(taskID string, fields []string) *entities.OrderedMap[any]
	// CacheFieldMapping is cache_field_mapping.
	CacheFieldMapping(taskID string, fields []string, data *entities.OrderedMap[any])
	// GetOptimalFieldSet is get_optimal_field_set; the result is the FieldSet value.
	GetOptimalFieldSet(operation, entityType string) any
	// GetMetrics is get_metrics.
	GetMetrics() map[string]int
	// EstimateSavings is estimate_savings.
	EstimateSavings(entityType string, fieldSet any) map[string]float64
}

// ORMTaskRepository is Python's ORMTaskRepository. It embeds the user-scoped ORM repository
// for session/user scoping and the event publishing mixin for domain events.
type ORMTaskRepository struct {
	*UserScopedORMRepository[database.Task]
	EventPublishingMixin

	GitBranchID     *string
	ProjectID       *string
	GitBranchName   *string
	PerformanceMode bool

	// FieldSelector is the optional ContextFieldSelector implementation (nil when none).
	FieldSelector TaskRepoFieldSelector

	taskRepoBranches *ORMRepository[database.ProjectGitBranch]
}

// Assert the domain interface is implemented.
var _ domainrepos.TaskRepository = (*ORMTaskRepository)(nil)

// NewORMTaskRepository builds the repository (Python __init__; session = sessions).
func NewORMTaskRepository(sessions *database.SessionManager, gitBranchID, projectID, gitBranchName, userID *string, performanceMode bool) (*ORMTaskRepository, error) {
	base, err := NewUserScopedORMRepository[database.Task]("tasks", sessions, userID)
	if err != nil {
		return nil, err
	}
	branches, err := NewORMRepository[database.ProjectGitBranch]("project_git_branchs", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMTaskRepository{
		UserScopedORMRepository: base,
		EventPublishingMixin:    NewEventPublishingMixin(),
		GitBranchID:             gitBranchID,
		ProjectID:               projectID,
		GitBranchName:           gitBranchName,
		PerformanceMode:         performanceMode,
		taskRepoBranches:        branches,
	}, nil
}

// WithUser returns a new instance scoped to userID (with_user).
func (r *ORMTaskRepository) WithUser(userID string) (*ORMTaskRepository, error) {
	return NewORMTaskRepository(r.Sessions, r.GitBranchID, r.ProjectID, r.GitBranchName, &userID, r.PerformanceMode)
}

// ---- small helpers -------------------------------------------------------------

var errTaskRepoStrHasNoTouch = errors.New("'str' object has no attribute 'touch'")

func taskRepoStrPtr(s string) *string { return &s }

func taskRepoDeref(p *string) string {
	if p == nil {
		return ""
	}
	return *p
}

func taskRepoInt64(v any) int64 {
	switch x := v.(type) {
	case int:
		return int64(x)
	case int8:
		return int64(x)
	case int16:
		return int64(x)
	case int32:
		return int64(x)
	case int64:
		return x
	case uint:
		return int64(x)
	case uint8:
		return int64(x)
	case uint16:
		return int64(x)
	case uint32:
		return int64(x)
	case uint64:
		return int64(x)
	case float32:
		return int64(x)
	case float64:
		return int64(x)
	case bool:
		if x {
			return 1
		}
		return 0
	}
	return 0
}

// taskRepoEnsureEstimatedEffort is _ensure_estimated_effort_default.
func taskRepoEnsureEstimatedEffort(value any) string {
	switch v := value.(type) {
	case nil:
		return "2 hours"
	case string:
		if value_objects.PyStrip(v) == "" {
			return "2 hours"
		}
		return value_objects.PyStrip(v)
	case *string:
		if v == nil {
			return "2 hours"
		}
		if value_objects.PyStrip(*v) == "" {
			return "2 hours"
		}
		return value_objects.PyStrip(*v)
	}
	s := value_objects.PyStrip(value_objects.PyStr(value))
	if s == "" {
		return "2 hours"
	}
	return s
}

// taskRepoDecodeHistory decodes a JSON progress_history column to map[string]any.
func taskRepoDecodeHistory(raw []byte) map[string]any {
	if len(raw) == 0 {
		return map[string]any{}
	}
	decoded, err := entities.DecodeJSON(raw)
	if err != nil {
		return map[string]any{}
	}
	ordered, ok := decoded.(*entities.OrderedMap[any])
	if !ok || ordered.Len() == 0 {
		return map[string]any{}
	}
	out := map[string]any{}
	for _, key := range ordered.Keys() {
		value, _ := ordered.Get(key)
		out[key] = value
	}
	return out
}

// taskRepoUserCondition appends the apply_user_filter condition for the current scope.
func (r *ORMTaskRepository) taskRepoUserCondition(args *[]any, conds *[]string) {
	r.taskRepoUserConditionOn(`"user_id"`, args, conds)
}

// taskRepoUserConditionOn is taskRepoUserCondition for a qualified column (joined queries).
func (r *ORMTaskRepository) taskRepoUserConditionOn(column string, args *[]any, conds *[]string) {
	if !r.IsSystemMode() && r.UserID != nil {
		*args = append(*args, *r.UserID)
		*conds = append(*conds, fmt.Sprintf(`%s = $%d`, column, len(*args)))
	}
}

// ---- relationship loading (per-relationship failures degrade to empty) ---------

func (r *ORMTaskRepository) taskRepoAssigneeIDs(ctx context.Context, s database.DBTX, taskID string) []string {
	out := []string{}
	rows, err := s.QueryContext(ctx, `SELECT assignee_id FROM task_assignees WHERE task_id = $1::uuid`, taskID)
	if err != nil {
		return out
	}
	defer rows.Close()
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return out
		}
		out = append(out, id)
	}
	return out
}

func (r *ORMTaskRepository) taskRepoLabelNames(ctx context.Context, s database.DBTX, taskID string) []string {
	out := []string{}
	rows, err := s.QueryContext(ctx,
		`SELECT l.name FROM task_labels tl JOIN labels l ON tl.label_id = l.id WHERE tl.task_id = $1::uuid`, taskID)
	if err != nil {
		return out
	}
	defer rows.Close()
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			return out
		}
		out = append(out, name)
	}
	return out
}

func (r *ORMTaskRepository) taskRepoSubtaskIDs(ctx context.Context, s database.DBTX, taskID string) []string {
	out := []string{}
	rows, err := s.QueryContext(ctx, `SELECT id::text FROM subtasks WHERE task_id = $1::uuid`, taskID)
	if err != nil {
		return out
	}
	defer rows.Close()
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return out
		}
		out = append(out, id)
	}
	return out
}

func (r *ORMTaskRepository) taskRepoDependencyIDs(ctx context.Context, s database.DBTX, taskID string) []string {
	out := []string{}
	rows, err := s.QueryContext(ctx, `SELECT depends_on_task_id::text FROM task_dependencies WHERE task_id = $1::uuid`, taskID)
	if err != nil {
		return out
	}
	defer rows.Close()
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return out
		}
		out = append(out, id)
	}
	return out
}

// ---- domain <-> row conversion -------------------------------------------------

// taskRepoModelToEntity is _model_to_entity. Relationship loads are eager queries; a load
// failure degrades to the empty relationship like the try/except blocks in Python.
func (r *ORMTaskRepository) taskRepoModelToEntity(ctx context.Context, s database.DBTX, row *database.Task) (*entities.Task, error) {
	assigneeIDs := r.taskRepoAssigneeIDs(ctx, s, row.ID)
	labelNames := r.taskRepoLabelNames(ctx, s, row.ID)
	subtaskIDs := r.taskRepoSubtaskIDs(ctx, s, row.ID)
	dependencyIDs := r.taskRepoDependencyIDs(ctx, s, row.ID)

	var id *value_objects.TaskId
	if row.ID != "" {
		v, err := value_objects.NewTaskId(row.ID)
		if err != nil {
			return nil, err
		}
		id = &v
	}
	var status *value_objects.TaskStatus
	if row.Status != "" {
		v, err := value_objects.NewTaskStatus(row.Status)
		if err != nil {
			return nil, err
		}
		status = &v
	}
	var priority *value_objects.Priority
	if row.Priority != "" {
		v, err := value_objects.PriorityFromString(row.Priority)
		if err != nil {
			return nil, err
		}
		priority = &v
	}
	dependencies := []value_objects.TaskId{}
	for _, d := range dependencyIDs {
		v, err := value_objects.NewTaskId(d)
		if err != nil {
			return nil, err
		}
		dependencies = append(dependencies, v)
	}
	completed := int64(0)
	if row.CompletedSubtasks != nil {
		completed = *row.CompletedSubtasks
	}
	createdAt, updatedAt := row.CreatedAt, row.UpdatedAt
	userID := row.UserID
	entity, err := entities.NewTask(entities.Task{
		BaseTimestampEntity: base.BaseTimestampEntity{CreatedAt: &createdAt, UpdatedAt: &updatedAt},
		Title:               row.Title,
		Description:         row.Description,
		ID:                  id,
		GitBranchID:         &row.GitBranchID,
		Status:              status,
		Priority:            priority,
		ProgressHistory:     taskRepoDecodeHistory(row.ProgressHistory),
		ProgressCount:       int(row.ProgressCount),
		EstimatedEffort:     row.EstimatedEffort,
		DueDate:             row.DueDate,
		Assignees:           assigneeIDs,
		Labels:              labelNames,
		Subtasks:            subtaskIDs,
		CompletedSubtasks:   int(completed),
		Dependencies:        dependencies,
		ContextID:           row.ContextID,
		UserID:              &userID,
	})
	if err != nil {
		return nil, err
	}
	// _model_to_entity maps progress_percentage into overall_progress when present.
	entity.OverallProgress = float64(row.ProgressPercentage)
	entity.OverallProgressIsFloat = false
	if row.CompletionSummary != "" {
		cs := row.CompletionSummary
		entity.CompletionSummary = &cs
	}
	return entity, nil
}

// taskRepoOverallProgressValue returns overall_progress as int or float like Python.
func taskRepoOverallProgressValue(task *entities.Task) any {
	if task.OverallProgressIsFloat {
		return task.OverallProgress
	}
	return int64(task.OverallProgress)
}

// taskRepoEntityToModelDict is _entity_to_model_dict.
func (r *ORMTaskRepository) taskRepoEntityToModelDict(task *entities.Task) Kwargs {
	m := NewKwargs()
	if task.ID != nil {
		m.Set("id", task.ID.Value)
	}
	m.Set("title", task.Title)
	m.Set("description", task.Description)
	m.Set("git_branch_id", task.GitBranchID)
	if task.Status != nil {
		m.Set("status", task.Status.Value)
	}
	if task.Priority != nil {
		m.Set("priority", task.Priority.Value)
	}
	m.Set("progress_history", task.ProgressHistory)
	m.Set("progress_count", task.ProgressCount)
	m.Set("estimated_effort", taskRepoEnsureEstimatedEffort(task.EstimatedEffort))
	m.Set("due_date", task.DueDate)
	m.Set("context_id", task.ContextID)
	m.Set("completed_subtasks", task.CompletedSubtasks)
	// hasattr(task, "overall_progress") is always true for the entity.
	m.Set("progress_percentage", taskRepoOverallProgressValue(task))
	if task.CompletionSummary != nil {
		m.Set("completion_summary", *task.CompletionSummary)
	}
	return m
}

// taskRepoFindLabelID is the Label lookup by name (global, as in Python).
func (r *ORMTaskRepository) taskRepoFindLabelID(ctx context.Context, s database.DBTX, name string) (string, error) {
	var id string
	err := s.QueryRowContext(ctx, `SELECT id FROM labels WHERE name = $1 LIMIT 1`, name).Scan(&id)
	if errors.Is(err, sql.ErrNoRows) {
		return "", nil
	}
	if err != nil {
		return "", err
	}
	return id, nil
}

// taskRepoCreateLabel creates a Label with the Python defaults.
func (r *ORMTaskRepository) taskRepoCreateLabel(ctx context.Context, s database.DBTX, name string, userID *string) (string, error) {
	id := value_objects.NewUUIDv4()
	now := database.TimestampNow()
	if _, err := s.ExecContext(ctx,
		`INSERT INTO labels (id, name, color, description, user_id, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, $7)`,
		id, name, "#0066cc", "", taskRepoDeref(userID), now, now); err != nil {
		return "", err
	}
	return id, nil
}

// taskRepoExistingAssigneeIDs is the existing assignee set used for the idempotent diff.
func (r *ORMTaskRepository) taskRepoExistingAssigneeIDs(ctx context.Context, s database.DBTX, taskID string) ([]string, error) {
	out := []string{}
	rows, err := s.QueryContext(ctx, `SELECT assignee_id FROM task_assignees WHERE task_id = $1::uuid`, taskID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return nil, err
		}
		out = append(out, id)
	}
	return out, rows.Err()
}

// ---- create_task ---------------------------------------------------------------

// CreateTask is create_task. kwargs carry id, status, progress_history, progress_count,
// estimated_effort, due_date, context_id and assignee_role.
func (r *ORMTaskRepository) CreateTask(ctx context.Context, title, description, priority string, assigneeIDs, labelNames []string, kwargs Kwargs) (*entities.Task, error) {
	var out *entities.Task
	err := r.Transaction(ctx, func(ctx context.Context) error {
		return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
			taskID := ""
			if kwargs != nil {
				if v, ok := kwargs.Get("id"); ok && v != nil {
					taskID = value_objects.PyStr(v)
				}
			}
			if taskID == "" {
				taskID = value_objects.NewUUIDv4()
			}
			status := "todo"
			if kwargs != nil {
				if v, ok := kwargs.Get("status"); ok && v != nil {
					status = value_objects.PyStr(v)
				}
			}
			progressHistory := any(map[string]any{})
			if kwargs != nil {
				if v, ok := kwargs.Get("progress_history"); ok && v != nil {
					progressHistory = v
				}
			}
			progressCount := int64(0)
			if kwargs != nil {
				if v, ok := kwargs.Get("progress_count"); ok && v != nil {
					progressCount = taskRepoInt64(v)
				}
			}
			var estimatedRaw any
			if kwargs != nil {
				estimatedRaw, _ = kwargs.Get("estimated_effort")
			}
			var dueDate any
			if kwargs != nil {
				dueDate, _ = kwargs.Get("due_date")
			}
			var contextID any
			if kwargs != nil {
				contextID, _ = kwargs.Get("context_id")
			}
			taskData := NewKwargs(
				"id", taskID,
				"title", title,
				"description", description,
				"git_branch_id", r.GitBranchID,
				"priority", priority,
				"status", status,
				"progress_history", progressHistory,
				"progress_count", progressCount,
				"estimated_effort", taskRepoEnsureEstimatedEffort(estimatedRaw),
				"due_date", dueDate,
				"context_id", contextID,
			)
			taskData, err := r.SetUserID(taskData)
			if err != nil {
				return err
			}
			if _, err := r.ORMRepository.Create(ctx, taskData); err != nil {
				return err
			}
			// Branch counters (ProjectGitBranch).
			if r.GitBranchID != nil && *r.GitBranchID != "" {
				var taskCount, completedCount int64
				err := s.QueryRowContext(ctx,
					`SELECT task_count, completed_task_count FROM project_git_branchs WHERE id = $1::uuid LIMIT 1`,
					*r.GitBranchID).Scan(&taskCount, &completedCount)
				if err == nil {
					taskCount++
					if status == "done" {
						completedCount++
					}
					if _, err := s.ExecContext(ctx,
						`UPDATE project_git_branchs SET task_count = $1, completed_task_count = $2, updated_at = $3 WHERE id = $4::uuid`,
						taskCount, completedCount, database.TimestampNow(), *r.GitBranchID); err != nil {
						return err
					}
				} else if !errors.Is(err, sql.ErrNoRows) {
					return err
				}
			}
			// Assignees and labels are optional steps with their own try/except + rollback in
			// Python: a failure undoes that whole step but keeps the task. A savepoint keeps the
			// surrounding PG transaction usable after the swallowed error.
			if len(assigneeIDs) > 0 {
				role := "contributor"
				if kwargs != nil {
					if v, ok := kwargs.Get("assignee_role"); ok && v != nil {
						role = value_objects.PyStr(v)
					}
				}
				taskRepoOptionalStep(ctx, s, "task_assignees_step", func() error {
					for _, assigneeID := range assigneeIDs {
						if _, err := s.ExecContext(ctx,
							`INSERT INTO task_assignees (id, task_id, assignee_id, role, user_id, assigned_at) VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6)`,
							value_objects.NewUUIDv4(), taskID, assigneeID, role, taskRepoDeref(r.UserID), database.TimestampNow()); err != nil {
							return err
						}
					}
					return nil
				})
			}
			if len(labelNames) > 0 {
				taskRepoOptionalStep(ctx, s, "task_labels_step", func() error {
					for _, name := range labelNames {
						labelID, err := r.taskRepoFindLabelID(ctx, s, name)
						if err != nil {
							return err
						}
						if labelID == "" {
							labelID, err = r.taskRepoCreateLabel(ctx, s, name, r.UserID)
							if err != nil {
								return err
							}
						}
						if _, err := s.ExecContext(ctx,
							`INSERT INTO task_labels (task_id, label_id, user_id, applied_at) VALUES ($1::uuid, $2, $3, $4)`,
							taskID, labelID, taskRepoDeref(r.UserID), database.TimestampNow()); err != nil {
							return err
						}
					}
					return nil
				})
			}
			// Reload with relationships.
			row, err := r.ORMRepository.getByID(ctx, s, taskID)
			if err != nil {
				return err
			}
			if row == nil {
				return nil
			}
			out, err = r.taskRepoModelToEntity(ctx, s, row)
			return err
		})
	})
	if err != nil {
		return nil, exceptions.NewTaskCreationError("Failed to create task: " + err.Error())
	}
	return out, nil
}

// ---- get_task ------------------------------------------------------------------

// GetTask is get_task (user isolation and git branch filter in non-system mode).
func (r *ORMTaskRepository) GetTask(ctx context.Context, taskID string) (*entities.Task, error) {
	var out *entities.Task
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		// Python wraps the load in try/except and returns None on any failure.
		taskRepoOptionalStep(ctx, s, "get_task", func() error {
			args := []any{taskID}
			suffix := ` WHERE "id" = $1::uuid`
			if !r.IsSystemMode() && r.UserID != nil {
				args = append(args, *r.UserID)
				suffix += fmt.Sprintf(` AND "user_id" = $%d`, len(args))
			}
			if !r.IsSystemMode() && r.GitBranchID != nil && *r.GitBranchID != "" {
				args = append(args, *r.GitBranchID)
				suffix += fmt.Sprintf(` AND "git_branch_id" = $%d::uuid`, len(args))
			}
			suffix += " LIMIT 1"
			rows, err := r.selectRows(ctx, s, suffix, args...)
			if err != nil {
				return err
			}
			if len(rows) == 0 {
				return nil
			}
			entity, err := r.taskRepoModelToEntity(ctx, s, rows[0])
			if err != nil {
				return err
			}
			out = entity
			return nil
		})
		return nil
	})
	return out, err
}

// ---- update_task ---------------------------------------------------------------

// UpdateTask is update_task. Python calls self.update(task_id, **basic_updates); the class
// MRO resolves that to BaseTimestampRepository.update(entity, **kwargs), which calls
// entity.touch(...) on the ID string and raises AttributeError. Every failure (including
// not-found) is wrapped in TaskUpdateError, so update_task always raises. Defect preserved.
func (r *ORMTaskRepository) UpdateTask(ctx context.Context, taskID string, updates Kwargs) (*entities.Task, error) {
	err := r.Transaction(ctx, func(ctx context.Context) error {
		row, e := r.ORMRepository.GetByID(ctx, taskID)
		if e != nil {
			return e
		}
		if row == nil {
			return exceptions.NewTaskNotFoundError("Task " + taskID + " not found")
		}
		return errTaskRepoStrHasNoTouch
	})
	if err != nil {
		return nil, exceptions.NewTaskUpdateError("Failed to update task: " + err.Error())
	}
	return nil, nil
}

// ---- delete_task ---------------------------------------------------------------

// DeleteTask is delete_task: manual cascade deletes of the related rows, branch counter
// decrement and the task row, all in one session. Any failure returns false like Python.
func (r *ORMTaskRepository) DeleteTask(ctx context.Context, taskID string) (bool, error) {
	deleted := false
	err := r.Transaction(ctx, func(ctx context.Context) error {
		return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
			row, err := r.ORMRepository.getByID(ctx, s, taskID)
			if err != nil {
				return err
			}
			if row == nil {
				return nil
			}
			if !r.IsSystemMode() && r.UserID != nil && row.UserID != *r.UserID {
				return nil
			}
			if _, err := s.ExecContext(ctx, `DELETE FROM task_contexts WHERE task_id = $1::uuid`, taskID); err != nil {
				return err
			}
			if _, err := s.ExecContext(ctx, `DELETE FROM subtasks WHERE task_id = $1::uuid`, taskID); err != nil {
				return err
			}
			if _, err := s.ExecContext(ctx, `DELETE FROM task_assignees WHERE task_id = $1::uuid`, taskID); err != nil {
				return err
			}
			if _, err := s.ExecContext(ctx, `DELETE FROM task_dependencies WHERE task_id = $1::uuid OR depends_on_task_id = $1::uuid`, taskID); err != nil {
				return err
			}
			if _, err := s.ExecContext(ctx, `DELETE FROM task_labels WHERE task_id = $1::uuid`, taskID); err != nil {
				return err
			}
			if row.GitBranchID != "" {
				var taskCount, completedCount int64
				var status string
				err := s.QueryRowContext(ctx,
					`SELECT task_count, completed_task_count, status FROM project_git_branchs WHERE id = $1::uuid LIMIT 1`,
					row.GitBranchID).Scan(&taskCount, &completedCount, &status)
				if err == nil {
					taskCount = max(0, taskCount-1)
					if row.Status == "done" {
						completedCount = max(0, completedCount-1)
					}
					if _, err := s.ExecContext(ctx,
						`UPDATE project_git_branchs SET task_count = $1, completed_task_count = $2, updated_at = $3 WHERE id = $4::uuid`,
						taskCount, completedCount, database.TimestampNow(), row.GitBranchID); err != nil {
						return err
					}
				} else if !errors.Is(err, sql.ErrNoRows) {
					return err
				}
			}
			res, err := s.ExecContext(ctx, `DELETE FROM tasks WHERE id = $1::uuid`, taskID)
			if err != nil {
				return err
			}
			n, _ := res.RowsAffected()
			deleted = n > 0
			return nil
		})
	})
	if err != nil {
		return false, nil
	}
	return deleted, nil
}

// ---- list_tasks / list_tasks_optimized -----------------------------------------

// ListTasks is list_tasks (offset/limit are always applied, as in Python).
func (r *ORMTaskRepository) ListTasks(ctx context.Context, status, priority, assigneeID *string, limit, offset int) ([]*entities.Task, error) {
	out := []*entities.Task{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{}
		conds := []string{}
		r.taskRepoUserCondition(&args, &conds)
		if r.GitBranchID != nil && *r.GitBranchID != "" {
			args = append(args, *r.GitBranchID)
			conds = append(conds, fmt.Sprintf(`"git_branch_id" = $%d::uuid`, len(args)))
		}
		if status != nil && *status != "" {
			args = append(args, *status)
			conds = append(conds, fmt.Sprintf(`"status" = $%d`, len(args)))
		}
		if priority != nil && *priority != "" {
			args = append(args, *priority)
			conds = append(conds, fmt.Sprintf(`"priority" = $%d`, len(args)))
		}
		if assigneeID != nil && *assigneeID != "" {
			args = append(args, *assigneeID)
			conds = append(conds, fmt.Sprintf(`EXISTS (SELECT 1 FROM task_assignees ta WHERE ta.task_id = tasks.id AND ta.assignee_id = $%d)`, len(args)))
		}
		suffix := ""
		if len(conds) > 0 {
			suffix = " WHERE " + strings.Join(conds, " AND ")
		}
		suffix += ` ORDER BY "created_at" DESC`
		suffix += fmt.Sprintf(" LIMIT %d OFFSET %d", limit, offset)
		rows, err := r.selectRows(ctx, s, suffix, args...)
		if err != nil {
			return err
		}
		for _, row := range rows {
			e, err := r.taskRepoModelToEntity(ctx, s, row)
			if err != nil {
				return err
			}
			out = append(out, e)
		}
		return nil
	})
	return out, err
}

// ListTasksOptimized is list_tasks_optimized (the dead raw SQL is dropped; the ORM query
// is identical to list_tasks apart from the limit default).
func (r *ORMTaskRepository) ListTasksOptimized(ctx context.Context, status, priority, assigneeID *string, limit, offset int) ([]*entities.Task, error) {
	return r.ListTasks(ctx, status, priority, assigneeID, limit, offset)
}

// ---- get_task_count ------------------------------------------------------------

// GetTaskCount is get_task_count.
func (r *ORMTaskRepository) GetTaskCount(ctx context.Context, status *string) (int, error) {
	count := 0
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{}
		conds := []string{}
		r.taskRepoUserCondition(&args, &conds)
		if r.GitBranchID != nil && *r.GitBranchID != "" {
			args = append(args, *r.GitBranchID)
			conds = append(conds, fmt.Sprintf(`"git_branch_id" = $%d::uuid`, len(args)))
		}
		if status != nil && *status != "" {
			args = append(args, *status)
			conds = append(conds, fmt.Sprintf(`"status" = $%d`, len(args)))
		}
		q := `SELECT count(*) FROM tasks`
		if len(conds) > 0 {
			q += " WHERE " + strings.Join(conds, " AND ")
		}
		return s.QueryRowContext(ctx, q, args...).Scan(&count)
	})
	return count, err
}

// GetTaskCountOptimized is get_task_count_optimized (direct SQL, self.user_id only).
func (r *ORMTaskRepository) GetTaskCountOptimized(ctx context.Context, status, priority *string) (int, error) {
	count := 0
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{}
		conds := []string{"1=1"}
		if r.UserID != nil {
			args = append(args, *r.UserID)
			conds = append(conds, fmt.Sprintf(`user_id = $%d`, len(args)))
		}
		if r.GitBranchID != nil && *r.GitBranchID != "" {
			args = append(args, *r.GitBranchID)
			conds = append(conds, fmt.Sprintf(`git_branch_id = $%d::uuid`, len(args)))
		}
		if status != nil && *status != "" {
			args = append(args, *status)
			conds = append(conds, fmt.Sprintf(`status = $%d`, len(args)))
		}
		if priority != nil && *priority != "" {
			args = append(args, *priority)
			conds = append(conds, fmt.Sprintf(`priority = $%d`, len(args)))
		}
		q := "SELECT COUNT(*) FROM tasks WHERE " + strings.Join(conds, " AND ")
		return s.QueryRowContext(ctx, q, args...).Scan(&count)
	})
	return count, err
}

// ---- list_tasks_minimal --------------------------------------------------------

// ListTasksMinimal is list_tasks_minimal. limit nil / <= 0 becomes 20 and is capped at 1000;
// offset nil / < 0 becomes 0. The result dicts keep Python insertion order. On any query
// failure the method degrades to an empty list, as in Python.
func (r *ORMTaskRepository) ListTasksMinimal(ctx context.Context, status, priority, assigneeID, gitBranchID *string, limit, offset *int) ([]*entities.OrderedMap[any], error) {
	lim, off := 20, 0
	if limit != nil && *limit > 0 {
		lim = *limit
	}
	if lim > 1000 {
		lim = 1000
	}
	if offset != nil {
		off = *offset
	}
	if off < 0 {
		off = 0
	}

	effectiveBranch := r.GitBranchID
	if gitBranchID != nil {
		effectiveBranch = gitBranchID
	}

	out := []*entities.OrderedMap[any]{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{}
		conds := []string{}
		r.taskRepoUserConditionOn(`t."user_id"`, &args, &conds)
		if effectiveBranch != nil && *effectiveBranch != "" {
			args = append(args, *effectiveBranch)
			conds = append(conds, fmt.Sprintf(`t."git_branch_id" = $%d::uuid`, len(args)))
		}
		if status != nil && *status != "" {
			args = append(args, *status)
			conds = append(conds, fmt.Sprintf(`t."status" = $%d`, len(args)))
		}
		if priority != nil && *priority != "" {
			args = append(args, *priority)
			conds = append(conds, fmt.Sprintf(`t."priority" = $%d`, len(args)))
		}
		if assigneeID != nil && *assigneeID != "" {
			args = append(args, *assigneeID)
			conds = append(conds, fmt.Sprintf(`ta."assignee_id" = $%d`, len(args)))
		}
		where := ""
		if len(conds) > 0 {
			where = " WHERE " + strings.Join(conds, " AND ")
		}
		q := `SELECT t.id::text, t.title, t.status, t.priority, t.progress_percentage, t.due_date, t.updated_at, t.git_branch_id::text,` +
			` COUNT(ta.id), COALESCE(sc.subtask_count, 0), t.completed_subtasks` +
			` FROM tasks t` +
			` LEFT JOIN task_assignees ta ON t.id = ta.task_id` +
			` LEFT JOIN (SELECT task_id, COUNT(*) AS subtask_count FROM subtasks GROUP BY task_id) sc ON t.id = sc.task_id` +
			where +
			` GROUP BY t.id, t.title, t.status, t.priority, t.progress_percentage, t.due_date, t.updated_at, t.git_branch_id, sc.subtask_count, t.completed_subtasks` +
			` ORDER BY t.updated_at DESC` +
			fmt.Sprintf(" LIMIT %d OFFSET %d", lim, off)

		type minimalRow struct {
			id                string
			title             string
			status            string
			priority          string
			progressPct       int64
			dueDate           *string
			updatedAt         time.Time
			gitBranchID       string
			assigneesCount    int64
			subtaskCount      int64
			completedSubtasks *int64
		}
		rows, err := s.QueryContext(ctx, q, args...)
		if err != nil {
			return err
		}
		results := []minimalRow{}
		for rows.Next() {
			var m minimalRow
			if err := rows.Scan(&m.id, &m.title, &m.status, &m.priority, &m.progressPct, &m.dueDate, &m.updatedAt,
				&m.gitBranchID, &m.assigneesCount, &m.subtaskCount, &m.completedSubtasks); err != nil {
				rows.Close()
				return err
			}
			results = append(results, m)
		}
		if err := rows.Err(); err != nil {
			rows.Close()
			return err
		}
		rows.Close()

		taskIDs := make([]string, len(results))
		for i, m := range results {
			taskIDs[i] = m.id
		}
		labelsByTask := map[string][]string{}
		assigneesByTask := map[string][]string{}
		dependenciesByTask := map[string][]string{}
		if len(taskIDs) > 0 {
			// each follow-up query numbers its own placeholders from $1
			var labelArgs []any
			in := taskRepoInClause("tl.task_id", taskIDs, &labelArgs, "::uuid")
			labelRows, err := s.QueryContext(ctx,
				`SELECT tl.task_id::text, l.name FROM task_labels tl JOIN labels l ON tl.label_id = l.id WHERE `+in, labelArgs...)
			if err != nil {
				return err
			}
			for labelRows.Next() {
				var taskID, name string
				if err := labelRows.Scan(&taskID, &name); err != nil {
					labelRows.Close()
					return err
				}
				labelsByTask[taskID] = append(labelsByTask[taskID], name)
			}
			labelRows.Close()
			if err := labelRows.Err(); err != nil {
				return err
			}

			if r.PerformanceMode {
				var assigneeArgs []any
				in2 := taskRepoInClause("task_id", taskIDs, &assigneeArgs, "::uuid")
				assigneeRows, err := s.QueryContext(ctx,
					`SELECT task_id::text, assignee_id FROM task_assignees WHERE `+in2, assigneeArgs...)
				if err != nil {
					return err
				}
				for assigneeRows.Next() {
					var taskID, assigneeID string
					if err := assigneeRows.Scan(&taskID, &assigneeID); err != nil {
						assigneeRows.Close()
						return err
					}
					assigneesByTask[taskID] = append(assigneesByTask[taskID], assigneeID)
				}
				assigneeRows.Close()
				if err := assigneeRows.Err(); err != nil {
					return err
				}
			}

			var depArgs []any
			in3 := taskRepoInClause("task_id", taskIDs, &depArgs, "::uuid")
			depRows, err := s.QueryContext(ctx,
				`SELECT task_id::text, depends_on_task_id::text FROM task_dependencies WHERE `+in3, depArgs...)
			if err != nil {
				return err
			}
			for depRows.Next() {
				var taskID, dependsOn string
				if err := depRows.Scan(&taskID, &dependsOn); err != nil {
					depRows.Close()
					return err
				}
				dependenciesByTask[taskID] = append(dependenciesByTask[taskID], dependsOn)
			}
			depRows.Close()
			if err := depRows.Err(); err != nil {
				return err
			}
		}

		for _, m := range results {
			dependencies := dependenciesByTask[m.id]
			if dependencies == nil {
				dependencies = []string{}
			}
			labels := labelsByTask[m.id]
			if labels == nil {
				labels = []string{}
			}
			completed := int64(0)
			if m.completedSubtasks != nil {
				completed = *m.completedSubtasks
			}
			var updatedAt any
			if !m.updatedAt.IsZero() {
				updatedAt = value_objects.IsoFormatNaive(m.updatedAt)
			}
			taskData := entities.NewOrderedMap[any]()
			taskData.Set("id", m.id)
			taskData.Set("title", m.title)
			taskData.Set("status", m.status)
			taskData.Set("priority", m.priority)
			taskData.Set("progress_percentage", m.progressPct)
			taskData.Set("assignees_count", m.assigneesCount)
			taskData.Set("subtask_count", m.subtaskCount)
			taskData.Set("completed_subtasks", completed)
			taskData.Set("labels", labels)
			if m.dueDate != nil {
				taskData.Set("due_date", *m.dueDate)
			} else {
				taskData.Set("due_date", nil)
			}
			taskData.Set("updated_at", updatedAt)
			taskData.Set("git_branch_id", m.gitBranchID)
			taskData.Set("dependencies", dependencies)
			taskData.Set("has_dependencies", len(dependencies) > 0)
			taskData.Set("dependency_count", len(dependencies))
			if r.PerformanceMode {
				assignees := assigneesByTask[m.id]
				if assignees == nil {
					assignees = []string{}
				}
				taskData.Set("assignees", assignees)
			}
			out = append(out, taskData)
		}
		return nil
	})
	if err != nil {
		return []*entities.OrderedMap[any]{}, nil
	}
	return out, nil
}

// taskRepoInClause builds "column IN ($n, ...)" appending args; cast appends e.g. "::uuid".
func taskRepoInClause(column string, ids []string, args *[]any, cast string) string {
	holders := make([]string, len(ids))
	for i, id := range ids {
		*args = append(*args, id)
		h := fmt.Sprintf("$%d", len(*args))
		if cast != "" {
			h += cast
		}
		holders[i] = h
	}
	return column + " IN (" + strings.Join(holders, ", ") + ")"
}

// ---- search_tasks --------------------------------------------------------------

// SearchTasks is search_tasks: ANY word matches ANY of title/description/label name.
func (r *ORMTaskRepository) SearchTasks(ctx context.Context, query string, filters map[string]any, limit int) ([]*entities.Task, error) {
	out := []*entities.Task{}
	searchWords := []string{}
	for _, w := range value_objects.PySplit(query) {
		if value_objects.PyStrip(w) != "" {
			searchWords = append(searchWords, w)
		}
	}
	if len(searchWords) == 0 {
		return out, nil
	}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{}
		conds := []string{}
		r.taskRepoUserCondition(&args, &conds)
		if r.GitBranchID != nil && *r.GitBranchID != "" {
			args = append(args, *r.GitBranchID)
			conds = append(conds, fmt.Sprintf(`"git_branch_id" = $%d::uuid`, len(args)))
		}
		if v, ok := filters["status"]; ok {
			sv := taskRepoEnumValue(v)
			if sv == nil {
				conds = append(conds, `"status" IS NULL`)
			} else {
				args = append(args, value_objects.PyStr(sv))
				conds = append(conds, fmt.Sprintf(`"status" = $%d`, len(args)))
			}
		}
		if v, ok := filters["priority"]; ok {
			pv := taskRepoEnumValue(v)
			if pv == nil {
				conds = append(conds, `"priority" IS NULL`)
			} else {
				args = append(args, value_objects.PyStr(pv))
				conds = append(conds, fmt.Sprintf(`"priority" = $%d`, len(args)))
			}
		}
		if v, ok := filters["assignees"]; ok && value_objects.PyTruthy(v) {
			assignees := taskRepoStringList(v)
			if len(assignees) > 0 {
				in := taskRepoInClause("ta.assignee_id", assignees, &args, "")
				conds = append(conds, `EXISTS (SELECT 1 FROM task_assignees ta WHERE ta.task_id = tasks.id AND `+in+`)`)
			}
		}
		if v, ok := filters["labels"]; ok && value_objects.PyTruthy(v) {
			labels := taskRepoStringList(v)
			if len(labels) > 0 {
				in := taskRepoInClause("l.name", labels, &args, "")
				conds = append(conds, `EXISTS (SELECT 1 FROM task_labels tl JOIN labels l ON tl.label_id = l.id WHERE tl.task_id = tasks.id AND `+in+`)`)
			}
		}
		wordConds := []string{}
		for _, word := range searchWords {
			pattern := "%" + word + "%"
			args = append(args, pattern)
			p1 := len(args)
			args = append(args, pattern)
			p2 := len(args)
			args = append(args, pattern)
			p3 := len(args)
			wordConds = append(wordConds, fmt.Sprintf(
				`("title" ILIKE $%d OR "description" ILIKE $%d OR EXISTS (SELECT 1 FROM task_labels tl JOIN labels l ON tl.label_id = l.id WHERE tl.task_id = tasks.id AND l.name ILIKE $%d))`,
				p1, p2, p3))
		}
		conds = append(conds, "("+strings.Join(wordConds, " OR ")+")")
		suffix := " WHERE " + strings.Join(conds, " AND ")
		suffix += ` ORDER BY "created_at" DESC`
		suffix += fmt.Sprintf(" LIMIT %d", limit)
		rows, err := r.selectRows(ctx, s, suffix, args...)
		if err != nil {
			return err
		}
		for _, row := range rows {
			e, err := r.taskRepoModelToEntity(ctx, s, row)
			if err != nil {
				return err
			}
			out = append(out, e)
		}
		return nil
	})
	return out, err
}

// GetTasksByAssignee is get_tasks_by_assignee (list_tasks with the assignee filter).
func (r *ORMTaskRepository) GetTasksByAssignee(ctx context.Context, assigneeID string) ([]*entities.Task, error) {
	return r.ListTasks(ctx, nil, nil, &assigneeID, 100, 0)
}

// ---- overdue / batch -----------------------------------------------------------

// GetOverdueTasks is get_overdue_tasks. Python compares the VARCHAR due_date column with
// datetime.now(UTC); PostgreSQL has no varchar < timestamp operator, so the query raises.
// Defect preserved.
func (r *ORMTaskRepository) GetOverdueTasks(ctx context.Context) ([]*entities.Task, error) {
	out := []*entities.Task{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{}
		conds := []string{}
		if r.GitBranchID != nil && *r.GitBranchID != "" {
			args = append(args, *r.GitBranchID)
			conds = append(conds, fmt.Sprintf(`"git_branch_id" = $%d::uuid`, len(args)))
		}
		args = append(args, time.Now().UTC())
		conds = append(conds, fmt.Sprintf(`"due_date" < $%d`, len(args)))
		conds = append(conds, `"status" != 'completed'`)
		suffix := " WHERE " + strings.Join(conds, " AND ")
		rows, err := r.selectRows(ctx, s, suffix, args...)
		if err != nil {
			return err
		}
		for _, row := range rows {
			e, err := r.taskRepoModelToEntity(ctx, s, row)
			if err != nil {
				return err
			}
			out = append(out, e)
		}
		return nil
	})
	return out, err
}

// BatchUpdateStatus is batch_update_status (no user filter, no timestamp event).
func (r *ORMTaskRepository) BatchUpdateStatus(ctx context.Context, taskIDs []string, status string) (int, error) {
	updated := 0
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{status}
		in := taskRepoInClause("id", taskIDs, &args, "::uuid")
		q := fmt.Sprintf(`UPDATE tasks SET "status" = $1 WHERE %s`, in)
		if r.GitBranchID != nil && *r.GitBranchID != "" {
			args = append(args, *r.GitBranchID)
			q += fmt.Sprintf(` AND "git_branch_id" = $%d::uuid`, len(args))
		}
		res, err := s.ExecContext(ctx, q, args...)
		if err != nil {
			return err
		}
		n, _ := res.RowsAffected()
		updated = int(n)
		return nil
	})
	return updated, err
}

// ---- save ----------------------------------------------------------------------

// Save is save: touch the entity, then _perform_save.
func (r *ORMTaskRepository) Save(ctx context.Context, task *entities.Task) (*entities.Task, error) {
	if err := task.Touch("repository_save_task"); err != nil {
		return nil, err
	}
	return r.taskRepoSave(ctx, task)
}

// taskRepoSave is _perform_save. It shares one transaction with every nested repository
// call; the timestamp hooks fire through ORMRepository.Update/Create.
func (r *ORMTaskRepository) taskRepoSave(ctx context.Context, task *entities.Task) (*entities.Task, error) {
	if task.ID == nil {
		return nil, &ValueError{Msg: "Task ID is required to save a task"}
	}
	id := task.ID.Value
	err := r.Transaction(ctx, func(ctx context.Context) error {
		return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
			existing, err := r.ORMRepository.getByID(ctx, s, id)
			if err != nil {
				return err
			}
			effectiveUserID := taskRepoPickUserID(r.UserID, task.UserID, existing)
			if existing != nil {
				modelDict := r.taskRepoEntityToModelDict(task)
				if _, err := r.ORMRepository.Update(ctx, id, modelDict); err != nil {
					return err
				}
				if err := r.taskRepoReplaceDependencies(ctx, s, id, task, effectiveUserID); err != nil {
					return err
				}
				if err := r.taskRepoReplaceAssignees(ctx, s, id, task, effectiveUserID); err != nil {
					return err
				}
				if err := r.taskRepoReplaceLabels(ctx, s, id, task, effectiveUserID); err != nil {
					return err
				}
				updated, err := r.ORMRepository.getByID(ctx, s, id)
				if err != nil {
					return err
				}
				if updated != nil {
					task.CreatedAt = &updated.CreatedAt
					task.UpdatedAt = &updated.UpdatedAt
				}
				r.PublishEntityEvents(task)
				return nil
			}

			// New task: validate the user like Python.
			userIDToUse := taskRepoPickUserID(r.UserID, task.UserID, nil)
			var taskUserID string
			if userIDToUse != nil {
				taskUserID, err = domain.ValidateUserID(userIDToUse, "Task creation")
				if err != nil {
					return err
				}
			} else {
				return exceptions.NewUserAuthenticationRequiredError("Task creation")
			}
			taskStatus := ""
			if task.Status != nil {
				taskStatus = task.Status.Value
			}
			taskPriority := ""
			if task.Priority != nil {
				taskPriority = task.Priority.Value
			}
			progressPct := int64(0)
			if v, ok := taskRepoOverallProgressValue(task).(int64); ok {
				progressPct = v
			} else if v, ok := taskRepoOverallProgressValue(task).(float64); ok {
				progressPct = int64(v)
			}
			completionSummary := ""
			if task.CompletionSummary != nil {
				completionSummary = *task.CompletionSummary
			}
			data := NewKwargs(
				"id", id,
				"title", task.Title,
				"description", task.Description,
				"git_branch_id", task.GitBranchID,
				"status", taskStatus,
				"priority", taskPriority,
				"progress_history", task.ProgressHistory,
				"progress_count", task.ProgressCount,
				"estimated_effort", taskRepoEnsureEstimatedEffort(task.EstimatedEffort),
				"due_date", task.DueDate,
				"context_id", task.ContextID,
				"user_id", taskUserID,
				"progress_percentage", progressPct,
				"completion_summary", completionSummary,
			)
			if _, err := r.ORMRepository.Create(ctx, data); err != nil {
				return err
			}
			if err := r.taskRepoReplaceDependencies(ctx, s, id, task, &taskUserID); err != nil {
				return err
			}
			if len(task.Assignees) > 0 {
				for _, assignee := range task.Assignees {
					_, _ = s.ExecContext(ctx,
						`INSERT INTO task_assignees (id, task_id, assignee_id, role, user_id, assigned_at) VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6)`,
						value_objects.NewUUIDv4(), id, assignee, "agent", taskUserID, database.TimestampNow())
				}
			}
			for _, labelName := range task.Labels {
				labelID, err := r.taskRepoFindLabelID(ctx, s, labelName)
				if err != nil {
					return err
				}
				if labelID == "" {
					labelID, err = r.taskRepoCreateLabel(ctx, s, labelName, r.UserID)
					if err != nil {
						return err
					}
				}
				_, _ = s.ExecContext(ctx,
					`INSERT INTO task_labels (task_id, label_id, user_id, applied_at) VALUES ($1::uuid, $2, $3, $4)`,
					id, labelID, taskRepoDeref(r.UserID), database.TimestampNow())
			}
			created, err := r.ORMRepository.getByID(ctx, s, id)
			if err != nil {
				return err
			}
			if created != nil {
				task.CreatedAt = &created.CreatedAt
				task.UpdatedAt = &created.UpdatedAt
			}
			r.PublishEntityEvents(task)
			return nil
		})
	})
	if err != nil {
		return nil, err
	}
	return task, nil
}

// taskRepoPickUserID is the repo.user_id -> task.user_id -> existing.user_id chain Python
// uses for dependency/assignee/label writes (empty strings are falsy).
func taskRepoPickUserID(repoUserID, taskUserID *string, existing *database.Task) *string {
	if repoUserID != nil && *repoUserID != "" {
		return repoUserID
	}
	if taskUserID != nil && *taskUserID != "" {
		return taskUserID
	}
	if existing != nil && existing.UserID != "" {
		v := existing.UserID
		return &v
	}
	return nil
}

// taskRepoReplaceDependencies deletes and re-creates the task dependencies.
func (r *ORMTaskRepository) taskRepoReplaceDependencies(ctx context.Context, s database.DBTX, taskID string, task *entities.Task, userID *string) error {
	if _, err := s.ExecContext(ctx, `DELETE FROM task_dependencies WHERE task_id = $1::uuid`, taskID); err != nil {
		return err
	}
	if userID == nil {
		return &value_objects.ValueError{Msg: "User ID is required for creating task dependencies (DDD compliance)"}
	}
	for _, dependency := range task.Dependencies {
		if _, err := s.ExecContext(ctx,
			`INSERT INTO task_dependencies (task_id, depends_on_task_id, dependency_type, user_id, created_at) VALUES ($1::uuid, $2::uuid, $3, $4, $5)`,
			taskID, dependency.Value, "blocks", *userID, database.TimestampNow()); err != nil {
			return err
		}
	}
	return nil
}

// taskRepoReplaceAssignees is the idempotent assignee diff (role "agent").
func (r *ORMTaskRepository) taskRepoReplaceAssignees(ctx context.Context, s database.DBTX, taskID string, task *entities.Task, userID *string) error {
	if len(task.Assignees) == 0 {
		return nil
	}
	if userID == nil {
		// Python logs an error and skips assignee creation.
		return nil
	}
	existingIDs, err := r.taskRepoExistingAssigneeIDs(ctx, s, taskID)
	if err != nil {
		return err
	}
	existingSet := map[string]bool{}
	for _, a := range existingIDs {
		existingSet[a] = true
	}
	newSet := map[string]bool{}
	for _, a := range task.Assignees {
		newSet[a] = true
	}
	toRemove := []string{}
	for _, a := range existingIDs {
		if !newSet[a] {
			toRemove = append(toRemove, a)
		}
	}
	if len(toRemove) > 0 {
		args := []any{}
		in := taskRepoInClause("assignee_id", toRemove, &args, "")
		args = append(args, taskID)
		if _, err := s.ExecContext(ctx,
			fmt.Sprintf(`DELETE FROM task_assignees WHERE task_id = $%d::uuid AND %s`, len(args), in), args...); err != nil {
			return err
		}
	}
	for _, assignee := range task.Assignees {
		if newSet[assignee] && existingSet[assignee] {
			continue
		}
		_, _ = s.ExecContext(ctx,
			`INSERT INTO task_assignees (id, task_id, assignee_id, role, user_id, assigned_at) VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6)`,
			value_objects.NewUUIDv4(), taskID, assignee, "agent", *userID, database.TimestampNow())
	}
	return nil
}

// taskRepoReplaceLabels deletes and re-creates the task labels (effective user id).
func (r *ORMTaskRepository) taskRepoReplaceLabels(ctx context.Context, s database.DBTX, taskID string, task *entities.Task, userID *string) error {
	if _, err := s.ExecContext(ctx, `DELETE FROM task_labels WHERE task_id = $1::uuid`, taskID); err != nil {
		return err
	}
	for _, labelName := range task.Labels {
		labelID, err := r.taskRepoFindLabelID(ctx, s, labelName)
		if err != nil {
			return err
		}
		if labelID == "" {
			if userID == nil {
				continue
			}
			labelID, err = r.taskRepoCreateLabel(ctx, s, labelName, userID)
			if err != nil {
				return err
			}
		}
		if userID == nil {
			continue
		}
		_, _ = s.ExecContext(ctx,
			`INSERT INTO task_labels (task_id, label_id, user_id, applied_at) VALUES ($1::uuid, $2, $3, $4)`,
			taskID, labelID, *userID, database.TimestampNow())
	}
	return nil
}

// ---- TaskRepository interface methods ------------------------------------------

// FindByID is find_by_id.
func (r *ORMTaskRepository) FindByID(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
	return r.GetTask(ctx, taskID.Value)
}

// FindAll is find_all (list_tasks with the Python limit default 100).
func (r *ORMTaskRepository) FindAll(ctx context.Context) ([]*entities.Task, error) {
	return r.ListTasks(ctx, nil, nil, nil, 100, 0)
}

// FindByStatus is find_by_status.
func (r *ORMTaskRepository) FindByStatus(ctx context.Context, status value_objects.TaskStatus) ([]*entities.Task, error) {
	return r.ListTasks(ctx, &status.Value, nil, nil, 100, 0)
}

// FindByPriority is find_by_priority.
func (r *ORMTaskRepository) FindByPriority(ctx context.Context, priority value_objects.Priority) ([]*entities.Task, error) {
	return r.ListTasks(ctx, nil, &priority.Value, nil, 100, 0)
}

// FindByAssignee is find_by_assignee.
func (r *ORMTaskRepository) FindByAssignee(ctx context.Context, assignee string) ([]*entities.Task, error) {
	return r.GetTasksByAssignee(ctx, assignee)
}

// FindByLabels is find_by_labels: the Python stub always returns an empty list.
func (r *ORMTaskRepository) FindByLabels(ctx context.Context, labels []string) ([]*entities.Task, error) {
	return []*entities.Task{}, nil
}

// Search is search (Python default limit 10).
func (r *ORMTaskRepository) Search(ctx context.Context, query string, filters map[string]any, limit int) ([]*entities.Task, error) {
	return r.SearchTasks(ctx, query, filters, limit)
}

// Delete is delete.
func (r *ORMTaskRepository) Delete(ctx context.Context, taskID value_objects.TaskId) (bool, error) {
	return r.DeleteTask(ctx, taskID.Value)
}

// Exists is exists.
func (r *ORMTaskRepository) Exists(ctx context.Context, taskID value_objects.TaskId) (bool, error) {
	task, err := r.GetTask(ctx, taskID.Value)
	if err != nil {
		return false, err
	}
	return task != nil, nil
}

// GetNextID is get_next_id.
func (r *ORMTaskRepository) GetNextID(ctx context.Context) (value_objects.TaskId, error) {
	return value_objects.NewTaskId(value_objects.NewUUIDv4())
}

// Count is count (only the status kwarg is relevant).
func (r *ORMTaskRepository) Count(ctx context.Context) (int, error) {
	return r.GetTaskCount(ctx, nil)
}

// GetStatistics is get_statistics.
func (r *ORMTaskRepository) GetStatistics(ctx context.Context) (map[string]any, error) {
	total, err := r.GetTaskCount(ctx, nil)
	if err != nil {
		return nil, err
	}
	completed, err := r.GetTaskCount(ctx, taskRepoStrPtr("completed"))
	if err != nil {
		return nil, err
	}
	inProgress, err := r.GetTaskCount(ctx, taskRepoStrPtr("in_progress"))
	if err != nil {
		return nil, err
	}
	todo, err := r.GetTaskCount(ctx, taskRepoStrPtr("todo"))
	if err != nil {
		return nil, err
	}
	return map[string]any{
		"total_tasks":       total,
		"completed_tasks":   completed,
		"in_progress_tasks": inProgress,
		"todo_tasks":        todo,
	}, nil
}

// taskRepoEnumValue is the `value.value if hasattr(value, "value") else value` conversion.
func taskRepoEnumValue(v any) any {
	switch x := v.(type) {
	case value_objects.TaskStatus:
		return x.Value
	case *value_objects.TaskStatus:
		if x == nil {
			return nil
		}
		return x.Value
	case value_objects.Priority:
		return x.Value
	case *value_objects.Priority:
		if x == nil {
			return nil
		}
		return x.Value
	}
	return v
}

// FindByCriteria is find_by_criteria.
func (r *ORMTaskRepository) FindByCriteria(ctx context.Context, filters map[string]any, limit *int) ([]*entities.Task, error) {
	out := []*entities.Task{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{}
		conds := []string{}
		r.taskRepoUserCondition(&args, &conds)

		gitBranchFilter := r.GitBranchID
		if gitBranchFilter == nil {
			if v, ok := filters["git_branch_id"]; ok {
				if sv, ok := v.(string); ok {
					gitBranchFilter = &sv
				} else if svp, ok := v.(*string); ok {
					gitBranchFilter = svp
				}
			}
		}
		if gitBranchFilter != nil {
			args = append(args, *gitBranchFilter)
			conds = append(conds, fmt.Sprintf(`"git_branch_id" = $%d::uuid`, len(args)))
		}
		if v, ok := filters["status"]; ok {
			sv := taskRepoEnumValue(v)
			if sv == nil {
				conds = append(conds, `"status" IS NULL`)
			} else {
				args = append(args, value_objects.PyStr(sv))
				conds = append(conds, fmt.Sprintf(`"status" = $%d`, len(args)))
			}
		}
		if v, ok := filters["priority"]; ok {
			pv := taskRepoEnumValue(v)
			if pv == nil {
				conds = append(conds, `"priority" IS NULL`)
			} else {
				args = append(args, value_objects.PyStr(pv))
				conds = append(conds, fmt.Sprintf(`"priority" = $%d`, len(args)))
			}
		}
		if v, ok := filters["assignees"]; ok && value_objects.PyTruthy(v) {
			assignees := taskRepoStringList(v)
			if len(assignees) > 0 {
				in := taskRepoInClause("ta.assignee_id", assignees, &args, "")
				conds = append(conds, `EXISTS (SELECT 1 FROM task_assignees ta WHERE ta.task_id = tasks.id AND `+in+`)`)
			}
		} else if v, ok := filters["assignee"]; ok && value_objects.PyTruthy(v) {
			args = append(args, value_objects.PyStr(v))
			conds = append(conds, fmt.Sprintf(`EXISTS (SELECT 1 FROM task_assignees ta WHERE ta.task_id = tasks.id AND ta.assignee_id = $%d)`, len(args)))
		}
		if v, ok := filters["labels"]; ok && value_objects.PyTruthy(v) {
			labels := taskRepoStringList(v)
			if len(labels) > 0 {
				in := taskRepoInClause("l.name", labels, &args, "")
				conds = append(conds, `EXISTS (SELECT 1 FROM task_labels tl JOIN labels l ON tl.label_id = l.id WHERE tl.task_id = tasks.id AND `+in+`)`)
			}
		}
		suffix := ""
		if len(conds) > 0 {
			suffix = " WHERE " + strings.Join(conds, " AND ")
		}
		suffix += ` ORDER BY "updated_at" DESC`
		if limit != nil && *limit != 0 {
			suffix += fmt.Sprintf(" LIMIT %d", *limit)
		}
		rows, err := r.selectRows(ctx, s, suffix, args...)
		if err != nil {
			return err
		}
		for _, row := range rows {
			e, err := r.taskRepoModelToEntity(ctx, s, row)
			if err != nil {
				return err
			}
			out = append(out, e)
		}
		return nil
	})
	return out, err
}

// taskRepoStringList converts a Python list-like value to []string.
func taskRepoStringList(v any) []string {
	switch x := v.(type) {
	case []string:
		return append([]string{}, x...)
	case []any:
		out := make([]string, 0, len(x))
		for _, e := range x {
			out = append(out, value_objects.PyStr(e))
		}
		return out
	}
	return nil
}

// FindByIDAllStates is find_by_id_all_states (no user or branch filter).
func (r *ORMTaskRepository) FindByIDAllStates(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
	var out *entities.Task
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := r.selectRows(ctx, s, ` WHERE "id" = $1::uuid LIMIT 1`, taskID.Value)
		if err != nil {
			return err
		}
		if len(rows) == 0 {
			return nil
		}
		out, err = r.taskRepoModelToEntity(ctx, s, rows[0])
		return err
	})
	return out, err
}

// ---- git branch helpers --------------------------------------------------------

// GitBranchExists is git_branch_exists.
func (r *ORMTaskRepository) GitBranchExists(ctx context.Context, gitBranchID string) (bool, error) {
	exists := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var one int
		err := s.QueryRowContext(ctx, `SELECT 1 FROM project_git_branchs WHERE id = $1::uuid LIMIT 1`, gitBranchID).Scan(&one)
		if errors.Is(err, sql.ErrNoRows) {
			return nil
		}
		if err != nil {
			return err
		}
		exists = true
		return nil
	})
	return exists, err
}

// FindByGitBranchID is find_by_git_branch_id (created_at desc, no limit). Failures degrade
// to an empty list, as in Python.
func (r *ORMTaskRepository) FindByGitBranchID(ctx context.Context, gitBranchID string) ([]*entities.Task, error) {
	out := []*entities.Task{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{gitBranchID}
		conds := []string{`"git_branch_id" = $1::uuid`}
		r.taskRepoUserCondition(&args, &conds)
		suffix := " WHERE " + strings.Join(conds, " AND ") + ` ORDER BY "created_at" DESC`
		rows, err := r.selectRows(ctx, s, suffix, args...)
		if err != nil {
			return err
		}
		for _, row := range rows {
			e, err := r.taskRepoModelToEntity(ctx, s, row)
			if err != nil {
				return err
			}
			out = append(out, e)
		}
		return nil
	})
	if err != nil {
		return []*entities.Task{}, nil
	}
	return out, nil
}

// GetTasksByGitBranchID is get_tasks_by_git_branch_id (raw dict rows for statistics).
func (r *ORMTaskRepository) GetTasksByGitBranchID(ctx context.Context, gitBranchID string) ([]*entities.OrderedMap[any], error) {
	out := []*entities.OrderedMap[any]{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{gitBranchID}
		conds := []string{`"git_branch_id" = $1::uuid`}
		r.taskRepoUserCondition(&args, &conds)
		suffix := " WHERE " + strings.Join(conds, " AND ") + ` ORDER BY "created_at" DESC`
		rows, err := r.selectRows(ctx, s, suffix, args...)
		if err != nil {
			return err
		}
		for _, row := range rows {
			task, err := r.taskRepoModelToEntity(ctx, s, row)
			if err != nil {
				return err
			}
			var createdAt, updatedAt any
			if task.CreatedAt != nil {
				createdAt = *task.CreatedAt
			}
			if task.UpdatedAt != nil {
				updatedAt = *task.UpdatedAt
			}
			entry := entities.NewOrderedMap[any]()
			entry.Set("id", task.ID.Value)
			entry.Set("title", task.Title)
			entry.Set("status", task.Status.Value)
			entry.Set("priority", task.Priority.Value)
			entry.Set("progress_percentage", taskRepoOverallProgressValue(task))
			entry.Set("created_at", createdAt)
			entry.Set("updated_at", updatedAt)
			entry.Set("assignees_count", len(task.Assignees))
			entry.Set("labels_count", len(task.Labels))
			entry.Set("subtasks_count", len(task.Subtasks))
			entry.Set("git_branch_id", value_objects.PyStr(task.GitBranchID))
			out = append(out, entry)
		}
		return nil
	})
	if err != nil {
		return []*entities.OrderedMap[any]{}, nil
	}
	return out, nil
}

// ---- selective fields ----------------------------------------------------------

// GetTaskSelectiveFields is get_task_selective_fields.
func (r *ORMTaskRepository) GetTaskSelectiveFields(ctx context.Context, taskID string, fields any) (*entities.OrderedMap[any], error) {
	if r.FieldSelector == nil {
		return nil, nil
	}
	spec := r.FieldSelector.GetTaskFields(taskID, fields)
	optimized, _ := taskRepoSpecValue(spec, "optimized").(bool)
	fieldList := taskRepoSpecFields(spec)
	if optimized && len(fieldList) > 0 {
		if cached := r.FieldSelector.GetCachedFields(taskID, fieldList); cached != nil {
			return cached, nil
		}
	}
	var out *entities.OrderedMap[any]
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		task, err := r.GetTask(ctx, taskID)
		if err != nil {
			return err
		}
		if task == nil {
			return nil
		}
		if optimized && len(fieldList) > 0 {
			data := entities.NewOrderedMap[any]()
			for _, f := range fieldList {
				if v, ok := taskRepoFieldValue(task, f); ok {
					data.Set(f, v)
				}
			}
			r.FieldSelector.CacheFieldMapping(taskID, fieldList, data)
			out = data
			return nil
		}
		out = taskRepoEntityFieldsMap(task)
		return nil
	})
	if err != nil {
		return nil, nil
	}
	return out, nil
}

// ListTasksSelectiveFields is list_tasks_selective_fields.
func (r *ORMTaskRepository) ListTasksSelectiveFields(ctx context.Context, fields any, status, priority, assigneeID *string, limit, offset int) ([]*entities.OrderedMap[any], error) {
	if r.FieldSelector == nil {
		return nil, nil
	}
	if fields == nil {
		fields = r.FieldSelector.GetOptimalFieldSet("list", "task")
	}
	spec := r.FieldSelector.GetTaskFields("list_operation", fields)
	optimized, _ := taskRepoSpecValue(spec, "optimized").(bool)
	fieldList := taskRepoSpecFields(spec)
	if optimized && len(fieldList) > 0 {
		var out []*entities.OrderedMap[any]
		err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
			args := []any{}
			conds := []string{}
			r.taskRepoUserCondition(&args, &conds)
			if r.GitBranchID != nil && *r.GitBranchID != "" {
				args = append(args, *r.GitBranchID)
				conds = append(conds, fmt.Sprintf(`"git_branch_id" = $%d::uuid`, len(args)))
			}
			if status != nil && *status != "" {
				args = append(args, *status)
				conds = append(conds, fmt.Sprintf(`"status" = $%d`, len(args)))
			}
			if priority != nil && *priority != "" {
				args = append(args, *priority)
				conds = append(conds, fmt.Sprintf(`"priority" = $%d`, len(args)))
			}
			if assigneeID != nil && *assigneeID != "" {
				args = append(args, *assigneeID)
				conds = append(conds, fmt.Sprintf(`EXISTS (SELECT 1 FROM task_assignees ta WHERE ta.task_id = tasks.id AND ta.assignee_id = $%d)`, len(args)))
			}
			suffix := ""
			if len(conds) > 0 {
				suffix = " WHERE " + strings.Join(conds, " AND ")
			}
			suffix += ` ORDER BY "created_at" DESC`
			suffix += fmt.Sprintf(" LIMIT %d OFFSET %d", limit, offset)
			rows, err := r.selectRows(ctx, s, suffix, args...)
			if err != nil {
				return err
			}
			for _, row := range rows {
				task, err := r.taskRepoModelToEntity(ctx, s, row)
				if err != nil {
					return err
				}
				data := entities.NewOrderedMap[any]()
				for _, f := range fieldList {
					if v, ok := taskRepoFieldValue(task, f); ok {
						data.Set(f, v)
					}
				}
				out = append(out, data)
			}
			return nil
		})
		if err != nil {
			return nil, nil
		}
		return out, nil
	}
	tasks, err := r.ListTasks(ctx, status, priority, assigneeID, limit, offset)
	if err != nil {
		return nil, nil
	}
	out := make([]*entities.OrderedMap[any], 0, len(tasks))
	for _, task := range tasks {
		entry := entities.NewOrderedMap[any]()
		entry.Set("id", task.ID.Value)
		entry.Set("title", task.Title)
		entry.Set("status", task.Status.Value)
		entry.Set("priority", task.Priority.Value)
		entry.Set("progress_percentage", taskRepoOverallProgressValue(task))
		if task.UpdatedAt != nil {
			entry.Set("updated_at", *task.UpdatedAt)
		} else {
			entry.Set("updated_at", nil)
		}
		out = append(out, entry)
	}
	return out, nil
}

// GetFieldSelectorMetrics is get_field_selector_metrics.
func (r *ORMTaskRepository) GetFieldSelectorMetrics() map[string]int {
	if r.FieldSelector == nil {
		return map[string]int{}
	}
	return r.FieldSelector.GetMetrics()
}

// EstimateFieldOptimizationSavings is estimate_field_optimization_savings.
func (r *ORMTaskRepository) EstimateFieldOptimizationSavings(fieldSet any) map[string]float64 {
	if r.FieldSelector == nil {
		return map[string]float64{}
	}
	return r.FieldSelector.EstimateSavings("task", fieldSet)
}

func taskRepoSpecValue(spec *entities.OrderedMap[any], key string) any {
	if spec == nil {
		return nil
	}
	v, _ := spec.Get(key)
	return v
}

func taskRepoSpecFields(spec *entities.OrderedMap[any]) []string {
	v := taskRepoSpecValue(spec, "fields")
	switch f := v.(type) {
	case []string:
		return f
	case []any:
		out := make([]string, 0, len(f))
		for _, x := range f {
			if s, ok := x.(string); ok {
				out = append(out, s)
			}
		}
		return out
	}
	return nil
}

// taskRepoEntityFieldsMap is the non-optimized fallback dict of get_task_selective_fields.
func taskRepoEntityFieldsMap(task *entities.Task) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("id", value_objects.PyStr(task.ID))
	out.Set("title", task.Title)
	out.Set("description", task.Description)
	if task.Status != nil {
		out.Set("status", task.Status.Value)
	} else {
		out.Set("status", "None")
	}
	if task.Priority != nil {
		out.Set("priority", task.Priority.Value)
	} else {
		out.Set("priority", "None")
	}
	out.Set("assignees", task.Assignees)
	out.Set("labels", task.Labels)
	out.Set("progress_history", task.ProgressHistory)
	out.Set("progress_count", task.ProgressCount)
	out.Set("estimated_effort", task.EstimatedEffort)
	out.Set("due_date", task.DueDate)
	out.Set("created_at", task.CreatedAt)
	out.Set("updated_at", task.UpdatedAt)
	out.Set("context_id", task.ContextID)
	out.Set("git_branch_id", task.GitBranchID)
	out.Set("progress_percentage", taskRepoOverallProgressValue(task))
	return out
}

// taskRepoFieldValue maps a Task attribute name to its value for selective projection.
func taskRepoFieldValue(task *entities.Task, field string) (any, bool) {
	switch field {
	case "id":
		return value_objects.PyStr(task.ID), true
	case "title":
		return task.Title, true
	case "description":
		return task.Description, true
	case "status":
		if task.Status != nil {
			return task.Status.Value, true
		}
		return nil, true
	case "priority":
		if task.Priority != nil {
			return task.Priority.Value, true
		}
		return nil, true
	case "assignees":
		return task.Assignees, true
	case "labels":
		return task.Labels, true
	case "progress_history":
		return task.ProgressHistory, true
	case "progress_count":
		return task.ProgressCount, true
	case "estimated_effort":
		return task.EstimatedEffort, true
	case "due_date":
		return task.DueDate, true
	case "created_at":
		return task.CreatedAt, true
	case "updated_at":
		return task.UpdatedAt, true
	case "context_id":
		return task.ContextID, true
	case "git_branch_id":
		return task.GitBranchID, true
	case "progress_percentage", "overall_progress":
		return taskRepoOverallProgressValue(task), true
	}
	return nil, false
}

// ---- misc ----------------------------------------------------------------------

// GetCompletedSubtaskCounts is get_completed_subtask_counts (batch, 'done' only).
func (r *ORMTaskRepository) GetCompletedSubtaskCounts(ctx context.Context, taskIDs []string) (map[string]int, error) {
	out := map[string]int{}
	if len(taskIDs) == 0 {
		return out, nil
	}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{}
		in := taskRepoInClause("task_id", taskIDs, &args, "::uuid")
		rows, err := s.QueryContext(ctx,
			`SELECT task_id::text, COUNT(id) FROM subtasks WHERE `+in+` AND status = 'done' GROUP BY task_id`, args...)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var taskID string
			var count int
			if err := rows.Scan(&taskID, &count); err != nil {
				return err
			}
			out[taskID] = count
		}
		return rows.Err()
	})
	if err != nil {
		return map[string]int{}, nil
	}
	return out, nil
}

// InvalidateCache is invalidate_cache; the performance cache is dropped (no-op).
func (r *ORMTaskRepository) InvalidateCache(operation string) {}

// AtomicIncrementCompletedSubtasks is atomic_increment_completed_subtasks.
func (r *ORMTaskRepository) AtomicIncrementCompletedSubtasks(ctx context.Context, taskID string) (bool, error) {
	ok := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		res, err := s.ExecContext(ctx,
			`UPDATE tasks SET completed_subtasks = completed_subtasks + 1 WHERE id = $1::uuid`, taskID)
		if err != nil {
			return err
		}
		n, _ := res.RowsAffected()
		ok = n > 0
		return nil
	})
	if err != nil {
		return false, nil
	}
	return ok, nil
}

// taskRepoOptionalStep runs step inside a savepoint; on error the step is rolled back and the
// error swallowed (Python's per-step try/except + session.rollback()).
func taskRepoOptionalStep(ctx context.Context, s database.DBTX, name string, step func() error) {
	if _, err := s.ExecContext(ctx, "SAVEPOINT "+name); err != nil {
		return
	}
	if err := step(); err != nil {
		_, _ = s.ExecContext(ctx, "ROLLBACK TO SAVEPOINT "+name)
		return
	}
	_, _ = s.ExecContext(ctx, "RELEASE SAVEPOINT "+name)
}
