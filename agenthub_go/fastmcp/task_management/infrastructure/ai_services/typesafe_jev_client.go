package ai_services

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/utilities"
	roomservices "agenthub/fastmcp/room_decisions/application/services"
	roomquestions "agenthub/fastmcp/room_decisions/domain/questions"
)

// ErrMissingAPIKey indicates no TypeSafe / Jev API key was provided.
var ErrMissingAPIKey = errors.New("typesafe/jev api key not configured (set TYPESAFE_API_KEY or JEV_API_KEY in ~/.config/4genthub/.env or environment)")

// TypeSafeJevClientConfig holds configuration for the TypeSafe AI System One client.
type TypeSafeJevClientConfig struct {
	APIKey     string
	BaseURL    string
	HTTPClient *http.Client
}

// TypeSafeJevClient calls the TypeSafe AI System One API to evaluate criteria.
type TypeSafeJevClient struct {
	apiKey     string
	baseURL    string
	httpClient *http.Client
}

// NewTypeSafeJevClient initializes a TypeSafeJevClient using provided config, environment variables, or ~/.config/4genthub/.env.
func NewTypeSafeJevClient(cfg TypeSafeJevClientConfig) *TypeSafeJevClient {
	apiKey := cfg.APIKey
	if apiKey == "" {
		apiKey = utilities.ResolveConfigVar("TYPESAFE_API_KEY", "JEV_API_KEY", "JEV_TOKEN")
	}

	baseURL := strings.TrimRight(cfg.BaseURL, "/")
	if baseURL == "" {
		if v := utilities.ResolveConfigVar("TYPESAFE_BASE_URL"); v != "" {
			baseURL = strings.TrimRight(v, "/")
		} else {
			baseURL = "https://api.typesafe.ai/v1"
		}
	}

	client := cfg.HTTPClient
	if client == nil {
		client = &http.Client{Timeout: 30 * time.Second}
	}

	return &TypeSafeJevClient{
		apiKey:     apiKey,
		baseURL:    baseURL,
		httpClient: client,
	}
}

// NoulQuestion represents a System One question evaluated for yes/true probability.
type NoulQuestion struct {
	Type         string `json:"type"`
	Instructions string `json:"instructions"`
}

// ChoiceQuestion represents a System One question that selects from a set of choices.
type ChoiceQuestion struct {
	Type         string            `json:"type"`
	Instructions string            `json:"instructions"`
	Criteria     map[string]string `json:"criteria"`
}

// SystemOneRequest is the payload sent to TypeSafe AI System One.
type SystemOneRequest struct {
	Model     string         `json:"model"`
	Questions map[string]any `json:"questions"`
	State     any            `json:"state"`
}

// SystemOneAnswer is one criterion answer returned by TypeSafe AI.
type SystemOneAnswer struct {
	Type          string             `json:"type"`
	Noul          *float64           `json:"noul,omitempty"`
	Choice        *string            `json:"choice,omitempty"`
	Confidence    *float64           `json:"confidence,omitempty"`
	Probabilities map[string]float64 `json:"probabilities,omitempty"`
}

// SystemOneUsage tracks tokens reported by TypeSafe AI.
type SystemOneUsage struct {
	InputTokens  int `json:"input_tokens"`
	OutputTokens int `json:"output_tokens"`
}

// SystemOneResponse represents the response structure from TypeSafe AI.
type SystemOneResponse struct {
	Model    string                     `json:"model"`
	Answers  map[string]SystemOneAnswer `json:"answers,omitempty"`
	Usage    *SystemOneUsage            `json:"usage,omitempty"`
	Verdict  string                     `json:"verdict,omitempty"`
	Reasons  string                     `json:"reasons,omitempty"`
	Accepted *bool                      `json:"accepted,omitempty"`
}

