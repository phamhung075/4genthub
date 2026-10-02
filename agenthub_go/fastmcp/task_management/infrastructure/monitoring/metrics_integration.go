package monitoring

import (
	"errors"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/workers"
)

func init() {
	workers.GlobalOptimizationCollector = func() workers.OptimizationSummaryProvider {
		return GetGlobalOptimizationCollector()
	}
}

// MetricsMiddleware (FastAPI/ASGI) and the metrics_track / track_* decorators are
// Python-framework-specific (Starlette scope/receive/send, functools, inspect) and have
// no Go meaning, so they are not ported.

// OptimizationContext mirrors the async optimization_context context manager: it yields
// the tracking map and records metrics when the returned close function runs.
func OptimizationContext(optimizationType, operation string, tags *entities.OrderedMap[string]) (*entities.OrderedMap[any], func(err error)) {
	collector := GetGlobalOptimizationCollector()
	startTime := PerfCounter()
	contextTags := entities.NewOrderedMap[string]()
	if tags != nil {
		for _, k := range tags.Keys() {
			v, _ := tags.Get(k)
			contextTags.Set(k, v)
		}
	}
	contextTags.Set("optimization_type", optimizationType)
	contextTags.Set("operation", operation)

	contextData := obj(
		"original_size", nil,
		"optimized_size", nil,
		"fields_requested", nil,
		"fields_returned", nil,
		"cache_hit", false,
		"parse_success", true,
		"error_type", nil,
	)

	closeFn := func(err error) {
		if err != nil {
			contextData.Set("parse_success", false)
			contextData.Set("error_type", pyErrorName(err))
		}
		endTime := PerfCounter()
		processingTimeMs := (endTime - startTime) * 1000

		original := omGet(contextData, "original_size")
		optimized := omGet(contextData, "optimized_size")
		if pyTruthy(original) && pyTruthy(optimized) {
			collector.RecordResponseOptimization(
				asInt(original), asInt(optimized), processingTimeMs,
				optimizationType, operation, contextTags,
			)
		}

		if omGet(contextData, "fields_requested") != nil {
			cacheHit, _ := omGet(contextData, "cache_hit").(bool)
			collector.RecordContextInjectionMetrics(
				asInt(omGet(contextData, "fields_requested")),
				asInt(omGet(contextData, "fields_returned")),
				processingTimeMs, cacheHit, "", contextTags,
			)
		}

		parseSuccess, _ := omGet(contextData, "parse_success").(bool)
		var errorType *string
		if s, ok := omGet(contextData, "error_type").(string); ok {
			errorType = &s
		}
		collector.RecordAIPerformanceMetrics(
			parseSuccess, processingTimeMs, optimizationType, operation, errorType, contextTags,
		)
	}
	return contextData, closeFn
}

// pyErrorName is Python type(e).__name__ for the errors this code raises.
func pyErrorName(err error) string {
	switch err.(type) {
	case *tmvo.ValueError:
		return "ValueError"
	case *tmvo.TypeError:
		return "TypeError"
	}
	return "Exception"
}

// ResponseOptimizationTracker mirrors the response_optimization_tracker context manager.
func ResponseOptimizationTracker(optimizationType string, originalSize int, operation string, tags *entities.OrderedMap[string]) (*entities.OrderedMap[any], func(err error)) {
	collector := GetGlobalOptimizationCollector()
	startTime := PerfCounter()

	trackingData := obj(
		"optimized_size", originalSize,
		"cache_hit", false,
		"error_occurred", false,
	)

	closeFn := func(err error) {
		if err != nil {
			trackingData.Set("error_occurred", true)
		}
		endTime := PerfCounter()
		processingTimeMs := (endTime - startTime) * 1000
		collector.RecordResponseOptimization(
			originalSize, asInt(omGet(trackingData, "optimized_size")), processingTimeMs,
			optimizationType, operation, tags,
		)
	}
	return trackingData, closeFn
}

// MetricsCollectionService manages the metrics collection lifecycle.
type MetricsCollectionService struct {
	Collector *OptimizationMetricsCollector
	Reporter  *workers.MetricsReporter
	Started   bool
}

// NewMetricsCollectionService mirrors MetricsCollectionService.__init__.
func NewMetricsCollectionService() *MetricsCollectionService {
	return &MetricsCollectionService{Collector: GetGlobalOptimizationCollector()}
}

