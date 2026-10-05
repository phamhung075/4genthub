package facades

import (
	"context"
	"testing"
)

func TestAuthExtractTokenFromHeaders(t *testing.T) {
	f := &AuthApplicationFacade{}
	if got := f.ExtractTokenFromHeaders(map[string]string{"authorization": "Bearer abc"}); got == nil || *got != "abc" {
		t.Fatalf("bearer = %v", got)
	}
	if got := f.ExtractTokenFromHeaders(map[string]string{"x-api-token": "xyz"}); got == nil || *got != "xyz" {
		t.Fatalf("x-api-token = %v", got)
	}
	if got := f.ExtractTokenFromHeaders(map[string]string{"authorization": "Basic abc"}); got != nil {
		t.Fatalf("basic should be nil, got %v", *got)
	}
	if got := f.ExtractTokenFromHeaders(map[string]string{}); got != nil {
		t.Fatalf("empty should be nil, got %v", *got)
	}
}

func TestAuthExtractTokenFromCookies(t *testing.T) {
	f := &AuthApplicationFacade{}
	if got := f.ExtractTokenFromCookies(map[string]string{"access_token": "t"}); got == nil || *got != "t" {
		t.Fatalf("cookie = %v", got)
	}
	if got := f.ExtractTokenFromCookies(map[string]string{}); got != nil {
		t.Fatalf("missing cookie should be nil, got %v", *got)
	}
}

func TestDependencyFacadeValidationBranches(t *testing.T) {
	f := &DependencyApplicationFacade{}
	ctx := context.Background()

	got := f.ManageDependencies(ctx, "add_dependency", "", nil)
	if ok, _ := got.Get("success"); ok != false {
		t.Fatalf("empty task id success = %v", ok)
	}
	if msg, _ := got.Get("error"); msg != "Task ID is required for dependency operations" {
		t.Fatalf("empty task id error = %v", msg)
	}

	got = f.ManageDependencies(ctx, "foo", "t1", nil)
	if msg, _ := got.Get("error"); msg != "Unknown dependency action: foo" {
		t.Fatalf("unknown action error = %v", msg)
	}

	got = f.ManageDependencies(ctx, "add_dependency", "t1", nil)
	if msg, _ := got.Get("error"); msg != "dependency_data with dependency_id is required" {
		t.Fatalf("missing dependency data error = %v", msg)
	}
}