// EvaluateCriteria sends criteria and evidence to the TypeSafe AI System One API.
func (c *TypeSafeJevClient) EvaluateCriteria(ctx context.Context, model string, criteria []string, evidence map[string]any) (services.GateVerdict, string, error) {
	if c.apiKey == "" {
		return services.GateVerdictUncertain, "API key not configured", ErrMissingAPIKey
	}

	endpoint := fmt.Sprintf("%s/systemone", c.baseURL)
	questionsMap := make(map[string]any, len(criteria))
	for i, cr := range criteria {
		qKey := fmt.Sprintf("criterion_%d", i+1)
		questionsMap[qKey] = NoulQuestion{
			Type:         "noul",
			Instructions: cr,
		}
	}

	payload := SystemOneRequest{
		Model:     model,
		Questions: questionsMap,
		State:     evidence,
	}

	bodyBytes, err := json.Marshal(payload)
	if err != nil {
		return services.GateVerdictUncertain, fmt.Sprintf("failed to marshal request: %v", err), err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(bodyBytes))
	if err != nil {
		return services.GateVerdictUncertain, fmt.Sprintf("failed to create request: %v", err), err
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.apiKey))

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return services.GateVerdictUncertain, fmt.Sprintf("http request failed: %v", err), err
	}
	defer resp.Body.Close()

	respBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return services.GateVerdictUncertain, fmt.Sprintf("failed to read response: %v", err), err
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return services.GateVerdictUncertain, fmt.Sprintf("typesafe api returned HTTP %d: %s", resp.StatusCode, string(respBytes)), fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var parsed SystemOneResponse
	if err := json.Unmarshal(respBytes, &parsed); err != nil {
		return services.GateVerdictUncertain, fmt.Sprintf("failed to parse response JSON: %v", err), err
	}

	// Evaluate Noul probability answers if present
	if len(parsed.Answers) > 0 {
		allHigh := true
		anyLow := false
		var reasonParts []string
		for k, ans := range parsed.Answers {
			val := 0.0
			if ans.Noul != nil {
				val = *ans.Noul
			}
			reasonParts = append(reasonParts, fmt.Sprintf("%s: %.2f", k, val))
			if val < 0.8 {
				allHigh = false
			}
			if val <= 0.3 {
				anyLow = true
			}
		}
		sort.Strings(reasonParts)
		reasons := strings.Join(reasonParts, "; ")
		if anyLow {
			return services.GateVerdictReject, fmt.Sprintf("criteria rejected (%s)", reasons), nil
		}
		if allHigh {
			return services.GateVerdictAccept, fmt.Sprintf("criteria verified (%s)", reasons), nil
		}
		return services.GateVerdictUncertain, fmt.Sprintf("marginal criteria confidence (%s)", reasons), nil
	}

	// Fallback evaluation for direct verdict strings
	verdictStr := strings.ToLower(parsed.Verdict)
	switch verdictStr {
	case string(services.GateVerdictAccept):
		return services.GateVerdictAccept, parsed.Reasons, nil
	case string(services.GateVerdictReject):
		return services.GateVerdictReject, parsed.Reasons, nil
	case string(services.GateVerdictUncertain):
		return services.GateVerdictUncertain, parsed.Reasons, nil
	default:
		if parsed.Accepted != nil {
			if *parsed.Accepted {
				return services.GateVerdictAccept, parsed.Reasons, nil
			}
			return services.GateVerdictReject, parsed.Reasons, nil
		}
		return services.GateVerdictUncertain, fmt.Sprintf("unrecognized verdict from Jev: %s", parsed.Verdict), nil
	}
}

// SelectDecisionChoices evaluates questions using TypeSafe System One choice questions.
func (c *TypeSafeJevClient) SelectDecisionChoices(
	ctx context.Context,
	model string,
	summary, detail string,
	qs []roomquestions.HumanQuestion,
) (map[string]roomservices.DecisionChoiceSelection, error) {
	if c.apiKey == "" {
		return nil, ErrMissingAPIKey
	}
	if len(qs) == 0 {
		return make(map[string]roomservices.DecisionChoiceSelection), nil
	}

	endpoint := fmt.Sprintf("%s/systemone", c.baseURL)
	questionsMap := make(map[string]any, len(qs))

	for _, q := range qs {
		criteria := make(map[string]string, len(q.Options))
		for _, opt := range q.Options {
			criteria[opt.ID] = opt.Label
		}
		questionsMap[q.ID] = ChoiceQuestion{
			Type:         "choice",
			Instructions: q.Question,
			Criteria:     criteria,
		}
	}

	state := map[string]string{
		"summary": summary,
		"detail":  detail,
	}

	payload := SystemOneRequest{
		Model:     model,
		Questions: questionsMap,
		State:     state,
	}

	bodyBytes, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(bodyBytes))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.apiKey))

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http request failed: %w", err)
	}
	defer resp.Body.Close()

	respBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("typesafe api returned HTTP %d: %s", resp.StatusCode, string(respBytes))
	}

	var parsed SystemOneResponse
	if err := json.Unmarshal(respBytes, &parsed); err != nil {
		return nil, fmt.Errorf("failed to parse response JSON: %w", err)
	}

	selections := make(map[string]roomservices.DecisionChoiceSelection, len(parsed.Answers))
	for qID, ans := range parsed.Answers {
		if ans.Choice == nil {
			continue
		}
		conf := 0.0
		if ans.Confidence != nil {
			conf = *ans.Confidence
		}
		selections[qID] = roomservices.DecisionChoiceSelection{
			SelectedOptionID: *ans.Choice,
			Confidence:       conf,
		}
	}

	return selections, nil
}
