package repositories

// Supabase-Optimized Task Repository
// (Python repositories/orm/supabase_optimized_repository.py): minimal single-query task
// reads tuned for cloud latency.
//
// Python's class extends ORMTaskRepository. That module is not ported yet, so this Go
// type carries only the state and methods this module owns (Sessions, GitBranchID and its
// four methods); the inherited task-repository methods will arrive with task_repository.go.

import (
	"context"
	"database/sql"
	"fmt"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// SupabaseOptimizedRepository is SupabaseOptimizedRepository.
type SupabaseOptimizedRepository struct {
	Sessions    *database.SessionManager
	GitBranchID *string
}

// NewSupabaseOptimizedRepository builds the repository (Python's git_branch_id defaults to
// None; a nil pointer is None).
func NewSupabaseOptimizedRepository(sessions *database.SessionManager, gitBranchID *string) *SupabaseOptimizedRepository {
	return &SupabaseOptimizedRepository{Sessions: sessions, GitBranchID: gitBranchID}
}

func supabaseRepoTruthy(s *string) bool { return s != nil && *s != "" }

// ListTasksMinimal is list_tasks_minimal: one query, no joins, relationship counts as
// subqueries. It returns raw dict-like rows (dict key order preserved).
func (r *SupabaseOptimizedRepository) ListTasksMinimal(
	ctx context.Context, status, priority, assigneeID *string, limit, offset *int,
) ([]*entities.OrderedMap[any], error) {
	lim, off := 20, 0
	if limit != nil {
		lim = *limit
	}
	if offset != nil {
		off = *offset
	}
	if lim < 0 {
		lim = 20
	}
	if off < 0 {
		off = 0
	}
	if lim > 1000 {
		lim = 1000
	}

	out := []*entities.OrderedMap[any]{}
	err := r.Sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		filters := []string{"1=1"}
		var args []any
		if supabaseRepoTruthy(r.GitBranchID) {
			args = append(args, *r.GitBranchID)
			filters = append(filters, fmt.Sprintf("git_branch_id = $%d", len(args)))
		}
		if supabaseRepoTruthy(status) {
			args = append(args, *status)
			filters = append(filters, fmt.Sprintf("status = $%d", len(args)))
		}
		if supabaseRepoTruthy(priority) {
			args = append(args, *priority)
			filters = append(filters, fmt.Sprintf("priority = $%d", len(args)))
		}
		if supabaseRepoTruthy(assigneeID) {
			args = append(args, *assigneeID)
			filters = append(filters, fmt.Sprintf(
				"EXISTS (SELECT 1 FROM task_assignees WHERE task_id = tasks.id AND assignee_id = $%d)", len(args)))
		}
		args = append(args, lim, off)
		q := fmt.Sprintf(
			`SELECT id::text, title, status, priority, created_at, updated_at,
			 (SELECT COUNT(*) FROM subtasks WHERE task_id = tasks.id) as subtask_count,
			 (SELECT COUNT(*) FROM task_assignees WHERE task_id = tasks.id) as assignee_count,
			 (SELECT COUNT(*) FROM task_dependencies WHERE task_id = tasks.id) as dependency_count
			 FROM tasks WHERE %s ORDER BY created_at DESC LIMIT $%d OFFSET $%d`,
			strings.Join(filters, " AND "), len(args)-1, len(args))
		rows, err := s.QueryContext(ctx, q, args...)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var id, title, st, pr string
			var createdAt, updatedAt sql.NullTime
			var subtaskCount, assigneeCount, dependencyCount int64
			if err := rows.Scan(&id, &title, &st, &pr, &createdAt, &updatedAt,
				&subtaskCount, &assigneeCount, &dependencyCount); err != nil {
				return err
			}
			m := entities.NewOrderedMap[any]()
			m.Set("id", id)
			m.Set("title", title)
			m.Set("status", st)
			m.Set("priority", pr)
			if createdAt.Valid {
				m.Set("created_at", value_objects.IsoFormatNaive(createdAt.Time))
			} else {
				m.Set("created_at", nil)
			}
			if updatedAt.Valid {
				m.Set("updated_at", value_objects.IsoFormatNaive(updatedAt.Time))
			} else {
				m.Set("updated_at", nil)
			}
			m.Set("subtask_count", subtaskCount)
			m.Set("assignee_count", assigneeCount)
			m.Set("dependency_count", dependencyCount)
			m.Set("has_relationships", subtaskCount+assigneeCount+dependencyCount > 0)
			out = append(out, m)
		}
		return rows.Err()
	})
	return out, err
}

