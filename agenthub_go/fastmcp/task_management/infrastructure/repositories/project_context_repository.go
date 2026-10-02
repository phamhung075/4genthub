package repositories

// Project Context Repository (Python infrastructure/repositories/project_context_repository.py):
// persistence for the unified project-level context (project_contexts table). The
// CacheInvalidationMixin side effects are dropped like logging.

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// ProjectContextRepository is Python's ProjectContextRepository.
type ProjectContextRepository struct {
	*ORMRepository[database.ProjectContext]
	UserID *string
}

// NewProjectContextRepository builds the repository. The Python session_factory maps to the
// SessionManager.
func NewProjectContextRepository(sessions *database.SessionManager, userID *string) (*ProjectContextRepository, error) {
	base, err := NewORMRepository[database.ProjectContext]("project_contexts", sessions)
	if err != nil {
		return nil, err
	}
	return &ProjectContextRepository{ORMRepository: base, UserID: userID}, nil
}

// WithUser returns a new repository instance scoped to userID (with_user).
func (r *ProjectContextRepository) WithUser(userID string) *ProjectContextRepository {
	return &ProjectContextRepository{ORMRepository: r.ORMRepository, UserID: &userID}
}

// projectContextUserFilter is the user-scoping filter (empty when no user).
func (r *ProjectContextRepository) projectContextUserFilter() Kwargs {
	if r.UserID == nil {
		return NewKwargs()
	}
	return NewKwargs("user_id", *r.UserID)
}

// Create inserts a new project context; an existing id raises ValueError.
func (r *ProjectContextRepository) Create(ctx context.Context, entity *entities.ProjectContext) (*entities.ProjectContext, error) {
	var out *entities.ProjectContext
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		existing, err := r.ORMRepository.getByID(ctx, s, entity.ID)
		if err != nil {
			return err
		}
		if existing != nil {
			return &tmvo.ValueError{Msg: "Project context already exists: " + entity.ID}
		}
		kwargs := NewKwargs(
			"id", entity.ID,
			"project_id", entity.ID,
			"project_info", projectContextJSONOrEmpty(entity.ProjectInfo),
			"team_preferences", projectContextJSONOrEmpty(entity.TeamPreferences),
			"technology_stack", projectContextJSONOrEmpty(entity.TechnologyStack),
			"project_workflow", projectContextJSONOrEmpty(entity.ProjectWorkflow),
			"local_standards", projectContextJSONOrEmpty(entity.LocalStandards),
			"project_settings", projectContextJSONOrEmpty(entity.ProjectSettings),
			"technical_specifications", projectContextJSONOrEmpty(entity.TechnicalSpecifications),
			"global_overrides", projectContextMetadataValue(entity.Metadata, "global_overrides"),
			"delegation_rules", projectContextMetadataValue(entity.Metadata, "delegation_rules"),
			"user_id", r.UserID,
		)
		row, err := r.ORMRepository.insert(ctx, s, kwargs)
		if err != nil {
			return err
		}
		out = projectContextToEntity(row)
		return nil
	})
	return out, err
}

// Get returns the project context by id (optionally user-filtered), or nil.
func (r *ProjectContextRepository) Get(ctx context.Context, contextID string) (*entities.ProjectContext, error) {
	var out *entities.ProjectContext
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		filters := NewKwargs("id", contextID)
		if r.UserID != nil {
			filters.Set("user_id", *r.UserID)
		}
		w, args, err := r.where(filters, 1)
		if err != nil {
			return err
		}
		rows, err := r.selectRows(ctx, s, w+" LIMIT 1", args...)
		if err != nil {
			return err
		}
		if len(rows) > 0 {
			out = projectContextToEntity(rows[0])
		}
		return nil
	})
	return out, err
}

// Update replaces the mutable fields of the project context; a missing row raises ValueError.
func (r *ProjectContextRepository) Update(ctx context.Context, contextID string, entity *entities.ProjectContext) (*entities.ProjectContext, error) {
	var out *entities.ProjectContext
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.ORMRepository.getByID(ctx, s, contextID)
		if err != nil {
			return err
		}
		if row == nil {
			return &tmvo.ValueError{Msg: "Project context not found: " + contextID}
		}
		values := NewKwargs(
			"project_info", projectContextJSONOrEmpty(entity.ProjectInfo),
			"team_preferences", projectContextJSONOrEmpty(entity.TeamPreferences),
			"technology_stack", projectContextJSONOrEmpty(entity.TechnologyStack),
			"project_workflow", projectContextJSONOrEmpty(entity.ProjectWorkflow),
			"local_standards", projectContextJSONOrEmpty(entity.LocalStandards),
			"project_settings", projectContextJSONOrEmpty(entity.ProjectSettings),
			"technical_specifications", projectContextJSONOrEmpty(entity.TechnicalSpecifications),
			"global_overrides", projectContextMetadataValue(entity.Metadata, "global_overrides"),
			"delegation_rules", projectContextMetadataValue(entity.Metadata, "delegation_rules"),
		)
		var sets []string
		var args []any
		for _, attr := range values.Keys() {
			pos := r.byAttr[attr]
			c := r.Table.Columns[pos]
			v, _ := values.Get(attr)
			bv, err := bind(c, v)
			if err != nil {
				return err
			}
			args = append(args, bv)
			sets = append(sets, fmt.Sprintf("%s = $%d", quoteIdent(c.Name), len(args)))
		}
		pk := r.Table.Columns[r.byAttr[r.pkAttr]]
		pkv, err := bind(pk, contextID)
		if err != nil {
			return err
		}
		args = append(args, pkv)
		updated := r.newRow()
		q := fmt.Sprintf("UPDATE %s SET %s WHERE %s = $%d RETURNING %s",
			quoteIdent(r.Table.Name), strings.Join(sets, ", "), r.pkColumn(), len(args), r.selectList())
		if err := s.QueryRowContext(ctx, q, args...).Scan(r.scanDest(updated)...); err != nil {
			return err
		}
		out = projectContextToEntity(updated)
		return nil
	})
	return out, err
}

