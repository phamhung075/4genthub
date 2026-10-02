// Enhanced logging configuration for unified log management
// (unified_logging.py).
package infrastructure

import (
	"context"
	"fmt"
	"io"
	"log/slog"
	"os"
	"strings"
	"sync"
	"time"
)

// logNameKey is the slog attribute carrying the Python logger name.
const logNameKey = "logger"

var (
	logMu       sync.Mutex
	logLevelVar = new(slog.LevelVar)
	logBackend  string
)

// get_logging_level maps a logging level name (case-insensitive) to a slog level. An
// unknown name is WARNING, like getattr(logging, name) raising AttributeError.
func loggingLevel(name string) slog.Level {
	switch strings.ToUpper(name) {
	case "DEBUG":
		return slog.LevelDebug
	case "INFO":
		return slog.LevelInfo
	case "WARNING":
		return slog.LevelWarn
	case "ERROR", "CRITICAL", "FATAL":
		return slog.LevelError
	default:
		return slog.LevelWarn
	}
}

func nowAsctime() string { return time.Now().Format("2006-01-02 15:04:05") }

// rotator implements logging.handlers.RotatingFileHandler for a single file: it rolls
// over before every write whose size would reach maxBytes.
type rotator struct {
	path     string
	maxBytes int
	backups  int

	f *os.File
}

func newRotator(path string, maxBytes, backups int) (*rotator, error) {
	r := &rotator{path: path, maxBytes: maxBytes, backups: backups}
	if err := r.open(); err != nil {
		return nil, err
	}
	return r, nil
}

func (r *rotator) open() error {
	f, err := os.OpenFile(r.path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o666)
	if err != nil {
		return err
	}
	r.f = f
	return nil
}

func (r *rotator) currentSize() int64 {
	if r.f == nil {
		return 0
	}
	if fi, err := r.f.Stat(); err == nil {
		return fi.Size()
	}
	return 0
}

// rotateIfNeeded mirrors RotatingFileHandler.shouldRollover + doRollover: the file is
// rolled when the current size plus the message length is greater than or equal to
// maxBytes.
func (r *rotator) rotateIfNeeded(msgLen int) error {
	if r.maxBytes <= 0 || r.currentSize()+int64(msgLen) < int64(r.maxBytes) {
		return nil
	}
	if r.f != nil {
		r.f.Close()
		r.f = nil
	}
	if r.backups > 0 {
		for i := r.backups - 1; i >= 1; i-- {
			os.Rename(r.backupName(i), r.backupName(i+1))
		}
		os.Rename(r.path, r.backupName(1))
	} else {
		os.Remove(r.path)
	}
	return r.open()
}

func (r *rotator) backupName(i int) string { return fmt.Sprintf("%s.%d", r.path, i) }

func (r *rotator) Write(p []byte) (int, error) {
	if err := r.rotateIfNeeded(len(p)); err != nil {
		return 0, err
	}
	return r.f.Write(p)
}

func (r *rotator) Close() error {
	if r.f == nil {
		return nil
	}
	return r.f.Close()
}

// logHandler writes Python-formatted records to a rotating file and to stdout. The mutex
// is shared by value copies produced by WithAttrs, so no lock is ever copied.
type logHandler struct {
	mu      *sync.Mutex
	rot     *rotator
	console io.Writer
	attrs   []slog.Attr
}

func (h *logHandler) Enabled(_ context.Context, l slog.Level) bool { return l >= logLevelVar.Level() }

func (h *logHandler) Handle(_ context.Context, rec slog.Record) error {
	name := ""
	rec.Attrs(func(a slog.Attr) bool {
		if a.Key == logNameKey {
			name = a.Value.String()
			return false
		}
		return true
	})
	if name == "" {
		name = "root"
	}
	line := fmt.Sprintf("[%s] %s - %s - %s - %s\n",
		logBackend, nowAsctime(), name, strings.ToUpper(rec.Level.String()), rec.Message)
	h.mu.Lock()
	defer h.mu.Unlock()
	if h.console != nil {
		_, _ = h.console.Write([]byte(line))
	}
	if h.rot != nil {
		_, _ = h.rot.Write([]byte(line))
	}
	return nil
}

func (h *logHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
	next := *h
	next.attrs = append(append([]slog.Attr{}, h.attrs...), attrs...)
	return &next
}

// WithGroup is a no-op: Python logging has no group equivalent.
func (h *logHandler) WithGroup(string) slog.Handler { return h }

// GetProjectRoot is unified_logging.get_project_root.
func GetProjectRoot() string {
	if _, err := os.Stat("/app"); err == nil {
		return "/app"
	}
	exe, err := os.Executable()
	if err != nil {
		return "."
	}
	// Navigate up from agenthub_main/src/fastmcp/task_management/infrastructure/.
	cur := exe
	for i := 0; i < 5; i++ {
		cur = dirOf(cur)
	}
	return cur
}

func dirOf(p string) string {
	i := strings.LastIndex(p, "/")
	if i < 0 {
		return "."
	}
	if i == 0 {
		return "/"
	}
	return p[:i]
}

// InitLogging is unified_logging.init_logging. It configures the process logger with a
// rotating backend.log and a stdout handler.
func InitLogging(backendLogPath *string, logLevel string, maxBytes, backupCount int) error {
	projectRoot := GetProjectRoot()
	logsDir := projectRoot + "/logs"
	if err := os.MkdirAll(logsDir, 0o777); err != nil {
		logsDir = "/tmp/agenthub_logs"
		if mkErr := os.MkdirAll(logsDir, 0o777); mkErr != nil {
			return mkErr
		}
	}

	backend := logsDir + "/backend.log"
	if backendLogPath != nil {
		backend = *backendLogPath
	}

	logMu.Lock()
	defer logMu.Unlock()

	now := time.Now()
	timestamp := now.Format("20060102_150405") + fmt.Sprintf("_%06d", now.Nanosecond()/1000)
	logBackend = "backend_" + timestamp
	logLevelVar.Set(loggingLevel(logLevel))

	rot, err := newRotator(backend, maxBytes, backupCount)
	if err != nil {
		return err
	}
	slog.SetDefault(slog.New(&logHandler{mu: new(sync.Mutex), rot: rot, console: os.Stdout}))

	logger := GetLogger("root")
	logger.Info("Backend logging initialized - ID: " + logBackend)
	logger.Info("Log file: " + backend)
	logger.Info("Log level: " + logLevel)
	return nil
}

// GetLogger is unified_logging.get_logger: it returns a logger tagged with name.
func GetLogger(name string) *slog.Logger {
	return slog.Default().With(logNameKey, name)
}
