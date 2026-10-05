// placeholder_adapters.go ports task_management/infrastructure/adapters/placeholder_adapters.py.
//
// Placeholder implementations of the domain service interfaces. Python print()/logging
// calls are dropped; behavior and return shapes are preserved.
package adapters

import (
	"context"
	"os"
	"path/filepath"
	"time"

	"agenthub/fastmcp/task_management/domain/interfaces"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// PlaceholderNotification is placeholder_adapters.PlaceholderNotification.
type PlaceholderNotification struct {
	Type      interfaces.NotificationType
	To        string
	Msg       string
	ExtraData map[string]any
}

// NewPlaceholderNotification mirrors PlaceholderNotification.__init__ (metadata None -> {}).
func NewPlaceholderNotification(notificationType interfaces.NotificationType, recipient, message string, metadata map[string]any) *PlaceholderNotification {
	if metadata == nil {
		metadata = map[string]any{}
	}
	return &PlaceholderNotification{Type: notificationType, To: recipient, Msg: message, ExtraData: metadata}
}

func (n *PlaceholderNotification) NotificationType() interfaces.NotificationType { return n.Type }
func (n *PlaceholderNotification) Recipient() string                             { return n.To }
func (n *PlaceholderNotification) Message() string                               { return n.Msg }
func (n *PlaceholderNotification) Metadata() map[string]any                      { return n.ExtraData }

// PlaceholderNotificationService is PlaceholderNotificationService.
type PlaceholderNotificationService struct{}

func (s *PlaceholderNotificationService) SendNotification(ctx context.Context, notification interfaces.INotification) (bool, error) {
	return true, nil
}

func (s *PlaceholderNotificationService) SendBulkNotifications(ctx context.Context, notifications []interfaces.INotification) ([]bool, error) {
	results := make([]bool, 0, len(notifications))
	for _, notification := range notifications {
		result, _ := s.SendNotification(ctx, notification)
		results = append(results, result)
	}
	return results, nil
}

func (s *PlaceholderNotificationService) ScheduleNotification(ctx context.Context, notification interfaces.INotification, delaySeconds int) (string, error) {
	return "scheduled_" + value_objects.PyStr(float64(time.Now().UnixNano())/1e9), nil
}

func (s *PlaceholderNotificationService) CancelNotification(ctx context.Context, notificationID string) (bool, error) {
	return true, nil
}

func (s *PlaceholderNotificationService) CreateNotification(notificationType interfaces.NotificationType, recipient, message string, metadata map[string]any) interfaces.INotification {
	return NewPlaceholderNotification(notificationType, recipient, message, metadata)
}

// PlaceholderEventBus is PlaceholderEventBus.
type PlaceholderEventBus struct {
	handlers map[string][]interfaces.IEventHandler
	running  bool
}

// NewPlaceholderEventBus mirrors PlaceholderEventBus.__init__.
func NewPlaceholderEventBus() *PlaceholderEventBus {
	return &PlaceholderEventBus{handlers: map[string][]interfaces.IEventHandler{}}
}

func (b *PlaceholderEventBus) Publish(ctx context.Context, event interfaces.IEvent) error {
	for _, handler := range b.handlers[event.EventType()] {
		// Python catches every handler error and prints it.
		_ = handler.Handle(ctx, event)
	}
	return nil
}

func (b *PlaceholderEventBus) PublishMany(ctx context.Context, events []interfaces.IEvent) error {
	for _, event := range events {
		_ = b.Publish(ctx, event)
	}
	return nil
}

func (b *PlaceholderEventBus) Subscribe(eventType string, handler interfaces.IEventHandler) {
	b.handlers[eventType] = append(b.handlers[eventType], handler)
}

func (b *PlaceholderEventBus) Unsubscribe(eventType string, handler interfaces.IEventHandler) {
	existing := b.handlers[eventType]
	for i, candidate := range existing {
		if candidate == handler {
			b.handlers[eventType] = append(existing[:i:i], existing[i+1:]...)
			return
		}
	}
}

func (b *PlaceholderEventBus) SubscribeToAll(handler interfaces.IEventHandler) {
	for _, eventType := range handler.EventTypes() {
		b.Subscribe(eventType, handler)
	}
}

func (b *PlaceholderEventBus) GetHandlers(eventType string) []interfaces.IEventHandler {
	return b.handlers[eventType]
}

func (b *PlaceholderEventBus) Start(ctx context.Context) error { b.running = true; return nil }
func (b *PlaceholderEventBus) Stop(ctx context.Context) error  { b.running = false; return nil }
func (b *PlaceholderEventBus) IsRunning() bool                 { return b.running }

// PlaceholderLogger is PlaceholderLogger.
type PlaceholderLogger struct {
	Name string
}

func (l *PlaceholderLogger) Debug(message string, fields map[string]any)    {}
func (l *PlaceholderLogger) Info(message string, fields map[string]any)     {}
func (l *PlaceholderLogger) Warning(message string, fields map[string]any)  {}
func (l *PlaceholderLogger) Error(message string, fields map[string]any)    {}
func (l *PlaceholderLogger) Critical(message string, fields map[string]any) {}

func (l *PlaceholderLogger) Log(level interfaces.LogLevel, message string, fields map[string]any) {
	switch level {
	case interfaces.LogLevelDebug:
		l.Debug(message, fields)
	case interfaces.LogLevelInfo:
		l.Info(message, fields)
	case interfaces.LogLevelWarning:
		l.Warning(message, fields)
	case interfaces.LogLevelError:
		l.Error(message, fields)
	case interfaces.LogLevelCritical:
		l.Critical(message, fields)
	}
}

// PlaceholderLoggingService is PlaceholderLoggingService.
type PlaceholderLoggingService struct{}

func (s *PlaceholderLoggingService) GetLogger(name string) interfaces.ILogger {
	return &PlaceholderLogger{Name: name}
}

func (s *PlaceholderLoggingService) Configure(config map[string]any) error { return nil }

func (s *PlaceholderLoggingService) SetLevel(level interfaces.LogLevel) {}

func (s *PlaceholderLoggingService) AddHandler(handlerConfig map[string]any) error { return nil }

func (s *PlaceholderLoggingService) RemoveHandler(handlerName string) error { return nil }

// PlaceholderMetric is PlaceholderMetric.
type PlaceholderMetric struct {
	MetricName string
	Val        float64
	TS         time.Time
	Lbls       map[string]string
}

// NewPlaceholderMetric mirrors PlaceholderMetric.__init__ (labels None -> {}).
func NewPlaceholderMetric(name string, value float64, labels map[string]string) *PlaceholderMetric {
	if labels == nil {
		labels = map[string]string{}
	}
	return &PlaceholderMetric{MetricName: name, Val: value, TS: time.Now(), Lbls: labels}
}

func (m *PlaceholderMetric) Name() string              { return m.MetricName }
func (m *PlaceholderMetric) Value() float64            { return m.Val }
func (m *PlaceholderMetric) Timestamp() time.Time      { return m.TS }
func (m *PlaceholderMetric) Labels() map[string]string { return m.Lbls }

// PlaceholderMonitoringService is PlaceholderMonitoringService.
type PlaceholderMonitoringService struct{}

func (s *PlaceholderMonitoringService) RecordMetric(name string, value float64, metricType interfaces.MetricType, labels map[string]string) {
}
func (s *PlaceholderMonitoringService) IncrementCounter(name string, labels map[string]string) {}
func (s *PlaceholderMonitoringService) RecordTimer(name string, duration time.Duration, labels map[string]string) {
}
func (s *PlaceholderMonitoringService) GetMetrics(namePattern *string) []interfaces.IMetric {
	return []interfaces.IMetric{}
}

func (s *PlaceholderMonitoringService) GetHealthStatus() map[string]any {
	return map[string]any{"status": "healthy", "timestamp": value_objects.IsoFormat(time.Now())}
}

func (s *PlaceholderMonitoringService) CreateAlert(name, condition string, threshold float64) string {
	return "alert_" + value_objects.PyStr(float64(time.Now().UnixNano())/1e9)
}

func (s *PlaceholderMonitoringService) RemoveAlert(alertID string) bool { return true }

// PlaceholderProcessMonitor is PlaceholderProcessMonitor.
type PlaceholderProcessMonitor struct{}

func (s *PlaceholderProcessMonitor) StartMonitoring(processName string) (string, error) {
	return "monitor_" + processName + "_" + value_objects.PyStr(int64(time.Now().Unix())), nil
}

func (s *PlaceholderProcessMonitor) StopMonitoring(monitorID string) (bool, error) { return true, nil }

func (s *PlaceholderProcessMonitor) GetProcessMetrics(processName string) (map[string]any, error) {
	return map[string]any{"cpu": 0.0, "memory": 0.0, "threads": 1}, nil
}

func (s *PlaceholderProcessMonitor) IsProcessRunning(processName string) (bool, error) {
	return true, nil
}

func (s *PlaceholderProcessMonitor) GetResourceUsage(processName string) (map[string]float64, error) {
	return map[string]float64{"cpu_percent": 0.0, "memory_mb": 0.0}, nil
}

// PlaceholderValidationResult is PlaceholderValidationResult.
type PlaceholderValidationResult struct {
	Valid bool
	Errs  []string
	Warns []string
}

// NewPlaceholderValidationResult mirrors PlaceholderValidationResult.__init__ defaults.
func NewPlaceholderValidationResult(isValid bool, errors, warnings []string) *PlaceholderValidationResult {
	if errors == nil {
		errors = []string{}
	}
	if warnings == nil {
		warnings = []string{}
	}
	return &PlaceholderValidationResult{Valid: isValid, Errs: errors, Warns: warnings}
}

func (r *PlaceholderValidationResult) IsValid() bool      { return r.Valid }
func (r *PlaceholderValidationResult) Errors() []string   { return r.Errs }
func (r *PlaceholderValidationResult) Warnings() []string { return r.Warns }

func (r *PlaceholderValidationResult) Details() map[string]any {
	return map[string]any{
		"valid":         r.Valid,
		"error_count":   len(r.Errs),
		"warning_count": len(r.Warns),
	}
}

// PlaceholderValidationService is PlaceholderValidationService.
type PlaceholderValidationService struct {
	validators map[string]interfaces.IValidator
}

// NewPlaceholderValidationService mirrors PlaceholderValidationService.__init__ ({}, not None).
func NewPlaceholderValidationService() *PlaceholderValidationService {
	return &PlaceholderValidationService{validators: map[string]interfaces.IValidator{}}
}

func (s *PlaceholderValidationService) RegisterValidator(dataType string, validator interfaces.IValidator) {
	s.validators[dataType] = validator
}

func (s *PlaceholderValidationService) UnregisterValidator(dataType string) bool {
	if _, ok := s.validators[dataType]; !ok {
		return false
	}
	delete(s.validators, dataType)
	return true
}

func (s *PlaceholderValidationService) Validate(dataType string, data any) interfaces.IValidationResult {
	if validator, ok := s.validators[dataType]; ok {
		return validator.Validate(data)
	}
	return NewPlaceholderValidationResult(true, nil, nil)
}

func (s *PlaceholderValidationService) ValidateAll(data map[string]any) map[string]interfaces.IValidationResult {
	results := map[string]interfaces.IValidationResult{}
	for key, value := range data {
		results[key] = s.Validate(key, value)
	}
	return results
}

func (s *PlaceholderValidationService) GetValidator(dataType string) interfaces.IValidator {
	return s.validators[dataType]
}

func (s *PlaceholderValidationService) ListValidators() []string {
	names := make([]string, 0, len(s.validators))
	for name := range s.validators {
		names = append(names, name)
	}
	return names
}

// PlaceholderDocumentValidator is PlaceholderDocumentValidator.
type PlaceholderDocumentValidator struct{}

func (v *PlaceholderDocumentValidator) ValidateDocument(document map[string]any) interfaces.IValidationResult {
	return NewPlaceholderValidationResult(true, nil, nil)
}

func (v *PlaceholderDocumentValidator) ValidateSchema(document, schema map[string]any) interfaces.IValidationResult {
	return NewPlaceholderValidationResult(true, nil, nil)
}

func (v *PlaceholderDocumentValidator) GetSchema(documentType string) map[string]any { return nil }

// PlaceholderPathResolver is PlaceholderPathResolver (Python Path values are strings).
type PlaceholderPathResolver struct{}

func absPath(path string) string {
	resolved, err := filepath.Abs(path)
	if err != nil {
		return path
	}
	return resolved
}

func (r *PlaceholderPathResolver) ResolvePath(path string) string { return absPath(path) }

func (r *PlaceholderPathResolver) ResolveRelative(path, base string) string {
	return absPath(filepath.Join(base, path))
}

func (r *PlaceholderPathResolver) NormalizePath(path string) string { return absPath(path) }

func (r *PlaceholderPathResolver) PathExists(path string) bool {
	// Python Path.exists() is False for a dangling symlink; os.Stat follows symlinks.
	if _, err := os.Lstat(path); err != nil {
		return false
	}
	_, err := os.Stat(path)
	return err == nil
}

func (r *PlaceholderPathResolver) IsDirectory(path string) bool {
	info, err := os.Stat(path)
	return err == nil && info.IsDir()
}

func (r *PlaceholderPathResolver) IsFile(path string) bool {
	info, err := os.Stat(path)
	return err == nil && info.Mode().IsRegular()
}

func (r *PlaceholderPathResolver) GetParentDirectory(path string) string { return filepath.Dir(path) }

func (r *PlaceholderPathResolver) JoinPaths(paths ...string) string { return filepath.Join(paths...) }
