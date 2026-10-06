// alert_system_routes.go ports server/routes/alert_system_routes.py.
//
// The FastAPI APIRouter/Depends/BackgroundTasks plumbing has no Go meaning; the
// dataclasses, module-level in-memory state, handlers, background alert checking
// helpers and response key order are preserved. httpx is replaced by net/http
// (standard library, no new module). Logging calls are dropped.
package routes

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sort"
	"strings"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// AlertRule mirrors the AlertRule dataclass.
type AlertRule struct {
	ID              string
	Name            string
	Metric          string
	Condition       string
	Threshold       float64
	Enabled         bool
	WebhookURL      *string
	CooldownMinutes int
	Severity        string
	Description     string
}

// AlertEvent mirrors the AlertEvent dataclass.
type AlertEvent struct {
	RuleID       string
	RuleName     string
	Metric       string
	CurrentValue float64
	Threshold    float64
	Severity     string
	Message      string
	Timestamp    time.Time
	Acknowledged bool
	WebhookSent  bool
}

var (
	alertRules  = entities.NewOrderedMap[*AlertRule]()
	alertEvents []*AlertEvent
)

func alertRuleDict(r *AlertRule) *entities.OrderedMap[any] {
	d := entities.NewOrderedMap[any]()
	d.Set("id", r.ID)
	d.Set("name", r.Name)
	d.Set("metric", r.Metric)
	d.Set("condition", r.Condition)
	d.Set("threshold", r.Threshold)
	d.Set("enabled", r.Enabled)
	if r.WebhookURL == nil {
		d.Set("webhook_url", nil)
	} else {
		d.Set("webhook_url", *r.WebhookURL)
	}
	d.Set("cooldown_minutes", r.CooldownMinutes)
	d.Set("severity", r.Severity)
	d.Set("description", r.Description)
	return d
}

func alertEventDict(e *AlertEvent) *entities.OrderedMap[any] {
	d := entities.NewOrderedMap[any]()
	d.Set("rule_id", e.RuleID)
	d.Set("rule_name", e.RuleName)
	d.Set("metric", e.Metric)
	d.Set("current_value", e.CurrentValue)
	d.Set("threshold", e.Threshold)
	d.Set("severity", e.Severity)
	d.Set("message", e.Message)
	d.Set("timestamp", tmvo.IsoFormat(e.Timestamp))
	d.Set("acknowledged", e.Acknowledged)
	d.Set("webhook_sent", e.WebhookSent)
	return d
}

// ListAlertRules mirrors GET /rules.
func ListAlertRules() *entities.OrderedMap[any] {
	rules := make([]any, 0, alertRules.Len())
	enabled := 0
	for _, r := range alertRules.Values() {
		rules = append(rules, alertRuleDict(r))
		if r.Enabled {
			enabled++
		}
	}
	out := entities.NewOrderedMap[any]()
	out.Set("rules", rules)
	out.Set("total_rules", alertRules.Len())
	out.Set("enabled_rules", enabled)
	return out
}

func alertGet(m *entities.OrderedMap[any], key string) (any, bool) {
	if m == nil {
		return nil, false
	}
	return m.Get(key)
}

func alertStr(v any) (string, bool) {
	s, ok := v.(string)
	return s, ok
}

func alertFloat(v any) (float64, bool) {
	switch n := v.(type) {
	case float64:
		return n, true
	case float32:
		return float64(n), true
	case int:
		return float64(n), true
	case int64:
		return float64(n), true
	}
	return 0, false
}

func alertBool(v any) (bool, bool) {
	b, ok := v.(bool)
	return b, ok
}

func alertInt(v any) (int, bool) {
	switch n := v.(type) {
	case int:
		return n, true
	case int64:
		return int(n), true
	case float64:
		return int(n), true
	}
	return 0, false
}

