package httpapp

// The MCP submission path of the friction channel, and the evidence that it is the SAME writer as
// the HTTP path: both callings in one test, over one store, and the two stored rows compared field
// by field.

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	seatservices "agenthub/fastmcp/seat_management/application/services"
	"agenthub/fastmcp/seat_management/domain/feedback"
	"agenthub/fastmcp/seat_management/domain/repositories"
	seatcontrollers "agenthub/fastmcp/seat_management/interface/mcp_controllers"
	taskservices "agenthub/fastmcp/task_management/application/services"
	interfacelayer "agenthub/fastmcp/task_management/interface"
)

// feedbackTestAuth resolves the same tenant the route tests use, so a row written by the tool and
// a row written by the route can be compared field by field.
type feedbackTestAuth struct{}

func (feedbackTestAuth) GetAuthenticatedUserID(context.Context, *string, string) (string, error) {
	return tokenTestUserA, nil
}

func newSubmitFeedbackTestApp(t *testing.T, service *seatservices.SeatFeedbackService) *App {
	t.Helper()
	controller := seatcontrollers.NewSubmitFeedbackController(feedbackTestAuth{}, service)
	tools, err := interfacelayer.NewDDDCompliantMCPTools(interfacelayer.Dependencies{
		FacadeService:     taskservices.NewFacadeService(nil, nil, nil, nil, nil, nil, nil),
		DatabaseAvailable: true,
		SubmitFeedback:    controller,
	}, nil)
	if err != nil {
		t.Fatalf("NewDDDCompliantMCPTools: %v", err)
	}
	return &App{mcpTools: tools}
}

