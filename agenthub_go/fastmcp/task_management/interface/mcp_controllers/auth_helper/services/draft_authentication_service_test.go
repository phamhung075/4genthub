package services

import (
	"context"
	"errors"
	"testing"

	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/exceptions"
)

func TestDraftAuthenticationProvidedUserID(t *testing.T) {
	svc := NewAuthenticationService()
	provided := "123e4567-e89b-12d3-a456-426614174000"
	got, err := svc.GetAuthenticatedUserID(context.Background(), &provided, "Operation")
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	if got != provided {
		t.Fatalf("got = %q", got)
	}
}

func TestDraftAuthenticationTestingBypass(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	t.Setenv("MCP_AUTH_MODE", "production")
	testUserID := "test-user-001"
	t.Setenv("TEST_USER_ID", testUserID)

	svc := NewAuthenticationService()
	got, err := svc.GetAuthenticatedUserID(context.Background(), nil, "Operation")
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	want, _ := domain.ValidateUserID(&testUserID, "Operation")
	if got != want {
		t.Fatalf("got = %q, want = %q", got, want)
	}
}

func TestDraftAuthenticationRequiredError(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "true")
	t.Setenv("MCP_AUTH_MODE", "production")

	svc := NewAuthenticationService()
	_, err := svc.GetAuthenticatedUserID(context.Background(), nil, "manage_task")
	if err == nil {
		t.Fatal("expected error")
	}
	var required *exceptions.UserAuthenticationRequiredError
	if !errors.As(err, &required) {
		t.Fatalf("err type = %T", err)
	}
	want := "manage_task requires valid JWT authentication. " +
		"Please ensure you are authenticated and the JWT token is properly configured."
	if required.Error() != want {
		t.Fatalf("message = %q", required.Error())
	}
}
