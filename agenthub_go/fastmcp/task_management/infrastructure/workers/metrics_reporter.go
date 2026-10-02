// Package workers ports task_management/infrastructure/workers.
package workers

import (
	"fmt"
	"net"
	"net/smtp"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// OptimizationSummaryProvider is the cycle-break seam: Python's workers.metrics_reporter
// imports monitoring.optimization_metrics directly; Go cannot (monitoring imports
// workers), so the reporter depends on this minimal interface instead.
type OptimizationSummaryProvider interface {
	GetOptimizationSummary(timeWindowHours float64) *entities.OrderedMap[any]
}

// GlobalOptimizationCollector is registered by the monitoring package so that
// GetGlobalMetricsReporter can default to the global collector like Python does.
var GlobalOptimizationCollector func() OptimizationSummaryProvider

// Now is the wall clock used by the reporter (Python datetime.now(UTC)).
var Now = func() time.Time { return time.Now().UTC() }

// ReportConfig configures automated reports.
type ReportConfig struct {
	EmailEnabled    bool
	EmailSMTPServer string
	EmailSMTPPort   int
	EmailUsername   string
	EmailPassword   string
	EmailRecipients []string

	FileOutputEnabled bool
	OutputDirectory   string

	DailyReportTime  string
	WeeklyReportDay  string
	MonthlyReportDay int

	AlertThresholds map[string]float64
}

// NewReportConfig builds a ReportConfig with the Python defaults and __post_init__ values.
func NewReportConfig() *ReportConfig {
	c := &ReportConfig{}
	c.applyDefaults()
	return c
}

func (c *ReportConfig) applyDefaults() {
	if c.EmailSMTPServer == "" {
		c.EmailSMTPServer = "localhost"
	}
	if c.EmailSMTPPort == 0 {
		c.EmailSMTPPort = 587
	}
	if !c.FileOutputEnabled {
		c.FileOutputEnabled = true
	}
	if c.OutputDirectory == "" {
		c.OutputDirectory = "/tmp/mcp_reports"
	}
	if c.DailyReportTime == "" {
		c.DailyReportTime = "09:00"
	}
	if c.WeeklyReportDay == "" {
		c.WeeklyReportDay = "monday"
	}
	if c.MonthlyReportDay == 0 {
		c.MonthlyReportDay = 1
	}
	if c.EmailRecipients == nil {
		c.EmailRecipients = []string{}
	}
	if c.AlertThresholds == nil {
		c.AlertThresholds = map[string]float64{
			"compression_ratio_min": 30.0,
			"processing_time_max":   300.0,
			"cache_hit_rate_min":    70.0,
			"error_rate_max":        5.0,
			"system_health_min":     70.0,
		}
	}
}

// MetricsReporter is the automated metrics reporting and alerting system.
type MetricsReporter struct {
	MetricsCollector OptimizationSummaryProvider
	Config           *ReportConfig
	Running          bool
}

// NewMetricsReporter mirrors MetricsReporter.__init__ (jinja2 template loading dropped).
func NewMetricsReporter(metricsCollector OptimizationSummaryProvider, config *ReportConfig) *MetricsReporter {
	config.applyDefaults()
	_ = os.MkdirAll(config.OutputDirectory, 0o755)
	return &MetricsReporter{MetricsCollector: metricsCollector, Config: config}
}

// StartReporting starts automated reporting background tasks (Go keeps only the flag).
func (r *MetricsReporter) StartReporting() {
	if r.Running {
		return
	}
	r.Running = true
}

// StopReporting stops all reporting background tasks.
func (r *MetricsReporter) StopReporting() {
	if !r.Running {
		return
	}
	r.Running = false
}

// GenerateDailyReport generates the daily optimization report.
func (r *MetricsReporter) GenerateDailyReport(reportDate *time.Time) *entities.OrderedMap[any] {
	now := Now().UTC()
	var dateStr, reportDateISO string
	if reportDate == nil {
		d := now
		dateStr = d.Format("2006-01-02")
		reportDateISO = dateStr
	} else {
		dateStr = reportDate.Format("2006-01-02")
		reportDateISO = tmvo.IsoFormat(*reportDate)
	}

	summary := r.MetricsCollector.GetOptimizationSummary(24)
	reportData := obj(
		"report_date", dateStr,
		"time_period", "Past 24 Hours",
		"summary", summary,
		"generation_time", now.Format("2006-01-02 15:04:05 UTC"),
	)
	htmlContent := renderDailyHTML(reportData)

	if r.Config.FileOutputEnabled {
		filename := "daily_report_" + now.Format("20060102") + ".html"
		if reportDate != nil {
			filename = "daily_report_" + reportDate.Format("20060102") + ".html"
		}
		_ = os.WriteFile(filepath.Join(r.Config.OutputDirectory, filename), []byte(htmlContent), 0o644)
	}
	if r.Config.EmailEnabled {
		r.SendEmailReport("MCP Daily Report - "+dateStr, htmlContent, true)
	}

	return obj(
		"report_type", "daily",
		"report_date", reportDateISO,
		"html_content", htmlContent,
		"summary", summary,
		"file_saved", r.Config.FileOutputEnabled,
		"email_sent", r.Config.EmailEnabled,
	)
}

// GenerateWeeklyReport generates the weekly trend analysis report.
func (r *MetricsReporter) GenerateWeeklyReport(weekStart *time.Time) (*entities.OrderedMap[any], error) {
	var start, end time.Time
	startIsDate := weekStart == nil
	if weekStart == nil {
		today := Now().UTC()
		daysSinceMonday := (int(today.Weekday()) + 6) % 7
		start = time.Date(today.Year(), today.Month(), today.Day(), 0, 0, 0, 0, time.UTC).AddDate(0, 0, -daysSinceMonday)
	} else {
		start = *weekStart
	}
	end = start.AddDate(0, 0, 6)

	currentWeekSummary := r.MetricsCollector.GetOptimizationSummary(24 * 7)
	previousWeekSummary := r.MetricsCollector.GetOptimizationSummary(24 * 14)

	trends := r.calculateWeeklyTrends(currentWeekSummary, previousWeekSummary)
	weeklyRecommendations, err := r.generateWeeklyRecommendations(trends, currentWeekSummary)
	if err != nil {
		return nil, err
	}

	compressionTrendUp := omString(omMap(trends, "compression_ratio"), "trend") == "up"
	healthTrendUp := omString(omMap(trends, "system_health"), "trend") == "up"
	compressionTrend, compressionTrendClass := trendLabels(compressionTrendUp)
	healthTrend, healthTrendClass := trendLabels(healthTrendUp)

	reportData := obj(
		"week_start", start.Format("2006-01-02"),
		"week_end", end.Format("2006-01-02"),
		"total_optimizations", omGetDefault(omMap(currentWeekSummary, "optimization_performance"), "total_optimizations", 0),
		"avg_compression", omGetDefault(omMap(currentWeekSummary, "optimization_performance"), "avg_compression_ratio", 0),
		"avg_health", r.safeGetHealthScore(currentWeekSummary),
		"total_alerts", omGetDefault(omMap(currentWeekSummary, "alerts"), "total_alerts", 0),
		"trends", trends,
		"weekly_recommendations", weeklyRecommendations,
		"compression_trend", compressionTrend,
		"compression_trend_class", compressionTrendClass,
		"health_trend", healthTrend,
		"health_trend_class", healthTrendClass,
		"generation_time", Now().UTC().Format("2006-01-02 15:04:05 UTC"),
	)
	htmlContent := renderWeeklyHTML(reportData)

	if r.Config.FileOutputEnabled {
		filename := "weekly_report_" + start.Format("20060102") + ".html"
		_ = os.WriteFile(filepath.Join(r.Config.OutputDirectory, filename), []byte(htmlContent), 0o644)
	}
	if r.Config.EmailEnabled {
		r.SendEmailReport("MCP Weekly Report - Week of "+start.Format("2006-01-02"), htmlContent, true)
	}

	startISO, endISO := start.Format("2006-01-02"), end.Format("2006-01-02")
	if !startIsDate {
		startISO, endISO = tmvo.IsoFormat(start), tmvo.IsoFormat(end)
	}
	return obj(
		"report_type", "weekly",
		"week_start", startISO,
		"week_end", endISO,
		"html_content", htmlContent,
		"trends", trends,
		"recommendations", weeklyRecommendations,
		"file_saved", r.Config.FileOutputEnabled,
		"email_sent", r.Config.EmailEnabled,
	), nil
}

func trendLabels(up bool) (string, string) {
	if up {
		return "↗️ Improving", "trend-up"
	}
	return "↘️ Declining", "trend-down"
}

// GenerateMonthlyRoiReport generates the monthly ROI and cost-benefit report.
func (r *MetricsReporter) GenerateMonthlyRoiReport(monthStart *time.Time) (*entities.OrderedMap[any], error) {
	var start time.Time
	if monthStart == nil {
		now := Now().UTC()
		start = time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, time.UTC)
	} else {
		start = *monthStart
	}

	monthlySummary := r.MetricsCollector.GetOptimizationSummary(24 * 30)
	roiAnalysis, err := r.calculateROIMetrics(monthlySummary)
	if err != nil {
		return nil, err
	}

	reportData := obj(
		"month", start.Format("January 2006"),
		"summary", monthlySummary,
		"roi_analysis", roiAnalysis,
		"cost_savings", omGetDefault(roiAnalysis, "estimated_cost_savings", 0),
		"efficiency_gains", omGetDefault(roiAnalysis, "efficiency_improvement", 0),
		"generation_time", Now().UTC().Format("2006-01-02 15:04:05 UTC"),
	)

	if r.Config.FileOutputEnabled {
		filename := "monthly_roi_" + start.Format("200601") + ".json"
		_ = os.WriteFile(filepath.Join(r.Config.OutputDirectory, filename), []byte(tmvo.PyJSONDumpsDefaultStr(reportData, 2)), 0o644)
	}
	return reportData, nil
}

