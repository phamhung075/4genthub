package httpapp

import (
	"context"
	"os"
	"strings"
	"testing"

	authpkg "agenthub/fastmcp/auth"
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/application/factories"
	"agenthub/fastmcp/task_management/application/services"
)

const facadeWiringUserID = "3f0d8f7a-1b2c-4d5e-8f90-1234567890ab"

const facadeWiringJWTSecret = "wiring-test-jwt-secret-32-bytes-min!!"

func TestCreateTokenFacadeRefusesUnsetSecret(t *testing.T) {
	t.Setenv("JWT_SECRET_KEY", "")
	if _, err := (mcpTokenFacadeFactory{}).CreateTokenFacade(); err == nil {
		t.Fatal("CreateTokenFacade with an unset JWT_SECRET_KEY: expected refusal")
	} else if he, ok := err.(*authpkg.HTTPException); !ok {
		t.Fatalf("error type = %T, want *auth.HTTPException", err)
	} else if he.Detail != authpkg.ErrJWTSecretNotSet.Error() || he.StatusCode != 500 {
		t.Fatalf("refusal = %d %q, want 500 %q", he.StatusCode, he.Detail, authpkg.ErrJWTSecretNotSet)
	}
	if got := os.Getenv("JWT_SECRET_KEY"); got != "" {
		t.Fatalf("CreateTokenFacade mutated JWT_SECRET_KEY to %q; unset must stay unset", got)
	}
}

// TestBuildMCPFacadeFactoriesWireTypedFacades proves the four factories
// returned by buildMCPFacadeFactories are accepted by
// services.NewFacadeService (the unexported interface check) and that the MCP
// controllers' type assertions succeed. The ORM constructors do not touch the
// database, so nil sessions is enough.
func TestBuildMCPFacadeFactoriesWireTypedFacades(t *testing.T) {
	t.Setenv("JWT_SECRET_KEY", facadeWiringJWTSecret)
	ctx := context.Background()
	ctxFactory := factories.NewUnifiedContextFacadeFactory(ctx, nil)
	project, branch, agent, unifiedContext, token := buildMCPFacadeFactories(ctx, nil, ctxFactory)

	svc := services.NewFacadeService(nil, nil, project, branch, agent, unifiedContext, token)
	userID := facadeWiringUserID
	projectID := "11111111-1111-1111-1111-111111111111"

	if got, err := svc.GetProjectFacade(&userID); err != nil {
		t.Fatalf("GetProjectFacade: %v", err)
	} else if _, ok := got.(*facades.ProjectApplicationFacade); !ok {
		t.Fatalf("project facade has unexpected type %T", got)
	}

	if got, err := svc.GetBranchFacade(&projectID, &userID); err != nil {
		t.Fatalf("GetBranchFacade: %v", err)
	} else if _, ok := got.(*facades.GitBranchApplicationFacade); !ok {
		t.Fatalf("git branch facade has unexpected type %T", got)
	}

	if got, err := svc.GetAgentFacade(projectID, &userID); err != nil {
		t.Fatalf("GetAgentFacade: %v", err)
	} else if _, ok := got.(*facades.AgentApplicationFacade); !ok {
		t.Fatalf("agent facade has unexpected type %T", got)
	}

	// The context factory is wired; a database-less factory may still fail
	// inside CreateFacade, but it must not report the factory as unconfigured.
	if _, err := svc.GetContextFacade(&userID, &projectID, nil); err != nil && strings.Contains(err.Error(), "is not configured") {
		t.Fatalf("GetContextFacade reported unconfigured factory: %v", err)
	}

	if got, err := svc.GetTokenFacade(); err != nil {
		t.Fatalf("GetTokenFacade: %v", err)
	} else if _, ok := got.(*facades.TokenApplicationFacade); !ok {
		t.Fatalf("token facade has unexpected type %T", got)
	}
}

// TestFacadeServiceNilFactoriesReportUnconfigured is the contrast: with nil
// factories the same getters report the not-configured error, so the positive
// test above is not vacuous.
func TestFacadeServiceNilFactoriesReportUnconfigured(t *testing.T) {
	svc := services.NewFacadeService(nil, nil, nil, nil, nil, nil, nil)
	userID := facadeWiringUserID
	projectID := "11111111-1111-1111-1111-111111111111"

	cases := []struct {
		name string
		err  error
	}{
		{"project", getProjectFacadeErr(svc, &userID)},
		{"branch", getBranchFacadeErr(svc, &projectID, &userID)},
		{"agent", getAgentFacadeErr(svc, projectID, &userID)},
		{"context", getContextFacadeErr(svc, &userID, &projectID)},
		{"token", getTokenFacadeErr(svc)},
	}
	for _, c := range cases {
		if c.err == nil || !strings.Contains(c.err.Error(), "is not configured") {
			t.Fatalf("%s facade with nil factory: err = %v", c.name, c.err)
		}
	}
}

func getProjectFacadeErr(svc *services.FacadeService, userID *string) error {
	_, err := svc.GetProjectFacade(userID)
	return err
}

func getBranchFacadeErr(svc *services.FacadeService, projectID, userID *string) error {
	_, err := svc.GetBranchFacade(projectID, userID)
	return err
}

func getAgentFacadeErr(svc *services.FacadeService, projectID string, userID *string) error {
	_, err := svc.GetAgentFacade(projectID, userID)
	return err
}

func getContextFacadeErr(svc *services.FacadeService, userID, projectID *string) error {
	_, err := svc.GetContextFacade(userID, projectID, nil)
	return err
}

func getTokenFacadeErr(svc *services.FacadeService) error {
	_, err := svc.GetTokenFacade()
	return err
}