// CreateAlertRule mirrors POST /rules.
func CreateAlertRule(ruleData *entities.OrderedMap[any]) (*entities.OrderedMap[any], error) {
	for _, field := range []string{"name", "metric", "condition", "threshold"} {
		if !ruleData.Has(field) {
			return nil, routesHTTPErr(400, fmt.Sprintf("Missing required field: %s", field))
		}
	}
	name, _ := alertStr(mustGet(ruleData, "name"))
	metric, _ := alertStr(mustGet(ruleData, "metric"))
	condition, _ := alertStr(mustGet(ruleData, "condition"))
	threshold, ok := alertFloat(mustGet(ruleData, "threshold"))
	if !ok {
		return nil, routesHTTPErr(500, "Failed to create alert rule")
	}

	ruleID := fmt.Sprintf("rule_%d_%d", alertRules.Len()+1, time.Now().Unix())

	rule := &AlertRule{
		ID:              ruleID,
		Name:            name,
		Metric:          metric,
		Condition:       condition,
		Threshold:       threshold,
		Enabled:         true,
		CooldownMinutes: 30,
		Severity:        "warning",
		Description:     "",
	}
	if v, ok := alertGet(ruleData, "enabled"); ok {
		rule.Enabled, _ = alertBool(v)
	}
	if v, ok := alertGet(ruleData, "webhook_url"); ok && v != nil {
		s, _ := alertStr(v)
		rule.WebhookURL = &s
	}
	if v, ok := alertGet(ruleData, "cooldown_minutes"); ok {
		rule.CooldownMinutes, _ = alertInt(v)
	}
	if v, ok := alertGet(ruleData, "severity"); ok {
		rule.Severity, _ = alertStr(v)
	}
	if v, ok := alertGet(ruleData, "description"); ok {
		rule.Description, _ = alertStr(v)
	}

	validConditions := []string{"greater_than", "less_than", "equals"}
	if !containsString(validConditions, rule.Condition) {
		return nil, routesHTTPErr(400, "Invalid condition. Must be one of: ['greater_than', 'less_than', 'equals']")
	}

	alertRules.Set(ruleID, rule)

	out := entities.NewOrderedMap[any]()
	out.Set("message", "Alert rule created successfully")
	out.Set("rule_id", ruleID)
	out.Set("rule", alertRuleDict(rule))
	return out, nil
}

// UpdateAlertRule mirrors PUT /rules/{rule_id}.
func UpdateAlertRule(ruleID string, ruleData *entities.OrderedMap[any]) (*entities.OrderedMap[any], error) {
	rule, ok := alertRules.Get(ruleID)
	if !ok {
		return nil, routesHTTPErr(404, "Alert rule not found")
	}
	if v, ok := alertGet(ruleData, "name"); ok {
		rule.Name, _ = alertStr(v)
	}
	if v, ok := alertGet(ruleData, "metric"); ok {
		rule.Metric, _ = alertStr(v)
	}
	if v, ok := alertGet(ruleData, "condition"); ok {
		rule.Condition, _ = alertStr(v)
	}
	if v, ok := alertGet(ruleData, "threshold"); ok {
		if f, ok := alertFloat(v); ok {
			rule.Threshold = f
		}
	}
	if v, ok := alertGet(ruleData, "enabled"); ok {
		if b, ok := alertBool(v); ok {
			rule.Enabled = b
		}
	}
	if v, ok := alertGet(ruleData, "webhook_url"); ok {
		if v == nil {
			rule.WebhookURL = nil
		} else if s, ok := alertStr(v); ok {
			rule.WebhookURL = &s
		}
	}
	if v, ok := alertGet(ruleData, "cooldown_minutes"); ok {
		if n, ok := alertInt(v); ok {
			rule.CooldownMinutes = n
		}
	}
	if v, ok := alertGet(ruleData, "severity"); ok {
		rule.Severity, _ = alertStr(v)
	}
	if v, ok := alertGet(ruleData, "description"); ok {
		rule.Description, _ = alertStr(v)
	}

	out := entities.NewOrderedMap[any]()
	out.Set("message", "Alert rule updated successfully")
	out.Set("rule", alertRuleDict(rule))
	return out, nil
}

