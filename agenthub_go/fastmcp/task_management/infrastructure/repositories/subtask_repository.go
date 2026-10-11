package repositories

// ORM Subtask Repository (Python repositories/orm/subtask_repository.py): SQLAlchemy-backed
// implementation of the SubtaskRepository interface with user isolation, raw SQL for the
// queries the base cannot express, and the Python retry/early-return quirks preserved.

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// ORMSubtaskRepository is ORMSubtaskRepository. It embeds the user-scoped ORM repository for
// session/user scoping and the event publishing mixin for domain events.
type ORMSubtaskRepository struct {
	*UserScopedORMRepository[database.Subtask]
	EventPublishingMixin
}

// NewORMSubtaskRepository builds the subtask repository scoped to userID (nil = system mode).
func NewORMSubtaskRepository(sessions *database.SessionManager, userID *string) (*ORMSubtaskRepository, error) {
	base, err := NewUserScopedORMRepository[database.Subtask]("subtasks", sessions, userID)
	if err != nil {
		return nil, err
	}
	return &ORMSubtaskRepository{
		UserScopedORMRepository: base,
		EventPublishingMixin:    NewEventPublishingMixin(),
	}, nil
}

// ---- domain <-> row conversion -------------------------------------------------

// subtaskRepoModelToEntity is _model_to_entity.
func (r *ORMSubtaskRepository) subtaskRepoModelToEntity(model *database.Subtask) (*entities.Subtask, error) {
	id, err := value_objects.NewTaskId(model.ID)
	if err != nil {
		return nil, err
	}
	parent, err := value_objects.NewTaskId(model.TaskID)
	if err != nil {
		return nil, err
	}
	status, err := value_objects.TaskStatusFromString(model.Status)
	if err != nil {
		return nil, err
	}
	priority, err := value_objects.PriorityFromString(model.Priority)
	if err != nil {
		return nil, err
	}
	assignees, err := subtaskRepoDecodeAssignees(model.Assignees)
	if err != nil {
		return nil, err
	}
	history, err := subtaskRepoDecodeHistory(model.ProgressHistory)
	if err != nil {
		return nil, err
	}
	acceptanceCriteria, err := repoDecodeStringList(model.AcceptanceCriteria)
	if err != nil {
		return nil, err
	}
	scope, err := repoDecodeStringList(model.Scope)
	if err != nil {
		return nil, err
	}
	createdAt, updatedAt := model.CreatedAt, model.UpdatedAt
	st := entities.Subtask{
		ID: &id, Title: model.Title, Description: model.Description, ParentTaskID: &parent,
		Status: &status, Priority: &priority, Assignees: assignees,
		AcceptanceCriteria: acceptanceCriteria, Scope: scope,
		ProgressPercentage: int(model.ProgressPercentage), ProgressHistory: history,
		ProgressCount: int(model.ProgressCount),
	}
	st.CreatedAt = &createdAt
	st.UpdatedAt = &updatedAt
	return entities.RestoreSubtask(st)
}

// subtaskRepoEntityToModelDict is _entity_to_model_dict; it raises ValueError when the
// repository has no user id.
func (r *ORMSubtaskRepository) subtaskRepoEntityToModelDict(subtask *entities.Subtask) (Kwargs, error) {
	assignees := []string{}
	for _, assignee := range subtask.Assignees {
		assignees = append(assignees, assignee)
	}
	if subtask.ParentTaskID == nil {
		return nil, &ValueError{Msg: "Subtask must have a parent task ID"}
	}
	status := "todo"
	if subtask.Status != nil {
		status = subtask.Status.Value
	}
	priority := "medium"
	if subtask.Priority != nil {
		priority = subtask.Priority.Value
	}
	modelData := NewKwargs(
		"task_id", subtask.ParentTaskID.Value,
		"title", subtask.Title,
		"description", subtask.Description,
		"status", status,
		"priority", priority,
		"assignees", assignees,
		"acceptance_criteria", append([]string{}, subtask.AcceptanceCriteria...),
		"scope", append([]string{}, subtask.Scope...),
		"progress_percentage", subtask.ProgressPercentage,
		"progress_history", subtask.ProgressHistory,
		"progress_count", subtask.ProgressCount,
		"created_at", subtask.CreatedAt,
		"updated_at", subtask.UpdatedAt,
	)
	if r.UserID == nil || *r.UserID == "" {
		return nil, &ValueError{Msg: "User authentication required. No user ID provided for subtask creation."}
	}
	modelData.Set("user_id", *r.UserID)
	return modelData, nil
}

