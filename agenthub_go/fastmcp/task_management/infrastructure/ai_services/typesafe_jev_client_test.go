package ai_services

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"agenthub/fastmcp/task_management/domain/services"
)

func TestTypeSafeJevClientMissingAPIKey(t *testing.T) {
	client := &TypeSafeJevClient{
		apiKey:  "",
		baseURL: "http://localhost:1234",
	}

	verdict, _, err := client.EvaluateCriteria(context.Background(), "jev-1.13.0", []string{"test"}, map[string]any{})
	if err != ErrMissingAPIKey {
		t.Fatalf("expected ErrMissingAPIKey, got %v", err)
	}
	if verdict != services.GateVerdictUncertain {
		t.Fatalf("expected verdict uncertain, got %v", verdict)
	}
}

func TestTypeSafeJevClientAccept(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer test-secret-token" {
			w.WriteHeader(http.StatusUnauthorized)
			return
		}
		var req SystemOneRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			return
		}
		if req.Model != "jev-1.13.0" || len(req.Questions) != 1 {
			w.WriteHeader(http.StatusBadRequest)
			return
		}

		resp := SystemOneResponse{
			Verdict: "accept",
			Reasons: "All acceptance criteria verified",
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(resp)
	}))
	defer srv.Close()

	client := NewTypeSafeJevClient(TypeSafeJevClientConfig{
		APIKey:     "test-secret-token",
		BaseURL:    srv.URL,
		HTTPClient: srv.Client(),
	})

	verdict, reasons, err := client.EvaluateCriteria(context.Background(), "jev-1.13.0", []string{"feature works"}, map[string]any{"diff": "ok"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if verdict != services.GateVerdictAccept {
		t.Fatalf("expected verdict accept, got %s", verdict)
	}
	if reasons != "All acceptance criteria verified" {
		t.Fatalf("unexpected reasons: %s", reasons)
	}
}

func TestTypeSafeJevClientReject(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		resp := SystemOneResponse{
			Verdict: "reject",
			Reasons: "Criterion 1 failed validation",
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(resp)
	}))
	defer srv.Close()

	client := NewTypeSafeJevClient(TypeSafeJevClientConfig{
		APIKey:     "dummy-token",
		BaseURL:    srv.URL,
		HTTPClient: srv.Client(),
	})

	verdict, reasons, err := client.EvaluateCriteria(context.Background(), "jev-1.13.0", []string{"feature works"}, map[string]any{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if verdict != services.GateVerdictReject {
		t.Fatalf("expected verdict reject, got %s", verdict)
	}
	if reasons != "Criterion 1 failed validation" {
		t.Fatalf("unexpected reasons: %s", reasons)
	}
}

func TestTypeSafeJevClientResolvesFromEnv(t *testing.T) {
	t.Setenv("TYPESAFE_API_KEY", "env-resolved-key")
	t.Setenv("TYPESAFE_BASE_URL", "https://api.custom.ai/v1/")

	client := NewTypeSafeJevClient(TypeSafeJevClientConfig{})
	if client.apiKey != "env-resolved-key" {
		t.Errorf("expected apiKey 'env-resolved-key', got '%s'", client.apiKey)
	}
	if client.baseURL != "https://api.custom.ai/v1" {
		t.Errorf("expected baseURL 'https://api.custom.ai/v1', got '%s'", client.baseURL)
	}
}

func TestTypeSafeJevClientNoulProbabilities(t *testing.T) {
	var returnedAnswers map[string]SystemOneAnswer
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		resp := SystemOneResponse{
			Model:   "jev-1.13.0",
			Answers: returnedAnswers,
			Usage:   &SystemOneUsage{InputTokens: 250, OutputTokens: 15},
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(resp)
	}))
	defer srv.Close()

	client := NewTypeSafeJevClient(TypeSafeJevClientConfig{
		APIKey:     "test-token",
		BaseURL:    srv.URL,
		HTTPClient: srv.Client(),
	})

	// Case 1: High confidence -> Accept
	returnedAnswers = map[string]SystemOneAnswer{
		"criterion_1": {Type: "noul", Noul: 0.95},
	}
	verdict, _, err := client.EvaluateCriteria(context.Background(), "jev-1.13.0", []string{"feature works"}, map[string]any{})
	if err != nil || verdict != services.GateVerdictAccept {
		t.Fatalf("expected accept for 0.95, got %s (err: %v)", verdict, err)
	}

	// Case 2: Low confidence -> Reject
	returnedAnswers = map[string]SystemOneAnswer{
		"criterion_1": {Type: "noul", Noul: 0.15},
	}
	verdict, _, err = client.EvaluateCriteria(context.Background(), "jev-1.13.0", []string{"feature works"}, map[string]any{})
	if err != nil || verdict != services.GateVerdictReject {
		t.Fatalf("expected reject for 0.15, got %s (err: %v)", verdict, err)
	}

	// Case 3: Marginal confidence -> Uncertain
	returnedAnswers = map[string]SystemOneAnswer{
		"criterion_1": {Type: "noul", Noul: 0.55},
	}
	verdict, _, err = client.EvaluateCriteria(context.Background(), "jev-1.13.0", []string{"feature works"}, map[string]any{})
	if err != nil || verdict != services.GateVerdictUncertain {
		t.Fatalf("expected uncertain for 0.55, got %s (err: %v)", verdict, err)
	}
}