func (r *MetricsReporter) safeGetHealthScore(summary *entities.OrderedMap[any]) float64 {
	healthData := omMap(summary, "system_health")
	if !pyTruthy(healthData) {
		return 0.0
	}
	healthScore := omGet(healthData, "health_score")
	// Python checks isinstance(health_score, dict); a MetricSummary dataclass is not a
	// dict, so this always returns 0.0 in practice.
	if healthScore != nil {
		if hs, ok := healthScore.(*entities.OrderedMap[any]); ok {
			return asFloat(omGetDefault(hs, "avg_value", 0.0))
		}
	}
	return 0.0
}

func (r *MetricsReporter) calculateWeeklyTrends(current, previous *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	currentCompression := asFloat(omGetDefault(omMap(current, "optimization_performance"), "avg_compression_ratio", 0))
	previousCompression := 25.0

	compressionTrend := "down"
	compressionClass := "trend-down"
	if currentCompression > previousCompression {
		compressionTrend = "up"
		compressionClass = "trend-up"
	}
	compressionChange := tmvo.PyRound(((currentCompression-previousCompression)/maxF(previousCompression, 1))*100, 1)

	// Python's isinstance(health_score, dict) is False for MetricSummary, so 0.
	currentHealth := 0.0
	previousHealth := 75.0
	healthTrend := "down"
	healthClass := "trend-down"
	if currentHealth > previousHealth {
		healthTrend = "up"
		healthClass = "trend-up"
	}
	healthChange := tmvo.PyRound(((currentHealth-previousHealth)/maxF(previousHealth, 1))*100, 1)

	return obj(
		"compression_ratio", obj(
			"current", currentCompression,
			"previous", previousCompression,
			"trend", compressionTrend,
			"trend_class", compressionClass,
			"change_percent", compressionChange,
		),
		"system_health", obj(
			"current", currentHealth,
			"previous", previousHealth,
			"trend", healthTrend,
			"trend_class", healthClass,
			"change_percent", healthChange,
		),
	)
}