// ---- save ----------------------------------------------------------------------

// Save persists a subtask. Python retries ten times with exponential backoff and returns False
// (no error) when every attempt fails, because the transaction context manager converts
// SQLAlchemyError into DatabaseException before save's except clause can see it.
func (r *ORMSubtaskRepository) Save(ctx context.Context, subtask *entities.Subtask) (bool, error) {
	const maxRetries = 10
	retryDelay := 20 * time.Millisecond
	for attempt := 0; attempt < maxRetries; attempt++ {
		ok, err := r.subtaskRepoSaveOnce(ctx, subtask)
		if err == nil {
			return ok, nil
		}
		if attempt < maxRetries-1 {
			time.Sleep(retryDelay * time.Duration(1<<attempt))
			continue
		}
		return false, nil
	}
	return false, nil
}

func (r *ORMSubtaskRepository) subtaskRepoSaveOnce(ctx context.Context, subtask *entities.Subtask) (bool, error) {
	saved := false
	err := r.Transaction(ctx, func(ctx context.Context) error {
		modelData, err := r.subtaskRepoEntityToModelDict(subtask)
		if err != nil {
			return err
		}
		return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
			id := ""
			if subtask.ID != nil {
				id = subtask.ID.Value
			}
			if id != "" {
				existing, err := r.ORMRepository.GetByID(ctx, id)
				if err != nil {
					return err
				}
				if existing != nil {
					if err := r.subtaskRepoUpdateExisting(ctx, s, id, modelData); err != nil {
						return err
					}
					now := database.TimestampNow().UTC()
					subtask.UpdatedAt = &now
					saved = true
					// Python returns early here, so domain events are not published on update.
					return nil
				}
				modelData.Set("id", id)
			} else {
				newID := value_objects.GenerateNewTaskId()
				subtask.ID = &newID
				modelData.Set("id", newID.Value)
			}
			row, err := r.insert(ctx, s, modelData)
			if err != nil {
				return err
			}
			createdAt, updatedAt := row.CreatedAt, row.UpdatedAt
			subtask.CreatedAt = &createdAt
			subtask.UpdatedAt = &updatedAt
			saved = true
			r.PublishEntityEvents(subtask)
			return nil
		})
	})
	if err != nil {
		return false, err
	}
	return saved, nil
}

// subtaskRepoUpdateExisting sets every model_data column except id, then applies the
// existing.touch("subtask_updated") timestamp. No user filter is applied, as in Python.
func (r *ORMSubtaskRepository) subtaskRepoUpdateExisting(ctx context.Context, s database.DBTX, id string, data Kwargs) error {
	var sets []string
	var args []any
	for _, attr := range data.Keys() {
		if attr == "id" || attr == "updated_at" {
			continue
		}
		pos, ok := r.byAttr[attr]
		if !ok {
			continue
		}
		column := r.Table.Columns[pos]
		v, _ := data.Get(attr)
		bv, err := bind(column, v)
		if err != nil {
			return err
		}
		args = append(args, bv)
		sets = append(sets, fmt.Sprintf("%s = $%d", quoteIdent(column.Name), len(args)))
	}
	now := database.TimestampNow().UTC()
	args = append(args, now)
	sets = append(sets, `"updated_at" = $`+strconv.Itoa(len(args)))
	idColumn := r.Table.Columns[r.byAttr["id"]]
	bv, err := bind(idColumn, id)
	if err != nil {
		return err
	}
	args = append(args, bv)
	q := fmt.Sprintf("UPDATE %s SET %s WHERE %s = $%d", quoteIdent(r.Table.Name), strings.Join(sets, ", "), r.pkColumn(), len(args))
	_, err = s.ExecContext(ctx, q, args...)
	return err
}

// ---- reads ---------------------------------------------------------------------

