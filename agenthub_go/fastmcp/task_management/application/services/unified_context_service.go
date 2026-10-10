package services

import (
	"context"
	"crypto/sha1"
	"encoding/hex"
	"fmt"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/utilities"
)

// UnifiedContextRepository is the minimal duck-typed repository surface the Python
// UnifiedContextService relies on: get/create/update/delete/list. The Python service
// receives four repositories (one per ContextLevel) as Any; the concrete Go context
// repositories do not share a single interface, so this port declares the minimal
// interface it needs. It mirrors the Python method shapes with an OrderedMap filter
// for list.
type UnifiedContextRepository interface {
	Get(ctx context.Context, id string) (any, error)
	Create(ctx context.Context, entity any) (any, error)
	Update(ctx context.Context, id string, entity any) (any, error)
	Delete(ctx context.Context, id string) (bool, error)
	List(ctx context.Context, filters map[string]any) ([]any, error)
}

// zpUCSNamespace is the namespace UUID used for uuid5 global-context generation,
// mirroring a47ae7b9-1d4b-4e5f-8b5a-9c3e5d2f8a1c.
const zpUCSNamespace = "a47ae7b9-1d4b-4e5f-8b5a-9c3e5d2f8a1c"

// UnifiedContextService mirrors UnifiedContextService: a single service for all
// context operations (application/services/unified_context_service.py).
type UnifiedContextService struct {
	UserID             *string
	repositories       map[value_objects.ContextLevel]UnifiedContextRepository
	CacheService       *ContextCacheService
	InheritanceService *ContextInheritanceService
	DelegationService  *ContextDelegationService
	ValidationService  *ContextValidationService
	// EntityLookup resolves ids that create_context auto-detects from the branch and
	// task entities. Nil mirrors Python's "repository factory not available" skip.
	EntityLookup EntityIDLookup
}

// EntityIDLookup is the git branch / task repository access create_context uses to
// auto-detect project_id and git_branch_id. An empty id with a nil error means the
// entity has no such value.
type EntityIDLookup interface {
	BranchProjectID(ctx context.Context, userID *string, branchID string) (string, error)
	TaskGitBranchID(ctx context.Context, userID *string, taskID string) (string, error)
}

// WithEntityLookup returns the service with the given entity lookup.
func (s *UnifiedContextService) WithEntityLookup(l EntityIDLookup) *UnifiedContextService {
	s.EntityLookup = l
	return s
}

// autoDetectCreateIDs ports the two auto-detection blocks of create_context: a branch
// context without project_id takes it from the git branch, a task context without any
// of branch_id/parent_branch_id/git_branch_id takes git_branch_id from the task.
// Lookup failures are swallowed, as in Python, and validation reports the missing id.
func (s *UnifiedContextService) autoDetectCreateIDs(ctx context.Context, level value_objects.ContextLevel, contextID string, data *entities.OrderedMap[any], userID *string) {
	if s.EntityLookup == nil {
		return
	}
	truthy := func(key string) bool {
		v, _ := data.Get(key)
		return value_objects.PyTruthy(v)
	}
	switch {
	case level == value_objects.ContextLevelBranch && !truthy("project_id"):
		if id, err := s.EntityLookup.BranchProjectID(ctx, userOrDefault(userID, s.UserID), contextID); err == nil && id != "" {
			data.Set("project_id", id)
		}
	case level == value_objects.ContextLevelTask && !truthy("branch_id") && !truthy("parent_branch_id") && !truthy("git_branch_id"):
		if id, err := s.EntityLookup.TaskGitBranchID(ctx, userOrDefault(userID, s.UserID), contextID); err == nil && id != "" {
			data.Set("git_branch_id", id)
		}
	}
}

// NewUnifiedContextService mirrors __init__. Optional services fall back to their
// no-argument Python defaults.
func NewUnifiedContextService(
	globalContextRepository, projectContextRepository, branchContextRepository, taskContextRepository UnifiedContextRepository,
	cacheService *ContextCacheService,
	inheritanceService *ContextInheritanceService,
	delegationService *ContextDelegationService,
	validationService *ContextValidationService,
	userID *string,
) *UnifiedContextService {
	s := &UnifiedContextService{
		UserID: userID,
		repositories: map[value_objects.ContextLevel]UnifiedContextRepository{
			value_objects.ContextLevelGlobal:  globalContextRepository,
			value_objects.ContextLevelProject: projectContextRepository,
			value_objects.ContextLevelBranch:  branchContextRepository,
			value_objects.ContextLevelTask:    taskContextRepository,
		},
	}
	if cacheService == nil {
		cacheService = NewContextCacheService(nil, 1, userID)
	}
	s.CacheService = cacheService
	if inheritanceService == nil {
		inheritanceService = NewContextInheritanceService(s.repositories, userID)
	}
	s.InheritanceService = inheritanceService
	if delegationService == nil {
		delegationService = zpCtxDelNewContextDelegationService(nil, userID)
	}
	s.DelegationService = delegationService
	if validationService == nil {
		validationService = NewContextValidationService(userID, (*utilities.IDValidator)(nil))
	}
	s.ValidationService = validationService
	return s
}

// WithUser mirrors with_user: repositories are returned unchanged because the Go
// repository interfaces expose no with_user method (see getUserScopedRepository).
func (s *UnifiedContextService) WithUser(userID string) *UnifiedContextService {
	return NewUnifiedContextService(
		s.repositories[value_objects.ContextLevelGlobal],
		s.repositories[value_objects.ContextLevelProject],
		s.repositories[value_objects.ContextLevelBranch],
		s.repositories[value_objects.ContextLevelTask],
		s.CacheService, s.InheritanceService, s.DelegationService, s.ValidationService, &userID,
	).WithEntityLookup(s.EntityLookup)
}

// _get_user_scoped_repository_for_user mirrors the Python duck-typed with_user lookup.
// The Go repositories have no common with_user interface, so it is returned unchanged.
func (s *UnifiedContextService) getUserScopedRepositoryForUser(repository UnifiedContextRepository, userID string) UnifiedContextRepository {
	return repository
}

// _get_user_scoped_repository mirrors the user-scoped repository lookup.
func (s *UnifiedContextService) getUserScopedRepository(repository UnifiedContextRepository) UnifiedContextRepository {
	return repository
}

// _serialize_for_json recursively converts non-JSON-serializable objects to strings.
func (s *UnifiedContextService) serializeForJSON(data any) any {
	switch v := data.(type) {
	case nil:
		return nil
	case time.Time:
		// str(datetime) is isoformat(sep=" ").
		return strings.Replace(value_objects.IsoFormat(v), "T", " ", 1)
	case map[string]any:
		out := map[string]any{}
		for key, val := range v {
			out[key] = s.serializeForJSON(val)
		}
		return out
	case *entities.OrderedMap[any]:
		out := entities.NewOrderedMap[any]()
		for _, key := range v.Keys() {
			val, _ := v.Get(key)
			out.Set(key, s.serializeForJSON(val))
		}
		return out
	case []any:
		out := make([]any, 0, len(v))
		for _, item := range v {
			out = append(out, s.serializeForJSON(item))
		}
		return out
	default:
		return data
	}
}

// _normalize_global_context_id converts "global"/empty to a user-specific uuid5.
func (s *UnifiedContextService) normalizeGlobalContextID(contextID string, userID *string) (string, error) {
	if contextID == "" || strings.ToLower(contextID) == "global" {
		effectiveUserID := userOrDefault(userID, s.UserID)
		if effectiveUserID == nil || *effectiveUserID == "" {
			return "", &value_objects.ValueError{Msg: "user_id is required for global context normalization (no fallback allowed for DDD compliance)"}
		}
		userUUID, ok := value_objects.PyParseUUID(*effectiveUserID)
		if !ok {
			userUUID = zpUCSUUID5(zpUCSNamespace, *effectiveUserID)
		}
		return zpUCSUUID5(zpUCSNamespace, userUUID), nil
	}
	return contextID, nil
}

