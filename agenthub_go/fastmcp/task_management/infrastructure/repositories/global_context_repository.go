package repositories

// Global Context Repository (Python infrastructure/repositories/global_context_repository.py):
// user-scoped "global" contexts with nested (v2.0) categorisation. The
// CacheInvalidationMixin side effects are dropped like logging, as is the
// `_is_system_mode` distinction (system mode is userID == nil).

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// globalContextRepoGlobalSingletonUUID is GLOBAL_SINGLETON_UUID.
const globalContextRepoGlobalSingletonUUID = "00000000-0000-0000-0000-000000000001"

// GlobalContextRepository is Python's GlobalContextRepository.
type GlobalContextRepository struct {
	*ORMRepository[database.GlobalContext]
	Scope UserScope
}

// NewGlobalContextRepository builds the repository. Python opens a session from
// session_factory at construction; the Go form keeps the SessionManager only.
func NewGlobalContextRepository(sessions *database.SessionManager, userID *string) (*GlobalContextRepository, error) {
	base, err := NewORMRepository[database.GlobalContext]("global_contexts", sessions)
	if err != nil {
		return nil, err
	}
	return &GlobalContextRepository{ORMRepository: base, Scope: NewUserScope(userID)}, nil
}

// normalizeContextID is _normalize_context_id.
func (r *GlobalContextRepository) normalizeContextID(contextID string) string {
	if contextID != "global_singleton" {
		return contextID
	}
	if r.Scope.UserID == nil {
		return globalContextRepoGlobalSingletonUUID
	}
	return database.Uuid5(database.UserIDNamespace, "global_singleton:"+*r.Scope.UserID)
}

// globalContextRepoFindOne is the id (+ optional user) lookup used by Create and Get.
func (r *GlobalContextRepository) globalContextRepoFindOne(ctx context.Context, s database.DBTX, id string) (*database.GlobalContext, error) {
	filters := NewKwargs("id", id)
	if r.Scope.UserID != nil {
		filters.Set("user_id", *r.Scope.UserID)
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

// Create inserts a new global context for the current user.
func (r *GlobalContextRepository) Create(ctx context.Context, entity *entities.GlobalContext) (*entities.GlobalContext, error) {
	var out *entities.GlobalContext
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		normalizedID := r.normalizeContextID(entity.ID)
		var existing *database.GlobalContext
		var err error
		if r.Scope.IsSystemMode() {
			existing, err = r.ORMRepository.getByID(ctx, s, normalizedID)
		} else {
			existing, err = r.globalContextRepoFindOne(ctx, s, normalizedID)
		}
		if err != nil {
			return err
		}
		if existing != nil {
			return &tmvo.ValueError{Msg: "Global context already exists for user. Use update instead."}
		}

		nested := entity.GetNestedData().ToDict()
		organizationStandards := globalContextRepoNestedSub(nested, "organization", "standards")
		securityPolicies := globalContextRepoNestedSub(nested, "security", "access_control")
		complianceRequirements := globalContextRepoNestedSub(nested, "organization", "compliance")
		sharedResources := globalContextRepoNestedSub(nested, "operations", "resources")
		reusablePatterns := globalContextRepoNestedSub(nested, "development", "patterns")
		delegationRules := globalContextRepoNestedSub(nested, "organization", "policies")
		combinedPreferences := globalContextRepoMapAt(nested, "preferences")

		unified := entity.GlobalSettings
		if unified == nil {
			unified = map[string]any{}
		}
		now := Now().UTC()
		kwargs := NewKwargs(
			"id", normalizedID,
			"organization_id", entity.OrganizationName,
			"organization_standards", organizationStandards,
			"security_policies", securityPolicies,
			"compliance_requirements", complianceRequirements,
			"shared_resources", sharedResources,
			"reusable_patterns", reusablePatterns,
			"global_preferences", combinedPreferences,
			"delegation_rules", delegationRules,
			"nested_structure", nested,
			"unified_context_data", unified,
			"user_id", r.Scope.UserID,
			"created_at", now,
			"updated_at", now,
		)
		row, err := r.ORMRepository.insert(ctx, s, kwargs)
		if err != nil {
			return err
		}
		out = globalContextRepoToEntity(row)
		return nil
	})
	return out, err
}