// FindByID is find_by_id (user filtered).
func (r *ORMSubtaskRepository) FindByID(ctx context.Context, id string) (*entities.Subtask, error) {
	var out *entities.Subtask
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{id}
		suffix := ` WHERE "id" = $1`
		if r.UserID != nil && *r.UserID != "" {
			args = append(args, *r.UserID)
			suffix += fmt.Sprintf(` AND "user_id" = $%d`, len(args))
		}
		suffix += " LIMIT 1"
		rows, err := r.selectRows(ctx, s, suffix, args...)
		if err != nil {
			return err
		}
		if len(rows) == 0 {
			return nil
		}
		entity, err := r.subtaskRepoModelToEntity(rows[0])
		if err != nil {
			return err
		}
		out = entity
		return nil
	})
	return out, err
}

// FindByParentTaskID is find_by_parent_task_id (user filtered, created_at ascending).
func (r *ORMSubtaskRepository) FindByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) ([]*entities.Subtask, error) {
	out := []*entities.Subtask{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{parentTaskID.Value}
		suffix := ` WHERE "task_id" = $1`
		if r.UserID != nil && *r.UserID != "" {
			args = append(args, *r.UserID)
			suffix += fmt.Sprintf(` AND "user_id" = $%d`, len(args))
		}
		suffix += ` ORDER BY "created_at" ASC`
		rows, err := r.selectRows(ctx, s, suffix, args...)
		if err != nil {
			return err
		}
		for _, row := range rows {
			if row == nil {
				continue
			}
			entity, err := r.subtaskRepoModelToEntity(row)
			if err != nil {
				return err
			}
			out = append(out, entity)
		}
		return nil
	})
	return out, err
}

// FindByAssignee is find_by_assignee. Python compares the JSON column with LIKE, which
// PostgreSQL rejects for json/jsonb; this port uses jsonb containment instead (deviation
// recorded in MIGRATION.md), so a plain name or an @seat_key matches by array membership.
func (r *ORMSubtaskRepository) FindByAssignee(ctx context.Context, assignee string) ([]*entities.Subtask, error) {
	pattern, err := value_objects.PyJSONDumps([]any{assignee}, -1)
	if err != nil {
		return nil, err
	}
	return r.subtaskRepoFindByAssigneeQuery(ctx, pattern, "created_at", true)
}

// subtaskRepoFindByAssigneeQuery runs the shared assignee containment query (user filter optional).
func (r *ORMSubtaskRepository) subtaskRepoFindByAssigneeQuery(ctx context.Context, pattern, orderColumn string, userScoped bool) ([]*entities.Subtask, error) {
	out := []*entities.Subtask{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{pattern}
		suffix := ` WHERE "assignees"::jsonb @> $1::jsonb`
		if userScoped && r.UserID != nil && *r.UserID != "" {
			args = append(args, *r.UserID)
			suffix += fmt.Sprintf(` AND "user_id" = $%d`, len(args))
		}
		suffix += fmt.Sprintf(` ORDER BY %s DESC`, quoteIdent(orderColumn))
		rows, err := r.selectRows(ctx, s, suffix, args...)
		if err != nil {
			return err
		}
		for _, row := range rows {
			if row == nil {
				continue
			}
			entity, err := r.subtaskRepoModelToEntity(row)
			if err != nil {
				return err
			}
			out = append(out, entity)
		}
		return nil
	})
	return out, err
}

// FindByStatus is find_by_status (user filtered, created_at descending).
func (r *ORMSubtaskRepository) FindByStatus(ctx context.Context, status string) ([]*entities.Subtask, error) {
	out := []*entities.Subtask{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{status}
		suffix := ` WHERE "status" = $1`
		if r.UserID != nil && *r.UserID != "" {
			args = append(args, *r.UserID)
			suffix += fmt.Sprintf(` AND "user_id" = $%d`, len(args))
		}
		suffix += ` ORDER BY "created_at" DESC`
		rows, err := r.selectRows(ctx, s, suffix, args...)
		if err != nil {
			return err
		}
		for _, row := range rows {
			if row == nil {
				continue
			}
			entity, err := r.subtaskRepoModelToEntity(row)
			if err != nil {
				return err
			}
			out = append(out, entity)
		}
		return nil
	})
	return out, err
}

// FindCompleted is find_completed (user filtered, completed_at descending).
func (r *ORMSubtaskRepository) FindCompleted(ctx context.Context, parentTaskID value_objects.TaskId) ([]*entities.Subtask, error) {
	return r.subtaskRepoFindByTaskAndFilter(ctx, parentTaskID.Value, `"status" = 'done'`, `"completed_at" DESC`)
}