// DeleteAlertRule mirrors DELETE /rules/{rule_id}.
func DeleteAlertRule(ruleID string) (*entities.OrderedMap[any], error) {
	if !alertRules.Has(ruleID) {
		return nil, routesHTTPErr(404, "Alert rule not found")
	}
	alertRules.Delete(ruleID)
	out := entities.NewOrderedMap[any]()
	out.Set("message", "Alert rule deleted successfully")
	return out, nil
}

// ListAlertEvents mirrors GET /events.
func ListAlertEvents(limit int, severity *string, acknowledged *bool) *entities.OrderedMap[any] {
	events := alertEvents
	if severity != nil {
		filtered := make([]*AlertEvent, 0, len(events))
		for _, e := range events {
			if e.Severity == *severity {
				filtered = append(filtered, e)
			}
		}
		events = filtered
	}
	if acknowledged != nil {
		filtered := make([]*AlertEvent, 0, len(events))
		for _, e := range events {
			if e.Acknowledged == *acknowledged {
				filtered = append(filtered, e)
			}
		}
		events = filtered
	}
	sortedEvents := make([]*AlertEvent, len(events))
	copy(sortedEvents, events)
	sort.SliceStable(sortedEvents, func(i, j int) bool {
		return sortedEvents[i].Timestamp.After(sortedEvents[j].Timestamp)
	})
	if limit >= 0 && len(sortedEvents) > limit {
		sortedEvents = sortedEvents[:limit]
	}

	eventsData := make([]any, 0, len(sortedEvents))
	for _, e := range sortedEvents {
		eventsData = append(eventsData, alertEventDict(e))
	}
	unacknowledged := 0
	for _, e := range alertEvents {
		if !e.Acknowledged {
			unacknowledged++
		}
	}
	out := entities.NewOrderedMap[any]()
	out.Set("events", eventsData)
	out.Set("total_events", len(alertEvents))
	out.Set("unacknowledged_events", unacknowledged)
	return out
}

// AcknowledgeAlert mirrors POST /events/{event_index}/acknowledge.
func AcknowledgeAlert(eventIndex int) (*entities.OrderedMap[any], error) {
	if eventIndex >= len(alertEvents) || eventIndex < 0 {
		return nil, routesHTTPErr(404, "Alert event not found")
	}
	alertEvents[eventIndex].Acknowledged = true
	out := entities.NewOrderedMap[any]()
	out.Set("message", "Alert acknowledged successfully")
	return out, nil
}

// CheckAlertRules mirrors POST /check-rules. The background task is a goroutine
// with a WaitGroup, mirroring FastAPI BackgroundTasks.
func CheckAlertRules(ctx context.Context, wg *sync.WaitGroup) *entities.OrderedMap[any] {
	if wg != nil {
		wg.Add(1)
	}
	go func() {
		if wg != nil {
			defer wg.Done()
		}
		checkAndTriggerAlerts(ctx)
	}()
	active := 0
	for _, r := range alertRules.Values() {
		if r.Enabled {
			active++
		}
	}
	out := entities.NewOrderedMap[any]()
	out.Set("message", "Alert rule check initiated")
	out.Set("active_rules", active)
	return out
}

// TestWebhook mirrors POST /test-webhook.
func TestWebhook(webhookData *entities.OrderedMap[any]) (*entities.OrderedMap[any], error) {
	raw, _ := alertGet(webhookData, "webhook_url")
	webhookURL, ok := alertStr(raw)
	if !ok || webhookURL == "" {
		return nil, routesHTTPErr(400, "webhook_url is required")
	}

	testPayload := entities.NewOrderedMap[any]()
	testPayload.Set("alert_type", "test")
	testPayload.Set("rule_name", "Test Alert")
	testPayload.Set("metric", "test_metric")
	testPayload.Set("current_value", 0.5)
	testPayload.Set("threshold", 0.8)
	testPayload.Set("severity", "info")
	testPayload.Set("message", "This is a test alert from the agenthub system")
	testPayload.Set("timestamp", tmvo.IsoFormat(time.Now()))
	testPayload.Set("system", "agenthub")

	statusCode, text, err := postWebhook(context.Background(), webhookURL, testPayload)
	if err != nil {
		return nil, routesHTTPErr(500, fmt.Sprintf("Webhook test failed: %v", err))
	}
	out := entities.NewOrderedMap[any]()
	out.Set("message", "Test webhook sent successfully")
	out.Set("status_code", statusCode)
	if text != "" {
		if len(text) > 500 {
			text = text[:500]
		}
		out.Set("response", text)
	} else {
		out.Set("response", nil)
	}
	return out, nil
}

