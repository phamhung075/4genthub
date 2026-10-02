// Package logging provides centralized logging configuration for the task management system.
package logging

import (
	"context"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

var (
	configMu   sync.Mutex
	configured bool
	loggers    = make(map[string]*slog.Logger)
	rootLogger *slog.Logger
)

// LogContext holds optional structured context fields.
type LogContext struct {
	UserID    string
	TaskID    string
	ProjectID string
	Operation string
	ErrorCode string
}

// JSONLogRecord represents structured JSON logging output.
type JSONLogRecord struct {
	Timestamp string `json:"timestamp"`
	Level     string `json:"level"`
	Logger    string `json:"logger"`
	Message   string `json:"message"`
	Module    string `json:"module,omitempty"`
	Function  string `json:"function,omitempty"`
	Line      int    `json:"line,omitempty"`
	UserID    string `json:"user_id,omitempty"`
	TaskID    string `json:"task_id,omitempty"`
	ProjectID string `json:"project_id,omitempty"`
	Operation string `json:"operation,omitempty"`
	ErrorCode string `json:"error_code,omitempty"`
	Exception string `json:"exception,omitempty"`
}

// ConfigOptions holds logging configuration parameters.
type ConfigOptions struct {
	LogLevel      string
	LogDir        string
	EnableConsole bool
	EnableFile    bool
	EnableJSON    bool
	MaxBytes      int64
	BackupCount   int
}

// TaskManagementLogger manages centralized logger configuration.
type TaskManagementLogger struct{}

// Configure configures the logging system.
func (TaskManagementLogger) Configure(opts ConfigOptions) {
	configMu.Lock()
	defer configMu.Unlock()

	if configured {
		return
	}

	logLevel := slog.LevelInfo
	switch strings.ToUpper(opts.LogLevel) {
	case "DEBUG":
		logLevel = slog.LevelDebug
	case "INFO":
		logLevel = slog.LevelInfo
	case "WARN", "WARNING":
		logLevel = slog.LevelWarn
	case "ERROR", "CRITICAL", "FATAL":
		logLevel = slog.LevelError
	}

	var writers []io.Writer
	if opts.EnableConsole {
		writers = append(writers, os.Stdout)
	}

	if opts.EnableFile && opts.LogDir != "" {
		if err := os.MkdirAll(opts.LogDir, 0o755); err == nil {
			logFilePath := filepath.Join(opts.LogDir, "agenthub.log")
			f, err := os.OpenFile(logFilePath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
			if err == nil {
				writers = append(writers, f)
			}
		}
	}

	var w io.Writer
	if len(writers) == 0 {
		w = os.Stdout
	} else if len(writers) == 1 {
		w = writers[0]
	} else {
		w = io.MultiWriter(writers...)
	}

	var handler slog.Handler
	handlerOpts := &slog.HandlerOptions{
		Level: logLevel,
	}
	if opts.EnableJSON {
		handler = slog.NewJSONHandler(w, handlerOpts)
	} else {
		handler = slog.NewTextHandler(w, handlerOpts)
	}

	rootLogger = slog.New(handler)
	slog.SetDefault(rootLogger)
	configured = true
}

// Reset clears the configured state (mainly for testing).
func (TaskManagementLogger) Reset() {
	configMu.Lock()
	defer configMu.Unlock()
	configured = false
	loggers = make(map[string]*slog.Logger)
	rootLogger = nil
}

// GetLogger returns a logger instance with the given name.
func (TaskManagementLogger) GetLogger(name string) *slog.Logger {
	configMu.Lock()
	defer configMu.Unlock()

	if !configured {
		// Default configuration
		logLevel := os.Getenv("LOG_LEVEL")
		if logLevel == "" {
			logLevel = "INFO"
		}
		opts := ConfigOptions{
			LogLevel:      logLevel,
			EnableConsole: true,
			EnableJSON:    strings.ToLower(os.Getenv("LOG_FORMAT")) == "json",
		}
		configMu.Unlock()
		TaskManagementLogger{}.Configure(opts)
		configMu.Lock()
	}

	if l, exists := loggers[name]; exists {
		return l
	}

	l := rootLogger.With("logger", name)
	loggers[name] = l
	return l
}

// AddContext adds contextual fields to the logger.
func (TaskManagementLogger) AddContext(logger *slog.Logger, ctx LogContext) *slog.Logger {
	if logger == nil {
		logger = slog.Default()
	}
	var attrs []any
	if ctx.UserID != "" {
		attrs = append(attrs, "user_id", ctx.UserID)
	}
	if ctx.TaskID != "" {
		attrs = append(attrs, "task_id", ctx.TaskID)
	}
	if ctx.ProjectID != "" {
		attrs = append(attrs, "project_id", ctx.ProjectID)
	}
	if ctx.Operation != "" {
		attrs = append(attrs, "operation", ctx.Operation)
	}
	if ctx.ErrorCode != "" {
		attrs = append(attrs, "error_code", ctx.ErrorCode)
	}
	if len(attrs) == 0 {
		return logger
	}
	return logger.With(attrs...)
}

// LogOperation runs fn wrapped with start, completion, and error timing logs.
func LogOperation[T any](ctx context.Context, logger *slog.Logger, operation string, logCtx LogContext, fn func() (T, error)) (T, error) {
	if logger == nil {
		logger = slog.Default()
	}
	logCtx.Operation = operation
	ctxLogger := TaskManagementLogger{}.AddContext(logger, logCtx)

	ctxLogger.Info("Starting " + operation)
	startTime := time.Now()

	result, err := fn()
	duration := time.Since(startTime).Seconds()

	if err != nil {
		ctxLogger.Error(fmt.Sprintf("Failed %s after %.3fs: %v", operation, duration, err))
		return result, err
	}

	ctxLogger.Info(fmt.Sprintf("Completed %s in %.3fs", operation, duration))
	return result, nil
}

// InitLogging initializes logging with environment-based configuration.
func InitLogging() {
	logLevel := os.Getenv("LOG_LEVEL")
	if logLevel == "" {
		logLevel = "INFO"
	}
	logDir := os.Getenv("LOG_DIR")
	enableJSON := strings.ToLower(os.Getenv("LOG_FORMAT")) == "json"

	TaskManagementLogger{}.Configure(ConfigOptions{
		LogLevel:      logLevel,
		LogDir:        logDir,
		EnableConsole: true,
		EnableFile:    logDir != "",
		EnableJSON:    enableJSON,
		MaxBytes:      10 * 1024 * 1024,
		BackupCount:   5,
	})
}
