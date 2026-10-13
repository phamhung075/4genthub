package ai_services

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/utilities"
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

// SystemOneRequest is the payload sent to TypeSafe AI System One.
type SystemOneRequest struct {
	Model     string         `json:"model"`
	Questions []string       `json:"questions"`
	State     map[string]any `json:"state"`
}

// SystemOneResponse represents the expected response structure from TypeSafe AI.
type SystemOneResponse struct {
	Verdict         string   `json:"verdict"`
	Reasons         string   `json:"reasons"`
	Accepted        *bool    `json:"accepted,omitempty"`
	CriteriaResults []string `json:"criteria_results,omitempty"`
}

// EvaluateCriteria sends criteria and evidence to the TypeSafe AI System One API.
func (c *TypeSafeJevClient) EvaluateCriteria(ctx context.Context, model string, criteria []string, evidence map[string]any) (services.GateVerdict, string, error) {
	if c.apiKey == "" {
		return services.GateVerdictUncertain, "API key not configured", ErrMissingAPIKey
	}

	endpoint := fmt.Sprintf("%s/systemone", c.baseURL)
	payload := SystemOneRequest{
		Model:     model,
		Questions: criteria,
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

	verdictStr := strings.ToLower(parsed.Verdict)
	switch verdictStr {
	case string(services.GateVerdictAccept):
		return services.GateVerdictAccept, parsed.Reasons, nil
	case string(services.GateVerdictReject):
		return services.GateVerdictReject, parsed.Reasons, nil
	case string(services.GateVerdictUncertain):
		return services.GateVerdictUncertain, parsed.Reasons, nil
	default:
		// Fallback check on boolean Accepted field if verdict string is omitted
		if parsed.Accepted != nil {
			if *parsed.Accepted {
				return services.GateVerdictAccept, parsed.Reasons, nil
			}
			return services.GateVerdictReject, parsed.Reasons, nil
		}
		return services.GateVerdictUncertain, fmt.Sprintf("unrecognized verdict from Jev: %s", parsed.Verdict), nil
	}
}
