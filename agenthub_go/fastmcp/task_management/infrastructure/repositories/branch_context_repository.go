package repositories

// Branch Context Repository (Python infrastructure/repositories/branch_context_repository.py):
// persistence for the unified branch-level context (branch_contexts table). Cache
// invalidation and logging are dropped. The IntegrityError recovery path is only reachable
// through a duplicate-key race; Go returns the ValueError conversion used when no existing
// row is found.

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// BranchContextRepository is Python's BranchContextRepository.
type BranchContextRepository struct {
	*ORMRepository[database.BranchContext]
	UserID *string
}

// NewBranchContextRepository builds the repository.
func NewBranchContextRepository(sessions *database.SessionManager, userID *string) (*BranchContextRepository, error) {
	base, err := NewORMRepository[database.BranchContext]("branch_contexts", sessions)
	if err != nil {
		return nil, err
	}
	return &BranchContextRepository{ORMRepository: base, UserID: userID}, nil
}

// WithUser returns a new instance scoped to userID.
func (r *BranchContextRepository) WithUser(userID string) *BranchContextRepository {
	return &BranchContextRepository{ORMRepository: r.ORMRepository, UserID: &userID}
}

// branchContextRepoNormalizeUUID is _normalize_uuid for the string inputs Go carries.
func branchContextRepoNormalizeUUID(value string, isNone bool) string {
	if isNone || value == "" {
		return tmvo.NewUUIDv4()
	}
	if _, ok := tmvo.PyParseUUID(value); ok {
		return value
	}
	return tmvo.NewUUIDv4()
}

// branchContextRepoLookup applies the optional user filter and LIMIT 1.
func (r *BranchContextRepository) branchContextRepoLookup(ctx context.Context, s database.DBTX, id string) (*database.BranchContext, error) {
	filters := NewKwargs("id", id)
	if r.UserID != nil {
		filters.Set("user_id", *r.UserID)
	}
	w, args, err := r.where(filters, 1)
	if err != nil {
		return nil, err
	}
	rows, err := r.selectRows(ctx, s, w+" LIMIT 1", args...)
	if err != nil {
		return nil, err
	}
	if len(rows) > 0 {
		return rows[0], nil
	}
	return nil, nil
}

// branchContextRepoMerged builds the (branch_info, branch_workflow, branch_decisions,
// feature_flags, discovered_patterns) tuple after merging legacy branch_settings.
func branchContextRepoMerged(entity *entities.BranchContext) (map[string]any, map[string]any, map[string]any, map[string]any, map[string]any) {
	branchInfo := entity.BranchInfo
	if branchInfo == nil {
		branchInfo = map[string]any{}
	}
	branchWorkflow := entity.BranchWorkflow
	if branchWorkflow == nil {
		branchWorkflow = map[string]any{}
	}
	featureFlags := entity.FeatureFlags
	if featureFlags == nil {
		featureFlags = map[string]any{}
	}
	discoveredPatterns := entity.DiscoveredPatterns
	if discoveredPatterns == nil {
		discoveredPatterns = map[string]any{}
	}
	branchDecisions := entity.BranchDecisions
	if branchDecisions == nil {
		branchDecisions = map[string]any{}
	}
	branchSettings := entity.BranchSettings
	if branchSettings == nil {
		branchSettings = map[string]any{}
	}
	if v, ok := branchSettings["branch_workflow"].(map[string]any); ok {
		for k, val := range v {
			branchWorkflow[k] = val
		}
	}
	if v, ok := branchSettings["branch_standards"].(map[string]any); ok {
		for k, val := range v {
			branchDecisions[k] = val
		}
	}
	if v, ok := branchSettings["agent_assignments"]; ok {
		branchInfo["agent_assignments"] = v
	}
	return branchInfo, branchWorkflow, featureFlags, discoveredPatterns, branchDecisions
}

// branchContextRepoMetadataValue is entity.metadata.get(key, {}).
func branchContextRepoMetadataValue(metadata map[string]any, key string) any {
	if metadata != nil {
		if v, ok := metadata[key]; ok {
			return v
		}
	}
	return map[string]any{}
}

