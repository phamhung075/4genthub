package api_controllers

import (
	"context"
	"testing"

	authpkg "agenthub/fastmcp/auth"
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

type fakeTokenProvider struct {
	facade TokenManageFacade
	err    error
}

func (p fakeTokenProvider) GetTokenFacade() (any, error) { return p.facade, p.err }

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

	out, err := c.GenerateAPIToken(context.Background(), "u1", "name", []string{"read"}, 30, nil, nil)
	if err != nil {
		t.Fatalf("err = %v", err)
	}
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

	out, err := c.GenerateAPIToken(context.Background(), "u1", "name", nil, 30, nil, nil)
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	if out != result {
		t.Fatalf("out = %v, want the facade result unchanged", out)
	}
}

// TestGenerateAPITokenPropagatesFacadeError pins the swallow fix: when the facade
// cannot be resolved (unset JWT_SECRET_KEY), GenerateAPIToken returns the error
// instead of discarding it and returning nil.
func TestGenerateAPITokenPropagatesFacadeError(t *testing.T) {
	want := &authpkg.HTTPException{StatusCode: 500, Detail: authpkg.ErrJWTSecretNotSet.Error()}
	c := NewTokenAPIController(fakeTokenProvider{err: want})

	out, err := c.GenerateAPIToken(context.Background(), "u1", "name", nil, 30, nil, nil)
	if out != nil {
		t.Fatalf("out = %v, want nil", out)
	}
	if err != want {
		t.Fatalf("err = %v, want the facade error %v", err, want)
	}
}

// TestSiblingFacadeResolutionErrorPropagates pins the shape fix for the eight
// TokenAPIController methods wired to the REST surface: a facade-resolution error (unset
// JWT_SECRET_KEY) is returned to the caller UNCHANGED, not collapsed into a nil map. The
// identity comparison is deliberate - a wrapped or replaced error would not carry the
// cause the HTTP layer turns into the actionable 500.
func TestSiblingFacadeResolutionErrorPropagates(t *testing.T) {
	want := &authpkg.HTTPException{StatusCode: 500, Detail: authpkg.ErrJWTSecretNotSet.Error()}
	cases := []struct {
		name string
		call func(*TokenAPIController) (*entities.OrderedMap[any], error)
	}{
		{"ListUserTokens", func(c *TokenAPIController) (*entities.OrderedMap[any], error) {
			return c.ListUserTokens(context.Background(), "u1", nil, 0, 100)
		}},
		{"GetTokenDetails", func(c *TokenAPIController) (*entities.OrderedMap[any], error) {
			return c.GetTokenDetails(context.Background(), "t1", "u1", nil)
		}},
		{"DeleteToken", func(c *TokenAPIController) (*entities.OrderedMap[any], error) {
			return c.DeleteToken(context.Background(), "t1", "u1", nil)
		}},
		{"RevokeToken", func(c *TokenAPIController) (*entities.OrderedMap[any], error) {
			return c.RevokeToken(context.Background(), "t1", "u1", nil)
		}},
		{"ReactivateToken", func(c *TokenAPIController) (*entities.OrderedMap[any], error) {
			return c.ReactivateToken(context.Background(), "t1", "u1", nil)
		}},
		{"RotateToken", func(c *TokenAPIController) (*entities.OrderedMap[any], error) {
			return c.RotateToken(context.Background(), "t1", "u1", nil)
		}},
		{"ValidateToken", func(c *TokenAPIController) (*entities.OrderedMap[any], error) {
			return c.ValidateToken(context.Background(), "tok", nil)
		}},
		{"CleanupExpiredTokens", func(c *TokenAPIController) (*entities.OrderedMap[any], error) {
			return c.CleanupExpiredTokens(context.Background())
		}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			c := NewTokenAPIController(fakeTokenProvider{err: want})
			out, err := tc.call(c)
			if out != nil {
				t.Fatalf("out = %v, want nil", out)
			}
			if err != want {
				t.Fatalf("err = %v, want the facade error %v", err, want)
			}
		})
	}
}

// TestFacadeNilInvariantReturnsBareFailure pins the other half of the shape: when
// ensureFacade reports the composition-root invariant (facade == nil, err == nil) there is
// no cause to carry, so a wired method returns (nil, nil) - the same bare failure the route
// already turns into its default 500. It must NOT fabricate an error.
func TestFacadeNilInvariantReturnsBareFailure(t *testing.T) {
	c := NewTokenAPIController(fakeTokenProvider{})
	out, err := c.ListUserTokens(context.Background(), "u1", nil, 0, 100)
	if out != nil || err != nil {
		t.Fatalf("(out, err) = (%v, %v), want (nil, nil)", out, err)
	}
}

// TestUnwiredPortMethodsKeepDeliberateDiscard pins the per-method decision for the two
// TokenAPIController methods with no Go caller (RevokeUserTokens, GetTokenStats): they keep
// their single-value signature, so the facade-resolution cause cannot be carried and the
// nil return is DELIBERATE (see the doc comment on RevokeUserTokens). Wiring either method
// to a caller must change this test to expect the propagated error, like the eight
// REST-backed siblings in TestSiblingFacadeResolutionErrorPropagates.
func TestUnwiredPortMethodsKeepDeliberateDiscard(t *testing.T) {
	want := &authpkg.HTTPException{StatusCode: 500, Detail: authpkg.ErrJWTSecretNotSet.Error()}
	c := NewTokenAPIController(fakeTokenProvider{err: want})
	if out := c.RevokeUserTokens(context.Background(), "u1"); out != nil {
		t.Fatalf("RevokeUserTokens = %v, want nil (deliberate discard)", out)
	}
	if out := c.GetTokenStats(); out != nil {
		t.Fatalf("GetTokenStats = %v, want nil (deliberate discard)", out)
	}
}