// Get returns the global context by id (user-filtered), or nil.
func (r *GlobalContextRepository) Get(ctx context.Context, contextID string) (*entities.GlobalContext, error) {
	var out *entities.GlobalContext
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.globalContextRepoFindOne(ctx, s, contextID)
		if err != nil {
			return err
		}
		if row != nil {
			out = globalContextRepoToEntity(row)
		}
		return nil
	})
	return out, err
}

// ensureUserOwnership mirrors BaseUserScopedRepository.ensure_user_ownership.
func (r *GlobalContextRepository) ensureUserOwnership(row *database.GlobalContext) error {
	if r.Scope.UserID == nil {
		return nil
	}
	if row != nil && row.UserID != *r.Scope.UserID {
		return &PermissionError{Msg: "Access denied: Entity does not belong to user " + *r.Scope.UserID}
	}
	return nil
}

// Update replaces the global context and returns the refreshed entity.
func (r *GlobalContextRepository) Update(ctx context.Context, contextID string, entity *entities.GlobalContext) (*entities.GlobalContext, error) {
	var out *entities.GlobalContext
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.globalContextRepoFindOne(ctx, s, contextID)
		if err != nil {
			return err
		}
		if row == nil {
			return &tmvo.ValueError{Msg: "Global context not found for user " + globalContextRepoUserStr(r.Scope.UserID) + ": " + contextID}
		}
		if err := r.ensureUserOwnership(row); err != nil {
			return err
		}

		globalSettings := entity.GlobalSettings
		if globalSettings == nil {
			globalSettings = map[string]any{}
		}

		var globalPreferences map[string]any
		if userPreferences, ok := globalSettings["user_preferences"].(map[string]any); ok && len(userPreferences) > 0 {
			globalPreferences = userPreferences
		} else if gp, ok := globalSettings["global_preferences"].(map[string]any); ok {
			globalPreferences = gp
		} else {
			globalPreferences = map[string]any{}
		}

		organizationStandards := globalContextRepoMapKey(globalSettings, "organization_standards")
		securityPolicies := globalContextRepoMapKey(globalSettings, "security_policies")
		complianceRequirements := globalContextRepoMapKey(globalSettings, "compliance_requirements")
		sharedResources := globalContextRepoMapKey(globalSettings, "shared_resources")
		reusablePatterns := globalContextRepoMapKey(globalSettings, "reusable_patterns")
		delegationRules := globalContextRepoMapKey(globalSettings, "delegation_rules")

		knownFields := []string{
			"organization_standards", "security_policies", "compliance_requirements",
			"shared_resources", "reusable_patterns", "global_preferences", "delegation_rules",
			"user_preferences",
		}
		frontendFields := []string{
			"ai_agent_settings", "workflow_preferences", "development_tools",
			"security_settings", "dashboard_settings",
		}
		customFields := map[string]any{}
		for _, fieldName := range frontendFields {
			if v, ok := globalSettings[fieldName]; ok && tmvo.PyTruthy(v) {
				customFields[fieldName] = v
			}
		}
		for _, key := range globalContextRepoOrderedKeys(globalSettings) { // Python dict iteration order
			if globalContextRepoIndexOf(knownFields, key) >= 0 || globalContextRepoIndexOf(frontendFields, key) >= 0 {
				continue
			}
			customFields[key] = globalSettings[key]
		}
		if len(customFields) > 0 {
			globalPreferences["_custom"] = customFields
		}

		nested := entity.GetNestedData().ToDict()
		organizationStandardsNested := globalContextRepoNestedSub(nested, "organization", "standards")
		securityPoliciesNested := globalContextRepoNestedSub(nested, "security", "access_control")
		complianceRequirementsNested := globalContextRepoNestedSub(nested, "organization", "compliance")
		sharedResourcesNested := globalContextRepoNestedSub(nested, "operations", "resources")
		reusablePatternsNested := globalContextRepoNestedSub(nested, "development", "patterns")
		delegationRulesNested := globalContextRepoNestedSub(nested, "organization", "policies")
		combinedPreferencesNested := globalContextRepoMapAt(nested, "preferences")

		organizationStandards = globalContextRepoPrefer(organizationStandards, organizationStandardsNested)
		securityPolicies = globalContextRepoPrefer(securityPolicies, securityPoliciesNested)
		complianceRequirements = globalContextRepoPrefer(complianceRequirements, complianceRequirementsNested)
		sharedResources = globalContextRepoPrefer(sharedResources, sharedResourcesNested)
		reusablePatterns = globalContextRepoPrefer(reusablePatterns, reusablePatternsNested)
		if !tmvo.PyTruthy(globalPreferences) {
			globalPreferences = globalContextRepoMapAt(map[string]any{"preferences": combinedPreferencesNested}, "preferences")
		}
		delegationRules = globalContextRepoPrefer(delegationRules, delegationRulesNested)

		existingUnified := projectContextJSONMap(row.UnifiedContextData)
		newGlobalSettings := entity.GlobalSettings
		if newGlobalSettings == nil {
			newGlobalSettings = map[string]any{}
		}
		merged := map[string]any{}
		for k, v := range existingUnified {
			merged[k] = v
		}
		for k, v := range newGlobalSettings {
			merged[k] = v
		}

		values := NewKwargs(
			"organization_id", entity.OrganizationName,
			"organization_standards", organizationStandards,
			"security_policies", securityPolicies,
			"compliance_requirements", complianceRequirements,
			"shared_resources", sharedResources,
			"reusable_patterns", reusablePatterns,
			"global_preferences", globalPreferences,
			"delegation_rules", delegationRules,
			"nested_structure", nested,
			"unified_context_data", merged,
		)
		updated, err := globalContextRepoUpdateReturning(r.ORMRepository, ctx, s, contextID, values)
		if err != nil {
			return err
		}
		out = globalContextRepoToEntity(updated)
		return nil
	})
	return out, err
}

