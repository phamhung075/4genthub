package repositories

// ORM Label Repository (Python infrastructure/repositories/orm/label_repository.py):
// CRUD for labels and their task relationships.
//
// Python's LabelEntity.id is annotated `int`, but the repository stores and returns the
// labels.id UUID string (create_label does `id=str(uuid.uuid4())`). Go's entities.Label.ID
// is an int and cannot carry that value, so this module returns ORMLabelEntity: the same
// fields with a string id (entities.Label is otherwise reused for validation).

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// ORMLabelEntity is the Label domain entity as the ORM repository returns it. It mirrors
// entities.Label (id, name, color, description, created_at, updated_at); only the id type
// differs (string here, int there) because labels.id is a UUID string.
type ORMLabelEntity struct {
	ID          string
	Name        string
	Color       string
	Description string
	CreatedAt   time.Time
	UpdatedAt   time.Time
}

// ORMLabelRepository is ORMLabelRepository(db_adapter); UserID plays the role of the
// dynamically attached `user_id` attribute Python reads with getattr.
type ORMLabelRepository struct {
	*ORMRepository[database.Label]
	UserID *string
}

// NewORMLabelRepository builds the repository; a nil userID is Python's missing user_id.
func NewORMLabelRepository(sessions *database.SessionManager, userID *string) (*ORMLabelRepository, error) {
	base, err := NewORMRepository[database.Label]("labels", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMLabelRepository{ORMRepository: base, UserID: userID}, nil
}

// labelRepoEntity is _model_to_entity: LabelEntity(...) runs the base entity's timestamp
// cleanup and validation, so conversion errors propagate exactly as Python's constructor.
func labelRepoEntity(row *database.Label) (*ORMLabelEntity, error) {
	l := &entities.Label{Name: row.Name, Color: row.Color, Description: row.Description}
	c, u := row.CreatedAt, row.UpdatedAt
	l.CreatedAt, l.UpdatedAt = &c, &u
	if err := l.Init(l); err != nil {
		return nil, err
	}
	return &ORMLabelEntity{
		ID: row.ID, Name: l.Name, Color: l.Color, Description: l.Description,
		CreatedAt: *l.CreatedAt, UpdatedAt: *l.UpdatedAt,
	}, nil
}

func labelRepoCreateIntegrity(msg, name string) error {
	lower := strings.ToLower(msg)
	switch {
	case strings.Contains(msg, "created_at") || strings.Contains(msg, "updated_at"):
		return exceptions.NewRepositoryError(
			"Label creation failed due to timestamp constraint violation. "+
				"Timestamps must be timezone-aware UTC datetime objects. "+
				"Use datetime.now(UTC) instead of datetime.now(). "+
				"Technical details: "+msg, "")
	case strings.Contains(msg, "user_id"):
		return exceptions.NewRepositoryError(
			"Label creation failed: user_id is required and must reference a valid user. "+
				"Ensure authentication context is properly set. "+
				"Technical details: "+msg, "")
	case strings.Contains(lower, "unique") || strings.Contains(lower, "duplicate"):
		return exceptions.NewValidationError(
			fmt.Sprintf("Label with name '%s' already exists. Use a different name or update the existing label.", name), "", nil)
	default:
		return exceptions.NewRepositoryError(
			"Label creation failed due to database constraint violation. "+
				"Ensure all required fields (name, created_at, updated_at, user_id) are provided correctly. "+
				"Technical details: "+msg, "")
	}
}

func labelRepoAssignIntegrity(msg, taskID, labelID string) error {
	lower := strings.ToLower(msg)
	switch {
	case strings.Contains(msg, "user_id"):
		return exceptions.NewRepositoryError(
			"Failed to assign label to task: user_id is required. "+
				"Ensure authentication context is properly set. "+
				"Technical details: "+msg, "")
	case strings.Contains(lower, "foreign key"):
		return exceptions.NewRepositoryError(
			fmt.Sprintf("Failed to assign label to task: Invalid task_id or label_id reference. "+
				"Ensure both task (ID: %s) and label (ID: %s) exist. Technical details: %s", taskID, labelID, msg), "")
	default:
		return exceptions.NewRepositoryError(
			fmt.Sprintf("Failed to assign label to task due to database constraint. "+
				"Task ID: %s, Label ID: %s. Technical details: %s", taskID, labelID, msg), "")
	}
}

// CreateLabel is create_label. An empty color takes the Python default "#0066cc" (an
// explicit "" cannot be distinguished from omitted).
func (r *ORMLabelRepository) CreateLabel(ctx context.Context, name, color, description string) (*ORMLabelEntity, error) {
	if color == "" {
		color = "#0066cc"
	}
	var out *ORMLabelEntity
	err := r.Transaction(ctx, func(ctx context.Context) error {
		existing, err := r.FindOneBy(ctx, NewKwargs("name", name))
		if err != nil {
			return err
		}
		if existing != nil {
			return exceptions.NewValidationError(fmt.Sprintf("Label with name '%s' already exists", name), "", nil)
		}
		if r.UserID == nil {
			return &value_objects.ValueError{Msg: "user_id is required for label creation"}
		}
		id := value_objects.NewUUIDv4()
		createdAt, updatedAt := Now(), Now()
		var row database.Label
		err = r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
			_, err := s.ExecContext(ctx,
				`INSERT INTO labels (id, name, color, description, user_id, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, $7)`,
				id, name, color, description, *r.UserID, createdAt, updatedAt)
			if err != nil {
				if database.IsIntegrityError(err) {
					return labelRepoCreateIntegrity(err.Error(), name)
				}
				return err
			}
			return s.QueryRowContext(ctx,
				`SELECT id, name, color, description, user_id, created_at, updated_at FROM labels WHERE id = $1`, id).
				Scan(&row.ID, &row.Name, &row.Color, &row.Description, &row.UserID, &row.CreatedAt, &row.UpdatedAt)
		})
		if err != nil {
			return err
		}
		out, err = labelRepoEntity(&row)
		return err
	})
	return out, err
}

