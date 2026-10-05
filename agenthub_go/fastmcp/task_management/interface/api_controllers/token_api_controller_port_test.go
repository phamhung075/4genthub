package api_controllers

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// fakeTokenFacade implements TokenManageFacade with only the methods under test
// returning canned data.
type fakeTokenFacade struct {
	createResult *entities.OrderedMap[any]
}

func (f *fakeTokenFacade) RevokeUserTokens(context.Context, string) *entities.OrderedMap[any] {
	return nil
}
func (f *fakeTokenFacade) GetTokenStats() *entities.OrderedMap[any] { return nil }
func (f *fakeTokenFacade) CleanupExpiredTokens(context.Context) *entities.OrderedMap[any] {
	return nil
}
func (f *fakeTokenFacade) CreateAPIToken(context.Context, string, string, []string, int, *int, *entities.OrderedMap[any], any) *entities.OrderedMap[any] {
	return f.createResult
}
func (f *fakeTokenFacade) ListUserTokens(context.Context, string, any, int, int) *entities.OrderedMap[any] {
	return nil
}
func (f *fakeTokenFacade) GetTokenDetails(context.Context, string, string, any) *entities.OrderedMap[any] {
	return nil
}
func (f *fakeTokenFacade) RevokeToken(context.Context, string, string, any) *entities.OrderedMap[any] {
	return nil
}
func (f *fakeTokenFacade) DeleteToken(context.Context, string, string, any) *entities.OrderedMap[any] {
	return nil
}
func (f *fakeTokenFacade) ReactivateToken(context.Context, string, string, any) *entities.OrderedMap[any] {
	return nil
}
func (f *fakeTokenFacade) RotateToken(context.Context, string, string, any) *entities.OrderedMap[any] {
	return nil
}
func (f *fakeTokenFacade) ValidateToken(context.Context, string, any) *entities.OrderedMap[any] {
	return nil
}

type fakeTokenProvider struct{ facade TokenManageFacade }

func (p fakeTokenProvider) GetTokenFacade() (any, error) { return p.facade, nil }

// TestGenerateAPITokenSuccess mirrors token_api_controller.generate_api_token:
// when result["success"] is truthy the response reshapes to
// {"success": true, "token_data": result["token"]}.
func TestGenerateAPITokenSuccess(t *testing.T) {
	token := entities.NewOrderedMap[any]()
	token.Set("id", "tok1")
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("token", token)
	facade := &fakeTokenFacade{createResult: result}
	c := NewTokenAPIController(fakeTokenProvider{facade: facade})

	out := c.GenerateAPIToken(context.Background(), "u1", "name", []string{"read"}, 30, nil, nil)
	if out == nil {
		t.Fatal("out = nil")
	}
	if v, _ := out.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
	got, _ := out.Get("token_data")
	if got != token {
		t.Fatalf("token_data = %v", got)
	}
}

// TestGenerateAPITokenFailure mirrors the else branch: the facade result is
// returned unchanged.
func TestGenerateAPITokenFailure(t *testing.T) {
	result := entities.NewOrderedMap[any]()
	result.Set("success", false)
	result.Set("error", "nope")
	facade := &fakeTokenFacade{createResult: result}
	c := NewTokenAPIController(fakeTokenProvider{facade: facade})

	out := c.GenerateAPIToken(context.Background(), "u1", "name", nil, 30, nil, nil)
	if out != result {
		t.Fatalf("out = %v, want the facade result unchanged", out)
	}
}