// globalContextRepoUpdateReturning runs an explicit UPDATE ... RETURNING over a set of
// attributes, reusing the current session. It is shared by the context repositories.
func globalContextRepoUpdateReturning[M any](r *ORMRepository[M], ctx context.Context, s database.DBTX, id any, values Kwargs) (*M, error) {
	var sets []string
	var args []any
	for _, attr := range values.Keys() {
		pos, ok := r.byAttr[attr]
		if !ok {
			continue
		}
		c := r.Table.Columns[pos]
		v, _ := values.Get(attr)
		bv, err := bind(c, v)
		if err != nil {
			return nil, err
		}
		args = append(args, bv)
		sets = append(sets, fmt.Sprintf("%s = $%d", quoteIdent(c.Name), len(args)))
	}
	pk := r.Table.Columns[r.byAttr[r.pkAttr]]
	pkv, err := bind(pk, id)
	if err != nil {
		return nil, err
	}
	args = append(args, pkv)
	updated := r.newRow()
	q := fmt.Sprintf("UPDATE %s SET %s WHERE %s = $%d RETURNING %s",
		quoteIdent(r.Table.Name), globalContextRepoJoinComma(sets), r.pkColumn(), len(args), r.selectList())
	if err := s.QueryRowContext(ctx, q, args...).Scan(r.scanDest(updated)...); err != nil {
		return nil, err
	}
	return updated, nil
}