// CreateContext mirrors create_context. It returns the Python response dict as an
// OrderedMap; errors raised inside the Python try block become {"success": false, ...}.
func (s *UnifiedContextService) CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID, projectID *string, autoCreateParents bool) (*entities.OrderedMap[any], error) {
	if data == nil {
		data = entities.NewOrderedMap[any]()
	}
	originalUserID := s.UserID
	if userID != nil {
		s.UserID = userID
	}
	contextLevel, err := value_objects.ContextLevelFromEnumValue(level)
	if err != nil {
		s.UserID = originalUserID
		return zpUCSError(err.Error()), nil
	}
	if contextLevel == value_objects.ContextLevelGlobal {
		effectiveUser := userOrDefault(userID, s.UserID)
		normalized, nerr := s.normalizeGlobalContextID(contextID, effectiveUser)
		if nerr != nil {
			s.UserID = originalUserID
			return zpUCSError(nerr.Error()), nil
		}
		contextID = normalized
	}
	s.UserID = originalUserID

	s.autoDetectCreateIDs(ctx, contextLevel, contextID, data, userID)

	if autoCreateParents && contextLevel != value_objects.ContextLevelGlobal {
		s.ensureParentContextsExist(ctx, contextLevel, contextID, data, userID, projectID)
	}

	if s.hierarchyValidator(ctx) != nil {
		isValid, errorMsg, guidance := s.hierarchyValidator(ctx).ValidateHierarchyRequirements(contextLevel, contextID, data)
		if !isValid {
			if !autoCreateParents {
				resp := zpUCSError(zpUCSDeref(errorMsg))
				resp.Set("auto_creation_disabled", true)
				zpUCSMerge(resp, guidance)
				return resp, nil
			}
			if s.shouldAllowOrphanedCreation(contextLevel, contextID, data) {
				isValid = true
				errorMsg = nil
			} else {
				resp := zpUCSError(zpUCSDeref(errorMsg))
				resp.Set("auto_creation_attempted", true)
				zpUCSMerge(resp, guidance)
				return resp, nil
			}
		}
		_ = isValid
	}

	validationResult, verr := s.ValidationService.ValidateContextData(contextLevel, zpUCSMap(data))
	if verr != nil {
		return zpUCSError(verr.Error()), nil
	}
	if valid, _ := validationResult.Get("valid"); valid != true {
		errs, _ := validationResult.Get("errors")
		return zpUCSError(fmt.Sprintf("Validation failed: %v", errs)), nil
	}

	baseRepository := s.repositories[contextLevel]
	if baseRepository == nil {
		return zpUCSError(fmt.Sprintf("No repository configured for level: %s", level)), nil
	}
	effectiveUserID := userOrDefault(userID, s.UserID)
	repo := baseRepository
	if effectiveUserID != nil {
		repo = s.getUserScopedRepository(baseRepository)
	}

	if contextLevel == value_objects.ContextLevelGlobal {
		contextID = zpUCSCompositeGlobalID(contextID)
	}

	if existing, gerr := repo.Get(ctx, contextID); gerr == nil && existing != nil {
		resp := entities.NewOrderedMap[any]()
		resp.Set("success", true)
		resp.Set("context", s.entityToDict(existing))
		resp.Set("level", level)
		resp.Set("context_id", zpUCSEntityID(existing))
		resp.Set("already_existed", true)
		return resp, nil
	}

	contextEntity := s.createContextEntity(contextLevel, contextID, data, userID, projectID)
	if contextEntity == nil {
		return zpUCSError("Unsupported context level"), nil
	}
	savedContext, cerr := repo.Create(ctx, contextEntity)
	if cerr != nil {
		return zpUCSError(cerr.Error()), nil
	}

	resp := entities.NewOrderedMap[any]()
	resp.Set("success", true)
	resp.Set("context", s.entityToDict(savedContext))
	resp.Set("level", level)
	resp.Set("context_id", zpUCSEntityID(savedContext))
	return resp, nil
}

// GetContext mirrors get_context.
func (s *UnifiedContextService) GetContext(ctx context.Context, level, contextID string, includeInherited, forceRefresh bool, userID *string) (*entities.OrderedMap[any], error) {
	if contextID == "" {
		return zpUCSError("Context ID is required"), nil
	}
	// Python `if user_id:` ignores an empty string and keeps the service user.
	if userID != nil && *userID == "" {
		userID = nil
	}
	originalUserID := s.UserID
	if userID != nil {
		s.UserID = userID
	}
	contextLevel, err := value_objects.ContextLevelFromEnumValue(level)
	if err != nil {
		s.UserID = originalUserID
		return zpUCSError(err.Error()), nil
	}
	if contextLevel == value_objects.ContextLevelGlobal {
		effectiveUser := userOrDefault(userID, s.UserID)
		normalized, nerr := s.normalizeGlobalContextID(contextID, effectiveUser)
		if nerr != nil {
			s.UserID = originalUserID
			return zpUCSError(nerr.Error()), nil
		}
		contextID = normalized
	}
	s.UserID = originalUserID

	repository := s.repositories[contextLevel]
	if repository == nil {
		return zpUCSError(fmt.Sprintf("No repository configured for level: %s", level)), nil
	}
	effectiveUserID := userOrDefault(userID, s.UserID)
	repo := repository
	if effectiveUserID != nil {
		repo = s.getUserScopedRepository(repository)
	}
	contextEntity, gerr := repo.Get(ctx, contextID)
	if gerr != nil {
		// Python reports a repository exception as str(e), not as "not found".
		return zpUCSError(gerr.Error()), nil
	}
	if contextEntity == nil {
		return zpUCSError(fmt.Sprintf("Context not found: %s", contextID)), nil
	}
	contextData := s.entityToDict(contextEntity)
	if includeInherited {
		contextData = s.resolveInheritanceSync(ctx, contextLevel, contextEntity, contextData)
	}
	resp := entities.NewOrderedMap[any]()
	resp.Set("success", true)
	resp.Set("context", contextData)
	resp.Set("level", level)
	resp.Set("context_id", zpUCSEntityID(contextEntity))
	resp.Set("inherited", includeInherited)
	return resp, nil
}

// UpdateContext mirrors update_context.
func (s *UnifiedContextService) UpdateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], propagateChanges bool, userID *string) (*entities.OrderedMap[any], error) {
	if data == nil {
		data = entities.NewOrderedMap[any]()
	}
	contextLevel, err := value_objects.ContextLevelFromEnumValue(level)
	if err != nil {
		return zpUCSError(err.Error()), nil
	}
	if contextLevel == value_objects.ContextLevelGlobal {
		effectiveUser := userOrDefault(userID, s.UserID)
		normalized, nerr := s.normalizeGlobalContextID(contextID, effectiveUser)
		if nerr != nil {
			return zpUCSError(nerr.Error()), nil
		}
		contextID = normalized
	}
	repository := s.getUserScopedRepository(s.repositories[contextLevel])
	if repository == nil {
		return zpUCSError(fmt.Sprintf("No repository configured for level: %s", level)), nil
	}
	repo := s.getUserScopedRepository(repository)
	existing, gerr := repo.Get(ctx, contextID)
	if gerr != nil {
		// Python reports a repository exception as str(e), not as "not found".
		return zpUCSError(gerr.Error()), nil
	}
	if existing == nil {
		return zpUCSError(fmt.Sprintf("Context not found: %s", contextID)), nil
	}

	existingDict := s.entityToDict(existing)
	var updatedData *entities.OrderedMap[any]
	if contextLevel == value_objects.ContextLevelGlobal {
		if globalSettings, ok := existingDict.Get("global_settings"); ok {
			merged := s.mergeContextData(zpUCSAsOrdered(globalSettings), data)
			updatedData = existingDict.Copy()
			updatedData.Set("global_settings", merged)
		} else {
			updatedData = existingDict.Copy()
			updatedData.Set("global_settings", data)
		}
	} else {
		updatedData = s.mergeContextData(existingDict, data)
	}

	updatedEntity := s.updateContextEntity(existing, updatedData)
	savedContext, uerr := repo.Update(ctx, contextID, updatedEntity)
	if uerr != nil {
		return zpUCSError(uerr.Error()), nil
	}
	resp := entities.NewOrderedMap[any]()
	resp.Set("success", true)
	resp.Set("context", s.entityToDict(savedContext))
	resp.Set("level", level)
	resp.Set("context_id", contextID)
	resp.Set("propagated", propagateChanges)
	return resp, nil
}

// DeleteContext mirrors delete_context.
func (s *UnifiedContextService) DeleteContext(ctx context.Context, level, contextID string, userID *string) (*entities.OrderedMap[any], error) {
	contextLevel, err := value_objects.ContextLevelFromEnumValue(level)
	if err != nil {
		return zpUCSError(err.Error()), nil
	}
	if contextLevel == value_objects.ContextLevelGlobal {
		effectiveUser := userOrDefault(userID, s.UserID)
		normalized, nerr := s.normalizeGlobalContextID(contextID, effectiveUser)
		if nerr != nil {
			return zpUCSError(nerr.Error()), nil
		}
		contextID = normalized
	}
	repository := s.getUserScopedRepository(s.repositories[contextLevel])
	if repository == nil {
		return zpUCSError(fmt.Sprintf("No repository configured for level: %s", level)), nil
	}
	repo := s.getUserScopedRepository(repository)
	existing, gerr := repo.Get(ctx, contextID)
	if gerr != nil {
		// Python reports a repository exception as str(e), not as "not found".
		return zpUCSError(gerr.Error()), nil
	}
	if existing == nil {
		return zpUCSError(fmt.Sprintf("Context not found: %s", contextID)), nil
	}
	result, derr := repo.Delete(ctx, contextID)
	if derr != nil {
		return zpUCSError(derr.Error()), nil
	}
	resp := entities.NewOrderedMap[any]()
	resp.Set("success", result)
	resp.Set("level", level)
	resp.Set("context_id", contextID)
	return resp, nil
}

// ResolveContext mirrors resolve_context.
func (s *UnifiedContextService) ResolveContext(ctx context.Context, level, contextID string, forceRefresh bool, userID *string) (*entities.OrderedMap[any], error) {
	contextLevel, err := value_objects.ContextLevelFromEnumValue(level)
	if err != nil {
		return zpUCSError(err.Error()), nil
	}
	if contextLevel == value_objects.ContextLevelGlobal {
		effectiveUser := userOrDefault(userID, s.UserID)
		normalized, nerr := s.normalizeGlobalContextID(contextID, effectiveUser)
		if nerr != nil {
			return zpUCSError(nerr.Error()), nil
		}
		contextID = normalized
	}
	result, _ := s.GetContext(ctx, level, contextID, true, forceRefresh, nil)
	if success, _ := result.Get("success"); success == true {
		result.Set("resolved", true)
		result.Set("inheritance_applied", true)
	}
	return result, nil
}

// DelegateContext mirrors delegate_context (delegation is skipped in sync mode).
func (s *UnifiedContextService) DelegateContext(ctx context.Context, level, contextID, delegateTo string, data *entities.OrderedMap[any], delegationReason *string) (*entities.OrderedMap[any], error) {
	if _, err := value_objects.ContextLevelFromEnumValue(level); err != nil {
		return zpUCSError(err.Error()), nil
	}
	if _, err := value_objects.ContextLevelFromEnumValue(delegateTo); err != nil {
		return zpUCSError(err.Error()), nil
	}
	delegationResult := entities.NewOrderedMap[any]()
	delegationResult.Set("success", true)
	delegationResult.Set("message", "Delegation skipped in sync mode")
	resp := entities.NewOrderedMap[any]()
	resp.Set("success", true)
	resp.Set("delegation", delegationResult)
	resp.Set("source_level", level)
	resp.Set("target_level", delegateTo)
	resp.Set("context_id", contextID)
	return resp, nil
}

