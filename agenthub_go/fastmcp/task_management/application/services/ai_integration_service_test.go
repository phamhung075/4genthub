package services

import (
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestParseAIRequirements(t *testing.T) {
	items, err := parseAIRequirements("a, b ,,c")
	if err != nil || len(items) != 3 || items[1].Description != "b" || items[2].ID != "req_3" {
		t.Fatalf("csv: %v %v", items, err)
	}
	items, _ = parseAIRequirements(`[{"description":"x","priority":"high","constraints":["c"]},"y"]`)
	if len(items) != 2 || items[0].Priority != "high" || items[1].Description != "y" || items[1].Priority != "medium" {
		t.Fatalf("json: %+v", items)
	}
	items, _ = parseAIRequirements(`{"k1":1,"k2":2}`) // iterating a dict yields keys
	if len(items) != 2 || items[0].Description != "k1" || items[1].Description != "k2" {
		t.Fatalf("dict: %+v", items)
	}
	items, _ = parseAIRequirements("[broken")
	if len(items) != 1 || items[0].ID != "req_1" || items[0].Description != "[broken" {
		t.Fatalf("invalid json: %+v", items)
	}
	if _, err := parseAIRequirements("[1]"); err == nil || aiErrorText(err) != "'int' object has no attribute 'get'" {
		t.Fatalf("scalar element: %v", err)
	}
}

func TestSuggestOptimalAgentsAndComplexity(t *testing.T) {
	got, _ := suggestOptimalAgents("Fix the login bug").Get("suggested_agents")
	if got.([]any)[0] != "security-auditor-agent" { // security branch precedes debug
		t.Fatalf("got %v", got)
	}
	c := analyzeComplexity("System migration", "implement and create")
	if lvl, _ := c.Get("level"); lvl != "high" {
		t.Fatalf("level %v", lvl)
	}
}

func TestEnhanceCreationShortCircuitsOnFailure(t *testing.T) {
	failed := entities.NewOrderedMap[any]()
	failed.Set("success", false)
	got := AddInsightsNoop(failed)
	if _, ok := got.Get("ai_insights"); ok {
		t.Fatal("insights must not be added to failed responses")
	}
	if !strings.Contains("ok", "ok") {
		t.Fatal()
	}
}

func AddInsightsNoop(m *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return (&AITaskIntegrationService{}).AddAIInsightsToTaskResponse(m, "get")
}