// Delete removes the project context and reports whether it existed.
func (r *ProjectContextRepository) Delete(ctx context.Context, contextID string) (bool, error) {
	deleted := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.ORMRepository.getByID(ctx, s, contextID)
		if err != nil {
			return err
		}
		if row == nil {
			return nil
		}
		pk := r.Table.Columns[r.byAttr[r.pkAttr]]
		bv, err := bind(pk, contextID)
		if err != nil {
			return err
		}
		res, err := s.ExecContext(ctx, fmt.Sprintf("DELETE FROM %s WHERE %s = $1", quoteIdent(r.Table.Name), r.pkColumn()), bv)
		if err != nil {
			return err
		}
		n, _ := res.RowsAffected()
		deleted = n > 0
		return nil
	})
	return deleted, err
}

// List returns the project contexts, optionally filtered by project_id.
func (r *ProjectContextRepository) List(ctx context.Context, filters Kwargs) ([]*entities.ProjectContext, error) {
	var out []*entities.ProjectContext
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		where := r.projectContextUserFilter()
		if filters != nil {
			if v, ok := filters.Get("project_id"); ok {
				where.Set("project_id", v)
			}
		}
		w, args, err := r.where(where, 1)
		if err != nil {
			return err
		}
		rows, err := r.selectRows(ctx, s, w, args...)
		if err != nil {
			return err
		}
		out = make([]*entities.ProjectContext, 0, len(rows))
		for _, row := range rows {
			out = append(out, projectContextToEntity(row))
		}
		return nil
	})
	return out, err
}

// projectContextToEntity is _to_entity; note it uses project_id (not id) as the entity id.
func projectContextToEntity(row *database.ProjectContext) *entities.ProjectContext {
	projectInfo := projectContextJSONMap(row.ProjectInfo)
	projectName := "Project-" + projectContextProjectID(row.ProjectID)
	if v, ok := projectInfo["name"]; ok {
		if s, ok := v.(string); ok {
			projectName = s
		}
	}
	id := ""
	if row.ProjectID != nil {
		id = *row.ProjectID
	}
	metadata := map[string]any{
		"global_overrides": projectContextJSONMap(row.GlobalOverrides),
		"delegation_rules": projectContextJSONMap(row.DelegationRules),
		"created_at":       nil,
		"updated_at":       nil,
		"version":          row.Version,
	}
	if row.CreatedAt != nil {
		metadata["created_at"] = tmvo.IsoFormatNaive(*row.CreatedAt)
	}
	if row.UpdatedAt != nil {
		metadata["updated_at"] = tmvo.IsoFormatNaive(*row.UpdatedAt)
	}
	return &entities.ProjectContext{
		ID:                      id,
		ProjectName:             projectName,
		ProjectInfo:             projectInfo,
		TeamPreferences:         projectContextJSONMap(row.TeamPreferences),
		TechnologyStack:         projectContextJSONMap(row.TechnologyStack),
		ProjectWorkflow:         projectContextJSONMap(row.ProjectWorkflow),
		LocalStandards:          projectContextJSONMap(row.LocalStandards),
		ProjectSettings:         projectContextJSONMap(row.ProjectSettings),
		TechnicalSpecifications: projectContextJSONMap(row.TechnicalSpecifications),
		Metadata:                metadata,
	}
}

func projectContextProjectID(id *string) string {
	if id == nil {
		return "None"
	}
	return *id
}

// projectContextJSONOrEmpty is `value or {}` for a JSON object field.
func projectContextJSONOrEmpty(m map[string]any) map[string]any {
	if m == nil {
		return map[string]any{}
	}
	return m
}

// projectContextMetadataValue is metadata.get(key, {}).
func projectContextMetadataValue(metadata map[string]any, key string) any {
	if metadata != nil {
		if v, ok := metadata[key]; ok {
			return v
		}
	}
	return map[string]any{}
}

// projectContextJSONMap decodes a JSON object column (`value or {}`).
func projectContextJSONMap(raw json.RawMessage) map[string]any {
	if len(raw) == 0 {
		return map[string]any{}
	}
	v, err := entities.DecodeJSON(raw)
	if err != nil {
		return map[string]any{}
	}
	om, ok := v.(*entities.OrderedMap[any])
	if !ok {
		return map[string]any{}
	}
	out := make(map[string]any, om.Len())
	for _, k := range om.Keys() {
		val, _ := om.Get(k)
		out[k] = val
	}
	return out
}