// ListContexts mirrors list_contexts.
func (s *UnifiedContextService) ListContexts(ctx context.Context, level string, filters *entities.OrderedMap[any]) (*entities.OrderedMap[any], error) {
	contextLevel, err := value_objects.ContextLevelFromEnumValue(level)
	if err != nil {
		return zpUCSError(err.Error()), nil
	}
	repository := s.getUserScopedRepository(s.repositories[contextLevel])
	if repository == nil {
		return zpUCSError(fmt.Sprintf("No repository configured for level: %s", level)), nil
	}
	repo := s.getUserScopedRepository(repository)
	contexts, lerr := repo.List(ctx, zpUCSMap(filters))
	if lerr != nil {
		return zpUCSError(lerr.Error()), nil
	}
	dicts := make([]any, 0, len(contexts))
	for _, c := range contexts {
		dicts = append(dicts, s.entityToDict(c))
	}
	resp := entities.NewOrderedMap[any]()
	resp.Set("success", true)
	resp.Set("contexts", dicts)
	resp.Set("level", level)
	resp.Set("count", len(contexts))
	return resp, nil
}

// AddInsight mirrors add_insight.
func (s *UnifiedContextService) AddInsight(ctx context.Context, level, contextID, content string, category, importance, agent *string) (*entities.OrderedMap[any], error) {
	contextResult, _ := s.GetContext(ctx, level, contextID, false, false, nil)
	if success, _ := contextResult.Get("success"); success != true {
		return contextResult, nil
	}
	contextVal, _ := contextResult.Get("context")
	contextOM := zpUCSAsOrdered(contextVal)
	insights := zpUCSList(contextOM, "insights")
	insight := entities.NewOrderedMap[any]()
	insight.Set("content", content)
	cat := "general"
	if category != nil {
		cat = *category
	}
	insight.Set("category", cat)
	imp := "medium"
	if importance != nil {
		imp = *importance
	}
	insight.Set("importance", imp)
	if agent != nil {
		insight.Set("agent", *agent)
	} else {
		insight.Set("agent", "unified_context_service")
	}
	insight.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))
	insights = append(insights, insight)
	update := entities.NewOrderedMap[any]()
	update.Set("insights", insights)
	return s.UpdateContext(ctx, level, contextID, update, true, nil)
}

// AddProgress mirrors add_progress.
func (s *UnifiedContextService) AddProgress(ctx context.Context, level, contextID, content string, agent *string) (*entities.OrderedMap[any], error) {
	contextResult, _ := s.GetContext(ctx, level, contextID, false, false, nil)
	if success, _ := contextResult.Get("success"); success != true {
		return contextResult, nil
	}
	contextVal, _ := contextResult.Get("context")
	contextOM := zpUCSAsOrdered(contextVal)
	// The entity's load (createContextEntity / updateContextEntity) reads its notes from the top-level
	// implementation_notes key, so a note written anywhere else is a write no reader can find. Inside that
	// map the merge replaces progress_updates wholesale; at the top level it would append-merge and
	// duplicate the entry on every call.
	implementationNotes := zpUCSAsOrdered(zpUCSGetOr(contextOM, "implementation_notes", nil))
	progressUpdates := zpUCSList(implementationNotes, "progress_updates")
	progress := entities.NewOrderedMap[any]()
	progress.Set("content", content)
	if agent != nil {
		progress.Set("agent", *agent)
	} else {
		progress.Set("agent", "unified_context_service")
	}
	progress.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))
	progressUpdates = append(progressUpdates, progress)
	implementationNotes.Set("progress_updates", progressUpdates)
	update := entities.NewOrderedMap[any]()
	update.Set("implementation_notes", implementationNotes)
	return s.UpdateContext(ctx, level, contextID, update, true, nil)
}

// AutoCreateContextIfMissing mirrors auto_create_context_if_missing.
func (s *UnifiedContextService) AutoCreateContextIfMissing(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID, projectID, gitBranchID *string) (*entities.OrderedMap[any], error) {
	contextLevel, err := value_objects.ContextLevelFromEnumValue(level)
	if err != nil {
		return zpUCSError(err.Error()), nil
	}
	repository := s.getUserScopedRepository(s.repositories[contextLevel])
	if repository == nil {
		return zpUCSError(fmt.Sprintf("No repository configured for level: %s", level)), nil
	}
	if existing, gerr := repository.Get(ctx, contextID); gerr == nil && existing != nil {
		resp := entities.NewOrderedMap[any]()
		resp.Set("success", true)
		resp.Set("message", fmt.Sprintf("Context %s already exists", contextID))
		resp.Set("context", s.entityToDict(existing))
		resp.Set("created", false)
		return resp, nil
	}
	contextData := data
	if contextData == nil || contextData.Len() == 0 {
		contextData = s.buildDefaultContextData(level, contextID, entities.NewOrderedMap[any](), projectID, gitBranchID)
	}
	result, _ := s.CreateContext(ctx, level, contextID, contextData, userID, projectID, true)
	if success, _ := result.Get("success"); success == true {
		result.Set("created", true)
	}
	return result, nil
}

// BootstrapContextHierarchy mirrors bootstrap_context_hierarchy.
func (s *UnifiedContextService) BootstrapContextHierarchy(ctx context.Context, userID, projectID, branchID *string) (*entities.OrderedMap[any], error) {
	createdContexts := entities.NewOrderedMap[any]()
	errorsList := []string{}

	globalResult, _ := s.ensureGlobalContextExists(ctx, userID)
	if success, _ := globalResult.Get("success"); success == true {
		entry := entities.NewOrderedMap[any]()
		ctxID, _ := globalResult.Get("context_id")
		entry.Set("id", ctxID)
		created, _ := globalResult.Get("created")
		entry.Set("created", created)
		createdContexts.Set("global", entry)
	} else {
		errVal, _ := globalResult.Get("error")
		errorsList = append(errorsList, fmt.Sprintf("Global context creation failed: %v", errVal))
	}

	if projectID != nil {
		projectResult, _ := s.ensureProjectContextExists(ctx, *projectID, userID)
		if success, _ := projectResult.Get("success"); success == true {
			entry := entities.NewOrderedMap[any]()
			ctxID, _ := projectResult.Get("context_id")
			entry.Set("id", ctxID)
			created, _ := projectResult.Get("created")
			entry.Set("created", created)
			createdContexts.Set("project", entry)
		} else {
			errVal, _ := projectResult.Get("error")
			errorsList = append(errorsList, fmt.Sprintf("Project context creation failed: %v", errVal))
		}
	}

	if branchID != nil && projectID != nil {
		branchResult, _ := s.ensureBranchContextExists(ctx, *branchID, *projectID, userID)
		if success, _ := branchResult.Get("success"); success == true {
			entry := entities.NewOrderedMap[any]()
			ctxID, _ := branchResult.Get("context_id")
			entry.Set("id", ctxID)
			created, _ := branchResult.Get("created")
			entry.Set("created", created)
			createdContexts.Set("branch", entry)
		} else {
			errVal, _ := branchResult.Get("error")
			errorsList = append(errorsList, fmt.Sprintf("Branch context creation failed: %v", errVal))
		}
	}

	success := len(errorsList) == 0 && createdContexts.Len() > 0
	result := entities.NewOrderedMap[any]()
	result.Set("success", success)
	result.Set("bootstrap_completed", true)
	result.Set("created_contexts", createdContexts)
	result.Set("hierarchy_ready", createdContexts.Len() > 0)
	if len(errorsList) > 0 {
		result.Set("errors", errorsList)
		result.Set("partial_success", createdContexts.Len() > 0)
	}
	result.Set("usage_guidance", s.generateBootstrapUsageGuidance(createdContexts))
	return result, nil
}

// generateBootstrapUsageGuidance mirrors _generate_bootstrap_usage_guidance.
func (s *UnifiedContextService) generateBootstrapUsageGuidance(createdContexts *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	guidance := entities.NewOrderedMap[any]()
	nextSteps := []any{}
	examples := []any{}
	guidance.Set("next_steps", nextSteps)
	guidance.Set("examples", examples)
	if createdContexts == nil {
		return guidance
	}
	if entry, ok := createdContexts.Get("global"); ok {
		nextSteps = append(nextSteps, "Global context is ready for organization-wide settings")
		id, _ := zpUCSAsOrdered(entry).Get("id")
		ex := entities.NewOrderedMap[any]()
		ex.Set("action", "Update global settings")
		ex.Set("command", fmt.Sprintf("manage_context(action=\"update\", level=\"global\", context_id=\"%v\", data={\"global_settings\": {\"timezone\": \"UTC\"}})", id))
		examples = append(examples, ex)
	}
	if entry, ok := createdContexts.Get("project"); ok {
		nextSteps = append(nextSteps, "Project context is ready for project-specific configuration")
		id, _ := zpUCSAsOrdered(entry).Get("id")
		ex := entities.NewOrderedMap[any]()
		ex.Set("action", "Update project settings")
		ex.Set("command", fmt.Sprintf("manage_context(action=\"update\", level=\"project\", context_id=\"%v\", data={\"project_settings\": {\"default_branch\": \"main\"}})", id))
		examples = append(examples, ex)
	}
	if entry, ok := createdContexts.Get("branch"); ok {
		nextSteps = append(nextSteps, "Branch context is ready for branch-specific workflows")
		id, _ := zpUCSAsOrdered(entry).Get("id")
		ex := entities.NewOrderedMap[any]()
		ex.Set("action", "Update branch settings")
		ex.Set("command", fmt.Sprintf("manage_context(action=\"update\", level=\"branch\", context_id=\"%v\", data={\"branch_settings\": {\"workflow_type\": \"gitflow\"}})", id))
		examples = append(examples, ex)
	}
	guidance.Set("next_steps", nextSteps)
	guidance.Set("examples", examples)
	return guidance
}

