package services

import (
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func zpFeatOrderedKeys(t *testing.T, m *entities.OrderedMap[any]) string {
	t.Helper()
	return strings.Join(m.Keys(), ",")
}

func zpFeatTestNewService(t *testing.T) (*FeatureFlagService, string) {
	t.Helper()
	path := filepath.Join(t.TempDir(), "feature_flags.json")
	return NewFeatureFlagService(&path, nil), path
}

func TestFeatureFlagService_NewCreatesMigrationFlags(t *testing.T) {
	svc, path := zpFeatTestNewService(t)

	flags := svc.ListFlags()
	if flags.Len() != 12 {
		t.Fatalf("flags len = %d, want 12", flags.Len())
	}
	if !svc.IsEnabled("ENABLE_PARALLEL_TESTING") {
		t.Error("ENABLE_PARALLEL_TESTING should default to enabled")
	}
	if !svc.IsEnabled("ENABLE_MIGRATION_LOGGING") {
		t.Error("ENABLE_MIGRATION_LOGGING should default to enabled")
	}
	if svc.IsEnabled("USE_DDD_COMPLIANT_TOOLS") {
		t.Error("USE_DDD_COMPLIANT_TOOLS should default to disabled")
	}
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("expected migration flags to be persisted: %v", err)
	}
}

func TestFeatureFlagService_LoadFromFile(t *testing.T) {
	path := filepath.Join(t.TempDir(), "feature_flags.json")
	content := `{"MY_FLAG": {"name": "MY_FLAG", "enabled": true, "description": "my desc", "created_at": "t1", "updated_at": "t2", "metadata": {"owner": "me", "level": 2}}}`
	if err := os.WriteFile(path, []byte(content), 0o666); err != nil {
		t.Fatal(err)
	}

	svc := NewFeatureFlagService(&path, nil)
	if !svc.IsEnabled("MY_FLAG") {
		t.Fatal("MY_FLAG should be enabled")
	}
	status := svc.GetFlagStatus("MY_FLAG")
	if status == nil {
		t.Fatal("MY_FLAG status is nil")
	}
	if v, _ := status.Get("description"); v != "my desc" {
		t.Errorf("description = %v, want my desc", v)
	}
	metadata, _ := status.Get("metadata")
	md, ok := metadata.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("metadata type = %T, want *entities.OrderedMap[any]", metadata)
	}
	if got := zpFeatOrderedKeys(t, md); got != "owner,level" {
		t.Errorf("metadata key order = %q, want owner,level", got)
	}
	if v, _ := md.Get("level"); v != int64(2) {
		t.Errorf("metadata level = %v, want 2", v)
	}
	// Migration flags that were missing are still created.
	if !svc.IsEnabled("ENABLE_PARALLEL_TESTING") {
		t.Error("ENABLE_PARALLEL_TESTING should default to enabled")
	}
}

func TestFeatureFlagService_IsEnabledEnvOverride(t *testing.T) {
	svc, _ := zpFeatTestNewService(t)

	if !svc.EnableFlag("USE_DDD_COMPLIANT_TOOLS", nil) {
		t.Fatal("EnableFlag failed")
	}
	if !svc.IsEnabled("USE_DDD_COMPLIANT_TOOLS") {
		t.Fatal("flag should be enabled")
	}

	t.Setenv("FEATURE_USE_DDD_COMPLIANT_TOOLS", "false")
	if svc.IsEnabled("USE_DDD_COMPLIANT_TOOLS") {
		t.Error(`"false" override should disable the flag`)
	}

	t.Setenv("FEATURE_USE_DDD_COMPLIANT_TOOLS", "YES")
	if !svc.IsEnabled("USE_DDD_COMPLIANT_TOOLS") {
		t.Error(`"YES" override should enable the flag`)
	}

	t.Setenv("FEATURE_USE_DDD_COMPLIANT_TOOLS", "off")
	if svc.IsEnabled("USE_DDD_COMPLIANT_TOOLS") {
		t.Error(`"off" override should disable the flag`)
	}

	// A set-but-empty variable short-circuits to False (os.getenv returns "", not None).
	t.Setenv("FEATURE_USE_DDD_COMPLIANT_TOOLS", "")
	if svc.IsEnabled("USE_DDD_COMPLIANT_TOOLS") {
		t.Error("empty override should disable the flag")
	}
}

func TestFeatureFlagService_IsEnabledUnknownDefaultFalse(t *testing.T) {
	svc, _ := zpFeatTestNewService(t)
	if svc.IsEnabled("DOES_NOT_EXIST") {
		t.Error("unknown flag should default to False")
	}
}