// GetLabel is get_label.
func (r *ORMLabelRepository) GetLabel(ctx context.Context, labelID string) (*ORMLabelEntity, error) {
	row, err := r.FindOneBy(ctx, NewKwargs("id", labelID))
	if err != nil || row == nil {
		return nil, err
	}
	return labelRepoEntity(row)
}

// GetLabelByName is get_label_by_name.
func (r *ORMLabelRepository) GetLabelByName(ctx context.Context, name string) (*ORMLabelEntity, error) {
	row, err := r.FindOneBy(ctx, NewKwargs("name", name))
	if err != nil || row == nil {
		return nil, err
	}
	return labelRepoEntity(row)
}

// UpdateLabel is update_label; nil parameters mean "leave unchanged".
func (r *ORMLabelRepository) UpdateLabel(ctx context.Context, labelID string, name, color, description *string) (*ORMLabelEntity, error) {
	var out *ORMLabelEntity
	err := r.Transaction(ctx, func(ctx context.Context) error {
		cur, err := r.ORMRepository.GetByID(ctx, labelID)
		if err != nil {
			return err
		}
		if cur == nil {
			return exceptions.NewNotFoundError("Label", labelID, "")
		}
		if name != nil && *name != "" && *name != cur.Name {
			existing, err := r.FindOneBy(ctx, NewKwargs("name", *name))
			if err != nil {
				return err
			}
			if existing != nil {
				return exceptions.NewValidationError(fmt.Sprintf("Label with name '%s' already exists", *name), "", nil)
			}
		}
		newName, newColor, newDesc := cur.Name, cur.Color, cur.Description
		if name != nil {
			newName = *name
		}
		if color != nil {
			newColor = *color
		}
		if description != nil {
			newDesc = *description
		}
		check := &entities.Label{Name: newName, Color: newColor}
		if err := check.ValidateEntity(); err != nil {
			return err
		}
		if newName == cur.Name && newColor == cur.Color && newDesc == cur.Description {
			out, err = labelRepoEntity(cur)
			return err
		}
		row, err := r.ORMRepository.Update(ctx, labelID, NewKwargs(
			"name", newName, "color", newColor, "description", newDesc, "updated_at", Now()))
		if err != nil {
			return err
		}
		out, err = labelRepoEntity(row)
		return err
	})
	return out, err
}

// DeleteLabel is delete_label.
func (r *ORMLabelRepository) DeleteLabel(ctx context.Context, labelID string) (bool, error) {
	return r.ORMRepository.Delete(ctx, labelID)
}