func checkAndTriggerAlerts(ctx context.Context) {
	defer func() {
		if r := recover(); r != nil {
			// Python except Exception: log and continue.
			_ = r
		}
	}()

	if performanceOverviewFunc == nil {
		return
	}
	currentMetrics, err := performanceOverviewFunc(ctx, map[string]any{"sub": "system"}, false)
	if err != nil {
		return
	}

	for _, rule := range alertRules.Values() {
		if !rule.Enabled {
			continue
		}
		lastTrigger := getLastTriggerTime(rule.ID)
		if lastTrigger != nil && time.Since(*lastTrigger).Seconds() < float64(rule.CooldownMinutes*60) {
			continue
		}
		value := extractMetricValue(currentMetrics, rule.Metric)
		if value == nil {
			continue
		}
		triggered := false
		if rule.Condition == "greater_than" && *value > rule.Threshold {
			triggered = true
		} else if rule.Condition == "less_than" && *value < rule.Threshold {
			triggered = true
		} else if rule.Condition == "equals" && absFloat(*value-rule.Threshold) < 0.001 {
			triggered = true
		}
		if triggered {
			triggerAlert(ctx, rule, *value)
		}
	}
}

// performanceOverviewFunc mirrors performance_metrics_routes.get_performance_overview.
// It is nil until a caller wires it.
var performanceOverviewFunc func(ctx context.Context, user map[string]any, includeDetails bool) (map[string]any, error)

func triggerAlert(ctx context.Context, rule *AlertRule, currentValue float64) {
	message := fmt.Sprintf("%s: %s is %.2f (threshold: %.2f)", rule.Name, rule.Metric, currentValue, rule.Threshold)
	event := &AlertEvent{
		RuleID:       rule.ID,
		RuleName:     rule.Name,
		Metric:       rule.Metric,
		CurrentValue: currentValue,
		Threshold:    rule.Threshold,
		Severity:     rule.Severity,
		Message:      message,
		Timestamp:    time.Now(),
	}
	alertEvents = append(alertEvents, event)
	if len(alertEvents) > 1000 {
		alertEvents = alertEvents[1:]
	}

	if rule.WebhookURL != nil {
		payload := entities.NewOrderedMap[any]()
		payload.Set("alert_type", "performance_alert")
		payload.Set("rule_name", rule.Name)
		payload.Set("metric", rule.Metric)
		payload.Set("current_value", currentValue)
		payload.Set("threshold", rule.Threshold)
		payload.Set("severity", rule.Severity)
		payload.Set("message", message)
		payload.Set("timestamp", tmvo.IsoFormat(event.Timestamp))
		payload.Set("system", "agenthub")
		payload.Set("rule_id", rule.ID)
		if _, _, err := postWebhook(ctx, *rule.WebhookURL, payload); err == nil {
			event.WebhookSent = true
		}
	}
}

func getLastTriggerTime(ruleID string) *time.Time {
	for i := len(alertEvents) - 1; i >= 0; i-- {
		if alertEvents[i].RuleID == ruleID {
			t := alertEvents[i].Timestamp
			return &t
		}
	}
	return nil
}

