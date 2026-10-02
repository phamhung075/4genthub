package services

// Feature Flag Service for DDD Migration
// Provides safe migration capabilities with instant rollback support.
// (Python application/services/feature_flag_service.py)

import (
	"fmt"
	"os"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/utilities"
)

// FeatureFlag represents a feature flag configuration.
type FeatureFlag struct {
	Name        string
	Enabled     bool
	Description string
	CreatedAt   string
	UpdatedAt   string
	Metadata    *entities.OrderedMap[any]
}

// zpFeatAsDict mirrors dataclasses.asdict(flag): the ordered dict follows the
// dataclass field order (name, enabled, description, created_at, updated_at, metadata).
func zpFeatAsDict(flag *FeatureFlag) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("name", flag.Name)
	m.Set("enabled", flag.Enabled)
	m.Set("description", flag.Description)
	m.Set("created_at", flag.CreatedAt)
	m.Set("updated_at", flag.UpdatedAt)
	if flag.Metadata != nil {
		m.Set("metadata", flag.Metadata)
	} else {
		m.Set("metadata", entities.NewOrderedMap[any]())
	}
	return m
}

// zpFeatDirname is os.path.dirname (posixpath.split head); filepath.Dir differs for a
// bare filename ("" vs ".") and "//a".
func zpFeatDirname(p string) string {
	i := strings.LastIndex(p, "/") + 1
	head := p[:i]
	if head != "" && head != strings.Repeat("/", len(head)) {
		head = strings.TrimRight(head, "/")
	}
	return head
}

// zpFeatFlagFromMap mirrors FeatureFlag(**flag_data): every value is taken from the
// decoded dict (the outer key does not feed the name) and unexpected / missing keys are
// a TypeError, which aborts the load loop.
func zpFeatFlagFromMap(flagData *entities.OrderedMap[any]) (*FeatureFlag, error) {
	flag := &FeatureFlag{Metadata: entities.NewOrderedMap[any]()}
	seen := map[string]bool{}
	for _, k := range flagData.Keys() {
		seen[k] = true
		v, _ := flagData.Get(k)
		switch k {
		case "name":
			s, ok := v.(string)
			if !ok {
				return nil, fmt.Errorf("FeatureFlag() argument 'name' must be str")
			}
			flag.Name = s
		case "enabled":
			b, ok := v.(bool)
			if !ok {
				return nil, fmt.Errorf("FeatureFlag() argument 'enabled' must be bool")
			}
			flag.Enabled = b
		case "description":
			s, ok := v.(string)
			if !ok {
				return nil, fmt.Errorf("FeatureFlag() argument 'description' must be str")
			}
			flag.Description = s
		case "created_at":
			s, ok := v.(string)
			if !ok {
				return nil, fmt.Errorf("FeatureFlag() argument 'created_at' must be str")
			}
			flag.CreatedAt = s
		case "updated_at":
			s, ok := v.(string)
			if !ok {
				return nil, fmt.Errorf("FeatureFlag() argument 'updated_at' must be str")
			}
			flag.UpdatedAt = s
		case "metadata":
			if v == nil {
				continue
			}
			md, ok := v.(*entities.OrderedMap[any])
			if !ok {
				return nil, fmt.Errorf("FeatureFlag() argument 'metadata' must be dict")
			}
			flag.Metadata = md
		default:
			return nil, fmt.Errorf("FeatureFlag() got an unexpected keyword argument '%s'", k)
		}
	}
	for _, k := range []string{"name", "enabled", "description", "created_at", "updated_at"} {
		if !seen[k] {
			return nil, fmt.Errorf("FeatureFlag() missing required argument: '%s'", k)
		}
	}
	return flag, nil
}

// FeatureFlagService manages feature flags during DDD migration.
type FeatureFlagService struct {
	userID     *string
	configPath string
	flags      *entities.OrderedMap[*FeatureFlag]
}

// NewFeatureFlagService mirrors __init__(config_path=None, user_id=None). A nil or empty
// config path uses Path.cwd()/".cursor"/"feature_flags.json".
func NewFeatureFlagService(configPath *string, userID *string) *FeatureFlagService {
	s := &FeatureFlagService{userID: userID, flags: entities.NewOrderedMap[*FeatureFlag]()}
	if configPath != nil && *configPath != "" {
		s.configPath = *configPath
	} else {
		s.configPath = s.getDefaultConfigPath()
	}
	s.loadFlags()
	s.initializeMigrationFlags()
	return s
}

