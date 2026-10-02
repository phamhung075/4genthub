package repositories

import (
	"context"
	"errors"
	"reflect"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure"
	"agenthub/fastmcp/task_management/infrastructure/database"

	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
)

func TestBaseTimestampRepositoryQueriesAndCRUD(t *testing.T) {
	fx := newSubtaskRepoFixture(t)
	ctx := context.Background()
	repo := subtaskRepoNewRepo(t, fx, fx.userID)
	first := subtaskRepoNewEntity(t, fx.parent, "one", "todo", 0, nil)
	subtaskRepoMustSave(t, repo, first)
	second := subtaskRepoNewEntity(t, fx.parent, "two", "todo", 0, nil)
	subtaskRepoMustSave(t, repo, second)

	base, err := NewBaseTimestampRepository[database.Subtask]("subtasks", fx.sm)
	if err != nil {
		t.Fatal(err)
	}
	stats, err := base.GetTimestampStats(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := stats.Get("entity_type"); v != "Subtask" {
		t.Fatalf("entity_type %v", v)
	}
	if v, _ := stats.Get("total_count"); v != 2 {
		t.Fatalf("total_count %v", v)
	}
	if v, _ := stats.Get("oldest_created"); v == nil {
		t.Fatal("oldest_created should be an ISO timestamp")
	}

	rows, err := base.FindByTimestampRange(ctx, time.Now().UTC().Add(-time.Hour), time.Now().UTC().Add(time.Hour), "created_at")
	if err != nil || len(rows) != 2 {
		t.Fatalf("range: %v %d", err, len(rows))
	}
	if _, err := base.FindByTimestampRange(ctx, time.Now().UTC(), time.Now().UTC(), "bogus"); err == nil {
		t.Fatal("invalid timestamp field must be rejected")
	}
	stale, err := base.FindStaleEntities(ctx, 24)
	if err != nil || len(stale) != 0 {
		t.Fatalf("stale: %v %d", err, len(stale))
	}
	touched, err := base.TouchEntity(ctx, first.ID.Value, "reason")
	if err != nil || touched == nil {
		t.Fatalf("touch: %v %v", touched, err)
	}
	if _, err := base.TouchEntity(ctx, value_objects.NewUUIDv4(), "reason"); err == nil {
		t.Fatal("touch on a missing entity must fail")
	}

	row, err := base.GetByID(ctx, second.ID.Value)
	if err != nil || row == nil {
		t.Fatalf("get: %v %v", row, err)
	}
	row.Title = "updated-by-base"
	saved, err := base.Save(ctx, row, true)
	if err != nil || saved == nil || saved.Title != "updated-by-base" {
		t.Fatalf("base save: %v %+v", err, saved)
	}
	if err := base.Delete(ctx, row); err != nil {
		t.Fatalf("base delete: %v", err)
	}
	if gone, _ := base.GetByID(ctx, second.ID.Value); gone != nil {
		t.Fatal("row should be deleted")
	}
}

func TestEventPublishingMixin(t *testing.T) {
	bus := infrastructure.NewEventBus()
	received := []any{}
	bus.Subscribe(reflect.TypeOf(events.TaskUpdatedEvent{}), "spy", func(e any) { received = append(received, e) }, 0)

	mixin := NewEventPublishingMixin()
	mixin.SetEventBus(bus)
	if !mixin.IsEventPublishingEnabled() {
		t.Fatal("event publishing must default to enabled")
	}
	parent := value_objects.GenerateNewTaskId()
	st := subtaskRepoNewEntity(t, parent, "evented", "todo", 0, nil)
	if err := st.UpdateTitle("changed"); err != nil {
		t.Fatal(err)
	}
	if got := mixin.PublishEntityEvents(st); got != 1 || len(received) != 1 {
		t.Fatalf("sync published=%d received=%d", got, len(received))
	}
	if len(st.GetEvents()) != 0 {
		t.Fatal("sync publish must clear the entity events")
	}

	st2 := subtaskRepoNewEntity(t, parent, "evented-2", "todo", 0, nil)
	_ = st2.UpdateTitle("changed-2")
	if got := mixin.PublishEntityEventsAsync(st2); got != 1 {
		t.Fatalf("async published=%d", got)
	}

	mixin.DisableEventPublishing()
	st3 := subtaskRepoNewEntity(t, parent, "evented-3", "todo", 0, nil)
	_ = st3.UpdateTitle("changed-3")
	if got := mixin.PublishEntityEvents(st3); got != 0 {
		t.Fatalf("disabled should publish nothing, got %d", got)
	}
	if got := mixin.PublishEventsBatch([]any{st3}); got != 0 {
		t.Fatalf("disabled batch should publish nothing, got %d", got)
	}

	mixin.EnableEventPublishing()
	st4 := subtaskRepoNewEntity(t, parent, "evented-4", "todo", 0, nil)
	_ = st4.UpdateTitle("changed-4")
	if got := mixin.PublishEventsBatch([]any{st4}); got != 1 {
		t.Fatalf("batch published=%d", got)
	}
}

type subtaskRepoFakeCleanEntity struct {
	UpdatedAt *time.Time
	touches   int
	reason    string
}

func (e *subtaskRepoFakeCleanEntity) Touch(reason string) error {
	e.touches++
	e.reason = reason
	return nil
}

type subtaskRepoFakeCleanImpl struct {
	saved []*subtaskRepoFakeCleanEntity
}

func (i *subtaskRepoFakeCleanImpl) PerformSave(entity *subtaskRepoFakeCleanEntity) (*subtaskRepoFakeCleanEntity, error) {
	i.saved = append(i.saved, entity)
	return entity, nil
}

func (i *subtaskRepoFakeCleanImpl) PerformBulkSave(entities []*subtaskRepoFakeCleanEntity) ([]*subtaskRepoFakeCleanEntity, error) {
	i.saved = append(i.saved, entities...)
	return entities, nil
}

func TestCleanTimestampRepositoryMixin(t *testing.T) {
	impl := &subtaskRepoFakeCleanImpl{}
	repository := &CleanTimestampRepository[*subtaskRepoFakeCleanEntity]{Impl: impl}

	single := &subtaskRepoFakeCleanEntity{}
	out, err := repository.SaveWithCleanTimestamp(single, "single")
	if err != nil || out != single || single.touches != 1 || single.reason != "single" {
		t.Fatalf("single: err=%v touches=%d reason=%q", err, single.touches, single.reason)
	}
	if empty, err := repository.SaveBulkWithConsistentTimestamp(nil, "bulk"); err != nil || len(empty) != 0 {
		t.Fatalf("empty bulk: %v %d", err, len(empty))
	}
	a, b := &subtaskRepoFakeCleanEntity{}, &subtaskRepoFakeCleanEntity{}
	list, err := repository.SaveBulkWithConsistentTimestamp([]*subtaskRepoFakeCleanEntity{a, b}, "bulk")
	if err != nil || len(list) != 2 {
		t.Fatalf("bulk: %v %d", err, len(list))
	}
	if a.UpdatedAt == nil || b.UpdatedAt == nil || !a.UpdatedAt.Equal(*b.UpdatedAt) {
		t.Fatalf("bulk timestamps differ: %v %v", a.UpdatedAt, b.UpdatedAt)
	}
	if a.touches != 1 || b.touches != 1 {
		t.Fatalf("bulk touches: %d %d", a.touches, b.touches)
	}
}

type subtaskRepoTimeEntity struct {
	CreatedAt *time.Time
	UpdatedAt *time.Time
}

type subtaskRepoNoTimeEntity struct {
	Name string
}

type subtaskRepoFakeDBUtils struct{}

func (subtaskRepoFakeDBUtils) NormalizeTimestamp(timestamp any) (*time.Time, error) {
	switch v := timestamp.(type) {
	case time.Time:
		return &v, nil
	case *time.Time:
		return v, nil
	}
	return nil, errors.New("bad timestamp")
}

func (subtaskRepoFakeDBUtils) CheckDatabaseHealth() (*entities.OrderedMap[any], error) {
	out := entities.NewOrderedMap[any]()
	out.Set("status", "healthy")
	return out, nil
}

func (subtaskRepoFakeDBUtils) GetSession() (any, error) { return "session", nil }

func TestUtilsDatabaseTypeAndConfig(t *testing.T) {
	t.Setenv("DATABASE_TYPE", "PostgreSQL")
	got, err := GetValidatedDatabaseType()
	if err != nil || got != "postgresql" {
		t.Fatalf("type: %v %v", got, err)
	}
	t.Setenv("DATABASE_TYPE", "")
	if _, err := GetValidatedDatabaseType(); err == nil {
		t.Fatal("empty DATABASE_TYPE must be rejected")
	}
	t.Setenv("DATABASE_TYPE", "oracle")
	if _, err := GetValidatedDatabaseType(); err == nil {
		t.Fatal("invalid DATABASE_TYPE must be rejected")
	}

	t.Setenv("DATABASE_TYPE", "postgresql")
	t.Setenv("ENVIRONMENT", "development")
	t.Setenv("REDIS_ENABLED", "TRUE")
	t.Setenv("USE_CACHE", "true")
	t.Setenv("PERFORMANCE_MODE", "false")
	config, err := GetRepositoryConfig()
	if err != nil {
		t.Fatal(err)
	}
	checks := map[string]any{
		"environment": "development", "database_type": "postgresql", "redis_enabled": true,
		"use_cache": true, "debug_mode": true, "performance_mode": false,
		"timestamp_events_enabled": true, "clean_architecture_mode": true,
	}
	for key, want := range checks {
		if v, _ := config.Get(key); v != want {
			t.Fatalf("%s=%v want %v", key, v, want)
		}
	}
	t.Setenv("ENVIRONMENT", "not-real")
	config, _ = GetRepositoryConfig()
	if v, _ := config.Get("environment"); v != "production" {
		t.Fatalf("unknown environment should fall back: %v", v)
	}
}

func TestUtilsValidateEntityTimestamps(t *testing.T) {
	now := time.Now().UTC()
	ok := &subtaskRepoTimeEntity{CreatedAt: &now, UpdatedAt: &now}
	result, err := ValidateEntityTimestamps(ok)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := result.Get("has_timestamps"); v != true {
		t.Fatalf("has_timestamps %v", v)
	}
	if v, _ := result.Get("timestamps_valid"); v != true {
		t.Fatalf("timestamps_valid %v", v)
	}
	if v, _ := result.Get("timezone_compliant"); v != true {
		t.Fatalf("timezone_compliant %v", v)
	}

	missing, _ := ValidateEntityTimestamps(&subtaskRepoNoTimeEntity{})
	if v, _ := missing.Get("has_timestamps"); v != false {
		t.Fatalf("has_timestamps missing %v", v)
	}
	if errs, _ := missing.Get("errors"); len(errs.([]any)) != 1 {
		t.Fatalf("errors %v", errs)
	}

	zone := time.FixedZone("offset", 3600)
	zoned := time.Now().In(zone)
	notUTC, _ := ValidateEntityTimestamps(&subtaskRepoTimeEntity{CreatedAt: &zoned, UpdatedAt: &zoned})
	if v, _ := notUTC.Get("timestamps_valid"); v != false {
		t.Fatalf("non-UTC should be invalid: %v", v)
	}

	before := now.Add(-time.Hour)
	backwards, _ := ValidateEntityTimestamps(&subtaskRepoTimeEntity{CreatedAt: &now, UpdatedAt: &before})
	if v, _ := backwards.Get("timestamps_valid"); v != false {
		t.Fatalf("updated_at before created_at should be invalid: %v", v)
	}
}

func TestUtilsNormalizeQueryParams(t *testing.T) {
	SetRepositoryDatabaseUtils(subtaskRepoFakeDBUtils{})
	defer SetRepositoryDatabaseUtils(nil)
	ts := time.Now().UTC()
	params := NewKwargs(
		"created_at", ts,
		"name", "  spaced  ",
		"blank", "   ",
		"none", nil,
		"list", []any{1, nil, 2},
		"keep", 5,
	)
	normalized, err := NormalizeQueryParams(params)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := normalized.Get("created_at"); v != ts {
		t.Fatalf("created_at %v", v)
	}
	if v, _ := normalized.Get("name"); v != "spaced" {
		t.Fatalf("name %v", v)
	}
	if v, ok := normalized.Get("blank"); !ok || v != nil {
		t.Fatalf("blank %v", v)
	}
	if normalized.Has("none") {
		t.Fatal("None values are skipped")
	}
	if v, _ := normalized.Get("list"); !reflect.DeepEqual(v, []any{1, 2}) {
		t.Fatalf("list %v", v)
	}
	if v, _ := normalized.Get("keep"); v != 5 {
		t.Fatalf("keep %v", v)
	}

	if !BothAreDatetime(ts, &ts) || BothAreDatetime(ts, "x") {
		t.Fatal("BothAreDatetime")
	}
}

func TestUtilsWithDatabaseErrorHandling(t *testing.T) {
	_, err := WithDatabaseErrorHandling(func() (int, error) {
		return 0, exceptions.NewValidationException("validation", "", nil)
	})
	var ve *exceptions.ValidationException
	if !errors.As(err, &ve) {
		t.Fatalf("validation must pass through: %T %v", err, err)
	}
	_, err = WithDatabaseErrorHandling(func() (int, error) { return 0, errors.New("boom") })
	var de *exceptions.DatabaseException
	if !errors.As(err, &de) || !strings.Contains(err.Error(), "Unexpected database error") {
		t.Fatalf("generic error wrapping: %T %v", err, err)
	}
}

func TestUtilsPerformanceSettingsAndMetrics(t *testing.T) {
	t.Setenv("DATABASE_TYPE", "postgresql")
	t.Setenv("REPO_BATCH_SIZE", "7")
	t.Setenv("DB_POOL_SIZE", "3")
	t.Setenv("QUERY_TIMEOUT", "9")
	t.Setenv("USE_CACHE", "true")
	settings, err := GetPerformanceSettings()
	if err != nil {
		t.Fatal(err)
	}
	for key, want := range map[string]any{
		"batch_size": 7, "connection_pool_size": 3, "query_timeout": 9,
		"enable_query_cache": true, "timestamp_index_optimization": true, "bulk_operations_enabled": true,
	} {
		if v, _ := settings.Get(key); v != want {
			t.Fatalf("%s=%v want %v", key, v, want)
		}
	}

	metrics := NewRepositoryMetrics()
	metrics.RecordOperation("a")
	metrics.RecordOperation("a")
	metrics.RecordError("b")
	if got := metrics.CalculateSuccessRate(); got != 2.0/3.0 {
		t.Fatalf("success rate %v", got)
	}
	snapshot := metrics.GetMetrics()
	if v, _ := snapshot.Get("total_operations"); v != 2 {
		t.Fatalf("total_operations %v", v)
	}
	if v, _ := snapshot.Get("total_errors"); v != 1 {
		t.Fatalf("total_errors %v", v)
	}
	if v, _ := snapshot.Get("collected_at"); v == nil {
		t.Fatal("collected_at missing")
	}
	if GetRepositoryMetrics() != GetRepositoryMetrics() {
		t.Fatal("GetRepositoryMetrics must be a singleton")
	}

	// health status without registered database utils
	SetRepositoryDatabaseUtils(nil)
	health := GetRepositoryHealthStatus()
	if v, _ := health.Get("status"); v != "unhealthy" {
		t.Fatalf("health without utils: %v", v)
	}
	// health status with the fake registration
	SetRepositoryDatabaseUtils(subtaskRepoFakeDBUtils{})
	defer SetRepositoryDatabaseUtils(nil)
	health = GetRepositoryHealthStatus()
	if v, _ := health.Get("status"); v != "healthy" {
		t.Fatalf("health: %v", v)
	}
	if _, err := CreateRepositorySessionContext(); err != nil {
		t.Fatalf("session context: %v", err)
	}
}

type subtaskRepoFakeFactoryBackend struct{}

func (subtaskRepoFakeFactoryBackend) GetSubtaskRepository(userID *string) (domainrepos.SubtaskRepository, error) {
	return nil, nil
}

func subtaskRepoStringPtr(v string) *string { return &v }

func TestSubtaskRepositoryFactory(t *testing.T) {
	t.Setenv("MCP_DB_PATH", "/tmp/agenthub-factory.db")
	emptyRoot := ""
	factory := NewSubtaskRepositoryFactory(nil, nil, &emptyRoot, nil)
	if got := factory.GetSubtaskDBPath("p", "main", nil); got != "/tmp/agenthub-factory.db" {
		t.Fatalf("db path %q", got)
	}
	if !factory.ValidateUserProjectTree("p", "main", nil) {
		t.Fatal("validate must be true")
	}
	if _, err := factory.CreateSubtaskRepository("", "main", nil); err == nil {
		t.Fatal("project_id is required")
	}
	SetSubtaskRepositoryFactoryBackend(nil)
	defer SetSubtaskRepositoryFactoryBackend(nil)
	if _, err := factory.CreateSubtaskRepository("p", "main", nil); err == nil {
		t.Fatal("backend missing")
	}
	SetSubtaskRepositoryFactoryBackend(subtaskRepoFakeFactoryBackend{})
	if _, err := factory.CreateSubtaskRepository("p", "main", nil); err != nil {
		t.Fatalf("backend delegation: %v", err)
	}
	if _, err := factory.Create("p", "main", "u"); err != nil {
		t.Fatalf("classmethod create: %v", err)
	}
	if _, err := factory.CreateSQLiteSubtaskRepository("p", "main", nil, nil); err != nil {
		t.Fatalf("sqlite create: %v", err)
	}
	if got := factory.GetSubtaskDBPath("p", "main", nil); got != "/tmp/agenthub-factory.db" {
		t.Fatalf("sqlite db path %q", got)
	}

	fx := newSubtaskRepoFixture(t)
	withSession := NewSubtaskRepositoryFactory(nil, &fx.userID, nil, fx.sm)
	repo, err := withSession.CreateORMSubtaskRepository(nil)
	if err != nil || repo == nil {
		t.Fatalf("orm factory: %v %v", repo, err)
	}
	if repo.UserID == nil || *repo.UserID != fx.userID {
		t.Fatal("default user id not applied")
	}
	if root := FindProjectRoot(); root == "" {
		t.Fatal("project root must not be empty")
	}
}