// FindPending is find_pending (user filtered, created_at ascending).
func (r *ORMSubtaskRepository) FindPending(ctx context.Context, parentTaskID value_objects.TaskId) ([]*entities.Subtask, error) {
	return r.subtaskRepoFindByTaskAndFilter(ctx, parentTaskID.Value, `"status" IN ('todo', 'in_progress', 'blocked')`, `"created_at" ASC`)
}

func (r *ORMSubtaskRepository) subtaskRepoFindByTaskAndFilter(ctx context.Context, taskID, condition, order string) ([]*entities.Subtask, error) {
	out := []*entities.Subtask{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{taskID}
		suffix := ` WHERE "task_id" = $1 AND ` + condition
		if r.UserID != nil && *r.UserID != "" {
			args = append(args, *r.UserID)
			suffix += fmt.Sprintf(` AND "user_id" = $%d`, len(args))
		}
		suffix += ` ORDER BY ` + order
		rows, err := r.selectRows(ctx, s, suffix, args...)
		if err != nil {
			return err
		}
		for _, row := range rows {
			if row == nil {
				continue
			}
			entity, err := r.subtaskRepoModelToEntity(row)
			if err != nil {
				return err
			}
			out = append(out, entity)
		}
		return nil
	})
	return out, err
}

// Delete is delete (user filtered).
func (r *ORMSubtaskRepository) Delete(ctx context.Context, id string) (bool, error) {
	deleted := false
	err := r.Transaction(ctx, func(ctx context.Context) error {
		return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
			args := []any{id}
			condition := `"id" = $1`
			if r.UserID != nil && *r.UserID != "" {
				args = append(args, *r.UserID)
				condition += fmt.Sprintf(` AND "user_id" = $%d`, len(args))
			}
			res, err := s.ExecContext(ctx, fmt.Sprintf("DELETE FROM %s WHERE %s", quoteIdent(r.Table.Name), condition), args...)
			if err != nil {
				return err
			}
			n, _ := res.RowsAffected()
			deleted = n > 0
			return nil
		})
	})
	return deleted, err
}

// DeleteByParentTaskID is delete_by_parent_task_id (no user filter, no transaction).
func (r *ORMSubtaskRepository) DeleteByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) (bool, error) {
	deleted := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		res, err := s.ExecContext(ctx, fmt.Sprintf("DELETE FROM %s WHERE %s = $1", quoteIdent(r.Table.Name), quoteIdent("task_id")), parentTaskID.Value)
		if err != nil {
			return err
		}
		n, _ := res.RowsAffected()
		deleted = n > 0
		return nil
	})
	return deleted, err
}

// Exists is exists (user filtered).
func (r *ORMSubtaskRepository) Exists(ctx context.Context, id string) (bool, error) {
	exists := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{id}
		condition := `"id" = $1`
		if r.UserID != nil && *r.UserID != "" {
			args = append(args, *r.UserID)
			condition += fmt.Sprintf(` AND "user_id" = $%d`, len(args))
		}
		var one int
		err := s.QueryRowContext(ctx, fmt.Sprintf(`SELECT 1 FROM %s WHERE %s LIMIT 1`, quoteIdent(r.Table.Name), condition), args...).Scan(&one)
		if err == sql.ErrNoRows {
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

// CountByParentTaskID is count_by_parent_task_id (no user filter).
func (r *ORMSubtaskRepository) CountByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) (int, error) {
	return r.ORMRepository.Count(ctx, NewKwargs("task_id", parentTaskID.Value))
}

// CountCompletedByParentTaskID is count_completed_by_parent_task_id (no user filter).
func (r *ORMSubtaskRepository) CountCompletedByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) (int, error) {
	return r.ORMRepository.Count(ctx, NewKwargs("task_id", parentTaskID.Value, "status", "done"))
}

// GetNextID is get_next_id: always a fresh UUID, the parent id is ignored.
func (r *ORMSubtaskRepository) GetNextID(ctx context.Context, parentTaskID value_objects.TaskId) (value_objects.TaskId, error) {
	return value_objects.GenerateNewTaskId(), nil
}