// Delete removes the global context; a missing row raises ValueError.
func (r *GlobalContextRepository) Delete(ctx context.Context, contextID string) (bool, error) {
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.globalContextRepoFindOne(ctx, s, contextID)
		if err != nil {
			return err
		}
		if row == nil {
			return &tmvo.ValueError{Msg: "Global context with ID " + contextID + " not found"}
		}
		if err := r.ensureUserOwnership(row); err != nil {
			return err
		}
		pk := r.Table.Columns[r.byAttr[r.pkAttr]]
		bv, err := bind(pk, contextID)
		if err != nil {
			return err
		}
		_, err = s.ExecContext(ctx, fmt.Sprintf("DELETE FROM %s WHERE %s = $1", quoteIdent(r.Table.Name), r.pkColumn()), bv)
		return err
	})
	return err == nil, err
}

// List returns the global contexts for the current user.
func (r *GlobalContextRepository) List(ctx context.Context, filters Kwargs) ([]*entities.GlobalContext, error) {
	var out []*entities.GlobalContext
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		where := r.Scope.GetUserFilter()
		if filters != nil {
			for _, key := range filters.Keys() {
				if _, ok := r.byAttr[key]; !ok {
					continue
				}
				v, _ := filters.Get(key)
				where.Set(key, v)
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
		out = make([]*entities.GlobalContext, 0, len(rows))
		for _, row := range rows {
			out = append(out, globalContextRepoToEntity(row))
		}
		return nil
	})
	return out, err
}

// Exists reports whether the global context exists for the current user.
func (r *GlobalContextRepository) Exists(ctx context.Context, contextID string) (bool, error) {
	found := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.globalContextRepoFindOne(ctx, s, contextID)
		if err != nil {
			return err
		}
		found = row != nil
		return nil
	})
	return found, err
}

// CountUserContexts counts the global contexts for the current user.
func (r *GlobalContextRepository) CountUserContexts(ctx context.Context) (int, error) {
	return r.Count(ctx, r.Scope.GetUserFilter())
}

// MigrateToUserScoped mirrors the Python method, including its `user_id is None`
// identity bug: the filter is the constant False, so no context is ever migrated.
func (r *GlobalContextRepository) MigrateToUserScoped(ctx context.Context) (int, error) {
	systemUserID, ok := os.LookupEnv("SYSTEM_USER_ID")
	if !ok || systemUserID == "" {
		return 0, &tmvo.ValueError{Msg: "SYSTEM_USER_ID environment variable is required for migration"}
	}
	migrated := 0
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := r.selectRows(ctx, s, " WHERE false")
		if err != nil {
			return err
		}
		migrated = len(rows)
		return nil
	})
	return migrated, err
}

