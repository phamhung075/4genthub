package interfacelayer

// Regression for the reason that reached no caller. The five AI actions answer
// through the interface formatter, which writes the reason into a nested error
// map ({message, code, operation, timestamp}); the controller's final
// standardisation pass read `error` as a plain string, failed the type
// assertion, and fell back to "Unknown error occurred" — so a caller was told
// the operation failed without being told why.

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/factories"
	"agenthub/fastmcp/task_management/interface/utils"
)

const aiSeamRefusal = "AI integration is not available: the AITaskIntegrationService seam is not wired in this build"

// errorMessageOf reads the reason out of either shape the pipeline can emit: the
// nested formatter map or a flat string.
func errorMessageOf(response *entities.OrderedMap[any]) string {
	if response == nil {
		return ""
	}
	v, ok := response.Get("error")
	if !ok {
		return ""
	}
	switch typed := v.(type) {
	case string:
		return typed
	case *entities.OrderedMap[any]:
		if s, ok := typed.Get("message"); ok {
			out, _ := s.(string)
			return out
		}
	}
	return ""
}

func TestStandardizeFacadeResponseKeepsFormatterErrorMessage(t *testing.T) {
	formatter := utils.NewMCPResponseFormatter()
	rf := factories.NewResponseFactory(taskResponseFormatter{formatter})

	// The handler layer's refusal, exactly as the AI handler builds it.
	raw := formatter.CreateErrorResponse("ai_plan", aiSeamRefusal, factories.ErrorCodeOperationFailed, nil)

	standardized := rf.StandardizeFacadeResponse(raw, "ai_plan")

	if got := errorMessageOf(standardized); got != aiSeamRefusal {
		t.Fatalf("error message = %q, want %q\nstandardized keys: %v", got, aiSeamRefusal, standardized.Keys())
	}
	if v, _ := standardized.Get("success"); v != false {
		t.Fatalf("success = %v, want false", v)
	}
}

// TestFiveAIActionsDispatchTheRefusal is the dispatched-path contract: with the
// seam unwired, each of the five actions answers a failure whose reason names
// the unwired seam, and no panic escapes the operation factory.
func TestFiveAIActionsDispatchTheRefusal(t *testing.T) {
	formatter := utils.NewMCPResponseFormatter()
	rf := factories.NewResponseFactory(taskResponseFormatter{formatter})
	factory := factories.NewOperationFactory(taskResponseFormatter{formatter}, nil)

	cases := []struct {
		operation string
		kwargs    map[string]any
	}{
		{"ai_plan", map[string]any{"requirements": "r", "title": "t", "git_branch_id": "b"}},
		{"ai_create", map[string]any{"title": "t", "git_branch_id": "b"}},
		{"ai_enhance", map[string]any{"task_id": "task-1"}},
		{"ai_analyze", map[string]any{"requirements": "r"}},
		{"ai_suggest_agents", map[string]any{"requirements": "r"}},
	}

	for _, tc := range cases {
		t.Run(tc.operation, func(t *testing.T) {
			raw := factory.HandleOperation(context.Background(), tc.operation, nil, tc.kwargs)
			if raw == nil {
				t.Fatal("HandleOperation returned nil")
			}
			standardized := rf.StandardizeFacadeResponse(raw, tc.operation)
			if v, _ := standardized.Get("success"); v != false {
				t.Fatalf("success = %v, want false", v)
			}
			if got := errorMessageOf(standardized); got != aiSeamRefusal {
				t.Fatalf("error message = %q, want %q", got, aiSeamRefusal)
			}
		})
	}
}
