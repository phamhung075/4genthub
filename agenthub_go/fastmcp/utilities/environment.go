package utilities

import (
	"fmt"
	"os"
	"runtime"
	"strings"
	"syscall"
	"unicode"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Environment types (Python Literal["docker", "local"]).
const (
	EnvironmentDocker = "docker"
	EnvironmentLocal  = "local"
)

// DetectEnvironment mirrors environment.detect_environment. All four indicators are
// evaluated before any(), like the Python list construction.
func DetectEnvironment() string {
	indicators := []bool{
		pathExists("/.dockerenv"),
		hasDockerCgroups(),
		os.Getenv("CONTAINER_ENV") == EnvironmentDocker,
		isContainerHostname(),
	}
	for _, ok := range indicators {
		if ok {
			return EnvironmentDocker
		}
	}
	return EnvironmentLocal
}

// hasDockerCgroups mirrors _has_docker_cgroups.
func hasDockerCgroups() bool {
	data, err := os.ReadFile("/proc/1/cgroup")
	if err != nil {
		return false
	}
	s := string(data)
	return strings.Contains(s, "docker") || strings.Contains(s, "containerd")
}

// isContainerHostname mirrors _is_container_hostname: a 12-character lowercase hostname.
func isContainerHostname() bool {
	hostname, err := os.Hostname()
	if err != nil {
		return false
	}
	return utf8.RuneCountInString(hostname) == 12 && pyIsLower(hostname)
}

// pyIsLower mirrors str.islower: at least one cased character, none uppercase/titlecase.
func pyIsLower(s string) bool {
	hasCased := false
	for _, r := range s {
		if unicode.IsUpper(r) || unicode.IsTitle(r) || unicode.Is(unicode.Other_Uppercase, r) {
			return false
		}
		if unicode.IsLower(r) || unicode.Is(unicode.Other_Lowercase, r) {
			hasCased = true
		}
	}
	return hasCased
}

func pathExists(p string) bool {
	_, err := os.Stat(p)
	return err == nil
}

// withParents is [current] + list(current.parents).
func withParents(current string) []string {
	out := []string{current}
	for p := current; PyParent(p) != p; {
		p = PyParent(p)
		out = append(out, p)
	}
	return out
}

// GetLogDirectory mirrors get_log_directory. environment "" means None (auto-detect).
func GetLogDirectory(environment string) string {
	if environment == "" {
		environment = DetectEnvironment()
	}
	if environment == EnvironmentDocker {
		return "/data/logs"
	}
	current, _ := os.Getwd()
	current = PyPath(current)
	for _, parent := range withParents(current) {
		if pathExists(PyJoin(parent, ".git")) {
			return PyJoin(parent, "logs")
		}
	}
	for _, parent := range withParents(current) {
		for _, indicator := range []string{"pyproject.toml", "CLAUDE.md", "docker-system"} {
			if pathExists(PyJoin(parent, indicator)) {
				return PyJoin(parent, "logs")
			}
		}
	}
	return PyJoin(current, "logs")
}

// EnsureLogDirectoryExists mirrors ensure_log_directory_exists. logDir nil means None.
func EnsureLogDirectoryExists(logDir *string) (string, error) {
	dir := ""
	if logDir == nil {
		dir = GetLogDirectory("")
	} else {
		dir = *logDir
	}
	if err := os.MkdirAll(dir, 0o777); err != nil {
		return "", fmt.Errorf("Log directory %s is not writable: %s", dir, err)
	}
	testFile := PyJoin(dir, ".write_test")
	f, err := os.OpenFile(testFile, os.O_CREATE|os.O_WRONLY, 0o666)
	if err != nil {
		return "", fmt.Errorf("Log directory %s is not writable: %s", dir, err)
	}
	f.Close()
	if err := os.Remove(testFile); err != nil {
		return "", fmt.Errorf("Log directory %s is not writable: %s", dir, err)
	}
	return dir, nil
}

// GetLogFilePath mirrors get_log_file_path. logDir nil means None.
func GetLogFilePath(filename string, logDir *string) (string, error) {
	dir := ""
	if logDir == nil {
		var err error
		dir, err = EnsureLogDirectoryExists(nil)
		if err != nil {
			return "", err
		}
	} else {
		dir = *logDir
	}
	return PyJoin(dir, filename), nil
}

// GetEnvironmentInfo mirrors get_environment_info. Python-specific values that have no
// Go equivalent use runtime information (see the module report).
func GetEnvironmentInfo() *entities.OrderedMap[any] {
	envType := DetectEnvironment()
	logDir := GetLogDirectory("")

	out := entities.NewOrderedMap[any]()
	out.Set("environment_type", envType)
	out.Set("log_directory", logDir)
	exists := pathExists(logDir)
	out.Set("log_directory_exists", exists)
	writable := false
	if exists {
		if info, err := os.Stat(logDir); err == nil && info.IsDir() {
			writable = syscall.Access(logDir, 2) == nil // 2 = os.W_OK
		}
	}
	out.Set("log_directory_writable", writable)
	out.Set("platform", runtime.GOOS+"-"+runtime.GOARCH)
	hostname, _ := os.Hostname()
	out.Set("hostname", hostname)
	out.Set("python_version", runtime.Version())
	cwd, _ := os.Getwd()
	out.Set("cwd", cwd)
	out.Set("docker_env_exists", pathExists("/.dockerenv"))
	if v, ok := os.LookupEnv("CONTAINER_ENV"); ok {
		out.Set("container_env_var", v)
	} else {
		out.Set("container_env_var", nil)
	}

	relevant := entities.NewOrderedMap[any]()
	for _, kv := range os.Environ() {
		i := strings.IndexByte(kv, '=')
		if i < 0 {
			continue
		}
		key, value := kv[:i], kv[i+1:]
		lower := value_objects.PyLower(key)
		for _, keyword := range []string{"docker", "container", "log"} {
			if strings.Contains(lower, keyword) {
				relevant.Set(key, value)
				break
			}
		}
	}
	out.Set("relevant_env_vars", relevant)
	return out
}