// ListLabels is list_labels; limit/offset are only applied when truthy (non-zero).
func (r *ORMLabelRepository) ListLabels(ctx context.Context, limit, offset *int) ([]*ORMLabelEntity, error) {
	out := []*ORMLabelEntity{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		suffix := ` ORDER BY "name" ASC`
		if limit != nil && *limit != 0 {
			suffix += fmt.Sprintf(" LIMIT %d", *limit)
		}
		if offset != nil && *offset != 0 {
			suffix += fmt.Sprintf(" OFFSET %d", *offset)
		}
		rows, err := r.selectRows(ctx, s, suffix)
		if err != nil {
			return err
		}
		for _, row := range rows {
			e, err := labelRepoEntity(row)
			if err != nil {
				return err
			}
			out = append(out, e)
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// AssignLabelToTask is assign_label_to_task; it returns false when already assigned.
func (r *ORMLabelRepository) AssignLabelToTask(ctx context.Context, taskID, labelID string) (bool, error) {
	assigned := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var one int
		err := s.QueryRowContext(ctx, `SELECT 1 FROM tasks WHERE id = $1::uuid`, taskID).Scan(&one)
		if errors.Is(err, sql.ErrNoRows) {
			return exceptions.NewNotFoundError("Task", taskID, "")
		}
		if err != nil {
			return err
		}
		err = s.QueryRowContext(ctx, `SELECT 1 FROM labels WHERE id = $1`, labelID).Scan(&one)
		if errors.Is(err, sql.ErrNoRows) {
			return exceptions.NewNotFoundError("Label", labelID, "")
		}
		if err != nil {
			return err
		}
		err = s.QueryRowContext(ctx, `SELECT 1 FROM task_labels WHERE task_id = $1::uuid AND label_id = $2`, taskID, labelID).Scan(&one)
		if err == nil {
			return nil // already assigned
		}
		if !errors.Is(err, sql.ErrNoRows) {
			return err
		}
		if r.UserID == nil {
			return &value_objects.ValueError{Msg: "user_id is required for task label assignment"}
		}
		if _, err := s.ExecContext(ctx,
			`INSERT INTO task_labels (task_id, label_id, user_id, applied_at) VALUES ($1::uuid, $2, $3, $4)`,
			taskID, labelID, *r.UserID, Now()); err != nil {
			if database.IsIntegrityError(err) {
				return labelRepoAssignIntegrity(err.Error(), taskID, labelID)
			}
			return err
		}
		assigned = true
		return nil
	})
	return assigned, err
}

// RemoveLabelFromTask is remove_label_from_task; it returns false when not assigned.
func (r *ORMLabelRepository) RemoveLabelFromTask(ctx context.Context, taskID, labelID string) (bool, error) {
	removed := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		res, err := s.ExecContext(ctx, `DELETE FROM task_labels WHERE task_id = $1::uuid AND label_id = $2`, taskID, labelID)
		if err != nil {
			return err
		}
		n, _ := res.RowsAffected()
		removed = n > 0
		return nil
	})
	return removed, err
}

// labelRepoTaskEntity is _task_model_to_entity: the Python entity receives the raw status
// and priority strings, which the TaskStatus/Priority value objects carry verbatim.
func labelRepoTaskEntity(row *database.Task) (*entities.Task, error) {
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
		GitBranchID: &row.GitBranchID, Status: &status, Priority: &priority,
		EstimatedEffort: row.EstimatedEffort, DueDate: row.DueDate,
		ContextID: row.ContextID,
	})
}

// GetTasksByLabel is get_tasks_by_label.
func (r *ORMLabelRepository) GetTasksByLabel(ctx context.Context, labelID string) ([]*entities.Task, error) {
	out := []*entities.Task{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var one int
		err := s.QueryRowContext(ctx, `SELECT 1 FROM labels WHERE id = $1`, labelID).Scan(&one)
		if errors.Is(err, sql.ErrNoRows) {
			return exceptions.NewNotFoundError("Label", labelID, "")
		}
		if err != nil {
			return err
		}
		rows, err := s.QueryContext(ctx,
			`SELECT t.id::text, t.title, t.description, t.git_branch_id::text, t.status, t.priority, t.estimated_effort, t.due_date, t.created_at, t.updated_at, t.context_id::text
			 FROM tasks t JOIN task_labels tl ON t.id = tl.task_id WHERE tl.label_id = $1`, labelID)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var row database.Task
			if err := rows.Scan(&row.ID, &row.Title, &row.Description, &row.GitBranchID, &row.Status, &row.Priority,
				&row.EstimatedEffort, &row.DueDate, &row.CreatedAt, &row.UpdatedAt, &row.ContextID); err != nil {
				return err
			}
			e, err := labelRepoTaskEntity(&row)
			if err != nil {
				return err
			}
			out = append(out, e)
		}
		return rows.Err()
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// GetLabelsByTask is get_labels_by_task.
func (r *ORMLabelRepository) GetLabelsByTask(ctx context.Context, taskID string) ([]*ORMLabelEntity, error) {
	out := []*ORMLabelEntity{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var one int
		err := s.QueryRowContext(ctx, `SELECT 1 FROM tasks WHERE id = $1::uuid`, taskID).Scan(&one)
		if errors.Is(err, sql.ErrNoRows) {
			return exceptions.NewNotFoundError("Task", taskID, "")
		}
		if err != nil {
			return err
		}
		rows, err := s.QueryContext(ctx,
			`SELECT l.id, l.name, l.color, l.description, l.created_at, l.updated_at
			 FROM labels l JOIN task_labels tl ON l.id = tl.label_id WHERE tl.task_id = $1::uuid`, taskID)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			row := &database.Label{}
			if err := rows.Scan(&row.ID, &row.Name, &row.Color, &row.Description, &row.CreatedAt, &row.UpdatedAt); err != nil {
				return err
			}
			e, err := labelRepoEntity(row)
			if err != nil {
				return err
			}
			out = append(out, e)
		}
		return rows.Err()
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}
