package utilities

import (
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestGetLogDirectoryDocker(t *testing.T) {
	if got := GetLogDirectory(EnvironmentDocker); got != "/data/logs" {
		t.Fatalf("docker log dir = %q", got)
	}
}

func TestEnsureLogDirectoryExistsCreatesAndCleans(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "nested", "logs")
	got, err := EnsureLogDirectoryExists(&dir)
	if err != nil {
		t.Fatalf("EnsureLogDirectoryExists: %v", err)
	}
	if got != dir {
		t.Fatalf("dir = %q, want %q", got, dir)
	}
	if _, err := os.Stat(dir); err != nil {
		t.Fatalf("directory not created: %v", err)
	}
	if _, err := os.Stat(filepath.Join(dir, ".write_test")); !os.IsNotExist(err) {
		t.Fatalf(".write_test should be removed, stat err = %v", err)
	}
}

func TestGetLogFilePath(t *testing.T) {
	dir := t.TempDir()
	got, err := GetLogFilePath("agenthub.log", &dir)
	if err != nil {
		t.Fatalf("GetLogFilePath: %v", err)
	}
	want := filepath.Join(dir, "agenthub.log")
	if got != want {
		t.Fatalf("path = %q, want %q", got, want)
	}
}

func TestGetEnvironmentInfoShape(t *testing.T) {
	t.Setenv("CONTAINER_ENV", "docker")
	t.Setenv("MY_LOG_SETTING", "yes")
	info := GetEnvironmentInfo()
	wantKeys := []string{
		"environment_type", "log_directory", "log_directory_exists", "log_directory_writable",
		"platform", "hostname", "python_version", "cwd", "docker_env_exists",
		"container_env_var", "relevant_env_vars",
	}
	if got := info.Keys(); !reflect.DeepEqual(got, wantKeys) {
		t.Fatalf("keys = %v", got)
	}
	envType, _ := info.Get("environment_type")
	if envType != EnvironmentDocker && envType != EnvironmentLocal {
		t.Fatalf("environment_type = %v", envType)
	}
	containerEnv, _ := info.Get("container_env_var")
	if containerEnv != "docker" {
		t.Fatalf("container_env_var = %v", containerEnv)
	}
	pyVersion, _ := info.Get("python_version")
	if pyVersion != runtime.Version() {
		t.Fatalf("python_version = %v, want %v", pyVersion, runtime.Version())
	}
	relevant, _ := info.Get("relevant_env_vars")
	relevantMap := relevant.(*entities.OrderedMap[any])
	if !relevantMap.Has("MY_LOG_SETTING") {
		t.Fatal("MY_LOG_SETTING should be in relevant_env_vars")
	}
	if relevantMap.Has("PATH") {
		t.Fatal("PATH should not match docker/container/log")
	}
}