// GetSubtaskProgress is get_subtask_progress.
func (r *ORMSubtaskRepository) GetSubtaskProgress(ctx context.Context, parentTaskID value_objects.TaskId) (map[string]any, error) {
	var total, completed, inProgress, blocked int64
	var avg sql.NullFloat64
	query := `SELECT count(*), count(*) FILTER (WHERE "status" = 'done'), ` +
		`count(*) FILTER (WHERE "status" = 'in_progress'), count(*) FILTER (WHERE "status" = 'blocked'), ` +
		`avg("progress_percentage")::double precision FROM ` + quoteIdent(r.Table.Name) + ` WHERE "task_id" = $1`
	if err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, query, parentTaskID.Value).Scan(&total, &completed, &inProgress, &blocked, &avg)
	}); err != nil {
		return nil, err
	}
	var completionPercentage any
	if total > 0 {
		completionPercentage = value_objects.PyRound(float64(completed)/float64(total)*100, 1)
	} else {
		completionPercentage = 0
	}
	avgProgress := 0.0
	if avg.Valid {
		avgProgress = avg.Float64
	}
	return map[string]any{
		"total_subtasks":        int(total),
		"completed_subtasks":    int(completed),
		"in_progress_subtasks":  int(inProgress),
		"blocked_subtasks":      int(blocked),
		"pending_subtasks":      int(total - completed - inProgress - blocked),
		"completion_percentage": completionPercentage,
		"average_progress":      value_objects.PyRound(avgProgress, 1),
		"has_blockers":          blocked > 0,
	}, nil
}

// BulkUpdateStatus is bulk_update_status (no user filter, no updated_at change: SQLAlchemy's
// Query.update does not fire mapper-level timestamp events).
func (r *ORMSubtaskRepository) BulkUpdateStatus(ctx context.Context, parentTaskID value_objects.TaskId, status string) (bool, error) {
	updated := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		sets := []string{`"status" = $1`}
		args := []any{status}
		if status == "done" {
			sets = append(sets, `"progress_percentage" = 100`)
		} else if status == "todo" || status == "in_progress" || status == "blocked" {
			sets = append(sets, `"completed_at" = NULL`)
		}
		args = append(args, parentTaskID.Value)
		q := fmt.Sprintf("UPDATE %s SET %s WHERE %s = $%d", quoteIdent(r.Table.Name), strings.Join(sets, ", "), quoteIdent("task_id"), len(args))
		res, err := s.ExecContext(ctx, q, args...)
		if err != nil {
			return err
		}
		n, _ := res.RowsAffected()
		updated = n > 0
		return nil
	})
	return updated, err
}

// BulkComplete is bulk_complete.
func (r *ORMSubtaskRepository) BulkComplete(ctx context.Context, parentTaskID value_objects.TaskId) (bool, error) {
	return r.BulkUpdateStatus(ctx, parentTaskID, "done")
}

// RemoveSubtask is remove_subtask (no user filter).
func (r *ORMSubtaskRepository) RemoveSubtask(ctx context.Context, parentTaskID, subtaskID string) (bool, error) {
	removed := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		res, err := s.ExecContext(ctx,
			fmt.Sprintf("DELETE FROM %s WHERE %s = $1 AND %s = $2", quoteIdent(r.Table.Name), quoteIdent("task_id"), quoteIdent("id")),
			parentTaskID, subtaskID)
		if err != nil {
			return err
		}
		n, _ := res.RowsAffected()
		removed = n > 0
		return nil
	})
	return removed, err
}

// UpdateProgress is update_progress (user filtered, no updated_at change).
func (r *ORMSubtaskRepository) UpdateProgress(ctx context.Context, subtaskID string, progressPercentage int, progressNotes string) (bool, error) {
	updated := false
	err := r.Transaction(ctx, func(ctx context.Context) error {
		return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
			progress := progressPercentage
			if progress < 0 {
				progress = 0
			}
			if progress > 100 {
				progress = 100
			}
			args := []any{progress, progressNotes, subtaskID}
			condition := `"id" = $3`
			if r.UserID != nil && *r.UserID != "" {
				args = append(args, *r.UserID)
				condition += fmt.Sprintf(` AND "user_id" = $%d`, len(args))
			}
			q := fmt.Sprintf(`UPDATE %s SET "progress_percentage" = $1, "progress_notes" = $2 WHERE %s`, quoteIdent(r.Table.Name), condition)
			res, err := s.ExecContext(ctx, q, args...)
			if err != nil {
				return err
			}
			n, _ := res.RowsAffected()
			updated = n > 0
			return nil
		})
	})
	return updated, err
}

