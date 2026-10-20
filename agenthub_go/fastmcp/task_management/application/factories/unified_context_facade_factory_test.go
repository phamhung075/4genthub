package factories

import (
	"context"
	"errors"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// Expectations computed from Python uuid.uuid5 with
// namespace a47ae7b9-1d4b-4e5f-8b5a-9c3e5d2f8a1c.

func TestZpUCFUUID5(t *testing.T) {
	userUUID := zpUCFUUID5(zpUCFNamespaceUUID, "non-uuid-user")
	if userUUID != "54d2b21e-3de3-59c9-9518-9880c26f9861" {
		t.Fatalf("user uuid = %s", userUUID)
	}
	global := zpUCFUUID5(zpUCFNamespaceUUID, userUUID)
	if global != "b404fbdf-7611-5d4a-82a2-fbcf2032e8f7" {
		t.Fatalf("global uuid = %s", global)
	}
}

func TestZpUCFTryParseUUID(t *testing.T) {
	got, ok := zpUCFTryParseUUID("11111111-1111-1111-1111-111111111111")
	if !ok || got != "11111111-1111-1111-1111-111111111111" {
		t.Fatalf("parse = %q ok=%v", got, ok)
	}
	if _, ok := zpUCFTryParseUUID("non-uuid-user"); ok {
		t.Fatal("non-uuid must fail to parse")
	}
	// Python: uuid5(ns, str(uuid.UUID(user_id))) for a valid user id.
	if g := zpUCFUUID5(zpUCFNamespaceUUID, got); g != "96c4468b-c109-5025-a99d-0b37e21fb92d" {
		t.Fatalf("global uuid = %s", g)
	}
}

func TestFactoryRefusesWithoutARepositoryBuilder(t *testing.T) {
	unifiedContextFacadeFactoryInstance = nil
	unifiedContextFacadeFactoryInitialized = false
	UnifiedContextRepositoryBuilder = nil

	f, err := NewUnifiedContextFacadeFactory(context.Background(), &database.SessionManager{})
	if err == nil || f != nil {
		t.Fatalf("nil repository builder: f=%v err=%v, want a refusal", f, err)
	}

	f, err = NewUnifiedContextFacadeFactory(context.Background(), nil)
	if err == nil || f != nil {
		t.Fatalf("nil session manager: f=%v err=%v, want a refusal", f, err)
	}
}

func TestFactoryRefusesWhenTheBuilderFails(t *testing.T) {
	unifiedContextFacadeFactoryInstance = nil
	unifiedContextFacadeFactoryInitialized = false
	UnifiedContextRepositoryBuilder = func(*database.SessionManager, *string) (
		services.UnifiedContextRepository, services.UnifiedContextRepository,
		services.UnifiedContextRepository, services.UnifiedContextRepository, error) {
		return nil, nil, nil, nil, errors.New("database unreachable")
	}
	t.Cleanup(func() { UnifiedContextRepositoryBuilder = nil })

	f, err := NewUnifiedContextFacadeFactory(context.Background(), &database.SessionManager{})
	if err == nil || f != nil {
		t.Fatalf("failing builder: f=%v err=%v, want a refusal", f, err)
	}
	if !strings.Contains(err.Error(), "database unreachable") {
		t.Fatalf("the builder's cause is not carried: %v", err)
	}
}
