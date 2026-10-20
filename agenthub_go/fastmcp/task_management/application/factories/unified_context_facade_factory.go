// Unified Context Facade Factory (Python
// task_management/application/factories/unified_context_facade_factory.py).
//
// The Python factory builds the four concrete context repositories from an
// SQLAlchemy session factory and passes them (duck-typed) to UnifiedContextService.
// The Go concrete context repositories expose typed methods that do not implement
// services.UnifiedContextRepository, so the repository construction is injected via
// UnifiedContextRepositoryBuilder (mirroring ProjectFacadeBuilder). A missing
// builder or session manager is a wiring error: construction fails instead of
// installing a service that cannot reach the database.
package factories

import (
	"context"
	"crypto/sha1"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// zpUCFNamespaceUUID is the namespace a47ae7b9-1d4b-4e5f-8b5a-9c3e5d2f8a1c.
const zpUCFNamespaceUUID = "a47ae7b9-1d4b-4e5f-8b5a-9c3e5d2f8a1c"

// Class-level singleton state (_instance / _initialized).
var (
	unifiedContextFacadeFactoryInstance    *UnifiedContextFacadeFactory
	unifiedContextFacadeFactoryInitialized bool
)

// UnifiedContextEntityLookup is the git branch / task lookup the services use to
// auto-detect ids in create_context (Python DomainServiceFactory repository factories).
var UnifiedContextEntityLookup services.EntityIDLookup

// UnifiedContextEventAppender writes context updates to the ledger.
var UnifiedContextEventAppender services.ContextEventAppender

// UnifiedContextRepositoryBuilder builds the four per-level repositories for a user.
// userID nil = the base repositories; non-nil = user-scoped (Python .with_user).
var UnifiedContextRepositoryBuilder func(sessions *database.SessionManager, userID *string) (
	global, project, branch, task services.UnifiedContextRepository, err error)

// UnifiedContextFacadeFactory mirrors UnifiedContextFacadeFactory.
type UnifiedContextFacadeFactory struct {
	SessionManager *database.SessionManager
	// UnifiedService is the service built over the four repositories (Python
	// unified_service). Construction fails rather than substituting a stand-in.
	UnifiedService *services.UnifiedContextService

	inheritanceService *services.ContextInheritanceService
	validationService  *services.ContextValidationService
}

// NewUnifiedContextFacadeFactory mirrors __init__ (skips work when already
// initialized). Python obtains SessionLocal from get_db_config(); in Go the
// SessionManager is supplied by the caller. Every failure to obtain the four
// repositories is returned: there is no in-memory substitute.
func NewUnifiedContextFacadeFactory(ctx context.Context, sessions *database.SessionManager) (*UnifiedContextFacadeFactory, error) {
	factoriesMu.Lock()
	defer factoriesMu.Unlock()
	if unifiedContextFacadeFactoryInitialized {
		return unifiedContextFacadeFactoryInstance, nil
	}
	if sessions == nil {
		return nil, errors.New("unified context factory: no session manager")
	}
	if UnifiedContextRepositoryBuilder == nil {
		return nil, errors.New("unified context factory: no repository builder")
	}

	global, project, branch, task, err := UnifiedContextRepositoryBuilder(sessions, nil)
	if err != nil {
		return nil, fmt.Errorf("unified context factory: build repositories: %w", err)
	}

	repoMap := map[string]any{"global": global, "project": project, "branch": branch, "task": task}
	f := &UnifiedContextFacadeFactory{SessionManager: sessions}
	// Python also builds ContextDelegationService(repo_map); that service has no
	// exported Go constructor, so nil is passed (the service tolerates nil).
	f.inheritanceService = services.NewContextInheritanceService(repoMap, nil)
	f.validationService = services.NewContextValidationService(nil, nil)
	f.UnifiedService = services.NewUnifiedContextService(
		global, project, branch, task,
		f.inheritanceService, nil, f.validationService, nil,
	).WithEntityLookup(UnifiedContextEntityLookup).WithEventAppender(UnifiedContextEventAppender)
	unifiedContextFacadeFactoryInitialized = true
	unifiedContextFacadeFactoryInstance = f
	return f, nil
}

// CreateFacade mirrors create_facade.
func (f *UnifiedContextFacadeFactory) CreateFacade(ctx context.Context, userID, projectID, gitBranchID *string) (*facades.UnifiedContextFacade, error) {
	scoped := f.UnifiedService

	if userID != nil && *userID != "" && UnifiedContextRepositoryBuilder != nil {
		global, project, branch, task, err := UnifiedContextRepositoryBuilder(f.SessionManager, userID)
		if err != nil {
			return nil, err
		}
		userRepoMap := map[string]any{"global": global, "project": project, "branch": branch, "task": task}
		userInheritance := services.NewContextInheritanceService(userRepoMap, userID)
		scoped = services.NewUnifiedContextService(
			global, project, branch, task,
			userInheritance, nil, f.validationService, nil,
		).WithEntityLookup(UnifiedContextEntityLookup).WithEventAppender(UnifiedContextEventAppender).WithUser(*userID)
	}

	return facades.NewUnifiedContextFacade(scoped, userID, projectID, gitBranchID), nil
}

// CreateUnifiedService mirrors create_unified_service.
func (f *UnifiedContextFacadeFactory) CreateUnifiedService() *services.UnifiedContextService {
	return f.UnifiedService
}

// AutoCreateGlobalContext mirrors auto_create_global_context.
func (f *UnifiedContextFacadeFactory) AutoCreateGlobalContext(ctx context.Context, userID *string) bool {
	uid := ""
	if userID != nil {
		uid = *userID
	}
	// Python falls back to get_current_user_id() from the request-context
	// middleware; Go has no such ambient context, so no user_id -> failure.
	if uid == "" {
		return false
	}

	facade, err := f.CreateFacade(ctx, &uid, nil, nil)
	if err != nil {
		return false
	}

	userUUID, ok := zpUCFTryParseUUID(uid)
	if !ok {
		userUUID = zpUCFUUID5(zpUCFNamespaceUUID, uid)
	}
	globalContextID := zpUCFUUID5(zpUCFNamespaceUUID, userUUID)

	if existing, err := facade.GetContext(ctx, "global", globalContextID, false, nil); err == nil {
		if zpUCFResultSuccess(existing) {
			return true
		}
	}

	defaultData := entities.NewOrderedMap[any]()
	defaultData.Set("organization_name", "Default Organization")
	settings := entities.NewOrderedMap[any]()
	for _, k := range []string{"autonomous_rules", "security_policies", "coding_standards", "workflow_templates", "delegation_rules"} {
		settings.Set(k, entities.NewOrderedMap[any]())
	}
	defaultData.Set("global_settings", settings)

	result, err := facade.CreateContext(ctx, "global", globalContextID, defaultData, nil)
	if err != nil {
		return false
	}
	return zpUCFResultSuccess(result)
}

// zpUCFResultSuccess mirrors result.get("success", False).
func zpUCFResultSuccess(result *entities.OrderedMap[any]) bool {
	if result == nil {
		return false
	}
	v, ok := result.Get("success")
	if !ok {
		return false
	}
	b, _ := v.(bool)
	return b
}

// zpUCFUUID5 is Python uuid.uuid5(namespace, name) for a canonical namespace string.
func zpUCFUUID5(namespace, name string) string {
	ns := zpUCFParseUUIDBytes(namespace)
	h := sha1.New()
	h.Write(ns)
	h.Write([]byte(name))
	sum := h.Sum(nil)
	var u [16]byte
	copy(u[:], sum[:16])
	u[6] = (u[6] & 0x0f) | 0x50
	u[8] = (u[8] & 0x3f) | 0x80
	return zpUCFFormatUUID(u)
}

// zpUCFTryParseUUID mirrors uuid.UUID(str(user_id)); ok is false on ValueError.
// It returns the canonical dashed lowercase form (str(uuid.UUID(...))).
func zpUCFTryParseUUID(s string) (string, bool) {
	t := strings.ReplaceAll(s, "-", "")
	if len(t) != 32 {
		return "", false
	}
	if _, err := hex.DecodeString(t); err != nil {
		return "", false
	}
	var u [16]byte
	b, _ := hex.DecodeString(t)
	copy(u[:], b)
	return zpUCFFormatUUID(u), true
}

func zpUCFParseUUIDBytes(s string) []byte {
	t := strings.ReplaceAll(s, "-", "")
	b, _ := hex.DecodeString(t)
	return b
}

func zpUCFFormatUUID(u [16]byte) string {
	h := hex.EncodeToString(u[:])
	return h[0:8] + "-" + h[8:12] + "-" + h[12:16] + "-" + h[16:20] + "-" + h[20:32]
}