// buildDefaultContextData mirrors _build_default_context_data.
func (s *UnifiedContextService) buildDefaultContextData(level, contextID string, data *entities.OrderedMap[any], projectID, gitBranchID *string) *entities.OrderedMap[any] {
	if data == nil {
		data = entities.NewOrderedMap[any]()
	}
	timestamp := value_objects.IsoFormat(time.Now().UTC())
	defaultMetadata := entities.NewOrderedMap[any]()
	defaultMetadata.Set("auto_created", true)
	defaultMetadata.Set("created_at", timestamp)
	defaultMetadata.Set("created_by", "auto_creation_service")
	baseMetadata := zpUCSAsOrdered(zpUCSGetOr(data, "metadata", nil)) // Python raises TypeError on an explicit null; Go treats it as {}
	mergedMetadata := defaultMetadata.Copy()
	for _, key := range baseMetadata.Keys() {
		v, _ := baseMetadata.Get(key)
		mergedMetadata.Set(key, v)
	}

	out := entities.NewOrderedMap[any]()
	switch level {
	case "global":
		out.Set("organization_name", zpUCSGetKey(data, "organization_name", "Default Organization"))
		gs, gsPresent := zpUCSGetPresent(data, "global_settings")
		if !gsPresent {
			gsOM := entities.NewOrderedMap[any]()
			gsOM.Set("default_timezone", "UTC")
			gsOM.Set("auto_create_contexts", true)
			gs = gsOM
		}
		out.Set("global_settings", gs)
		out.Set("metadata", mergedMetadata)
	case "project":
		out.Set("project_name", zpUCSGetKey(data, "project_name", fmt.Sprintf("Project %s", zpUCSFirst8(contextID))))
		ps, psPresent := zpUCSGetPresent(data, "project_settings")
		if !psPresent {
			psOM := entities.NewOrderedMap[any]()
			psOM.Set("auto_context_creation", true)
			psOM.Set("default_branch", "main")
			ps = psOM
		}
		out.Set("project_settings", ps)
		out.Set("metadata", mergedMetadata)
	case "branch":
		var pid any
		if projectID != nil && value_objects.PyTruthy(*projectID) {
			pid = *projectID
		} else {
			pid, _ = zpUCSGetPresent(data, "project_id")
		}
		out.Set("project_id", pid)
		out.Set("git_branch_name", zpUCSGetKey(data, "git_branch_name", "main"))
		bs, bsPresent := zpUCSGetPresent(data, "branch_settings")
		if !bsPresent {
			bsOM := entities.NewOrderedMap[any]()
			bsOM.Set("auto_created", true)
			bsOM.Set("workflow_type", "standard")
			bs = bsOM
		}
		out.Set("branch_settings", bs)
		out.Set("metadata", mergedMetadata)
	case "task":
		// git_branch_id or base.get("branch_id") or base.get("parent_branch_id"):
		// the last operand is returned even when falsy.
		var branchVal any
		if gitBranchID != nil && value_objects.PyTruthy(*gitBranchID) {
			branchVal = *gitBranchID
		} else if v, _ := zpUCSGetPresent(data, "branch_id"); value_objects.PyTruthy(v) {
			branchVal = v
		} else {
			branchVal, _ = zpUCSGetPresent(data, "parent_branch_id")
		}
		out.Set("branch_id", branchVal)
		td, tdPresent := zpUCSGetPresent(data, "task_data")
		if !tdPresent {
			tdOM := entities.NewOrderedMap[any]()
			tdOM.Set("title", zpUCSGetKey(data, "title", fmt.Sprintf("Task %s", zpUCSFirst8(contextID))))
			tdOM.Set("description", zpUCSGetKey(data, "description", "Auto-created task context"))
			tdOM.Set("auto_created", true)
			td = tdOM
		}
		out.Set("task_data", td)
		out.Set("progress", zpUCSGetKey(data, "progress", 0))
		out.Set("insights", zpUCSGetKey(data, "insights", []any{}))
		out.Set("next_steps", zpUCSGetKey(data, "next_steps", []any{}))
		out.Set("metadata", mergedMetadata)
	default:
		copy := data.Copy()
		for _, key := range copy.Keys() {
			v, _ := copy.Get(key)
			out.Set(key, v)
		}
		out.Set("metadata", mergedMetadata)
	}
	return out
}

// createContextEntity mirrors _create_context_entity.
func (s *UnifiedContextService) createContextEntity(level value_objects.ContextLevel, contextID string, data *entities.OrderedMap[any], userID, projectID *string) any {
	serialized := s.serializeForJSON(data)
	data = zpUCSAsOrdered(serialized)

	switch level {
	case value_objects.ContextLevelGlobal:
		metadata := zpUCSAsOrdered(zpUCSGetOr(data, "metadata", nil)).Copy()
		effectiveUser := userOrDefault(userID, s.UserID)
		if effectiveUser == nil {
			return nil
		}
		metadata.Set("user_id", *effectiveUser)
		orgName := "Default Organization"
		if v, ok := data.Get("organization_name"); ok {
			if s, isStr := v.(string); isStr {
				orgName = s
			}
		}
		return entities.NewGlobalContext(contextID, orgName, zpUCSMap(data), zpUCSMap(metadata))
	case value_objects.ContextLevelProject:
		predefined := map[string]bool{"team_preferences": true, "technology_stack": true, "project_workflow": true, "local_standards": true, "project_name": true, "project_settings": true, "metadata": true}
		localStandards := zpUCSAsOrdered(zpUCSGetOr(data, "local_standards", nil)).Copy()
		customFields := entities.NewOrderedMap[any]()
		for _, key := range data.Keys() {
			if !predefined[key] {
				v, _ := data.Get(key)
				customFields.Set(key, v)
			}
		}
		if customFields.Len() > 0 {
			existingCustom := zpUCSAsOrdered(zpUCSGetOr(localStandards, "_custom", nil)).Copy()
			for _, key := range customFields.Keys() {
				v, _ := customFields.Get(key)
				existingCustom.Set(key, v)
			}
			localStandards.Set("_custom", existingCustom)
		}
		projectName := "Unnamed Project"
		if v, ok := data.Get("project_name"); ok {
			if s, isStr := v.(string); isStr {
				projectName = s
			}
		}
		return &entities.ProjectContext{
			ID: contextID, ProjectName: projectName,
			ProjectInfo:             zpUCSMap(zpUCSGetOr(data, "project_info", nil)),
			TeamPreferences:         zpUCSMap(zpUCSGetOr(data, "team_preferences", nil)),
			TechnologyStack:         zpUCSMap(zpUCSGetOr(data, "technology_stack", nil)),
			ProjectWorkflow:         zpUCSMap(zpUCSGetOr(data, "project_workflow", nil)),
			LocalStandards:          zpUCSMap(localStandards),
			ProjectSettings:         zpUCSMap(zpUCSGetOr(data, "project_settings", nil)),
			TechnicalSpecifications: zpUCSMap(zpUCSGetOr(data, "technical_specifications", nil)),
			Metadata:                zpUCSMap(zpUCSGetOr(data, "metadata", nil)),
		}
	case value_objects.ContextLevelBranch:
		predefined := map[string]bool{"branch_info": true, "branch_workflow": true, "feature_flags": true, "discovered_patterns": true, "branch_decisions": true, "branch_settings": true, "branch_standards": true, "agent_assignments": true, "metadata": true, "project_id": true, "git_branch_name": true, "active_patterns": true, "local_overrides": true, "delegation_rules": true}
		branchWorkflow := zpUCSAsOrdered(zpUCSGetOr(data, "branch_workflow", nil))
		branchSettings := zpUCSAsOrdered(zpUCSGetOr(data, "branch_settings", nil)).Copy()
		if branchSettings.Len() == 0 {
			branchSettings.Set("branch_workflow", zpUCSGetOr(data, "branch_workflow", nil))
			branchSettings.Set("branch_standards", zpUCSGetOr(data, "branch_standards", nil))
			branchSettings.Set("agent_assignments", zpUCSGetOr(data, "agent_assignments", nil))
		}
		metadata := zpUCSAsOrdered(zpUCSGetOr(data, "metadata", nil)).Copy()
		effectiveUser := userOrDefault(userID, s.UserID)
		if effectiveUser == nil {
			return nil
		}
		metadata.Set("user_id", *effectiveUser)
		metadata.Set("active_patterns", zpUCSGetOr(data, "active_patterns", nil))
		metadata.Set("local_overrides", zpUCSGetOr(data, "local_overrides", nil))
		metadata.Set("delegation_rules", zpUCSGetOr(data, "delegation_rules", nil))
		for _, key := range data.Keys() {
			if !predefined[key] {
				v, _ := data.Get(key)
				metadata.Set(key, v)
			}
		}
		pid := zpUCSGetOr(data, "project_id", nil)
		if projectID != nil {
			pid = *projectID
		}
		gitBranchName := "main"
		if v, ok := data.Get("git_branch_name"); ok {
			if s, isStr := v.(string); isStr {
				gitBranchName = s
			}
		}
		return &entities.BranchContext{
			ID: contextID, ProjectID: zpUCSStr(pid), GitBranchName: gitBranchName,
			BranchInfo:         zpUCSMap(zpUCSGetOr(data, "branch_info", nil)),
			BranchWorkflow:     zpUCSMap(branchWorkflow),
			FeatureFlags:       zpUCSMap(zpUCSGetOr(data, "feature_flags", nil)),
			DiscoveredPatterns: zpUCSMap(zpUCSGetOr(data, "discovered_patterns", nil)),
			BranchDecisions:    zpUCSMap(zpUCSGetOr(data, "branch_decisions", nil)),
			BranchSettings:     zpUCSMap(branchSettings),
			Metadata:           zpUCSMap(metadata),
		}
	case value_objects.ContextLevelTask:
		branchID := zpUCSGetOr(data, "branch_id", nil)
		if branchID == nil {
			branchID = zpUCSGetOr(data, "parent_branch_id", nil)
		}
		if branchID == nil {
			branchID = zpUCSGetOr(data, "git_branch_id", nil)
		}
		if branchID == nil {
			return nil
		}
		branchIDStr := zpUCSStr(branchID)
		metadata := zpUCSAsOrdered(zpUCSGetOr(data, "metadata", nil)).Copy()
		metadata.Set("execution_context", zpUCSGetOr(data, "execution_context", nil))
		metadata.Set("discovered_patterns", zpUCSGetOr(data, "discovered_patterns", nil))
		metadata.Set("test_results", zpUCSGetOr(data, "test_results", nil))
		metadata.Set("blockers", zpUCSGetOr(data, "blockers", nil))
		t := entities.NewTaskContextUnified(contextID, branchIDStr)
		t.TaskData = zpUCSMap(zpUCSGetOr(data, "task_data", nil))
		t.ExecutionContext = zpUCSMap(zpUCSGetOr(data, "execution_context", nil))
		t.DiscoveredPatterns = zpUCSMap(zpUCSGetOr(data, "discovered_patterns", nil))
		t.ImplementationNotes = zpUCSMap(zpUCSGetOr(data, "implementation_notes", nil))
		t.TestResults = zpUCSMap(zpUCSGetOr(data, "test_results", nil))
		t.Blockers = zpUCSMap(zpUCSGetOr(data, "blockers", nil))
		t.Progress = zpUCSInt(zpUCSGetOr(data, "progress", 0))
		if v, ok := data.Get("insights"); ok {
			if l, isList := v.([]any); isList {
				t.Insights = l
			}
		}
		if v, ok := data.Get("next_steps"); ok {
			if l, isList := v.([]any); isList {
				t.NextSteps = l
			}
		}
		t.Metadata = zpUCSMap(metadata)
		return t
	}
	return nil
}