// Create inserts a branch context; an existing (id, user) returns the stored entity.
func (r *BranchContextRepository) Create(ctx context.Context, entity *entities.BranchContext) (*entities.BranchContext, error) {
	var out *entities.BranchContext
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		normalizedID := branchContextRepoNormalizeUUID(entity.ID, false)

		existing, err := r.branchContextRepoLookup(ctx, s, normalizedID)
		if err != nil {
			return err
		}
		if existing != nil {
			out = branchContextRepoToEntity(existing)
			return nil
		}
		if r.UserID == nil {
			return &tmvo.ValueError{Msg: "user_id is required for branch context creation"}
		}

		branchInfo, branchWorkflow, featureFlags, discoveredPatterns, branchDecisions := branchContextRepoMerged(entity)

		var projectID any
		if entity.ProjectID != "" {
			projectID = branchContextRepoNormalizeUUID(entity.ProjectID, false)
		}

		dataField := map[string]any{
			"branch_info":         branchInfo,
			"branch_workflow":     branchWorkflow,
			"feature_flags":       featureFlags,
			"discovered_patterns": discoveredPatterns,
			"branch_decisions":    branchDecisions,
			"active_patterns":     branchContextRepoMetadataValue(entity.Metadata, "active_patterns"),
			"local_overrides":     branchContextRepoMetadataValue(entity.Metadata, "local_overrides"),
			"delegation_rules":    branchContextRepoMetadataValue(entity.Metadata, "delegation_rules"),
		}
		predefined := []string{"user_id", "active_patterns", "local_overrides", "delegation_rules"}
		for _, key := range globalContextRepoOrderedKeys(entity.Metadata) {
			if globalContextRepoIndexOf(predefined, key) >= 0 {
				continue
			}
			dataField[key] = entity.Metadata[key]
		}

		kwargs := NewKwargs(
			"id", normalizedID,
			"branch_id", nil,
			"parent_project_id", projectID,
			"data", dataField,
			"branch_info", branchInfo,
			"branch_workflow", branchWorkflow,
			"feature_flags", featureFlags,
			"discovered_patterns", discoveredPatterns,
			"branch_decisions", branchDecisions,
			"active_patterns", branchContextRepoMetadataValue(entity.Metadata, "active_patterns"),
			"local_overrides", branchContextRepoMetadataValue(entity.Metadata, "local_overrides"),
			"delegation_rules", branchContextRepoMetadataValue(entity.Metadata, "delegation_rules"),
			"user_id", r.UserID,
		)
		row, err := r.ORMRepository.insert(ctx, s, kwargs)
		if err != nil {
			if _, ok := err.(*exceptions.DatabaseIntegrityException); ok {
				return &tmvo.ValueError{Msg: "Branch context creation failed due to constraint violation: " + err.Error()}
			}
			return err
		}
		out = branchContextRepoToEntity(row)
		return nil
	})
	return out, err
}

// Get returns the branch context by id (user-filtered), or nil.
func (r *BranchContextRepository) Get(ctx context.Context, contextID string) (*entities.BranchContext, error) {
	var out *entities.BranchContext
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.branchContextRepoLookup(ctx, s, contextID)
		if err != nil {
			return err
		}
		if row != nil {
			out = branchContextRepoToEntity(row)
		}
		return nil
	})
	return out, err
}

// Update replaces the mutable fields; the lookup deliberately has no user filter (Python
// uses session.get) and a missing row raises ValueError.
func (r *BranchContextRepository) Update(ctx context.Context, contextID string, entity *entities.BranchContext) (*entities.BranchContext, error) {
	var out *entities.BranchContext
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.ORMRepository.getByID(ctx, s, contextID)
		if err != nil {
			return err
		}
		if row == nil {
			return &tmvo.ValueError{Msg: "Branch context not found: " + contextID}
		}
		branchInfo, branchWorkflow, featureFlags, discoveredPatterns, branchDecisions := branchContextRepoMerged(entity)

		dataField := map[string]any{
			"branch_info":         branchInfo,
			"branch_workflow":     branchWorkflow,
			"feature_flags":       featureFlags,
			"discovered_patterns": discoveredPatterns,
			"branch_decisions":    branchDecisions,
			"active_patterns":     branchContextRepoMetadataValue(entity.Metadata, "active_patterns"),
			"local_overrides":     branchContextRepoMetadataValue(entity.Metadata, "local_overrides"),
			"delegation_rules":    branchContextRepoMetadataValue(entity.Metadata, "delegation_rules"),
		}
		userID := branchContextRepoFirstNonEmpty(r.UserID, branchContextRepoAnyString(entity.Metadata["user_id"]), &row.UserID)
		values := NewKwargs(
			"parent_project_id", entity.ProjectID,
			"branch_info", branchInfo,
			"branch_workflow", branchWorkflow,
			"feature_flags", featureFlags,
			"discovered_patterns", discoveredPatterns,
			"branch_decisions", branchDecisions,
			"active_patterns", branchContextRepoMetadataValue(entity.Metadata, "active_patterns"),
			"data", dataField,
			"local_overrides", branchContextRepoMetadataValue(entity.Metadata, "local_overrides"),
			"delegation_rules", branchContextRepoMetadataValue(entity.Metadata, "delegation_rules"),
			"user_id", userID,
		)
		updated, err := globalContextRepoUpdateReturning(r.ORMRepository, ctx, s, contextID, values)
		if err != nil {
			return err
		}
		out = branchContextRepoToEntity(updated)
		return nil
	})
	return out, err
}