// getUserScopedRepository mirrors the repository duck-typing branch through the shared
// services helper (only the with_user protocol is representable).
func (s *FeatureFlagService) getUserScopedRepository(repository any) any {
	return serviceUserScopedRepository(repository, s.userID)
}

// WithUser creates a new service instance scoped to a specific user.
func (s *FeatureFlagService) WithUser(userID string) *FeatureFlagService {
	return NewFeatureFlagService(&s.configPath, &userID)
}

// getDefaultConfigPath is str(Path.cwd() / ".cursor" / "feature_flags.json").
func (s *FeatureFlagService) getDefaultConfigPath() string {
	cwd, err := os.Getwd()
	if err != nil {
		cwd = ""
	}
	return utilities.PyJoin(cwd, ".cursor", "feature_flags.json")
}

// loadFlags mirrors _load_flags: any failure stops the loop and keeps the flags loaded
// so far (the exception is swallowed by the Python except).
func (s *FeatureFlagService) loadFlags() {
	if _, err := os.Stat(s.configPath); err != nil {
		return
	}
	raw, err := os.ReadFile(s.configPath)
	if err != nil {
		return
	}
	decoded, err := entities.DecodeJSON(raw)
	if err != nil {
		return
	}
	data, ok := decoded.(*entities.OrderedMap[any])
	if !ok {
		return
	}
	for _, flagName := range data.Keys() {
		rawFlag, _ := data.Get(flagName)
		flagData, ok := rawFlag.(*entities.OrderedMap[any])
		if !ok {
			return
		}
		flag, err := zpFeatFlagFromMap(flagData)
		if err != nil {
			return
		}
		s.flags.Set(flagName, flag)
	}
}

// saveFlags mirrors _save_flags: os.makedirs(dirname) then json.dump(..., indent=2).
// A bare filename makes dirname "" and aborts the save, like Python.
func (s *FeatureFlagService) saveFlags() {
	dir := zpFeatDirname(s.configPath)
	if dir == "" {
		return
	}
	if err := os.MkdirAll(dir, 0o777); err != nil {
		return
	}
	data := entities.NewOrderedMap[any]()
	for _, name := range s.flags.Keys() {
		flag, _ := s.flags.Get(name)
		data.Set(name, zpFeatAsDict(flag))
	}
	text, err := value_objects.PyJSONDumps(data, 2)
	if err != nil {
		return
	}
	_ = os.WriteFile(s.configPath, []byte(text), 0o666)
}

// initializeMigrationFlags mirrors _initialize_migration_flags.
func (s *FeatureFlagService) initializeMigrationFlags() {
	type zpFeatMigrationFlag struct {
		enabled     bool
		description string
	}
	migrationFlags := []struct {
		name   string
		config zpFeatMigrationFlag
	}{
		{"USE_DDD_COMPLIANT_TOOLS", zpFeatMigrationFlag{false, "Master flag for DDD-compliant architecture migration"}},
		{"USE_NEW_CREATE_TASK", zpFeatMigrationFlag{false, "Use new DDD-compliant create_task implementation"}},
		{"USE_NEW_UPDATE_TASK", zpFeatMigrationFlag{false, "Use new DDD-compliant update_task implementation"}},
		{"USE_NEW_GET_TASK", zpFeatMigrationFlag{false, "Use new DDD-compliant get_task implementation"}},
		{"USE_NEW_LIST_TASKS", zpFeatMigrationFlag{false, "Use new DDD-compliant list_tasks implementation"}},
		{"USE_NEW_DELETE_TASK", zpFeatMigrationFlag{false, "Use new DDD-compliant delete_task implementation"}},
		{"USE_NEW_SEARCH_TASKS", zpFeatMigrationFlag{false, "Use new DDD-compliant search_tasks implementation"}},
		{"USE_NEW_NEXT_TASK", zpFeatMigrationFlag{false, "Use new DDD-compliant next_task implementation"}},
		{"USE_NEW_MANAGE_DEPENDENCIES", zpFeatMigrationFlag{false, "Use new DDD-compliant dependency management"}},
		{"USE_NEW_MANAGE_SUBTASKS", zpFeatMigrationFlag{false, "Use new DDD-compliant subtask management"}},
		{"ENABLE_PARALLEL_TESTING", zpFeatMigrationFlag{true, "Run parallel tests during migration"}},
		{"ENABLE_MIGRATION_LOGGING", zpFeatMigrationFlag{true, "Enhanced logging during migration"}},
	}
	for _, entry := range migrationFlags {
		if s.flags.Has(entry.name) {
			continue
		}
		now := value_objects.IsoFormatNaive(time.Now())
		s.flags.Set(entry.name, &FeatureFlag{
			Name:        entry.name,
			Enabled:     entry.config.enabled,
			Description: entry.config.description,
			CreatedAt:   now,
			UpdatedAt:   now,
			Metadata:    entities.NewOrderedMap[any](),
		})
	}
	s.saveFlags()
}