// entityToDict mirrors _entity_to_dict using the Go entity ToDict() map method.
func (s *UnifiedContextService) entityToDict(entity any) *entities.OrderedMap[any] {
	if entity == nil {
		return entities.NewOrderedMap[any]()
	}
	if d, ok := entity.(interface{ ToDict() map[string]any }); ok {
		return zpUCSFromMap(d.ToDict())
	}
	return entities.NewOrderedMap[any]()
}

// mergeContextData mirrors _merge_context_data.
func (s *UnifiedContextService) mergeContextData(existingData, newData *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if existingData == nil {
		existingData = entities.NewOrderedMap[any]()
	}
	if newData == nil {
		newData = entities.NewOrderedMap[any]()
	}
	// Python serializes both inputs before merging, which also detaches the result
	// from the caller's nested objects.
	existingData = zpUCSAsOrdered(s.serializeForJSON(existingData))
	newData = zpUCSAsOrdered(s.serializeForJSON(newData))
	merged := existingData.Copy()
	replaceListFields := map[string]bool{"insights": true, "next_steps": true}
	for _, key := range newData.Keys() {
		value, _ := newData.Get(key)
		existing, hasExisting := merged.Get(key)
		if newMap, ok := value.(*entities.OrderedMap[any]); ok {
			if existingMap, ok := existing.(*entities.OrderedMap[any]); hasExisting && ok {
				deep := existingMap.Copy()
				for _, k := range newMap.Keys() {
					v, _ := newMap.Get(k)
					deep.Set(k, v)
				}
				merged.Set(key, deep)
				continue
			}
		}
		if newList, ok := value.([]any); ok && !replaceListFields[key] {
			if existingList, ok := existing.([]any); hasExisting && ok {
				merged.Set(key, append(append([]any{}, existingList...), newList...))
				continue
			}
		}
		merged.Set(key, value)
	}
	return merged
}

// updateContextEntity mirrors _update_context_entity.
func (s *UnifiedContextService) updateContextEntity(existingEntity any, newData *entities.OrderedMap[any]) any {
	switch existing := existingEntity.(type) {
	case *entities.TaskContextUnified:
		t := entities.NewTaskContextUnified(zpUCSGetOr(newData, "id", existing.ID).(string), zpUCSGetOr(newData, "branch_id", existing.BranchID).(string))
		t.TaskData = zpUCSMap(zpUCSGetOr(newData, "task_data", existing.TaskData))
		t.ExecutionContext = zpUCSMap(zpUCSGetOr(newData, "execution_context", existing.ExecutionContext))
		t.DiscoveredPatterns = zpUCSMap(zpUCSGetOr(newData, "discovered_patterns", existing.DiscoveredPatterns))
		t.ImplementationNotes = zpUCSMap(zpUCSGetOr(newData, "implementation_notes", existing.ImplementationNotes))
		t.TestResults = zpUCSMap(zpUCSGetOr(newData, "test_results", existing.TestResults))
		t.Blockers = zpUCSMap(zpUCSGetOr(newData, "blockers", existing.Blockers))
		t.Progress = zpUCSInt(zpUCSGetOr(newData, "progress", existing.Progress))
		if v, ok := newData.Get("insights"); ok {
			if l, isList := v.([]any); isList {
				t.Insights = l
			}
		} else {
			t.Insights = existing.Insights
		}
		if v, ok := newData.Get("next_steps"); ok {
			if l, isList := v.([]any); isList {
				t.NextSteps = l
			}
		} else {
			t.NextSteps = existing.NextSteps
		}
		t.Metadata = zpUCSMap(zpUCSGetOr(newData, "metadata", existing.Metadata))
		return t
	case *entities.ProjectContext:
		return &entities.ProjectContext{
			ID:                      zpUCSStrOr(newData, "id", existing.ID),
			ProjectName:             zpUCSStrOr(newData, "project_name", existing.ProjectName),
			ProjectInfo:             zpUCSMap(zpUCSGetOr(newData, "project_info", existing.ProjectInfo)),
			TeamPreferences:         zpUCSMap(zpUCSGetOr(newData, "team_preferences", existing.TeamPreferences)),
			TechnologyStack:         zpUCSMap(zpUCSGetOr(newData, "technology_stack", existing.TechnologyStack)),
			ProjectWorkflow:         zpUCSMap(zpUCSGetOr(newData, "project_workflow", existing.ProjectWorkflow)),
			LocalStandards:          zpUCSMap(zpUCSGetOr(newData, "local_standards", existing.LocalStandards)),
			ProjectSettings:         zpUCSMap(zpUCSGetOr(newData, "project_settings", existing.ProjectSettings)),
			TechnicalSpecifications: zpUCSMap(zpUCSGetOr(newData, "technical_specifications", existing.TechnicalSpecifications)),
			Metadata:                zpUCSMap(zpUCSGetOr(newData, "metadata", existing.Metadata)),
		}
	case *entities.GlobalContext:
		return entities.NewGlobalContext(
			zpUCSStrOr(newData, "id", existing.ID),
			zpUCSStrOr(newData, "organization_name", existing.OrganizationName),
			zpUCSMap(zpUCSGetOr(newData, "global_settings", existing.GlobalSettings)),
			zpUCSMap(zpUCSGetOr(newData, "metadata", existing.Metadata)),
		)
	case *entities.BranchContext:
		return &entities.BranchContext{
			ID:                 zpUCSStrOr(newData, "id", existing.ID),
			ProjectID:          zpUCSStrOr(newData, "project_id", existing.ProjectID),
			GitBranchName:      zpUCSStrOr(newData, "git_branch_name", existing.GitBranchName),
			BranchInfo:         zpUCSMap(zpUCSGetOr(newData, "branch_info", existing.BranchInfo)),
			BranchWorkflow:     zpUCSMap(zpUCSGetOr(newData, "branch_workflow", existing.BranchWorkflow)),
			FeatureFlags:       zpUCSMap(zpUCSGetOr(newData, "feature_flags", existing.FeatureFlags)),
			DiscoveredPatterns: zpUCSMap(zpUCSGetOr(newData, "discovered_patterns", existing.DiscoveredPatterns)),
			BranchDecisions:    zpUCSMap(zpUCSGetOr(newData, "branch_decisions", existing.BranchDecisions)),
			BranchSettings:     zpUCSMap(zpUCSGetOr(newData, "branch_settings", existing.BranchSettings)),
			Metadata:           zpUCSMap(zpUCSGetOr(newData, "metadata", existing.Metadata)),
		}
	}
	return existingEntity
}

