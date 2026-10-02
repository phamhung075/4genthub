package adapters

import (
	"context"
	"testing"
)

func TestServiceAdapterFactoryGetters(t *testing.T) {
	factory := GetServiceAdapterFactory()
	if factory == nil {
		t.Fatal("expected non-nil factory")
	}

	if factory.GetDatabaseSessionFactory() == nil {
		t.Fatal("expected non-nil database session factory")
	}
	if factory.GetEventStore() == nil {
		t.Fatal("expected non-nil event store")
	}
	if factory.GetCacheService() == nil {
		t.Fatal("expected non-nil cache service")
	}
	if factory.GetRepositoryFactory() == nil {
		t.Fatal("expected non-nil repository factory")
	}
	if factory.GetTaskRepositoryFactory() == nil {
		t.Fatal("expected non-nil task repository factory")
	}
	if factory.GetProjectRepositoryFactory() == nil {
		t.Fatal("expected non-nil project repository factory")
	}
	if factory.GetGitBranchRepositoryFactory() == nil {
		t.Fatal("expected non-nil git branch repository factory")
	}
	if factory.GetNotificationService() == nil {
		t.Fatal("expected non-nil notification service")
	}
	if factory.GetEventBus() == nil {
		t.Fatal("expected non-nil event bus")
	}
	if factory.GetLoggingService() == nil {
		t.Fatal("expected non-nil logging service")
	}
	if factory.GetMonitoringService() == nil {
		t.Fatal("expected non-nil monitoring service")
	}
	if factory.GetProcessMonitor() == nil {
		t.Fatal("expected non-nil process monitor")
	}
	if factory.GetValidationService() == nil {
		t.Fatal("expected non-nil validation service")
	}
	if factory.GetDocumentValidator() == nil {
		t.Fatal("expected non-nil document validator")
	}
	if factory.GetPathResolver() == nil {
		t.Fatal("expected non-nil path resolver")
	}
	if factory.GetAgentDocGenerator() == nil {
		t.Fatal("expected non-nil agent doc generator")
	}
}

func TestRepositoryFactoryAdapter(t *testing.T) {
	rf := NewRepositoryFactoryAdapter()
	ctx := context.Background()

	taskRepo := rf.CreateTaskRepository()
	if taskRepo == nil {
		t.Fatal("expected task repository")
	}
	_, _ = taskRepo.FindByID(ctx, "id-1")
	_, _ = taskRepo.FindAll(ctx)
	_, _ = taskRepo.Save(ctx, "entity")
	_, _ = taskRepo.Delete(ctx, "entity")

	projRepo := rf.CreateProjectRepository()
	if projRepo == nil {
		t.Fatal("expected project repository")
	}
	branchRepo := rf.CreateGitBranchRepository()
	if branchRepo == nil {
		t.Fatal("expected git branch repository")
	}
	agentRepo := rf.CreateAgentRepository()
	if agentRepo == nil {
		t.Fatal("expected agent repository")
	}
	ctxRepo := rf.CreateContextRepository()
	if ctxRepo == nil {
		t.Fatal("expected context repository")
	}
	subtaskRepo := rf.CreateSubtaskRepository()
	if subtaskRepo == nil {
		t.Fatal("expected subtask repository")
	}
}

func TestSQLAlchemySessionAdapter(t *testing.T) {
	factory := NewSQLAlchemySessionFactory()
	sess, closeFn, err := factory.CreateSession()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if sess == nil {
		t.Fatal("expected non-nil session")
	}
	if err := sess.Add("test"); err != nil {
		t.Fatalf("unexpected add error: %v", err)
	}
	if err := sess.Delete("test"); err != nil {
		t.Fatalf("unexpected delete error: %v", err)
	}
	if err := sess.Commit(); err != nil {
		t.Fatalf("unexpected commit error: %v", err)
	}
	if err := sess.Rollback(); err != nil {
		t.Fatalf("unexpected rollback error: %v", err)
	}
	if err := sess.Flush(); err != nil {
		t.Fatalf("unexpected flush error: %v", err)
	}
	q := sess.Query("model")
	if q == nil {
		t.Fatal("expected query")
	}
	q = q.Filter("crit").FilterBy(map[string]any{"a": 1}).OrderBy("crit").Limit(10).Offset(5)
	if count, _ := q.Count(); count != 0 {
		t.Fatalf("expected 0, got %d", count)
	}
	if first, _ := q.First(); first != nil {
		t.Fatalf("expected nil first, got %v", first)
	}
	if all, _ := q.All(); len(all) != 0 {
		t.Fatalf("expected empty all, got %v", all)
	}
	if err := closeFn(); err != nil {
		t.Fatalf("unexpected closeFn error: %v", err)
	}
}
