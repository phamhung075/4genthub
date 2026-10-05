package interfaces

// LogLevel is the log level enumeration.
type LogLevel string

const (
	LogLevelDebug    LogLevel = "debug"
	LogLevelInfo     LogLevel = "info"
	LogLevelWarning  LogLevel = "warning"
	LogLevelError    LogLevel = "error"
	LogLevelCritical LogLevel = "critical"
)

// LogLevelValues lists the levels in declaration order.
var LogLevelValues = []LogLevel{LogLevelDebug, LogLevelInfo, LogLevelWarning, LogLevelError, LogLevelCritical}

// ILogger is the logger contract; fields carry Python's **kwargs.
type ILogger interface {
	Debug(message string, fields map[string]any)
	Info(message string, fields map[string]any)
	Warning(message string, fields map[string]any)
	Error(message string, fields map[string]any)
	Critical(message string, fields map[string]any)
	Log(level LogLevel, message string, fields map[string]any)
}

// ILoggingService configures loggers and handlers.
type ILoggingService interface {
	GetLogger(name string) ILogger
	Configure(config map[string]any) error
	SetLevel(level LogLevel)
	AddHandler(handlerConfig map[string]any) error
	RemoveHandler(handlerName string) error
}
