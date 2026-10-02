package services

import (
	"context"
	"database/sql"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// DBWebSocketContextProvider is the SQL-backed WebSocketNotificationContextProvider: the
// _get_task_context/_get_subtask_context/_get_branch_context/_get_branch_cascade_data
// helpers of websocket_notification_service.py. Every failure (including a driver error)
// yields the Python fallback values (nil for cascade data), never an error.
type DBWebSocketContextProvider struct {
	Sessions *database.SessionManager
}

// uuidParam binds an ORM UUID column comparison (UnifiedUUID: non-UUID strings become uuid5).
func wsUUIDParam(v string) any {
	p, err := database.UnifiedUUIDBindParam(v, "postgresql")
	if err != nil {
		return v
	}
	return p
}

// GetTaskContext is _get_task_context.
func (p *DBWebSocketContextProvider) GetTaskContext(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any] {
	var out *entities.OrderedMap[any]
	err := p.Sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		q := `SELECT t."title", b."id", b."name", b."project_id", t."user_id" FROM "tasks" t ` +
			`JOIN "project_git_branchs" b ON t."git_branch_id" = b."id" WHERE t."id" = $1`
		args := []any{wsUUIDParam(taskID)}
		if userID != nil && *userID != "" {
			q += ` AND t."user_id" = $2`
			args = append(args, *userID)
		}
		q += ` LIMIT 1`
		var title, branchID, branchName, projectID, taskUserID string
		err := s.QueryRowContext(ctx, q, args...).Scan(&title, &branchID, &branchName, &projectID, &taskUserID)
		if err == sql.ErrNoRows {
			return nil
		}
		if err != nil {
			return err
		}
		c := entities.NewOrderedMap[any]()
		c.Set("task_title", title)
		c.Set("parent_branch_id", branchID)
		c.Set("parent_branch_title", branchName)
		c.Set("parent_project_id", projectID)
		c.Set("task_user_id", taskUserID)
		out = c
		return nil
	})
	if err != nil || out == nil {
		return wsTaskContextFallback(taskID)
	}
	return out
}

// GetSubtaskContext is _get_subtask_context.
func (p *DBWebSocketContextProvider) GetSubtaskContext(ctx context.Context, subtaskID, taskID string, userID *string) *entities.OrderedMap[any] {
	var out *entities.OrderedMap[any]
	err := p.Sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		q := `SELECT st."title", t."id", t."title" FROM "subtasks" st ` +
			`JOIN "tasks" t ON st."task_id" = t."id" WHERE st."id" = $1 AND st."task_id" = $2`
		args := []any{wsUUIDParam(subtaskID), wsUUIDParam(taskID)}
		if userID != nil && *userID != "" {
			q += ` AND st."user_id" = $3`
			args = append(args, *userID)
		}
		q += ` LIMIT 1`
		var subtaskTitle, parentID, parentTitle string
		err := s.QueryRowContext(ctx, q, args...).Scan(&subtaskTitle, &parentID, &parentTitle)
		if err == sql.ErrNoRows {
			return nil
		}
		if err != nil {
			return err
		}
		c := entities.NewOrderedMap[any]()
		c.Set("subtask_title", subtaskTitle)
		c.Set("parent_task_id", parentID)
		c.Set("parent_task_title", parentTitle)
		out = c
		return nil
	})
	if err != nil || out == nil {
		return wsSubtaskContextFallback(subtaskID, taskID)
	}
	return out
}

// GetBranchContext is _get_branch_context.
func (p *DBWebSocketContextProvider) GetBranchContext(ctx context.Context, branchID string, userID *string) *entities.OrderedMap[any] {
	var out *entities.OrderedMap[any]
	err := p.Sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		q := `SELECT "name" FROM "project_git_branchs" WHERE "id" = $1`
		args := []any{wsUUIDParam(branchID)}
		if userID != nil && *userID != "" {
			q += ` AND "user_id" = $2`
			args = append(args, *userID)
		}
		q += ` LIMIT 1`
		var name string
		err := s.QueryRowContext(ctx, q, args...).Scan(&name)
		if err == sql.ErrNoRows {
			return nil
		}
		if err != nil {
			return err
		}
		c := entities.NewOrderedMap[any]()
		c.Set("branch_title", name)
		out = c
		return nil
	})
	if err != nil || out == nil {
		return wsBranchContextFallback(branchID)
	}
	return out
}

// wsCascadeSelect is the _get_branch_cascade_data statement. Python runs it on PostgreSQL
// unchanged; ROUND(double precision, integer) does not exist there, so the statement
// fails and the helper returns None (the cascade is never attached). Running the same SQL
// keeps that outcome.
const wsCascadeSelect = `
SELECT
    b.id as branch_id,
    b.project_id,
    b.name as branch_name,
    b.status as branch_status,
    b.priority as branch_priority,
    COALESCE(b.task_count, 0) as task_count,
    COALESCE(b.completed_task_count, 0) as completed_tasks,
    COALESCE(b.task_count, 0) - COALESCE(b.completed_task_count, 0) as todo_tasks,
    CASE
        WHEN COALESCE(b.task_count, 0) = 0 THEN 0
        ELSE ROUND((CAST(COALESCE(b.completed_task_count, 0) AS REAL) / CAST(b.task_count AS REAL)) * 100, 2)
    END as progress_percentage,
    b.updated_at as last_activity
FROM project_git_branchs b
WHERE b.id = $1`

// GetBranchCascadeData is _get_branch_cascade_data: nil when the branch is not found or the
// query fails.
func (p *DBWebSocketContextProvider) GetBranchCascadeData(ctx context.Context, branchID string, userID *string) *entities.OrderedMap[any] {
	var out *entities.OrderedMap[any]
	err := p.Sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		q := wsCascadeSelect
		args := []any{wsUUIDParam(branchID)}
		if userID != nil && *userID != "" {
			q += ` AND b.user_id = $2`
			args = append(args, *userID)
		}
		var (
			id, projectID, name, status, priority sql.NullString
			taskCount, completed, todo            sql.NullInt64
			progress                              sql.NullFloat64
			lastActivity                          sql.NullTime
		)
		err := s.QueryRowContext(ctx, q, args...).Scan(&id, &projectID, &name, &status, &priority,
			&taskCount, &completed, &todo, &progress, &lastActivity)
		if err == sql.ErrNoRows {
			return nil
		}
		if err != nil {
			return err
		}
		var last any
		if lastActivity.Valid && !lastActivity.Time.IsZero() {
			last = value_objects.IsoFormatNaive(lastActivity.Time.In(time.UTC))
		}
		nullable := func(v sql.NullString) any {
			if v.Valid {
				return v.String
			}
			return nil
		}
		c := entities.NewOrderedMap[any]()
		c.Set("id", nullable(id))
		c.Set("project_id", nullable(projectID))
		c.Set("name", nullable(name))
		c.Set("status", nullable(status))
		c.Set("priority", nullable(priority))
		c.Set("task_count", int(taskCount.Int64))
		c.Set("completed_tasks", int(completed.Int64))
		c.Set("todo_tasks", int(todo.Int64))
		c.Set("progress_percentage", progress.Float64)
		c.Set("last_activity", last)
		out = c
		return nil
	})
	if err != nil {
		return nil
	}
	return out
}