// StartMetricsCollection starts metrics collection and optional reporting.
func (s *MetricsCollectionService) StartMetricsCollection(enableReporting bool, reportConfig *workers.ReportConfig) {
	if s.Started {
		return
	}
	s.Collector.StartCollection()

	if enableReporting {
		if reportConfig == nil {
			reportConfig = workers.NewReportConfig()
			reportConfig.FileOutputEnabled = true
			reportConfig.EmailEnabled = false
			reportConfig.OutputDirectory = "/tmp/mcp_reports"
		}
		s.Reporter = workers.GetGlobalMetricsReporter(reportConfig)
		s.Reporter.StartReporting()
	}
	s.Started = true
}

// StopMetricsCollection stops metrics collection and reporting.
func (s *MetricsCollectionService) StopMetricsCollection() {
	if !s.Started {
		return
	}
	if s.Reporter != nil {
		s.Reporter.StopReporting()
		s.Reporter = nil
	}
	s.Collector.StopCollection()
	s.Started = false
}

// GetRealTimeMetrics returns a real-time metrics summary.
func (s *MetricsCollectionService) GetRealTimeMetrics(timeWindowHours float64) *entities.OrderedMap[any] {
	return s.Collector.GetOptimizationSummary(timeWindowHours)
}

// GetDashboardData returns dashboard data for visualization.
func (s *MetricsCollectionService) GetDashboardData(timeWindowHours float64) *entities.OrderedMap[any] {
	return s.Collector.ExportOptimizationDashboardData(timeWindowHours)
}

// GenerateOnDemandReport generates a daily, weekly or monthly report.
func (s *MetricsCollectionService) GenerateOnDemandReport(reportType string) (*entities.OrderedMap[any], error) {
	if s.Reporter == nil {
		return nil, errors.New("Reporting not enabled - start metrics collection with enable_reporting=True")
	}
	switch reportType {
	case "daily":
		return s.Reporter.GenerateDailyReport(nil), nil
	case "weekly":
		return s.Reporter.GenerateWeeklyReport(nil)
	case "monthly":
		return s.Reporter.GenerateMonthlyRoiReport(nil)
	}
	return nil, &tmvo.ValueError{Msg: fmt.Sprintf("Unknown report type: %s", reportType)}
}

// AddCustomMetric adds a custom metric to the collection.
func (s *MetricsCollectionService) AddCustomMetric(name string, value float64, unit string, tags *entities.OrderedMap[string], category string) {
	s.Collector.RecordMetric(name, value, unit, tags, category)
}

// SetAlertThresholds updates the alert thresholds.
func (s *MetricsCollectionService) SetAlertThresholds(thresholds map[string]float64) {
	for k, v := range thresholds {
		s.Collector.PerformanceBaselines[k] = v
	}
}

var globalMetricsService *MetricsCollectionService

// GetMetricsService returns (creating if needed) the global metrics service.
func GetMetricsService() *MetricsCollectionService {
	if globalMetricsService == nil {
		globalMetricsService = NewMetricsCollectionService()
	}
	return globalMetricsService
}

// InitializeMetricsSystem initializes the complete metrics system.
func InitializeMetricsSystem(enableReporting bool, outputDirectory *string, emailConfig *entities.OrderedMap[any]) (*MetricsCollectionService, error) {
	service := GetMetricsService()

	var reportConfig *workers.ReportConfig
	if enableReporting {
		reportConfig = workers.NewReportConfig()
		reportConfig.FileOutputEnabled = true
		if outputDirectory != nil {
			reportConfig.OutputDirectory = *outputDirectory
		} else {
			reportConfig.OutputDirectory = "/tmp/mcp_reports"
		}

		if emailConfig != nil {
			if v, ok := emailConfig.Get("enabled"); ok {
				reportConfig.EmailEnabled, _ = v.(bool)
			}
			if v, ok := emailConfig.Get("smtp_server"); ok {
				reportConfig.EmailSMTPServer = tmvo.PyStr(v)
			}
			if v, ok := emailConfig.Get("smtp_port"); ok {
				reportConfig.EmailSMTPPort = asInt(v)
			}
			if v, ok := emailConfig.Get("username"); ok {
				reportConfig.EmailUsername = tmvo.PyStr(v)
			}
			if v, ok := emailConfig.Get("password"); ok {
				reportConfig.EmailPassword = tmvo.PyStr(v)
			}
			if v, ok := emailConfig.Get("recipients"); ok {
				if recipients, ok := v.([]string); ok {
					reportConfig.EmailRecipients = recipients
				} else if list, ok := v.([]any); ok {
					reportConfig.EmailRecipients = nil
					for _, item := range list {
						reportConfig.EmailRecipients = append(reportConfig.EmailRecipients, tmvo.PyStr(item))
					}
				}
			}
		}
	}

	service.StartMetricsCollection(enableReporting, reportConfig)
	return service, nil
}
