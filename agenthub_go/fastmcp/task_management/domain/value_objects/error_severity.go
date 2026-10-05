package value_objects

// ErrorSeverity levels for prioritizing handling and alerting.
type ErrorSeverity string

const (
	ErrorSeverityLow      ErrorSeverity = "low"      // Can be retried or ignored
	ErrorSeverityMedium   ErrorSeverity = "medium"   // Should be logged and monitored
	ErrorSeverityHigh     ErrorSeverity = "high"     // Requires immediate attention
	ErrorSeverityCritical ErrorSeverity = "critical" // System-breaking, requires immediate action
)