// IsEnabled checks if a feature flag is enabled (environment override first).
func (s *FeatureFlagService) IsEnabled(flagName string) bool {
	envVar := "FEATURE_" + strings.ToUpper(flagName)
	if envValue, ok := os.LookupEnv(envVar); ok {
		switch value_objects.PyLower(envValue) {
		case "true", "1", "yes", "on":
			return true
		}
		return false
	}
	flag, ok := s.flags.Get(flagName)
	if !ok {
		return false
	}
	return flag.Enabled
}

// EnableFlag enables a feature flag.
func (s *FeatureFlagService) EnableFlag(flagName string, metadata *entities.OrderedMap[any]) bool {
	return s.updateFlag(flagName, true, metadata)
}

// DisableFlag disables a feature flag.
func (s *FeatureFlagService) DisableFlag(flagName string, metadata *entities.OrderedMap[any]) bool {
	return s.updateFlag(flagName, false, metadata)
}

// updateFlag mirrors _update_flag. It returns false when the flag does not exist.
func (s *FeatureFlagService) updateFlag(flagName string, enabled bool, metadata *entities.OrderedMap[any]) bool {
	flag, ok := s.flags.Get(flagName)
	if !ok {
		return false
	}
	flag.Enabled = enabled
	flag.UpdatedAt = value_objects.IsoFormatNaive(time.Now())
	if metadata != nil && value_objects.PyTruthy(metadata) {
		if flag.Metadata == nil {
			flag.Metadata = entities.NewOrderedMap[any]()
		}
		for _, k := range metadata.Keys() {
			v, _ := metadata.Get(k)
			flag.Metadata.Set(k, v)
		}
	}
	s.saveFlags()
	return true
}

// GetFlagStatus returns the detailed status of a flag, or nil when it is unknown.
func (s *FeatureFlagService) GetFlagStatus(flagName string) *entities.OrderedMap[any] {
	flag, ok := s.flags.Get(flagName)
	if !ok {
		return nil
	}
	metadata := any(entities.NewOrderedMap[any]())
	if flag.Metadata != nil {
		metadata = flag.Metadata
	}
	var environmentOverride any
	if v, ok := os.LookupEnv("FEATURE_" + strings.ToUpper(flagName)); ok {
		environmentOverride = v
	}
	m := entities.NewOrderedMap[any]()
	m.Set("name", flag.Name)
	m.Set("enabled", flag.Enabled)
	m.Set("description", flag.Description)
	m.Set("created_at", flag.CreatedAt)
	m.Set("updated_at", flag.UpdatedAt)
	m.Set("metadata", metadata)
	m.Set("environment_override", environmentOverride)
	return m
}

// ListFlags lists all feature flags with their status, keyed in insertion order.
func (s *FeatureFlagService) ListFlags() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for _, name := range s.flags.Keys() {
		m.Set(name, s.GetFlagStatus(name))
	}
	return m
}

