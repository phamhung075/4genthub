package logging

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestTaskManagementLoggerConfigureAndGet(t *testing.T) {
	mgr := TaskManagementLogger{}
	mgr.Reset()

	tempDir, err := os.MkdirTemp("", "logging_test_*")
	if err != nil {
		t.Fatalf("failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	mgr.Configure(ConfigOptions{
		LogLevel:      "DEBUG",
		LogDir:        tempDir,
		EnableConsole: false,
		EnableFile:    true,
		EnableJSON:    true,
	})

	log := mgr.GetLogger("test.logger")
	if log == nil {
		t.Fatal("expected non-nil logger")
	}

	ctxLog := mgr.AddContext(log, LogContext{
		UserID:    "u1",
		TaskID:    "t1",
		Operation: "test_op",
	})
	ctxLog.Info("test message")

	// Verify log file was written
	logPath := filepath.Join(tempDir, "agenthub.log")
	data, err := os.ReadFile(logPath)
	if err != nil {
		t.Fatalf("failed to read log file: %v", err)
	}
	if !bytes.Contains(data, []byte("test message")) {
		t.Fatalf("expected log file to contain 'test message', got: %s", string(data))
	}
}

func TestLogOperation(t *testing.T) {
	mgr := TaskManagementLogger{}
	mgr.Reset()

	log := mgr.GetLogger("op.logger")

	// Success case
	res, err := LogOperation(context.Background(), log, "sample_task", LogContext{}, func() (string, error) {
		return "ok", nil
	})
	if err != nil || res != "ok" {
		t.Fatalf("unexpected result: res=%v, err=%v", res, err)
	}

	// Failure case
	expectedErr := errors.New("boom")
	_, err = LogOperation(context.Background(), log, "fail_task", LogContext{}, func() (string, error) {
		return "", expectedErr
	})
	if !errors.Is(err, expectedErr) {
		t.Fatalf("expected boom error, got %v", err)
	}
}
