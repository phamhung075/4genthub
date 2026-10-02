package use_cases

import (
	"context"
	"testing"

	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

type fakeAuth struct {
	userID string
}

func (f *fakeAuth) GetAuthenticatedUserID(ctx context.Context, providedUserID *string, operationName string) (string, error) {
	return f.userID, nil
}

type fakeFacade struct {
	config *tmentities.OrderedMap[any]
}

func (f *fakeFacade) GetAgentForCall(ctx context.Context, userID *amvo.UserId, agentSlug string) (*tmentities.OrderedMap[any], error) {
	return f.config, nil
}

func TestCallAgentUseCaseExecuteSuccess(t *testing.T) {
	config := tmentities.NewOrderedMap[any]()
	config.Set("slug", "coding-agent")
	uc := NewCallAgentUseCase(
		&fakeAuth{userID: "00000000-0000-0000-0000-000000000001"},
		&fakeFacade{config: config},
	)
	resp := uc.Execute(context.Background(), "coding-agent", nil)
	if v, _ := resp.Get("success"); v != true {
		t.Fatalf("success = %v, want true", v)
	}
	if v, _ := resp.Get("source"); v != "agent-management-system" {
		t.Fatalf("source = %v", v)
	}
	if v, _ := resp.Get("agent"); v != config {
		t.Fatalf("agent = %v, want the facade config", v)
	}
}