func TestFeatureFlagService_GetFlagStatusKeyOrder(t *testing.T) {
	svc, _ := zpFeatTestNewService(t)
	status := svc.GetFlagStatus("USE_NEW_GET_TASK")
	if status == nil {
		t.Fatal("status is nil")
	}
	want := "name,enabled,description,created_at,updated_at,metadata,environment_override"
	if got := zpFeatOrderedKeys(t, status); got != want {
		t.Fatalf("status key order = %q, want %q", got, want)
	}
	if v, _ := status.Get("environment_override"); v != nil {
		t.Errorf("environment_override = %v, want nil", v)
	}
	if svc.GetFlagStatus("MISSING") != nil {
		t.Error("missing flag status should be nil")
	}
}

func TestFeatureFlagService_EnableDisablePersists(t *testing.T) {
	svc, path := zpFeatTestNewService(t)

	metadata := entities.NewOrderedMap[any]()
	metadata.Set("reason", "test")
	if !svc.EnableFlag("USE_NEW_CREATE_TASK", metadata) {
		t.Fatal("EnableFlag returned false")
	}

	reloaded := NewFeatureFlagService(&path, nil)
	if !reloaded.IsEnabled("USE_NEW_CREATE_TASK") {
		t.Fatal("enabled flag was not persisted")
	}
	status := reloaded.GetFlagStatus("USE_NEW_CREATE_TASK")
	md, _ := status.Get("metadata")
	mdMap := md.(*entities.OrderedMap[any])
	if v, _ := mdMap.Get("reason"); v != "test" {
		t.Errorf("metadata reason = %v, want test", v)
	}

	if !reloaded.DisableFlag("USE_NEW_CREATE_TASK", nil) {
		t.Fatal("DisableFlag returned false")
	}
	if reloaded.IsEnabled("USE_NEW_CREATE_TASK") {
		t.Error("disabled flag should not be enabled")
	}

	if svc.EnableFlag("UNKNOWN", nil) {
		t.Error("EnableFlag on unknown flag should return false")
	}
}

func TestFeatureFlagService_SavedKeyOrder(t *testing.T) {
	svc, path := zpFeatTestNewService(t)
	_ = svc

	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	decoded, err := entities.DecodeJSON(raw)
	if err != nil {
		t.Fatal(err)
	}
	data := decoded.(*entities.OrderedMap[any])
	if got := zpFeatOrderedKeys(t, data); got != "USE_DDD_COMPLIANT_TOOLS,USE_NEW_CREATE_TASK,USE_NEW_UPDATE_TASK,USE_NEW_GET_TASK,USE_NEW_LIST_TASKS,USE_NEW_DELETE_TASK,USE_NEW_SEARCH_TASKS,USE_NEW_NEXT_TASK,USE_NEW_MANAGE_DEPENDENCIES,USE_NEW_MANAGE_SUBTASKS,ENABLE_PARALLEL_TESTING,ENABLE_MIGRATION_LOGGING" {
		t.Fatalf("saved top-level key order = %q", got)
	}
	first, _ := data.Get("USE_DDD_COMPLIANT_TOOLS")
	firstMap := first.(*entities.OrderedMap[any])
	if got := zpFeatOrderedKeys(t, firstMap); got != "name,enabled,description,created_at,updated_at,metadata" {
		t.Fatalf("saved flag key order = %q", got)
	}
}