// resolveInheritanceSync mirrors _resolve_inheritance_sync.
func (s *UnifiedContextService) resolveInheritanceSync(ctx context.Context, level value_objects.ContextLevel, contextEntity any, contextData *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	inheritanceChain := []*entities.OrderedMap[any]{}
	globalRepo := s.repositories[value_objects.ContextLevelGlobal]
	if globalRepo != nil && s.UserID != nil {
		globalContextID := *s.UserID
		if globalEntity, err := globalRepo.Get(ctx, globalContextID); err == nil && globalEntity != nil {
			entry := entities.NewOrderedMap[any]()
			entry.Set("level", "global")
			entry.Set("id", globalContextID)
			entry.Set("data", s.entityToDict(globalEntity))
			inheritanceChain = append(inheritanceChain, entry)
		}
	}
	if level == value_objects.ContextLevelProject || level == value_objects.ContextLevelBranch || level == value_objects.ContextLevelTask {
		projectID := ""
		if level == value_objects.ContextLevelProject {
			projectID = zpUCSEntityID(contextEntity)
		} else if branchID := zpUCSEntityField(contextEntity, "ProjectID"); level == value_objects.ContextLevelBranch && branchID != "" {
			projectID = branchID
		} else if level == value_objects.ContextLevelTask {
			if branchID := zpUCSEntityField(contextEntity, "BranchID"); branchID != "" {
				if branchRepo := s.repositories[value_objects.ContextLevelBranch]; branchRepo != nil {
					if branchEntity, err := branchRepo.Get(ctx, branchID); err == nil && branchEntity != nil {
						projectID = zpUCSEntityField(branchEntity, "ProjectID")
					}
				}
			}
		}
		if projectID != "" {
			if projectRepo := s.repositories[value_objects.ContextLevelProject]; projectRepo != nil {
				if projectEntity, err := projectRepo.Get(ctx, projectID); err == nil && projectEntity != nil {
					entry := entities.NewOrderedMap[any]()
					entry.Set("level", "project")
					entry.Set("id", projectID)
					entry.Set("data", s.entityToDict(projectEntity))
					inheritanceChain = append(inheritanceChain, entry)
				}
			}
		}
	}
	if level == value_objects.ContextLevelBranch || level == value_objects.ContextLevelTask {
		branchID := ""
		if level == value_objects.ContextLevelBranch {
			branchID = zpUCSEntityID(contextEntity)
		} else {
			branchID = zpUCSEntityField(contextEntity, "BranchID")
		}
		if branchID != "" {
			if branchRepo := s.repositories[value_objects.ContextLevelBranch]; branchRepo != nil {
				if branchEntity, err := branchRepo.Get(ctx, branchID); err == nil && branchEntity != nil {
					entry := entities.NewOrderedMap[any]()
					entry.Set("level", "branch")
					entry.Set("id", branchID)
					entry.Set("data", s.entityToDict(branchEntity))
					inheritanceChain = append(inheritanceChain, entry)
				}
			}
		}
	}
	levelInChain := false
	for _, item := range inheritanceChain {
		if v, _ := item.Get("level"); v == level.String() {
			levelInChain = true
		}
	}
	if !levelInChain {
		entry := entities.NewOrderedMap[any]()
		entry.Set("level", level.String())
		entry.Set("id", zpUCSEntityID(contextEntity))
		entry.Set("data", contextData)
		inheritanceChain = append(inheritanceChain, entry)
	}
	if len(inheritanceChain) > 1 {
		merged := s.mergeInheritanceChain(inheritanceChain)
		levels := make([]any, 0, len(inheritanceChain))
		for _, item := range inheritanceChain {
			v, _ := item.Get("level")
			levels = append(levels, v)
		}
		meta := entities.NewOrderedMap[any]()
		meta.Set("chain", levels)
		meta.Set("resolved_at", value_objects.IsoFormat(time.Now().UTC()))
		meta.Set("inheritance_depth", len(inheritanceChain))
		merged.Set("_inheritance", meta)
		return merged
	}
	return contextData
}

// mergeInheritanceChain mirrors _merge_inheritance_chain.
func (s *UnifiedContextService) mergeInheritanceChain(inheritanceChain []*entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if len(inheritanceChain) == 0 {
		return entities.NewOrderedMap[any]()
	}
	firstData, _ := inheritanceChain[0].Get("data")
	merged := zpUCSAsOrdered(firstData).Copy()
	for i := 1; i < len(inheritanceChain); i++ {
		currentLevel, _ := inheritanceChain[i].Get("level")
		currentData, _ := inheritanceChain[i].Get("data")
		currentOM := zpUCSAsOrdered(currentData)
		switch currentLevel {
		case "project":
			if s.InheritanceService != nil {
				merged = s.InheritanceService.InheritProjectFromGlobal(merged, currentOM)
				continue
			}
		case "branch":
			if s.InheritanceService != nil {
				merged = s.InheritanceService.InheritBranchFromProject(merged, currentOM)
				continue
			}
		case "task":
			if s.InheritanceService != nil {
				merged = s.InheritanceService.InheritTaskFromBranch(merged, currentOM)
				continue
			}
		}
		merged = s.mergeContextData(merged, currentOM)
	}
	return merged
}

// ensureParentContextsExist mirrors _ensure_parent_contexts_exist.
func (s *UnifiedContextService) ensureParentContextsExist(ctx context.Context, targetLevel value_objects.ContextLevel, contextID string, data *entities.OrderedMap[any], userID, projectID *string) *entities.OrderedMap[any] {
	createdContexts := []any{}
	ensuredContexts := []any{}
	errorsList := []string{}
	effectiveUserID := userOrDefault(userID, s.UserID)
	switch targetLevel {
	case value_objects.ContextLevelProject:
		globalResult, _ := s.ensureGlobalContextExists(ctx, effectiveUserID)
		if success, _ := globalResult.Get("success"); success == true {
			if created, _ := globalResult.Get("created"); created == true {
				createdContexts = append(createdContexts, "global")
			} else {
				ensuredContexts = append(ensuredContexts, "global")
			}
		} else {
			errVal, _ := globalResult.Get("error")
			errorsList = append(errorsList, fmt.Sprintf("Global context: %v", errVal))
		}
	case value_objects.ContextLevelBranch:
		// project_id or data.get("project_id")
		branchProjectID := ""
		if projectID != nil && *projectID != "" {
			branchProjectID = *projectID
		} else if v, _ := zpUCSGetPresent(data, "project_id"); value_objects.PyTruthy(v) {
			branchProjectID = zpUCSStr(v)
		}
		if branchProjectID == "" {
			resp := entities.NewOrderedMap[any]()
			resp.Set("success", false)
			resp.Set("error", "No project_id available for branch context parent creation")
			resp.Set("guidance", "Provide project_id in data or as parameter")
			return resp
		}
		globalResult, _ := s.ensureGlobalContextExists(ctx, effectiveUserID)
		if success, _ := globalResult.Get("success"); success == true {
			if created, _ := globalResult.Get("created"); created == true {
				createdContexts = append(createdContexts, "global")
			} else {
				ensuredContexts = append(ensuredContexts, "global")
			}
		} else {
			errVal, _ := globalResult.Get("error")
			errorsList = append(errorsList, fmt.Sprintf("Global context: %v", errVal))
		}
		projectResult, _ := s.ensureProjectContextExists(ctx, branchProjectID, effectiveUserID)
		if success, _ := projectResult.Get("success"); success == true {
			if created, _ := projectResult.Get("created"); created == true {
				createdContexts = append(createdContexts, "project")
			} else {
				ensuredContexts = append(ensuredContexts, "project")
			}
		} else {
			errVal, _ := projectResult.Get("error")
			errorsList = append(errorsList, fmt.Sprintf("Project context: %v", errVal))
		}
	case value_objects.ContextLevelTask:
		// data.get("branch_id") or data.get("parent_branch_id") or data.get("git_branch_id")
		var branchVal any
		for _, key := range []string{"branch_id", "parent_branch_id", "git_branch_id"} {
			if v, _ := zpUCSGetPresent(data, key); value_objects.PyTruthy(v) {
				branchVal = v
				break
			}
		}
		if branchVal == nil {
			resp := entities.NewOrderedMap[any]()
			resp.Set("success", false)
			resp.Set("error", "No branch_id available for task context parent creation")
			resp.Set("guidance", "Provide branch_id, parent_branch_id, or git_branch_id in data")
			return resp
		}
		branchID := zpUCSStr(branchVal)
		taskProjectID := ""
		if projectID != nil {
			taskProjectID = *projectID
		}
		if taskProjectID == "" {
			taskProjectID = s.resolveProjectIDFromBranch(ctx, branchID)
		}
		if taskProjectID == "" {
			resp := entities.NewOrderedMap[any]()
			resp.Set("success", false)
			resp.Set("error", "No project_id available for task context parent creation")
			resp.Set("guidance", "Ensure branch exists with project_id or provide project_id parameter")
			return resp
		}
		globalResult, _ := s.ensureGlobalContextExists(ctx, effectiveUserID)
		if success, _ := globalResult.Get("success"); success == true {
			if created, _ := globalResult.Get("created"); created == true {
				createdContexts = append(createdContexts, "global")
			} else {
				ensuredContexts = append(ensuredContexts, "global")
			}
		} else {
			errVal, _ := globalResult.Get("error")
			errorsList = append(errorsList, fmt.Sprintf("Global context: %v", errVal))
		}
		projectResult, _ := s.ensureProjectContextExists(ctx, taskProjectID, effectiveUserID)
		if success, _ := projectResult.Get("success"); success == true {
			if created, _ := projectResult.Get("created"); created == true {
				createdContexts = append(createdContexts, "project")
			} else {
				ensuredContexts = append(ensuredContexts, "project")
			}
		} else {
			errVal, _ := projectResult.Get("error")
			errorsList = append(errorsList, fmt.Sprintf("Project context: %v", errVal))
		}
		branchResult, _ := s.ensureBranchContextExists(ctx, branchID, taskProjectID, effectiveUserID)
		if success, _ := branchResult.Get("success"); success == true {
			if created, _ := branchResult.Get("created"); created == true {
				createdContexts = append(createdContexts, "branch")
			} else {
				ensuredContexts = append(ensuredContexts, "branch")
			}
		} else {
			errVal, _ := branchResult.Get("error")
			errorsList = append(errorsList, fmt.Sprintf("Branch context: %v", errVal))
		}
	}
	success := len(errorsList) == 0 || len(createdContexts)+len(ensuredContexts) > 0
	result := entities.NewOrderedMap[any]()
	result.Set("success", success)
	result.Set("created_contexts", createdContexts)
	result.Set("ensured_contexts", ensuredContexts)
	result.Set("total_contexts_handled", len(createdContexts)+len(ensuredContexts))
	if len(errorsList) > 0 {
		result.Set("errors", errorsList)
		result.Set("partial_success", len(createdContexts)+len(ensuredContexts) > 0)
	}
	return result
}