func (r *MetricsReporter) generateWeeklyRecommendations(trends, summary *entities.OrderedMap[any]) ([]string, error) {
	recommendations := []string{}

	if omString(omMap(trends, "compression_ratio"), "trend") == "down" {
		recommendations = append(recommendations, "Compression ratio declining - review optimization algorithms and consider profile adjustments")
	}
	if omString(omMap(trends, "system_health"), "trend") == "down" {
		recommendations = append(recommendations, "System health declining - monitor resource utilization and investigate performance bottlenecks")
	}

	totalAlerts := asInt(omGetDefault(omMap(summary, "alerts"), "total_alerts", 0))
	if totalAlerts > 10 {
		recommendations = append(recommendations, fmt.Sprintf("High alert volume (%d alerts) - review alert thresholds and address root causes", totalAlerts))
	}

	cachePerformance := omMap(omMap(summary, "performance_metrics"), "cache_hit_rates")
	if cachePerformance != nil {
		for _, tier := range cachePerformance.Keys() {
			data := omGet(cachePerformance, tier)
			if !pyTruthy(data) {
				continue
			}
			// Python calls data.get("latest_value", 0); a MetricSummary raises AttributeError.
			if _, isDict := data.(*entities.OrderedMap[any]); !isDict {
				return nil, fmt.Errorf("'%T' object has no attribute 'get'", data)
			}
		}
	}

	if len(recommendations) == 0 {
		recommendations = append(recommendations, "System performing well - maintain current optimization strategies")
	}
	return recommendations, nil
}