// CompleteSubtask is complete_subtask (user filtered, no updated_at change).
func (r *ORMSubtaskRepository) CompleteSubtask(ctx context.Context, subtaskID, completionSummary, impactOnParent string, insightsFound []string) (bool, error) {
	completed := false
	err := r.Transaction(ctx, func(ctx context.Context) error {
		return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
			sets := []string{`"status" = 'done'`, `"progress_percentage" = 100`}
			args := []any{}
			args = append(args, completionSummary)
			sets = append(sets, fmt.Sprintf(`"completion_summary" = $%d`, len(args)))
			args = append(args, impactOnParent)
			sets = append(sets, fmt.Sprintf(`"impact_on_parent" = $%d`, len(args)))
			if len(insightsFound) > 0 {
				encoded, err := value_objects.PyJSONDumps(insightsFound, -1)
				if err != nil {
					return err
				}
				args = append(args, encoded)
				sets = append(sets, fmt.Sprintf(`"insights_found" = $%d::json`, len(args)))
			}
			args = append(args, subtaskID)
			condition := fmt.Sprintf(`"id" = $%d`, len(args))
			if r.UserID != nil && *r.UserID != "" {
				args = append(args, *r.UserID)
				condition += fmt.Sprintf(` AND "user_id" = $%d`, len(args))
			}
			q := fmt.Sprintf("UPDATE %s SET %s WHERE %s", quoteIdent(r.Table.Name), strings.Join(sets, ", "), condition)
			res, err := s.ExecContext(ctx, q, args...)
			if err != nil {
				return err
			}
			n, _ := res.RowsAffected()
			completed = n > 0
			return nil
		})
	})
	return completed, err
}

// GetSubtasksByAssignee is get_subtasks_by_assignee (no user filter, updated_at descending);
// it uses the same jsonb containment as FindByAssignee (deviation recorded in MIGRATION.md).
func (r *ORMSubtaskRepository) GetSubtasksByAssignee(ctx context.Context, assignee string, limit *int) ([]*entities.Subtask, error) {
	pattern, err := value_objects.PyJSONDumps([]any{assignee}, -1)
	if err != nil {
		return nil, err
	}
	out := []*entities.Subtask{}
	err = r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		suffix := ` WHERE "assignees"::jsonb @> $1::jsonb ORDER BY "updated_at" DESC`
		if limit != nil && *limit != 0 {
			suffix += fmt.Sprintf(" LIMIT %d", *limit)
		}
		rows, err := r.selectRows(ctx, s, suffix, pattern)
		if err != nil {
			return err
		}
		for _, row := range rows {
			if row == nil {
				continue
			}
			entity, err := r.subtaskRepoModelToEntity(row)
			if err != nil {
				return err
			}
			out = append(out, entity)
		}
		return nil
	})
	return out, err
}

// ---- decoding helpers ----------------------------------------------------------

func subtaskRepoDecodeAssignees(raw json.RawMessage) ([]string, error) {
	if len(raw) == 0 {
		return []string{}, nil
	}
	decoded, err := entities.DecodeJSON(raw)
	if err != nil {
		return nil, err
	}
	if decoded == nil {
		return []string{}, nil
	}
	list, ok := decoded.([]any)
	if !ok {
		return []string{}, nil
	}
	out := []string{}
	for _, item := range list {
		if s, ok := item.(string); ok {
			out = append(out, s)
		} else {
			out = append(out, value_objects.PyStr(item))
		}
	}
	return out, nil
}

func subtaskRepoDecodeHistory(raw json.RawMessage) (map[string]any, error) {
	if len(raw) == 0 {
		return map[string]any{}, nil
	}
	decoded, err := entities.DecodeJSON(raw)
	if err != nil {
		return nil, err
	}
	ordered, ok := decoded.(*entities.OrderedMap[any])
	if !ok || ordered.Len() == 0 {
		return map[string]any{}, nil
	}
	out := map[string]any{}
	for _, key := range ordered.Keys() {
		value, _ := ordered.Get(key)
		out[key] = repoPlainValue(value)
	}
	return out, nil
}