// ListTasksNoRelations is list_tasks_no_relations.
func (r *SupabaseOptimizedRepository) ListTasksNoRelations(
	ctx context.Context, status, priority *string, limit, offset *int,
) ([]*entities.Task, error) {
	lim, off := 50, 0
	if limit != nil {
		lim = *limit
	}
	if offset != nil {
		off = *offset
	}
	out := []*entities.Task{}
	err := r.Sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var conds []string
		var args []any
		if supabaseRepoTruthy(r.GitBranchID) {
			args = append(args, *r.GitBranchID)
			conds = append(conds, fmt.Sprintf("git_branch_id = $%d", len(args)))
		}
		if supabaseRepoTruthy(status) {
			args = append(args, *status)
			conds = append(conds, fmt.Sprintf("status = $%d", len(args)))
		}
		if supabaseRepoTruthy(priority) {
			args = append(args, *priority)
			conds = append(conds, fmt.Sprintf("priority = $%d", len(args)))
		}
		args = append(args, lim, off)
		q := `SELECT id::text, title, description, status, priority, created_at, updated_at, git_branch_id::text, context_id::text, estimated_effort, due_date FROM tasks`
		if len(conds) > 0 {
			q += " WHERE " + strings.Join(conds, " AND ")
		}
		q += fmt.Sprintf(" ORDER BY created_at DESC LIMIT $%d OFFSET $%d", len(args)-1, len(args))
		rows, err := s.QueryContext(ctx, q, args...)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			row := &database.Task{}
			if err := rows.Scan(&row.ID, &row.Title, &row.Description, &row.Status, &row.Priority,
				&row.CreatedAt, &row.UpdatedAt, &row.GitBranchID, &row.ContextID, &row.EstimatedEffort, &row.DueDate); err != nil {
				return err
			}
			e, err := r.modelToEntityMinimal(row)
			if err != nil {
				return err
			}
			out = append(out, e)
		}
		return rows.Err()
	})
	return out, err
}

// modelToEntityMinimal is _model_to_entity_minimal: relationships are empty, not loaded.
func (r *SupabaseOptimizedRepository) modelToEntityMinimal(row *database.Task) (*entities.Task, error) {
	tid, err := value_objects.NewTaskId(row.ID)
	if err != nil {
		return nil, err
	}
	status := value_objects.TaskStatus{Value: row.Status}
	priority := value_objects.Priority{Value: row.Priority}
	c, u := row.CreatedAt, row.UpdatedAt
	return entities.NewTask(entities.Task{
		BaseTimestampEntity: base.BaseTimestampEntity{CreatedAt: &c, UpdatedAt: &u},
		ID:                  &tid, Title: row.Title, Description: row.Description,
		Status: &status, Priority: &priority,
		Subtasks: []string{}, Assignees: []string{}, Dependencies: []value_objects.TaskId{}, Labels: []string{},
		GitBranchID: &row.GitBranchID, ContextID: row.ContextID,
		EstimatedEffort: row.EstimatedEffort, DueDate: row.DueDate,
	})
}

// GetTaskWithCounts is get_task_with_counts. Python reads result.details, which is not a
// column on tasks, so any existing task raises AttributeError; the defect is preserved.
func (r *SupabaseOptimizedRepository) GetTaskWithCounts(ctx context.Context, taskID string) (*entities.OrderedMap[any], error) {
	if _, ok := value_objects.PyParseUUID(taskID); !ok {
		return nil, nil
	}
	var out *entities.OrderedMap[any]
	err := r.Sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var id, title, description, status, priority string
		var createdAt, updatedAt sql.NullTime
		var subtaskCount, assigneeCount, dependencyCount, labelCount int64
		err := s.QueryRowContext(ctx,
			`SELECT t.id::text, t.title, t.description, t.status, t.priority, t.created_at, t.updated_at,
			 (SELECT COUNT(*) FROM subtasks WHERE task_id = t.id) as subtask_count,
			 (SELECT COUNT(*) FROM task_assignees WHERE task_id = t.id) as assignee_count,
			 (SELECT COUNT(*) FROM task_dependencies WHERE task_id = t.id) as dependency_count,
			 (SELECT COUNT(*) FROM task_labels WHERE task_id = t.id) as label_count
			 FROM tasks t WHERE t.id = $1::uuid`, taskID).
			Scan(&id, &title, &description, &status, &priority, &createdAt, &updatedAt,
				&subtaskCount, &assigneeCount, &dependencyCount, &labelCount)
		if err == sql.ErrNoRows {
			return nil
		}
		if err != nil {
			return err
		}
		// result.details does not exist on the row (nor on the table).
		return value_objects.TypeErrorf("'Row' object has no attribute 'details'")
	})
	return out, err
}