// toolText is the text of the first content entry of an MCP tool result: the JSON the seat reads.
// It stays a string for assertions about the wire, and toolJSON parses it for field assertions -
// the tool result is pretty-printed, so substring checks on it would be a trap.
func toolText(t *testing.T, rec *httptest.ResponseRecorder) string {
	t.Helper()
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d: %s", rec.Code, rec.Body.String())
	}
	var wire struct {
		Result struct {
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
		} `json:"result"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil {
		t.Fatalf("decode tool result %s: %v", rec.Body.String(), err)
	}
	if len(wire.Result.Content) == 0 {
		t.Fatalf("tool result carries no content: %s", rec.Body.String())
	}
	return wire.Result.Content[0].Text
}

// toolJSON is the answer a seat parses out of the tool result.
func toolJSON(t *testing.T, rec *httptest.ResponseRecorder) map[string]any {
	t.Helper()
	text := toolText(t, rec)
	var answer map[string]any
	if err := json.Unmarshal([]byte(text), &answer); err != nil {
		t.Fatalf("decode tool answer %s: %v", text, err)
	}
	return answer
}

// assertSameRowShape compares two stored rows for everything that describes the submission. The id
// and the text identify it, and created_at is the instant of the call — the route stamps its own
// clock seam while the tool and the script use the wall clock — so those three are compared for
// presence rather than equality.
func assertSameRowShape(t *testing.T, a, b repositories.SeatFeedback) {
	t.Helper()
	if a.ID == b.ID {
		t.Fatalf("both paths produced id %q; the ids must be the store's", a.ID)
	}
	if a.CreatedAt.IsZero() || b.CreatedAt.IsZero() {
		t.Fatalf("a stored row has no created_at: %+v / %+v", a, b)
	}
	a.ID, b.ID = "", ""
	a.Text, b.Text = "", ""
	a.CreatedAt, b.CreatedAt = time.Time{}, time.Time{}
	if a != b {
		t.Fatalf("the two rows differ beyond id, text and the instant:\n a = %+v\n b = %+v", a, b)
	}
}

func findReport(t *testing.T, store *fakeSeatFeedback, text string) repositories.SeatFeedback {
	t.Helper()
	for _, report := range store.reports {
		if report.Text == text {
			return report
		}
	}
	t.Fatalf("no stored report with text %q: %+v", text, store.reports)
	return repositories.SeatFeedback{}
}

func TestMCPToolsListPublishesSubmitFeedback(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	app := newSubmitFeedbackTestApp(t, seatservices.NewSeatFeedbackService(&fakeSeatFeedback{}))
	rec := postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"tools/list"}`, "")

	var wire struct {
		Result struct {
			Tools []struct {
				Name        string `json:"name"`
				Description string `json:"description"`
				InputSchema struct {
					Type       string                    `json:"type"`
					Required   []string                  `json:"required"`
					Properties map[string]map[string]any `json:"properties"`
				} `json:"inputSchema"`
			} `json:"tools"`
		} `json:"result"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil {
		t.Fatalf("decode tools/list: %v", err)
	}
	for _, tool := range wire.Result.Tools {
		if tool.Name != seatcontrollers.SubmitFeedbackToolName {
			continue
		}
		if tool.Description != seatcontrollers.SubmitFeedbackToolDescription {
			t.Errorf("description = %q", tool.Description)
		}
		schema := tool.InputSchema
		if schema.Type != "object" || len(schema.Required) != 4 {
			t.Fatalf("schema = %+v", schema)
		}
		for _, name := range []string{"room", "seat", "layer", "text"} {
			if schema.Properties[name]["type"] != "string" {
				t.Errorf("property %s = %v", name, schema.Properties[name])
			}
		}
		// The advertised vocabulary is the domain's, so the tool cannot offer a layer the writer
		// refuses.
		values, ok := schema.Properties["layer"]["enum"].([]any)
		if !ok || len(values) != len(feedback.Layers) {
			t.Fatalf("layer enum = %v, want the %d domain layers", schema.Properties["layer"]["enum"], len(feedback.Layers))
		}
		for i, layer := range feedback.Layers {
			if values[i] != string(layer) {
				t.Errorf("layer enum[%d] = %v, want %q", i, values[i], layer)
			}
		}
		return
	}
	t.Fatalf("tools/list does not publish submit_feedback: %s", rec.Body.String())
}

// TestMCPSubmitFeedbackAndTheRouteAreOneWriter is the deliverable-2 evidence: the MCP tool and the
// HTTP route write through the same service, and the stored rows are identical in shape.
func TestMCPSubmitFeedbackAndTheRouteAreOneWriter(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	store := &fakeSeatFeedback{}
	service := seatservices.NewSeatFeedbackService(store)

	f := newFeedbackFixtureWithStore(t, store)
	app := newSubmitFeedbackTestApp(t, service)

	// Path one: the MCP tool.
	rec := postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"submit_feedback",`+
		`"arguments":{"room":"4genthub-min","seat":"go-dev","session":"4genthub-min-go-dev@4genthub-min","layer":"runtime","text":"the tool path"}}}`, "")
	toolAnswer := toolJSON(t, rec)
	if toolAnswer["success"] != true || toolAnswer["layer"] != "runtime" {
		t.Fatalf("tool answer = %v, want success and the stored layer", toolAnswer)
	}

	// Path two: the route.
	if routeRec := f.submit("user-jwt", `{"room":"4genthub-min","seat":"go-dev","session":"4genthub-min-go-dev@4genthub-min","layer":"runtime","text":"the route path"}`); routeRec.Code != http.StatusOK {
		t.Fatalf("route submit: %d %s", routeRec.Code, routeRec.Body.String())
	}

	toolRow := findReport(t, store, "the tool path")
	routeRow := findReport(t, store, "the route path")
	// The tool answer carries the id the store assigned.
	if toolAnswer["id"] != toolRow.ID {
		t.Fatalf("tool answer %v does not carry the stored id %q", toolAnswer, toolRow.ID)
	}
	assertSameRowShape(t, toolRow, routeRow)

	// And the read side renders both through the same grouping.
	body := readFeedback(t, f.do(http.MethodGet, "/api/v2/openrig/feedback", "user-jwt", ""))
	if body.Total != 2 || len(body.Layers) != 1 || body.Layers[0].Count != 2 {
		t.Fatalf("read = %+v, want one runtime group holding both rows", body)
	}
}

func TestMCPSubmitFeedbackRefusesAnUnknownLayer(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	store := &fakeSeatFeedback{}
	app := newSubmitFeedbackTestApp(t, seatservices.NewSeatFeedbackService(store))

	rec := postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"submit_feedback",`+
		`"arguments":{"room":"r","seat":"s","layer":"harness","text":"t"}}}`, "")
	answer := toolJSON(t, rec)
	if answer["success"] != false {
		t.Fatalf("answer = %v, want a refusal", answer)
	}
	message, _ := answer["error"].(string)
	if !strings.Contains(message, "is not one of runtime, openrig, cloud, seat-context, workspace, other") {
		t.Fatalf("refusal = %q, want the vocabulary named", message)
	}
	if len(store.reports) != 0 {
		t.Fatalf("a refused tool call stored a row: %+v", store.reports)
	}
}