// createContextAtomically mirrors _create_context_atomically.
func (s *UnifiedContextService) createContextAtomically(ctx context.Context, level value_objects.ContextLevel, contextID string, data *entities.OrderedMap[any]) bool {
	if data == nil {
		data = entities.NewOrderedMap[any]()
	}
	dataUserID := zpUCSStr(zpUCSGetOr(data, "user_id", nil))
	if dataUserID == "" {
		dataUserID = zpUCSStr(zpUCSGetOr(zpUCSAsOrdered(zpUCSGetOr(data, "metadata", nil)), "user_id", nil))
	}
	effectiveUserID := dataUserID
	if effectiveUserID == "" && s.UserID != nil {
		effectiveUserID = *s.UserID
	}
	baseRepository := s.repositories[level]
	if baseRepository == nil {
		return false
	}
	repository := baseRepository
	if effectiveUserID != "" {
		repository = s.getUserScopedRepository(baseRepository)
	}
	if existing, err := repository.Get(ctx, contextID); err == nil && existing != nil {
		return true
	}
	// Python passes data.get("project_id") and data.get("git_branch_id") (None when absent).
	dataProjectID := zpUCSOptStr(data, "project_id")
	dataBranchID := zpUCSOptStr(data, "git_branch_id")
	completeData := s.buildDefaultContextData(level.String(), contextID, data, dataProjectID, dataBranchID)
	if level == value_objects.ContextLevelGlobal {
		contextID = zpUCSCompositeGlobalID(contextID)
	}
	var entityUserID *string
	if effectiveUserID != "" {
		entityUserID = &effectiveUserID
	}
	entity := s.createContextEntity(level, contextID, completeData, entityUserID, dataProjectID)
	if entity == nil {
		return false
	}
	saved, err := repository.Create(ctx, entity)
	if err != nil {
		// A concurrent creator of the same parent context is success (idempotent).
		return zpUCSIsDuplicateKey(err)
	}
	return saved != nil
}

// zpUCSOptStr is data.get(key) as an optional string: nil when the key is absent or null.
func zpUCSOptStr(data *entities.OrderedMap[any], key string) *string {
	v, ok := zpUCSGetPresent(data, key)
	if !ok || v == nil {
		return nil
	}
	str := zpUCSStr(v)
	return &str
}

// zpUCSIsDuplicateKey is the IntegrityError "duplicate" / "unique constraint" test.
func zpUCSIsDuplicateKey(err error) bool {
	msg := strings.ToLower(err.Error())
	return strings.Contains(msg, "duplicate") || strings.Contains(msg, "unique constraint") || strings.Contains(msg, "23505")
}

// createHierarchyAtomically mirrors _create_hierarchy_atomically.
func (s *UnifiedContextService) createHierarchyAtomically(ctx context.Context, contextsToCreate []zpUCSContextSpec) bool {
	for _, spec := range contextsToCreate {
		s.createContextAtomically(ctx, spec.Level, spec.ContextID, spec.Data)
	}
	return true
}

// resolveProjectIDFromBranch mirrors _resolve_project_id_from_branch: the branch's
// project_id through EntityLookup (scoped to the service user), "" on any failure.
func (s *UnifiedContextService) resolveProjectIDFromBranch(ctx context.Context, branchID string) string {
	if s.EntityLookup == nil {
		return ""
	}
	id, err := s.EntityLookup.BranchProjectID(ctx, s.UserID, branchID)
	if err != nil {
		return ""
	}
	return id
}

// shouldAllowOrphanedCreation mirrors _should_allow_orphaned_creation.
func (s *UnifiedContextService) shouldAllowOrphanedCreation(contextLevel value_objects.ContextLevel, contextID string, data *entities.OrderedMap[any]) bool {
	switch contextLevel {
	case value_objects.ContextLevelGlobal:
		return true
	case value_objects.ContextLevelProject:
		if zpUCSTruthy(zpUCSGetOr(data, "auto_created", nil)) {
			return true
		}
		name := zpUCSStr(zpUCSGetOr(data, "project_name", nil))
		if strings.HasPrefix(name, "Test") {
			return true
		}
		return zpUCSTruthy(zpUCSGetOr(data, "allow_orphaned_creation", nil))
	case value_objects.ContextLevelBranch:
		if zpUCSStr(zpUCSGetOr(data, "project_id", nil)) != "" && zpUCSTruthy(zpUCSGetOr(data, "allow_orphaned_creation", nil)) {
			return true
		}
	case value_objects.ContextLevelTask:
		branchVal := zpUCSGetOr(data, "branch_id", nil)
		if branchVal == nil {
			branchVal = zpUCSGetOr(data, "parent_branch_id", nil)
		}
		if branchVal == nil {
			branchVal = zpUCSGetOr(data, "git_branch_id", nil)
		}
		if branchVal != nil && zpUCSTruthy(zpUCSGetOr(data, "allow_orphaned_creation", nil)) {
			return true
		}
	}
	return false
}

// getParentInfo mirrors _get_parent_info.
func (s *UnifiedContextService) getParentInfo(contextLevel value_objects.ContextLevel, contextEntity any) (value_objects.ContextLevel, *string) {
	switch contextLevel {
	case value_objects.ContextLevelProject:
		var parentID *string
		if s.UserID != nil {
			id := zpUCSUUID5(zpUCSNamespace, *s.UserID)
			parentID = &id
		}
		return value_objects.ContextLevelGlobal, parentID
	case value_objects.ContextLevelBranch:
		id := zpUCSEntityField(contextEntity, "ProjectID")
		if id == "" {
			return value_objects.ContextLevelProject, nil
		}
		return value_objects.ContextLevelProject, &id
	case value_objects.ContextLevelTask:
		id := zpUCSEntityField(contextEntity, "BranchID")
		if id == "" {
			return value_objects.ContextLevelBranch, nil
		}
		return value_objects.ContextLevelBranch, &id
	}
	return "", nil
}

// propagateChanges mirrors _propagate_changes (no cache invalidation for now).
func (s *UnifiedContextService) propagateChanges(level value_objects.ContextLevel, contextID string) {
}

// cleanupDependentContexts mirrors _cleanup_dependent_contexts.
func (s *UnifiedContextService) cleanupDependentContexts(level value_objects.ContextLevel, contextID string) {
}

// invalidateChildCaches mirrors _invalidate_child_caches.
func (s *UnifiedContextService) invalidateChildCaches(level value_objects.ContextLevel, contextID, userID string, cache *ContextCacheService) {
	if cache == nil {
		return
	}
}

// ensureGlobalContextExists mirrors _ensure_global_context_exists.
func (s *UnifiedContextService) ensureGlobalContextExists(ctx context.Context, userID *string) (*entities.OrderedMap[any], error) {
	effectiveUserID := userOrDefault(userID, s.UserID)
	if effectiveUserID == nil || *effectiveUserID == "" {
		return zpUCSError("user_id is required for context delegation"), nil
	}
	userUUID, ok := value_objects.PyParseUUID(*effectiveUserID)
	if !ok {
		userUUID = zpUCSUUID5(zpUCSNamespace, *effectiveUserID)
	}
	globalContextID := zpUCSUUID5(zpUCSNamespace, userUUID)
	globalRepo := s.getUserScopedRepository(s.repositories[value_objects.ContextLevelGlobal])
	if globalRepo != nil {
		if existing, err := globalRepo.Get(ctx, globalContextID); err == nil && existing != nil {
			resp := entities.NewOrderedMap[any]()
			resp.Set("success", true)
			resp.Set("created", false)
			resp.Set("context_id", globalContextID)
			return resp, nil
		}
	}
	globalData := entities.NewOrderedMap[any]()
	globalData.Set("organization_name", "Default Organization")
	settings := entities.NewOrderedMap[any]()
	settings.Set("auto_context_creation", true)
	settings.Set("default_timezone", "UTC")
	globalData.Set("global_settings", settings)
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("auto_created", true)
	metadata.Set("created_by", "context_bootstrap")
	metadata.Set("user_id", *effectiveUserID)
	globalData.Set("metadata", metadata)
	success := s.createContextAtomically(ctx, value_objects.ContextLevelGlobal, globalContextID, globalData)
	if success {
		resp := entities.NewOrderedMap[any]()
		resp.Set("success", true)
		resp.Set("created", true)
		resp.Set("context_id", globalContextID)
		return resp, nil
	}
	return zpUCSError("Unknown error"), nil
}

// ensureProjectContextExists mirrors _ensure_project_context_exists.
func (s *UnifiedContextService) ensureProjectContextExists(ctx context.Context, projectID string, userID *string) (*entities.OrderedMap[any], error) {
	projectRepo := s.getUserScopedRepository(s.repositories[value_objects.ContextLevelProject])
	if projectRepo != nil {
		if existing, err := projectRepo.Get(ctx, projectID); err == nil && existing != nil {
			resp := entities.NewOrderedMap[any]()
			resp.Set("success", true)
			resp.Set("created", false)
			resp.Set("context_id", projectID)
			return resp, nil
		}
	}
	projectData := entities.NewOrderedMap[any]()
	projectData.Set("project_name", fmt.Sprintf("Project %s", zpUCSFirst8(projectID)))
	settings := entities.NewOrderedMap[any]()
	settings.Set("auto_created", true)
	settings.Set("default_branch", "main")
	projectData.Set("project_settings", settings)
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("auto_created", true)
	metadata.Set("created_by", "context_bootstrap")
	mUser := userOrDefault(userID, s.UserID)
	metadata.Set("user_id", zpUCSDeref(mUser))
	projectData.Set("metadata", metadata)
	success := s.createContextAtomically(ctx, value_objects.ContextLevelProject, projectID, projectData)
	if success {
		resp := entities.NewOrderedMap[any]()
		resp.Set("success", true)
		resp.Set("created", true)
		resp.Set("context_id", projectID)
		return resp, nil
	}
	return zpUCSError("Unknown error"), nil
}