func (r *MetricsReporter) calculateROIMetrics(summary *entities.OrderedMap[any]) (*entities.OrderedMap[any], error) {
	totalOptimizations := asInt(omGetDefault(omMap(summary, "optimization_performance"), "total_optimizations", 0))
	avgCompression := asFloat(omGetDefault(omMap(summary, "optimization_performance"), "avg_compression_ratio", 0))

	estimatedBytesSaved := float64(totalOptimizations) * 5000 * (avgCompression / 100)
	estimatedCostSavings := estimatedBytesSaved * 0.0001

	avgProcessingTime := omGetDefault(omMap(summary, "performance_metrics"), "avg_processing_time_ms", nil)
	processingTimeValue := 100.0
	if pyTruthy(avgProcessingTime) {
		pt, isDict := avgProcessingTime.(*entities.OrderedMap[any])
		if !isDict {
			return nil, fmt.Errorf("'%T' object has no attribute 'get'", avgProcessingTime)
		}
		processingTimeValue = asFloat(omGetDefault(pt, "avg_value", 100))
	}

	efficiencyImprovement := maxF(0, (200-processingTimeValue)/200*100)

	return obj(
		"total_optimizations", totalOptimizations,
		"bytes_saved_estimate", estimatedBytesSaved,
		"estimated_cost_savings", estimatedCostSavings,
		"efficiency_improvement", efficiencyImprovement,
		"avg_compression_ratio", avgCompression,
		"processing_time_performance", processingTimeValue,
		"roi_calculation_method", "Conservative estimate based on bandwidth and processing savings",
	), nil
}

// SendEmailReport sends an email report to the configured recipients.
func (r *MetricsReporter) SendEmailReport(subject, htmlContent string, html bool) {
	if len(r.Config.EmailRecipients) == 0 {
		return
	}
	contentType := "text/plain"
	if html {
		contentType = "text/html"
	}
	msg := "Subject: " + subject + "\r\n" +
		"From: " + r.Config.EmailUsername + "\r\n" +
		"To: " + strings.Join(r.Config.EmailRecipients, ", ") + "\r\n" +
		"MIME-Version: 1.0\r\n" +
		"Content-Type: " + contentType + "; charset=\"utf-8\"\r\n" +
		"\r\n" + htmlContent
	r.smtpSend([]byte(msg))
}

func (r *MetricsReporter) smtpSend(msg []byte) {
	server := r.Config.EmailSMTPServer
	if server == "" {
		server = "localhost"
	}
	addr := net.JoinHostPort(server, fmt.Sprintf("%d", r.Config.EmailSMTPPort))
	c, err := smtp.Dial(addr)
	if err != nil {
		return
	}
	defer c.Quit()
	if r.Config.EmailUsername != "" && r.Config.EmailPassword != "" {
		_ = c.StartTLS(nil)
		auth := smtp.PlainAuth("", r.Config.EmailUsername, r.Config.EmailPassword, server)
		if err := c.Auth(auth); err != nil {
			return
		}
	}
	if err := c.Mail(r.Config.EmailUsername); err != nil {
		return
	}
	for _, rcpt := range r.Config.EmailRecipients {
		if err := c.Rcpt(rcpt); err != nil {
			return
		}
	}
	w, err := c.Data()
	if err != nil {
		return
	}
	_, _ = w.Write(msg)
	_ = w.Close()
}