// zpFeatMigrationFlagNames are the flags counted by get_migration_status, in order.
func zpFeatMigrationFlagNames() []string {
	return []string{
		"USE_DDD_COMPLIANT_TOOLS",
		"USE_NEW_CREATE_TASK",
		"USE_NEW_UPDATE_TASK",
		"USE_NEW_GET_TASK",
		"USE_NEW_LIST_TASKS",
		"USE_NEW_DELETE_TASK",
		"USE_NEW_SEARCH_TASKS",
		"USE_NEW_NEXT_TASK",
		"USE_NEW_MANAGE_DEPENDENCIES",
		"USE_NEW_MANAGE_SUBTASKS",
	}
}

// GetMigrationStatus summarizes migration progress across the migration flags.
func (s *FeatureFlagService) GetMigrationStatus() *entities.OrderedMap[any] {
	migrationFlags := zpFeatMigrationFlagNames()
	enabledCount := 0
	for _, flag := range migrationFlags {
		if s.IsEnabled(flag) {
			enabledCount++
		}
	}
	totalCount := len(migrationFlags)

	progress := entities.NewOrderedMap[any]()
	progress.Set("enabled_operations", enabledCount)
	progress.Set("total_operations", totalCount)
	progress.Set("percentage", float64(enabledCount)/float64(totalCount)*100)

	flagsStatus := entities.NewOrderedMap[any]()
	for _, flag := range migrationFlags {
		flagsStatus.Set(flag, s.IsEnabled(flag))
	}

	m := entities.NewOrderedMap[any]()
	m.Set("migration_progress", progress)
	m.Set("master_flag_enabled", s.IsEnabled("USE_DDD_COMPLIANT_TOOLS"))
	m.Set("parallel_testing_enabled", s.IsEnabled("ENABLE_PARALLEL_TESTING"))
	m.Set("migration_logging_enabled", s.IsEnabled("ENABLE_MIGRATION_LOGGING"))
	m.Set("flags_status", flagsStatus)
	return m
}

// EnableMigrationPhase enables all flags for a migration phase.
func (s *FeatureFlagService) EnableMigrationPhase(phase string) bool {
	var flags []string
	switch phase {
	case "critical":
		flags = []string{"USE_NEW_CREATE_TASK", "USE_NEW_UPDATE_TASK", "USE_NEW_GET_TASK"}
	case "remaining":
		flags = []string{
			"USE_NEW_LIST_TASKS", "USE_NEW_DELETE_TASK", "USE_NEW_SEARCH_TASKS",
			"USE_NEW_NEXT_TASK", "USE_NEW_MANAGE_DEPENDENCIES", "USE_NEW_MANAGE_SUBTASKS",
		}
	case "all":
		flags = []string{
			"USE_DDD_COMPLIANT_TOOLS", "USE_NEW_CREATE_TASK", "USE_NEW_UPDATE_TASK",
			"USE_NEW_GET_TASK", "USE_NEW_LIST_TASKS", "USE_NEW_DELETE_TASK",
			"USE_NEW_SEARCH_TASKS", "USE_NEW_NEXT_TASK", "USE_NEW_MANAGE_DEPENDENCIES",
			"USE_NEW_MANAGE_SUBTASKS",
		}
	default:
		return false
	}
	for _, flag := range flags {
		metadata := entities.NewOrderedMap[any]()
		metadata.Set("migration_phase", phase)
		s.EnableFlag(flag, metadata)
	}
	return true
}

// RollbackMigration disables every migration flag.
func (s *FeatureFlagService) RollbackMigration() bool {
	for _, flag := range zpFeatMigrationFlagNames() {
		metadata := entities.NewOrderedMap[any]()
		metadata.Set("rollback_at", value_objects.IsoFormatNaive(time.Now()))
		s.DisableFlag(flag, metadata)
	}
	return true
}

// zpFeatFeatureFlagService is the Python module-level global instance.
var zpFeatFeatureFlagService *FeatureFlagService

// GetFeatureFlagService returns the global feature flag service instance.
func GetFeatureFlagService() *FeatureFlagService {
	if zpFeatFeatureFlagService == nil {
		zpFeatFeatureFlagService = NewFeatureFlagService(nil, nil)
	}
	return zpFeatFeatureFlagService
}

// IsFeatureEnabled is the convenience check against the global service.
func IsFeatureEnabled(flagName string) bool {
	return GetFeatureFlagService().IsEnabled(flagName)
}