// globalContextRepoToEntity is _to_entity. Note the Python source (re)builds
// global_settings from the flat columns in the always-taken else branch, so the
// unified_context_data value never reaches the entity.
func globalContextRepoToEntity(row *database.GlobalContext) *entities.GlobalContext {
	globalSettings := map[string]any{
		"organization_standards":  globalContextRepoJSONMap(row.OrganizationStandards),
		"security_policies":       globalContextRepoJSONMap(row.SecurityPolicies),
		"compliance_requirements": globalContextRepoJSONMap(row.ComplianceRequirements),
		"shared_resources":        globalContextRepoJSONMap(row.SharedResources),
		"reusable_patterns":       globalContextRepoJSONMap(row.ReusablePatterns),
		"delegation_rules":        globalContextRepoJSONMap(row.DelegationRules),
		"autonomous_rules":        map[string]any{},
		"coding_standards":        map[string]any{},
		"workflow_templates":      map[string]any{},
	}

	globalPreferences := globalContextRepoJSONMap(row.GlobalPreferences)
	if customRaw, ok := globalPreferences["_custom"]; ok {
		globalPreferencesCopy := map[string]any{}
		for k, v := range globalPreferences {
			if k != "_custom" {
				globalPreferencesCopy[k] = v
			}
		}
		customFields := globalContextRepoAsMap(customRaw)
		frontendFields := []string{
			"ai_agent_settings", "workflow_preferences", "development_tools",
			"security_settings", "dashboard_settings",
		}
		for _, fieldName := range frontendFields {
			if v, ok := customFields[fieldName]; ok {
				globalSettings[fieldName] = v
			}
		}
		for k, v := range customFields {
			if globalContextRepoIndexOf(frontendFields, k) < 0 {
				globalSettings[k] = v
			}
		}
		globalSettings["user_preferences"] = globalPreferencesCopy
		globalSettings["global_preferences"] = globalPreferencesCopy
	} else {
		globalSettings["user_preferences"] = globalPreferences
		globalSettings["global_preferences"] = globalPreferences
	}

	workflowTemplates := globalContextRepoMapKey(globalSettings, "workflow_templates")
	if customRaw, ok := workflowTemplates["_custom"]; ok {
		customFields := globalContextRepoAsMap(customRaw)
		for k, v := range customFields {
			globalSettings[k] = v
		}
		cleaned := map[string]any{}
		for k, v := range workflowTemplates {
			if k != "_custom" {
				cleaned[k] = v
			}
		}
		globalSettings["workflow_templates"] = cleaned
	}

	nestedStructure := globalContextRepoJSONMap(row.NestedStructure)
	metadata := map[string]any{
		"created_at":     tmvo.IsoFormatNaive(row.CreatedAt),
		"updated_at":     tmvo.IsoFormatNaive(row.UpdatedAt),
		"version":        row.Version,
		"user_id":        row.UserID,
		"schema_version": "1.0",
		"is_migrated":    false,
	}
	if len(nestedStructure) > 0 {
		metadata["nested_structure"] = nestedStructure
	}
	organizationName := ""
	if row.OrganizationID != nil {
		organizationName = *row.OrganizationID
	}
	return entities.NewGlobalContext(row.ID, organizationName, globalSettings, metadata)
}

// ---- helpers -------------------------------------------------------------------

func globalContextRepoJSONMap(raw json.RawMessage) map[string]any {
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

// globalContextRepoNestedSub is nested.get(category, {}).get(sub, {}).
func globalContextRepoNestedSub(nested map[string]any, category, sub string) any {
	if inner, ok := nested[category].(map[string]any); ok {
		if v, ok := inner[sub]; ok {
			return v
		}
	}
	return map[string]any{}
}

// globalContextRepoMapAt is m.get(key, {}) restricted to dict values.
func globalContextRepoMapAt(m map[string]any, key string) map[string]any {
	return globalContextRepoAsMap(m[key])
}

// globalContextRepoAsMap treats an already-decoded JSON object (plain map or an
// entities.OrderedMap, which is what DecodeJSON yields) as a dict.
func globalContextRepoAsMap(v any) map[string]any {
	switch m := v.(type) {
	case map[string]any:
		return m
	case *entities.OrderedMap[any]:
		out := make(map[string]any, m.Len())
		for _, k := range m.Keys() {
			val, _ := m.Get(k)
			out[k] = val
		}
		return out
	}
	return map[string]any{}
}

// globalContextRepoMapKey is d.get(key, {}) restricted to dict values.
func globalContextRepoMapKey(d map[string]any, key string) map[string]any {
	return globalContextRepoMapAt(d, key)
}

// globalContextRepoPrefer is `flat if flat else nested`, returning plain maps.
func globalContextRepoPrefer(flat map[string]any, nested any) map[string]any {
	if len(flat) > 0 {
		return flat
	}
	if m, ok := nested.(map[string]any); ok {
		return m
	}
	return map[string]any{}
}

func globalContextRepoUserStr(userID *string) string {
	if userID == nil {
		return "None"
	}
	return *userID
}

// globalContextRepoOrderedKeys returns map keys sorted (Go maps have no insertion
// order; the Python insertion order is not recoverable from a map).
func globalContextRepoOrderedKeys(m map[string]any) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

func globalContextRepoIndexOf(xs []string, v string) int {
	for i, x := range xs {
		if x == v {
			return i
		}
	}
	return -1
}

func globalContextRepoJoinComma(parts []string) string { return strings.Join(parts, ", ") }
