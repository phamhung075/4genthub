package routes

import (
	"testing"

	"agenthub/fastmcp/auth"
	"agenthub/fastmcp/task_management/domain/entities"
)

func TestCalculateAgentEfficiencyMatchesPython(t *testing.T) {
	cases := []struct {
		rate, hours, blocked, want float64
	}{
		{100, 0, 0, 100},
		{50, 24, 0.1, 60},
		{0, 48, 1.0, 10},
	}
	for _, c := range cases {
		if got := calculateAgentEfficiency(c.rate, c.hours, c.blocked); got != c.want {
			t.Errorf("calculateAgentEfficiency(%v,%v,%v)=%v want %v", c.rate, c.hours, c.blocked, got, c.want)
		}
	}
}

func TestCalculateTrendMatchesPython(t *testing.T) {
	cases := []struct {
		values []float64
		want   string
	}{
		{[]float64{1, 2, 3, 4}, "declining"},
		{[]float64{10, 9, 1, 2}, "improving"},
		{[]float64{1, 1, 1, 1}, "stable"},
		{[]float64{1}, "insufficient_data"},
	}
	for _, c := range cases {
		if got := calculateTrend(c.values); got != c.want {
			t.Errorf("calculateTrend(%v)=%q want %q", c.values, got, c.want)
		}
	}
}

func TestGenerateSpecializationRecommendationsMatchesPython(t *testing.T) {
	empty := generateSpecializationRecommendations(nil)
	if len(empty) != 1 || empty[0] != "No agent data available for recommendations" {
		t.Fatalf("empty case = %v", empty)
	}
	metrics := []map[string]any{
		{"agent_name": "alpha", "efficiency_score": 80.0, "completion_rate": 60.0, "total_tasks": 5},
	}
	recs := generateSpecializationRecommendations(metrics)
	if len(recs) != 2 {
		t.Fatalf("recs = %v", recs)
	}
	if recs[0] != "Consider having alpha mentor other agents" {
		t.Errorf("recs[0] = %q", recs[0])
	}
	if recs[1] != "Consider specializing agents for specific task types to improve efficiency" {
		t.Errorf("recs[1] = %q", recs[1])
	}
}

func TestDefaultAlertRulesAndRuleDictOrder(t *testing.T) {
	rules := ListAlertRules()
	if total, _ := rules.Get("total_rules"); total != 4 {
		t.Fatalf("total_rules = %v", total)
	}
	if enabled, _ := rules.Get("enabled_rules"); enabled != 4 {
		t.Fatalf("enabled_rules = %v", enabled)
	}
	rule := &AlertRule{ID: "x", Name: "n", Metric: "m", Condition: "equals", Threshold: 1.5, Enabled: true, CooldownMinutes: 30, Severity: "warning"}
	want := []string{"id", "name", "metric", "condition", "threshold", "enabled", "webhook_url", "cooldown_minutes", "severity", "description"}
	got := alertRuleDict(rule).Keys()
	if len(got) != len(want) {
		t.Fatalf("keys = %v", got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Errorf("key[%d]=%q want %q", i, got[i], want[i])
		}
	}
}

func TestCreateAlertRuleValidationMatchesPython(t *testing.T) {
	incomplete := entities.NewOrderedMap[any]()
	incomplete.Set("metric", "m")
	_, err := CreateAlertRule(incomplete)
	he, ok := err.(*auth.HTTPException)
	if !ok || he.StatusCode != 400 || he.Detail != "Missing required field: name" {
		t.Fatalf("missing field err = %v", err)
	}

	bad := entities.NewOrderedMap[any]()
	bad.Set("name", "n")
	bad.Set("metric", "m")
	bad.Set("condition", "bogus")
	bad.Set("threshold", 1.0)
	_, err = CreateAlertRule(bad)
	he, ok = err.(*auth.HTTPException)
	if !ok || he.StatusCode != 400 {
		t.Fatalf("invalid condition err = %v", err)
	}
	if he.Detail != "Invalid condition. Must be one of: ['greater_than', 'less_than', 'equals']" {
		t.Fatalf("invalid condition detail = %q", he.Detail)
	}
}

func TestAcknowledgeAlertOutOfRange(t *testing.T) {
	_, err := AcknowledgeAlert(9999)
	he, ok := err.(*auth.HTTPException)
	if !ok || he.StatusCode != 404 || he.Detail != "Alert event not found" {
		t.Fatalf("err = %v", err)
	}
}