func extractMetricValue(metricsData map[string]any, metricName string) *float64 {
	switch metricName {
	case "performance_score":
		if v, ok := metricsData["performance_score"]; ok {
			if f, ok := alertFloat(v); ok {
				return &f
			}
		}
		return nil
	case "cache_hit_rate":
		caching := nestedMap(metricsData, "metrics", "caching")
		var hitRates []float64
		for _, cacheData := range caching {
			d, ok := cacheData.(map[string]any)
			if !ok {
				continue
			}
			if hr, ok := d["hit_rate"]; ok {
				if f, ok := alertFloat(hr); ok {
					hitRates = append(hitRates, f)
				}
			}
		}
		if len(hitRates) == 0 {
			return nil
		}
		sum := 0.0
		for _, v := range hitRates {
			sum += v
		}
		avg := sum / float64(len(hitRates))
		return &avg
	case "connection_wait_time":
		sqlite := nestedMap(metricsData, "metrics", "connections", "sqlite")
		if v, ok := sqlite["avg_wait_time"]; ok {
			if f, ok := alertFloat(v); ok {
				return &f
			}
		}
		return nil
	case "active_connections":
		health := nestedMap(metricsData, "metrics", "server_health")
		if v, ok := health["active_connections"]; ok {
			if f, ok := alertFloat(v); ok {
				return &f
			}
		}
		return nil
	case "system_health":
		health := "unknown"
		if v, ok := metricsData["system_health"]; ok {
			if s, ok := alertStr(v); ok {
				health = s
			}
		}
		scores := map[string]float64{"healthy": 1.0, "degraded": 0.5, "critical": 0.0}
		score := scores[health]
		return &score
	}
	return nil
}

func init() {
	initializeDefaultAlertRules()
}

func initializeDefaultAlertRules() {
	if alertRules.Len() != 0 {
		return
	}
	defaults := []*AlertRule{
		{Name: "Low Performance Score", Metric: "performance_score", Condition: "less_than", Threshold: 70.0, Severity: "warning", Description: "Alert when overall performance score drops below 70", Enabled: true},
		{Name: "Critical Performance Score", Metric: "performance_score", Condition: "less_than", Threshold: 50.0, Severity: "critical", Description: "Critical alert when performance score drops below 50", Enabled: true},
		{Name: "Low Cache Hit Rate", Metric: "cache_hit_rate", Condition: "less_than", Threshold: 0.6, Severity: "warning", Description: "Alert when average cache hit rate falls below 60%", Enabled: true},
		{Name: "High Connection Wait Time", Metric: "connection_wait_time", Condition: "greater_than", Threshold: 0.5, Severity: "warning", Description: "Alert when database connection wait time exceeds 500ms", Enabled: true},
	}
	for i, rule := range defaults {
		rule.ID = fmt.Sprintf("default_rule_%d", i+1)
		rule.CooldownMinutes = 30
		alertRules.Set(rule.ID, rule)
	}
}

// postWebhook mirrors httpx.AsyncClient(timeout=10).post(url, json=payload).
func postWebhook(ctx context.Context, url string, payload *entities.OrderedMap[any]) (int, string, error) {
	body := orderedMapToPlain(payload)
	buf, err := json.Marshal(body)
	if err != nil {
		return 0, "", err
	}
	reqCtx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	req, err := http.NewRequestWithContext(reqCtx, http.MethodPost, url, bytes.NewReader(buf))
	if err != nil {
		return 0, "", err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return 0, "", err
	}
	defer resp.Body.Close()
	var sb strings.Builder
	chunk := make([]byte, 4096)
	for {
		n, rerr := resp.Body.Read(chunk)
		if n > 0 {
			sb.Write(chunk[:n])
		}
		if rerr != nil {
			break
		}
	}
	return resp.StatusCode, sb.String(), nil
}

func orderedMapToPlain(m *entities.OrderedMap[any]) map[string]any {
	out := map[string]any{}
	for _, k := range m.Keys() {
		v, _ := m.Get(k)
		out[k] = v
	}
	return out
}

func nestedMap(m map[string]any, keys ...string) map[string]any {
	cur := m
	for _, k := range keys {
		next, ok := cur[k].(map[string]any)
		if !ok {
			return map[string]any{}
		}
		cur = next
	}
	return cur
}

func mustGet(m *entities.OrderedMap[any], key string) any {
	v, _ := m.Get(key)
	return v
}

func containsString(list []string, v string) bool {
	for _, s := range list {
		if s == v {
			return true
		}
	}
	return false
}

func absFloat(f float64) float64 {
	if f < 0 {
		return -f
	}
	return f
}