// Delete removes the branch context; a missing row is false.
func (r *BranchContextRepository) Delete(ctx context.Context, contextID string) (bool, error) {
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

// List returns the branch contexts; project_id maps to parent_project_id and
// git_branch_name is ignored (Python TODO).
func (r *BranchContextRepository) List(ctx context.Context, filters Kwargs) ([]*entities.BranchContext, error) {
	var out []*entities.BranchContext
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		where := NewKwargs()
		if r.UserID != nil {
			where.Set("user_id", *r.UserID)
		}
		if filters != nil {
			if v, ok := filters.Get("project_id"); ok {
				where.Set("parent_project_id", v)
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
		out = make([]*entities.BranchContext, 0, len(rows))
		for _, row := range rows {
			out = append(out, branchContextRepoToEntity(row))
		}
		return nil
	})
	return out, err
}

// branchContextRepoToEntity is _to_entity.
func branchContextRepoToEntity(row *database.BranchContext) *entities.BranchContext {
	dataField := projectContextJSONMap(row.Data)

	branchInfo := projectContextJSONMap(row.BranchInfo)
	if len(branchInfo) == 0 {
		branchInfo = globalContextRepoMapAt(dataField, "branch_info")
	}
	branchID := ""
	if row.BranchID != nil {
		branchID = *row.BranchID
	}
	if branchID == "" {
		branchID = row.ID
	}
	gitBranchName := "branch-" + branchID
	if v, ok := branchInfo["name"]; ok {
		if s, ok := v.(string); ok {
			gitBranchName = s
		}
	}

	branchSettings := map[string]any{}
	if v, ok := dataField["branch_standards"]; ok {
		branchSettings["branch_standards"] = v
	}
	if v, ok := dataField["agent_assignments"]; ok {
		branchSettings["agent_assignments"] = v
	}

	branchWorkflow := projectContextJSONMap(row.BranchWorkflow)
	if len(branchWorkflow) == 0 {
		branchWorkflow = globalContextRepoMapAt(dataField, "branch_workflow")
	}
	featureFlags := projectContextJSONMap(row.FeatureFlags)
	if len(featureFlags) == 0 {
		featureFlags = globalContextRepoMapAt(dataField, "feature_flags")
	}
	discoveredPatterns := projectContextJSONMap(row.DiscoveredPatterns)
	if len(discoveredPatterns) == 0 {
		discoveredPatterns = globalContextRepoMapAt(dataField, "discovered_patterns")
	}
	branchDecisions := projectContextJSONMap(row.BranchDecisions)
	if len(branchDecisions) == 0 {
		branchDecisions = globalContextRepoMapAt(dataField, "branch_decisions")
	}
	activePatterns := projectContextJSONMap(row.ActivePatterns)
	if len(activePatterns) == 0 {
		activePatterns = globalContextRepoMapAt(dataField, "active_patterns")
	}
	localOverrides := projectContextJSONMap(row.LocalOverrides)
	if len(localOverrides) == 0 {
		localOverrides = globalContextRepoMapAt(dataField, "local_overrides")
	}
	delegationRules := projectContextJSONMap(row.DelegationRules)
	if len(delegationRules) == 0 {
		delegationRules = globalContextRepoMapAt(dataField, "delegation_rules")
	}

	var projectID string
	if row.ParentProjectID != nil {
		projectID = *row.ParentProjectID
	}
	metadata := map[string]any{
		"active_patterns":  activePatterns,
		"local_overrides":  localOverrides,
		"delegation_rules": delegationRules,
		"created_at":       nil,
		"updated_at":       nil,
	}
	if row.CreatedAt != nil {
		metadata["created_at"] = tmvo.IsoFormatNaive(*row.CreatedAt)
	}
	if row.UpdatedAt != nil {
		metadata["updated_at"] = tmvo.IsoFormatNaive(*row.UpdatedAt)
	}
	return &entities.BranchContext{
		ID: row.ID, ProjectID: projectID, GitBranchName: gitBranchName,
		BranchInfo: branchInfo, BranchWorkflow: branchWorkflow, FeatureFlags: featureFlags,
		DiscoveredPatterns: discoveredPatterns, BranchDecisions: branchDecisions,
		BranchSettings: branchSettings, Metadata: metadata,
	}
}

func branchContextRepoAnyString(v any) *string {
	if s, ok := v.(string); ok {
		return &s
	}
	return nil
}

func branchContextRepoNullableString(s string) any {
	if s == "" {
		return nil
	}
	return s
}

func branchContextRepoFirstNonEmpty(candidates ...*string) *string {
	for _, c := range candidates {
		if c != nil && *c != "" {
			return c
		}
	}
	return nil
}