// ensureBranchContextExists mirrors _ensure_branch_context_exists.
func (s *UnifiedContextService) ensureBranchContextExists(ctx context.Context, branchID, projectID string, userID *string) (*entities.OrderedMap[any], error) {
	branchRepo := s.getUserScopedRepository(s.repositories[value_objects.ContextLevelBranch])
	if branchRepo != nil {
		if existing, err := branchRepo.Get(ctx, branchID); err == nil && existing != nil {
			resp := entities.NewOrderedMap[any]()
			resp.Set("success", true)
			resp.Set("created", false)
			resp.Set("context_id", branchID)
			return resp, nil
		}
	}
	branchIDStr := branchID
	gitBranchName := fmt.Sprintf("branch-%s", zpUCSFirst8(branchIDStr))
	branchData := entities.NewOrderedMap[any]()
	branchData.Set("project_id", projectID)
	branchData.Set("git_branch_name", gitBranchName)
	settings := entities.NewOrderedMap[any]()
	settings.Set("auto_created", true)
	settings.Set("workflow_type", "standard")
	settings.Set("created_from", "context_bootstrap")
	branchData.Set("branch_settings", settings)
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("auto_created", true)
	metadata.Set("created_by", "context_bootstrap")
	mUser := userOrDefault(userID, s.UserID)
	metadata.Set("user_id", zpUCSDeref(mUser))
	metadata.Set("branch_id", branchIDStr)
	metadata.Set("project_id", projectID)
	branchData.Set("metadata", metadata)
	success := s.createContextAtomically(ctx, value_objects.ContextLevelBranch, branchID, branchData)
	if success {
		resp := entities.NewOrderedMap[any]()
		resp.Set("success", true)
		resp.Set("created", true)
		resp.Set("context_id", branchID)
		return resp, nil
	}
	return zpUCSError("Atomic context creation failed"), nil
}

// hierarchyValidator builds the validator with adapters over the generic repos.
func (s *UnifiedContextService) hierarchyValidator(ctx context.Context) *ContextHierarchyValidator {
	adapter := func(repo UnifiedContextRepository) HierarchyContextRepo {
		if repo == nil {
			return nil
		}
		return zpUCSHierarchyAdapter{repo: repo}
	}
	return NewContextHierarchyValidator(
		adapter(s.repositories[value_objects.ContextLevelGlobal]),
		adapter(s.repositories[value_objects.ContextLevelProject]),
		adapter(s.repositories[value_objects.ContextLevelBranch]),
		adapter(s.repositories[value_objects.ContextLevelTask]),
		s.UserID,
	)
}

// zpUCSHierarchyAdapter adapts UnifiedContextRepository to HierarchyContextRepo.
type zpUCSHierarchyAdapter struct{ repo UnifiedContextRepository }

func (a zpUCSHierarchyAdapter) Get(ctx context.Context, id string) (any, error) {
	return a.repo.Get(ctx, id)
}

func (a zpUCSHierarchyAdapter) List(ctx context.Context) ([]any, error) {
	return a.repo.List(ctx, nil)
}

// zpUCSContextSpec is a (level, context_id, data) tuple for createHierarchyAtomically.
type zpUCSContextSpec struct {
	Level     value_objects.ContextLevel
	ContextID string
	Data      *entities.OrderedMap[any]
}

// ---- shared helpers ----

func zpUCSError(msg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", msg)
	return m
}

func zpUCSMerge(dst, src *entities.OrderedMap[any]) {
	if dst == nil || src == nil {
		return
	}
	for _, key := range src.Keys() {
		v, _ := src.Get(key)
		dst.Set(key, v)
	}
}

func zpUCSDeref(v *string) string {
	if v == nil {
		return ""
	}
	return *v
}

func zpUCSFirst8(s string) string {
	if len(s) > 8 {
		return s[:8]
	}
	return s
}

func zpUCSStr(v any) string {
	switch t := v.(type) {
	case nil:
		return ""
	case string:
		return t
	default:
		return value_objects.PyStr(v)
	}
}

func zpUCSStrOr(m *entities.OrderedMap[any], key, def string) string {
	if v, ok := m.Get(key); ok {
		if s, isStr := v.(string); isStr {
			return s
		}
	}
	return def
}

func zpUCSInt(v any) int {
	switch t := v.(type) {
	case int:
		return t
	case int64:
		return int(t)
	case float64:
		return int(t)
	case string:
		var n int
		fmt.Sscanf(t, "%d", &n)
		return n
	}
	return 0
}

func zpUCSTruthy(v any) bool {
	switch t := v.(type) {
	case nil:
		return false
	case bool:
		return t
	case string:
		return t != ""
	case int:
		return t != 0
	case float64:
		return t != 0
	case []any:
		return len(t) > 0
	case *entities.OrderedMap[any]:
		return t != nil && t.Len() > 0
	case map[string]any:
		return len(t) > 0
	}
	return true
}

func zpUCSGetOr(m *entities.OrderedMap[any], key string, def any) any {
	if m == nil {
		return def
	}
	if v, ok := m.Get(key); ok && v != nil {
		return v
	}
	return def
}

// zpUCSCompositeGlobalID ports the "UUID_UUID" rule of create_context: a global context id
// with exactly one underscore becomes uuid5(namespace, the part after the underscore).
func zpUCSCompositeGlobalID(contextID string) string {
	parts := strings.Split(contextID, "_")
	if len(parts) != 2 {
		return contextID
	}
	return zpUCSUUID5(zpUCSNamespace, parts[1])
}

// userOrDefault is Python `user_id or self._user_id`: an empty string falls back too.
func userOrDefault(userID, fallback *string) *string {
	if userID != nil && *userID != "" {
		return userID
	}
	return fallback
}

// zpUCSGetPresent is dict.get(key): the value (possibly nil) and whether the key exists.
func zpUCSGetPresent(m *entities.OrderedMap[any], key string) (any, bool) {
	if m == nil {
		return nil, false
	}
	return m.Get(key)
}

// zpUCSGetKey is dict.get(key, def): the default applies only when the key is absent,
// so an explicit null is kept.
func zpUCSGetKey(m *entities.OrderedMap[any], key string, def any) any {
	if v, ok := zpUCSGetPresent(m, key); ok {
		return v
	}
	return def
}

// zpUCSAsOrdered converts a value to an OrderedMap, mirroring dict handling. A nil
// pointer becomes an empty map; an already-OrderedMap is returned as-is.
func zpUCSAsOrdered(v any) *entities.OrderedMap[any] {
	switch t := v.(type) {
	case nil:
		return entities.NewOrderedMap[any]()
	case *entities.OrderedMap[any]:
		if t == nil {
			return entities.NewOrderedMap[any]()
		}
		return t
	case map[string]any:
		return zpUCSFromMap(t)
	}
	return entities.NewOrderedMap[any]()
}

// zpUCSFromMap converts a Go map to an OrderedMap. Go maps lose Python insertion
// order, so keys are sorted for determinism.
func zpUCSFromMap(m map[string]any) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	if m == nil {
		return out
	}
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	for i := 1; i < len(keys); i++ {
		for j := i; j > 0 && keys[j] < keys[j-1]; j-- {
			keys[j], keys[j-1] = keys[j-1], keys[j]
		}
	}
	for _, k := range keys {
		out.Set(k, m[k])
	}
	return out
}

// zpUCSMap converts an OrderedMap (or map) to map[string]any for the entity fields.
func zpUCSMap(v any) map[string]any {
	switch t := v.(type) {
	case nil:
		return map[string]any{}
	case map[string]any:
		return t
	case *entities.OrderedMap[any]:
		out := map[string]any{}
		if t == nil {
			return out
		}
		for _, k := range t.Keys() {
			val, _ := t.Get(k)
			out[k] = val
		}
		return out
	}
	return map[string]any{}
}

func zpUCSList(m *entities.OrderedMap[any], key string) []any {
	if m == nil {
		return []any{}
	}
	if v, ok := m.Get(key); ok {
		if l, isList := v.([]any); isList {
			return l
		}
	}
	return []any{}
}

// zpUCSEntityID returns entity.id via reflection-free type assertion.
func zpUCSEntityID(entity any) string {
	switch e := entity.(type) {
	case *entities.GlobalContext:
		return e.ID
	case *entities.ProjectContext:
		return e.ID
	case *entities.BranchContext:
		return e.ID
	case *entities.TaskContextUnified:
		return e.ID
	}
	return ""
}

// zpUCSEntityField returns a string field from a known context entity.
func zpUCSEntityField(entity any, field string) string {
	switch e := entity.(type) {
	case *entities.BranchContext:
		if field == "ProjectID" {
			return e.ProjectID
		}
	case *entities.TaskContextUnified:
		if field == "BranchID" {
			return e.BranchID
		}
	case *entities.ProjectContext:
		return e.ID
	}
	return ""
}

// zpUCSUUID5 mirrors uuid.uuid5(namespace, name): SHA-1 based UUID version 5.
func zpUCSUUID5(namespace, name string) string {
	nsHex := strings.ReplaceAll(namespace, "-", "")
	nsBytes, err := hex.DecodeString(nsHex)
	if err != nil || len(nsBytes) != 16 {
		return ""
	}
	h := sha1.New()
	h.Write(nsBytes)
	h.Write([]byte(name))
	sum := h.Sum(nil)[:16]
	sum[6] = (sum[6] & 0x0f) | 0x50
	sum[8] = (sum[8] & 0x3f) | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", sum[0:4], sum[4:6], sum[6:8], sum[8:10], sum[10:16])
}