// WaitUntilTime returns the seconds until the next occurrence of an HH:MM time.
func (r *MetricsReporter) WaitUntilTime(timeStr string) float64 {
	parts := strings.Split(timeStr, ":")
	hour, minute := 0, 0
	if len(parts) == 2 {
		hour = asInt(parseIntOrZero(parts[0]))
		minute = asInt(parseIntOrZero(parts[1]))
	}
	now := Now().UTC()
	target := time.Date(now.Year(), now.Month(), now.Day(), hour, minute, 0, 0, time.UTC)
	if !target.After(now) {
		target = target.AddDate(0, 0, 1)
	}
	return target.Sub(now).Seconds()
}

// WaitUntilWeekday returns the seconds until 09:00 on the next occurrence of a weekday.
func (r *MetricsReporter) WaitUntilWeekday(dayName string) float64 {
	days := []string{"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
	targetDay := indexOfString(days, tmvo.PyLower(dayName))
	if targetDay < 0 {
		targetDay = 0
	}
	now := Now().UTC()
	currentDay := (int(now.Weekday()) + 6) % 7
	daysAhead := targetDay - currentDay
	if daysAhead <= 0 {
		daysAhead += 7
	}
	target := now.AddDate(0, 0, daysAhead)
	target = time.Date(target.Year(), target.Month(), target.Day(), 9, 0, 0, 0, time.UTC)
	return target.Sub(now).Seconds()
}

// WaitUntilMonthday returns the seconds until 09:00 on the next occurrence of a month day.
func (r *MetricsReporter) WaitUntilMonthday(day int) float64 {
	now := Now().UTC()
	target := time.Date(now.Year(), now.Month(), day, 9, 0, 0, 0, time.UTC)
	// Go normalises an out-of-range day into the next month already.
	if !target.After(now) {
		target = time.Date(now.Year(), now.Month(), day, 9, 0, 0, 0, time.UTC).AddDate(0, 1, 0)
	}
	return target.Sub(now).Seconds()
}

// SendCriticalAlertEmail sends an immediate email for critical alerts.
func (r *MetricsReporter) SendCriticalAlertEmail(summary *entities.OrderedMap[any]) {
	alertData := omMap(summary, "alerts")
	recentAlerts, _ := omGet(alertData, "recent_alerts").([]*entities.OrderedMap[any])
	if len(recentAlerts) == 0 {
		return
	}
	subject := fmt.Sprintf("🚨 MCP CRITICAL ALERT - %d Critical Issues", asInt(omGetDefault(alertData, "critical_alerts", 0)))

	var alertMessages []string
	limit := len(recentAlerts)
	if limit > 5 {
		limit = 5
	}
	for _, alert := range recentAlerts[:limit] {
		if omString(alert, "severity") == "critical" {
			alertMessages = append(alertMessages, fmt.Sprintf("• %s at %s", omGetDefault(alert, "message", "Unknown alert"), omGetDefault(alert, "timestamp", "Unknown time")))
		}
	}

	emailBody := fmt.Sprintf("\n        CRITICAL ALERTS DETECTED\n        \n        %d critical issues require immediate attention:\n        \n        %s\n        \n        Please check the system immediately and review the full dashboard for details.\n        \n        Generated at: %s\n        ",
		len(alertMessages), strings.Join(alertMessages, "\n"), Now().UTC().Format("2006-01-02 15:04:05 UTC"))

	msg := "Subject: " + subject + "\r\n" +
		"From: " + r.Config.EmailUsername + "\r\n" +
		"To: " + strings.Join(r.Config.EmailRecipients, ", ") + "\r\n" +
		"MIME-Version: 1.0\r\n" +
		"Content-Type: text/plain; charset=\"utf-8\"\r\n" +
		"\r\n" + emailBody
	r.smtpSend([]byte(msg))
}

var (
	globalMetricsReporter *MetricsReporter
)

// GetGlobalMetricsReporter returns (creating if needed) the global metrics reporter.
func GetGlobalMetricsReporter(config *ReportConfig) *MetricsReporter {
	if globalMetricsReporter == nil {
		if config == nil {
			config = NewReportConfig()
		}
		provider := OptimizationSummaryProvider(nil)
		if GlobalOptimizationCollector != nil {
			provider = GlobalOptimizationCollector()
		}
		globalMetricsReporter = NewMetricsReporter(provider, config)
	}
	return globalMetricsReporter
}

// StartAutomatedReporting starts automated metrics reporting.
func StartAutomatedReporting(config *ReportConfig) {
	GetGlobalMetricsReporter(config).StartReporting()
}

// StopAutomatedReporting stops automated metrics reporting.
func StopAutomatedReporting() {
	if globalMetricsReporter != nil {
		globalMetricsReporter.StopReporting()
		globalMetricsReporter = nil
	}
}

// --- small helpers ---------------------------------------------------------

func obj(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

func omGet(m *entities.OrderedMap[any], k string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(k)
	return v
}

// omMap returns m[k] when it is a dict, else nil (Python's dict.get chaining).
func omMap(m *entities.OrderedMap[any], k string) *entities.OrderedMap[any] {
	if m == nil {
		return nil
	}
	v, ok := m.Get(k)
	if !ok {
		return nil
	}
	om, _ := v.(*entities.OrderedMap[any])
	return om
}

func omGetDefault(m *entities.OrderedMap[any], k string, def any) any {
	if m == nil {
		return def
	}
	v, ok := m.Get(k)
	if !ok {
		return def
	}
	return v
}

func omString(m *entities.OrderedMap[any], k string) string {
	s, _ := omGet(m, k).(string)
	return s
}

func asFloat(v any) float64 {
	f, ok := tmvo.PyFloat(v)
	if !ok {
		return 0
	}
	return f
}

func asInt(v any) int {
	f, ok := tmvo.PyFloat(v)
	if !ok {
		return 0
	}
	return int(f)
}

func maxF(a, b float64) float64 {
	if a > b {
		return a
	}
	return b
}

func pyTruthy(v any) bool { return tmvo.PyTruthy(v) }

func parseIntOrZero(s string) any {
	n, ok := tmvo.PyParseInt(s)
	if !ok {
		return 0
	}
	if n.IsInt64() {
		return int(n.Int64())
	}
	return 0
}

func indexOfString(xs []string, s string) int {
	for i, x := range xs {
		if x == s {
			return i
		}
	}
	return -1
}

// pyGet mirrors Python attribute access (jinja's getattr) on a value that may be an
// OrderedMap (dict) or a MetricSummary-style struct (no import needed).
func pyGet(v any, key string) any {
	if v == nil {
		return nil
	}
	if m, ok := v.(*entities.OrderedMap[any]); ok {
		return omGet(m, key)
	}
	rv := reflect.ValueOf(v)
	for rv.Kind() == reflect.Ptr || rv.Kind() == reflect.Interface {
		if rv.IsNil() {
			return nil
		}
		rv = rv.Elem()
	}
	if rv.Kind() != reflect.Struct {
		return nil
	}
	want := strings.ReplaceAll(key, "_", "")
	for i := 0; i < rv.NumField(); i++ {
		field := rv.Type().Field(i)
		if !field.IsExported() {
			continue
		}
		if strings.EqualFold(field.Name, want) || strings.EqualFold(strings.ReplaceAll(field.Name, "_", ""), want) {
			return rv.Field(i).Interface()
		}
	}
	return nil
}

func formatFloat(v any, verb string) string {
	f, ok := tmvo.PyFloat(v)
	if !ok {
		f = 0
	}
	return fmt.Sprintf(verb, f)
}

func sortedStringKeys(m *entities.OrderedMap[any]) []string {
	if m == nil {
		return nil
	}
	keys := m.Keys()
	sort.Strings(keys)
	return keys
}

// --- report HTML rendering -------------------------------------------------
//
// Python renders the reports with jinja2 templates. Go has no jinja2, so these two
// functions build the same document structure and interpolate the same values with the
// same "%.1f"/"%.0f" formats. Whitespace differs from jinja2's output.

func renderDailyHTML(data *entities.OrderedMap[any]) string {
	summary := omGet(data, "summary")
	optPerf := pyGet(summary, "optimization_performance")
	sysHealth := pyGet(summary, "system_health")
	healthScore := pyGet(sysHealth, "health_score")
	alerts := pyGet(summary, "alerts")
	perfMetrics := pyGet(summary, "performance_metrics")
	cacheRates := pyGet(perfMetrics, "cache_hit_rates")

	var b strings.Builder
	b.WriteString("<html>\n<head>\n    <title>MCP Optimization Daily Report - " + htmlEscape(strValue(omGet(data, "report_date"))) + "</title>\n")
	b.WriteString("</head>\n<body>\n")
	b.WriteString("<div class=\"header\">\n<h1>MCP Response Optimization Daily Report</h1>\n")
	b.WriteString("<p>Report Date: " + htmlEscape(strValue(omGet(data, "report_date"))) + "</p>\n")
	b.WriteString("<p>Time Period: " + htmlEscape(strValue(omGet(data, "time_period"))) + "</p>\n</div>\n")
	b.WriteString("<h2>Executive Summary</h2>\n")
	b.WriteString("<div class=\"metric-card\"><h3>Total Optimizations</h3><div class=\"metric-value\">" + strValue(pyGet(optPerf, "total_optimizations")) + "</div></div>\n")
	b.WriteString("<div class=\"metric-card\"><h3>Average Compression Ratio</h3><div class=\"metric-value\">" + formatFloat(pyGet(optPerf, "avg_compression_ratio"), "%.1f") + "%</div></div>\n")
	healthAvg := 0.0
	if pyTruthy(healthScore) {
		healthAvg = asFloat(pyGet(healthScore, "avg_value"))
	}
	b.WriteString("<div class=\"metric-card\"><h3>System Health Score</h3><div class=\"metric-value\">" + fmt.Sprintf("%.0f", healthAvg) + "/100</div></div>\n")

	critical := asInt(pyGet(alerts, "critical_alerts"))
	warning := asInt(pyGet(alerts, "warning_alerts"))
	if critical > 0 {
		b.WriteString("<div class=\"alert\"><h3>⚠️ Critical Alerts: " + fmt.Sprintf("%d", critical) + "</h3><p>Immediate attention required!</p></div>\n")
	} else if warning > 0 {
		b.WriteString("<div class=\"warning\"><h3>⚠️ Warning Alerts: " + fmt.Sprintf("%d", warning) + "</h3><p>Performance monitoring recommended.</p></div>\n")
	} else {
		b.WriteString("<div class=\"success\"><h3>✅ No Critical Issues</h3><p>All systems operating normally.</p></div>\n")
	}

	b.WriteString("<h2>Performance Metrics</h2>\n<table>\n<tr><th>Metric</th><th>Value</th><th>Status</th></tr>\n")
	avgComp := asFloat(pyGet(optPerf, "avg_compression_ratio"))
	compStatus := "Needs Improvement"
	if avgComp >= 30 {
		compStatus = "Good"
	}
	b.WriteString("<tr><td>Compression Ratio</td><td>" + fmt.Sprintf("%.1f", avgComp) + "%</td><td>" + compStatus + "</td></tr>\n")
	if cr, ok := cacheRates.(*entities.OrderedMap[any]); ok {
		for _, tier := range cr.Keys() {
			cacheData := omGet(cr, tier)
			latest := 0.0
			if pyTruthy(cacheData) {
				if _, isDict := cacheData.(*entities.OrderedMap[any]); isDict {
					latest = asFloat(pyGet(cacheData, "latest_value"))
				}
			}
			status := "Needs Improvement"
			if latest >= 70 {
				status = "Good"
			}
			b.WriteString("<tr><td>" + htmlEscape(tmvo.PyTitle(tier)) + " Cache Hit Rate</td><td>" + fmt.Sprintf("%.1f", latest) + "%</td><td>" + status + "</td></tr>\n")
		}
	}
	b.WriteString("</table>\n")

	if recs, ok := pyGet(summary, "recommendations").([]string); ok && len(recs) > 0 {
		b.WriteString("<h2>Recommendations</h2>\n<ul>\n")
		for _, rec := range recs {
			b.WriteString("<li>" + htmlEscape(rec) + "</li>\n")
		}
		b.WriteString("</ul>\n")
	}

	b.WriteString("<h2>Recent Alerts</h2>\n")
	if recent, ok := pyGet(alerts, "recent_alerts").([]*entities.OrderedMap[any]); ok && len(recent) > 0 {
		b.WriteString("<table>\n<tr><th>Time</th><th>Type</th><th>Severity</th><th>Message</th></tr>\n")
		for _, alert := range recent {
			b.WriteString("<tr><td>" + htmlEscape(strValue(omGet(alert, "timestamp"))) + "</td><td>" + htmlEscape(strValue(omGet(alert, "type"))) + "</td><td>" + strings.ToUpper(strValue(omGet(alert, "severity"))) + "</td><td>" + htmlEscape(strValue(omGet(alert, "message"))) + "</td></tr>\n")
		}
		b.WriteString("</table>\n")
	} else {
		b.WriteString("<p>No recent alerts.</p>\n")
	}
	b.WriteString("<div style=\"margin-top: 40px; font-size: 12px; color: #666;\"><p>Generated automatically by MCP Metrics Reporter at " + htmlEscape(strValue(omGet(data, "generation_time"))) + "</p></div>\n")
	b.WriteString("</body>\n</html>\n")
	return b.String()
}

func renderWeeklyHTML(data *entities.OrderedMap[any]) string {
	var b strings.Builder
	b.WriteString("<html>\n<head>\n    <title>MCP Optimization Weekly Report - Week of " + htmlEscape(strValue(omGet(data, "week_start"))) + "</title>\n</head>\n<body>\n")
	b.WriteString("<div class=\"header\">\n<h1>MCP Response Optimization Weekly Report</h1>\n")
	b.WriteString("<p>Week of " + htmlEscape(strValue(omGet(data, "week_start"))) + " to " + htmlEscape(strValue(omGet(data, "week_end"))) + "</p>\n</div>\n")
	b.WriteString("<h2>Weekly Summary</h2>\n<div class=\"metric-card\">\n<h3>Key Performance Indicators</h3>\n<ul>\n")
	b.WriteString("<li>Total Optimizations: <strong>" + strValue(omGet(data, "total_optimizations")) + "</strong></li>\n")
	b.WriteString("<li>Average Compression: <strong>" + formatFloat(omGet(data, "avg_compression"), "%.1f") + "%</strong> <span class=\"" + strValue(omGet(data, "compression_trend_class")) + "\">" + strValue(omGet(data, "compression_trend")) + "</span></li>\n")
	b.WriteString("<li>System Health: <strong>" + formatFloat(omGet(data, "avg_health"), "%.0f") + "/100</strong> <span class=\"" + strValue(omGet(data, "health_trend_class")) + "\">" + strValue(omGet(data, "health_trend")) + "</span></li>\n")
	b.WriteString("<li>Total Alerts: <strong>" + strValue(omGet(data, "total_alerts")) + "</strong></li>\n</ul>\n</div>\n")

	b.WriteString("<h2>Trend Analysis</h2>\n<table>\n<tr><th>Metric</th><th>Current Week</th><th>Previous Week</th><th>Trend</th><th>Change</th></tr>\n")
	if trends, ok := omGet(data, "trends").(*entities.OrderedMap[any]); ok {
		for _, metric := range trends.Keys() {
			td := omGet(trends, metric)
			b.WriteString("<tr><td>" + htmlEscape(metric) + "</td><td>" + formatFloat(pyGet(td, "current"), "%.1f") + "</td><td>" + formatFloat(pyGet(td, "previous"), "%.1f") + "</td><td class=\"" + strValue(pyGet(td, "trend_class")) + "\">" + strValue(pyGet(td, "trend")) + "</td><td>" + strValue(pyGet(td, "change_percent")) + "%</td></tr>\n")
		}
	}
	b.WriteString("</table>\n")

	b.WriteString("<h2>Weekly Recommendations</h2>\n<ul>\n")
	if recs, ok := omGet(data, "weekly_recommendations").([]string); ok {
		for _, rec := range recs {
			b.WriteString("<li>" + htmlEscape(rec) + "</li>\n")
		}
	}
	b.WriteString("</ul>\n")
	b.WriteString("<div style=\"margin-top: 40px; font-size: 12px; color: #666;\"><p>Generated automatically by MCP Metrics Reporter at " + htmlEscape(strValue(omGet(data, "generation_time"))) + "</p></div>\n")
	b.WriteString("</body>\n</html>\n")
	return b.String()
}

func strValue(v any) string {
	if v == nil {
		return ""
	}
	switch x := v.(type) {
	case string:
		return x
	case int:
		return fmt.Sprintf("%d", x)
	case float64:
		return tmvo.PyStr(x)
	}
	return tmvo.PyStr(v)
}

func htmlEscape(s string) string {
	r := strings.NewReplacer("&", "&amp;", "<", "&lt;", ">", "&gt;", "\"", "&#34;", "'", "&#39;")
	return r.Replace(s)
}