func TestFeatureFlagService_GetMigrationStatus(t *testing.T) {
	svc, _ := zpFeatTestNewService(t)

	status := svc.GetMigrationStatus()
	progress, _ := status.Get("migration_progress")
	progressMap := progress.(*entities.OrderedMap[any])
	if v, _ := progressMap.Get("enabled_operations"); v != 0 {
		t.Errorf("enabled_operations = %v, want 0", v)
	}
	if v, _ := progressMap.Get("total_operations"); v != 10 {
		t.Errorf("total_operations = %v, want 10", v)
	}
	if v, _ := progressMap.Get("percentage"); v != 0.0 {
		t.Errorf("percentage = %v, want 0.0", v)
	}
	if v, _ := status.Get("master_flag_enabled"); v != false {
		t.Errorf("master_flag_enabled = %v, want false", v)
	}
	if v, _ := status.Get("parallel_testing_enabled"); v != true {
		t.Errorf("parallel_testing_enabled = %v, want true", v)
	}

	if !svc.EnableMigrationPhase("critical") {
		t.Fatal("EnableMigrationPhase(critical) returned false")
	}
	status = svc.GetMigrationStatus()
	progress, _ = status.Get("migration_progress")
	progressMap = progress.(*entities.OrderedMap[any])
	if v, _ := progressMap.Get("enabled_operations"); v != 3 {
		t.Errorf("enabled_operations after critical = %v, want 3", v)
	}
	if v, _ := progressMap.Get("percentage"); v != 30.0 {
		t.Errorf("percentage after critical = %v, want 30.0", v)
	}
	if v, _ := status.Get("master_flag_enabled"); v != false {
		t.Errorf("master_flag_enabled after critical = %v, want false", v)
	}

	if !svc.EnableMigrationPhase("all") {
		t.Fatal("EnableMigrationPhase(all) returned false")
	}
	status = svc.GetMigrationStatus()
	progress, _ = status.Get("migration_progress")
	progressMap = progress.(*entities.OrderedMap[any])
	if v, _ := progressMap.Get("enabled_operations"); v != 10 {
		t.Errorf("enabled_operations after all = %v, want 10", v)
	}
	if v, _ := progressMap.Get("percentage"); v != 100.0 {
		t.Errorf("percentage after all = %v, want 100.0", v)
	}
	if v, _ := status.Get("master_flag_enabled"); v != true {
		t.Errorf("master_flag_enabled after all = %v, want true", v)
	}

	if svc.EnableMigrationPhase("bogus") {
		t.Error("unknown phase should return false")
	}

	if !svc.RollbackMigration() {
		t.Fatal("RollbackMigration returned false")
	}
	if svc.IsEnabled("USE_DDD_COMPLIANT_TOOLS") {
		t.Error("rollback should disable master flag")
	}
	if v, _ := svc.GetMigrationStatus().Get("master_flag_enabled"); v != false {
		t.Errorf("master_flag_enabled after rollback = %v, want false", v)
	}
}

func TestFeatureFlagService_WithUser(t *testing.T) {
	svc, _ := zpFeatTestNewService(t)
	other := svc.WithUser("user-1")
	if other == svc {
		t.Fatal("WithUser should return a new instance")
	}
	if other.userID == nil || *other.userID != "user-1" {
		t.Fatalf("userID = %v, want user-1", other.userID)
	}
	if other.configPath != svc.configPath {
		t.Errorf("configPath = %q, want %q", other.configPath, svc.configPath)
	}
}

func TestFeatureFlagService_IsFeatureEnabledSingleton(t *testing.T) {
	svc, _ := zpFeatTestNewService(t)
	if !svc.EnableFlag("USE_NEW_GET_TASK", nil) {
		t.Fatal("EnableFlag failed")
	}

	prev := zpFeatFeatureFlagService
	zpFeatFeatureFlagService = svc
	t.Cleanup(func() { zpFeatFeatureFlagService = prev })

	if GetFeatureFlagService() != svc {
		t.Fatal("GetFeatureFlagService should return the global instance")
	}
	if !IsFeatureEnabled("USE_NEW_GET_TASK") {
		t.Error("IsFeatureEnabled should use the global service")
	}
	if IsFeatureEnabled("USE_NEW_CREATE_TASK") {
		t.Error("disabled global flag should be false")
	}
}

func TestFeatureFlagService_MetadataUpdateMergesInPlace(t *testing.T) {
	svc, _ := zpFeatTestNewService(t)

	first := entities.NewOrderedMap[any]()
	first.Set("a", 1)
	first.Set("b", 2)
	if !svc.EnableFlag("USE_NEW_GET_TASK", first) {
		t.Fatal("EnableFlag failed")
	}
	second := entities.NewOrderedMap[any]()
	second.Set("b", 3)
	second.Set("c", 4)
	if !svc.EnableFlag("USE_NEW_GET_TASK", second) {
		t.Fatal("EnableFlag failed")
	}
	status := svc.GetFlagStatus("USE_NEW_GET_TASK")
	md, _ := status.Get("metadata")
	mdMap := md.(*entities.OrderedMap[any])
	if got := zpFeatOrderedKeys(t, mdMap); got != "a,b,c" {
		t.Fatalf("metadata key order = %q, want a,b,c", got)
	}
	if v, _ := mdMap.Get("b"); v != 3 {
		t.Errorf("metadata b = %v, want 3", v)
	}
	if !reflect.DeepEqual(mdMap.Keys(), []string{"a", "b", "c"}) {
		t.Errorf("metadata keys = %v", mdMap.Keys())
	}
}
