package infrastructure

import (
	"bytes"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

func TestLoggingLevelMapping(t *testing.T) {
	cases := map[string]slog.Level{
		"DEBUG": slog.LevelDebug, "info": slog.LevelInfo, "Warning": slog.LevelWarn,
		"ERROR": slog.LevelError, "CRITICAL": slog.LevelError, "nonsense": slog.LevelWarn,
	}
	for name, want := range cases {
		if got := loggingLevel(name); got != want {
			t.Errorf("loggingLevel(%q) = %v, want %v", name, got, want)
		}
	}
}

func TestRotatorRollover(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "backend.log")
	rot, err := newRotator(path, 10, 2)
	if err != nil {
		t.Fatal(err)
	}
	defer rot.Close()

	// size 0 + 5 < 10 -> no roll.
	if _, err := rot.Write([]byte("12345")); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(path + ".1"); !os.IsNotExist(err) {
		t.Fatalf("unexpected rollover: %v", err)
	}
	// size 5 + 5 >= 10 -> roll before writing.
	if _, err := rot.Write([]byte("67890")); err != nil {
		t.Fatal(err)
	}
	first, err := os.ReadFile(path + ".1")
	if err != nil {
		t.Fatalf("backup .1: %v", err)
	}
	if string(first) != "12345" {
		t.Fatalf("backup .1 content = %q", first)
	}
	cur, _ := os.ReadFile(path)
	if string(cur) != "67890" {
		t.Fatalf("current content = %q", cur)
	}
	// Another roll shifts .1 -> .2 and .2 is dropped after backupCount=2.
	rot.Write([]byte("abcde"))
	if _, err := rot.Write([]byte("FGHIJ")); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(path + ".3"); !os.IsNotExist(err) {
		t.Fatalf("backup .3 should not exist: %v", err)
	}
	two, err := os.ReadFile(path + ".2")
	if err != nil {
		t.Fatalf("backup .2: %v", err)
	}
	if string(two) != "67890" {
		t.Fatalf("backup .2 content = %q", two)
	}
}

func TestLogHandlerFormat(t *testing.T) {
	var console bytes.Buffer
	h := &logHandler{mu: new(sync.Mutex), console: &console}
	logLevelVar.Set(slog.LevelDebug)
	defer logLevelVar.Set(slog.LevelInfo)
	rec := slog.NewRecord(time.Now(), slog.LevelInfo, "hello", 0)
	rec.AddAttrs(slog.String(logNameKey, "my.logger"))
	if err := h.Handle(nil, rec); err != nil {
		t.Fatal(err)
	}
	line := console.String()
	if !strings.HasPrefix(line, "[") {
		t.Fatalf("line missing backend id: %q", line)
	}
	if !strings.HasSuffix(line, "my.logger - INFO - hello\n") {
		t.Fatalf("line = %q", line)
	}
}

func TestInitLoggingWritesFileAndStdout(t *testing.T) {
	dir := t.TempDir()
	logPath := filepath.Join(dir, "backend.log")

	oldStdout := os.Stdout
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	os.Stdout = w
	done := make(chan string, 1)
	go func() {
		var b bytes.Buffer
		_, _ = io.Copy(&b, r)
		done <- b.String()
	}()

	if err := InitLogging(&logPath, "DEBUG", 10*1024*1024, 5); err != nil {
		t.Fatal(err)
	}
	os.Stdout = oldStdout
	w.Close()
	stdout := <-done

	data, err := os.ReadFile(logPath)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), "Backend logging initialized - ID: backend_") {
		t.Fatalf("file content = %q", data)
	}
	if !strings.Contains(string(data), "Log level: DEBUG") {
		t.Fatalf("missing level line: %q", data)
	}
	if !strings.Contains(stdout, "Backend logging initialized") {
		t.Fatalf("stdout content = %q", stdout)
	}
}
