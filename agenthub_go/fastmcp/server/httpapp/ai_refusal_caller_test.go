package httpapp

// The caller-visible half of the AI refusal. The five task-management AI actions
// refuse legibly at the handler layer, but the reason was replaced with the
// generic "Unknown error occurred" by the controller's standardisation pass —
// so over the wire the caller received a failure with no reason. This drives the
// real POST /mcp route and pins the payload the caller actually gets.

import (
	"encoding/json"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/application/services"
	interfacelayer "agenthub/fastmcp/task_management/interface"
)

// stubTaskFacadeFactory answers GetTaskFacade without a database. The ai_plan
// path never reaches the repository: the refusal fires before any task is read.
type stubTaskFacadeFactory struct{}

func (stubTaskFacadeFactory) CreateTaskFacade(projectID, gitBranchID, userID *string) (any, error) {
	return facades.NewTaskApplicationFacade(nil, nil, facades.TaskFacadeDeps{}), nil
}

func TestMCPManageTaskAIPlanRefusalReachesCaller(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	fs := services.NewFacadeService(stubTaskFacadeFactory{}, nil, nil, nil, nil, nil)
	tools, err := interfacelayer.NewDDDCompliantMCPTools(interfacelayer.Dependencies{
		FacadeService:     fs,
		DatabaseAvailable: true,
	}, nil)
	if err != nil {
		t.Fatalf("NewDDDCompliantMCPTools: %v", err)
	}
	app := &App{mcpTools: tools}

	payload := `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"manage_task","arguments":{"action":"ai_plan","requirements":"r","title":"t","git_branch_id":"b"}}}`
	rec := postMCP(t, app, payload, "")
	if rec.Code != 200 {
		t.Fatalf("status = %d, want 200; body = %s", rec.Code, rec.Body.String())
	}

	var wire struct {
		Result struct {
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
		} `json:"result"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil {
		t.Fatalf("decode response: %v; body = %s", err, rec.Body.String())
	}
	if len(wire.Result.Content) == 0 {
		t.Fatalf("empty content; body = %s", rec.Body.String())
	}

	const sentence = "AI integration is not available: the AITaskIntegrationService seam is not wired in this build"
	text := wire.Result.Content[0].Text
	if !strings.Contains(text, sentence) {
		t.Fatalf("caller payload does not name the unwired seam:\n%s", text)
	}
	if strings.Contains(text, "Unknown error occurred") {
		t.Fatalf("caller payload still carries the generic message:\n%s", text)
	}
}
