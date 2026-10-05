package fastmcp

import (
	"fmt"
	"math"
	"os"
	"strconv"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/utilities"
)

// LogLevel is the LOG_LEVEL literal type.
type LogLevel string

const (
	LogLevelDebug    LogLevel = "DEBUG"
	LogLevelInfo     LogLevel = "INFO"
	LogLevelWarning  LogLevel = "WARNING"
	LogLevelError    LogLevel = "ERROR"
	LogLevelCritical LogLevel = "CRITICAL"
)

// DuplicateBehavior is the DuplicateBehavior literal type (defined by the Python module,
// currently unused there).
type DuplicateBehavior string

const (
	DuplicateBehaviorWarn    DuplicateBehavior = "warn"
	DuplicateBehaviorError   DuplicateBehavior = "error"
	DuplicateBehaviorReplace DuplicateBehavior = "replace"
	DuplicateBehaviorIgnore  DuplicateBehavior = "ignore"
)

// SettingsConfig holds the FastMCP settings. The Pydantic BaseSettings machinery and the
// .env file sources are not ported; values come from the injectable getenv with the same
// FASTMCP_ / FASTMCP_SERVER_ prefixes.
type SettingsConfig struct {
	Home                                string
	TestMode                            bool
	LogLevel                            LogLevel
	EnableRichTracebacks                bool
	DeprecationWarnings                 bool
	ClientRaiseFirstExceptiongroupError bool
	ResourcePrefixFormat                string
	ToolAttemptParseJSONArgs            bool
	ClientInitTimeout                   *float64

	Host               string
	Port               int
	SSEPath            string
	MessagePath        string
	StreamableHTTPPath string
	Debug              bool

	MaskErrorDetails   bool
	ServerDependencies []string

	JSONResponse  bool
	StatelessHTTP bool

	DefaultAuthProvider *string

	IncludeTags *entities.StringSet
	ExcludeTags *entities.StringSet

	EnableAsyncEventQueue bool
	EventQueueMaxSize     int
}

// LoadSettings reads the settings through getenv, applying the FASTMCP_ prefix first and
// the deprecated FASTMCP_SERVER_ prefix as a fallback (like ExtendedEnvSettingsSource).
func LoadSettings(getenv func(string) (string, bool)) (*SettingsConfig, error) {
	if getenv == nil {
		getenv = os.LookupEnv
	}
	s := &SettingsConfig{
		Home:                                defaultFastmcpHome(getenv),
		LogLevel:                            LogLevelInfo,
		EnableRichTracebacks:                true,
		DeprecationWarnings:                 true,
		ClientRaiseFirstExceptiongroupError: true,
		ResourcePrefixFormat:                "path",
		Host:                                "127.0.0.1",
		Port:                                8000,
		SSEPath:                             "/sse/",
		MessagePath:                         "/messages/",
		StreamableHTTPPath:                  "/mcp/",
		ServerDependencies:                  []string{},
		EventQueueMaxSize:                   10000,
	}

	if v, ok := settingsLookup(getenv, "home"); ok {
		s.Home = v
	}
	boolFields := []struct {
		name string
		dst  *bool
	}{
		{"test_mode", &s.TestMode},
		{"enable_rich_tracebacks", &s.EnableRichTracebacks},
		{"deprecation_warnings", &s.DeprecationWarnings},
		{"client_raise_first_exceptiongroup_error", &s.ClientRaiseFirstExceptiongroupError},
		{"tool_attempt_parse_json_args", &s.ToolAttemptParseJSONArgs},
		{"debug", &s.Debug},
		{"mask_error_details", &s.MaskErrorDetails},
		{"json_response", &s.JSONResponse},
		{"stateless_http", &s.StatelessHTTP},
		{"enable_async_event_queue", &s.EnableAsyncEventQueue},
	}
	for _, f := range boolFields {
		if v, ok := settingsLookup(getenv, f.name); ok {
			b, err := settingsBool(v)
			if err != nil {
				return nil, err
			}
			*f.dst = b
		}
	}

	if v, ok := settingsLookup(getenv, "log_level"); ok {
		switch LogLevel(v) {
		case LogLevelDebug, LogLevelInfo, LogLevelWarning, LogLevelError, LogLevelCritical:
			s.LogLevel = LogLevel(v)
		default:
			return nil, &tmvo.ValueError{Msg: "Input should be 'DEBUG', 'INFO', 'WARNING', 'ERROR' or 'CRITICAL'"}
		}
	}
	if v, ok := settingsLookup(getenv, "resource_prefix_format"); ok {
		switch v {
		case "protocol", "path":
			s.ResourcePrefixFormat = v
		default:
			return nil, &tmvo.ValueError{Msg: "Input should be 'protocol' or 'path'"}
		}
	}
	if v, ok := settingsLookup(getenv, "host"); ok {
		s.Host = v
	}
	if v, ok := settingsLookup(getenv, "port"); ok {
		n, err := settingsInt(v)
		if err != nil {
			return nil, err
		}
		s.Port = n
	}
	if v, ok := settingsLookup(getenv, "sse_path"); ok {
		s.SSEPath = v
	}
	if v, ok := settingsLookup(getenv, "message_path"); ok {
		s.MessagePath = v
	}
	if v, ok := settingsLookup(getenv, "streamable_http_path"); ok {
		s.StreamableHTTPPath = v
	}
	if v, ok := settingsLookup(getenv, "client_init_timeout"); ok {
		f, err := settingsFloat(v)
		if err != nil {
			return nil, err
		}
		s.ClientInitTimeout = &f
	}
	if v, ok := settingsLookup(getenv, "default_auth_provider"); ok {
		if v != "bearer_env" {
			return nil, &tmvo.ValueError{Msg: "Input should be 'bearer_env'"}
		}
		s.DefaultAuthProvider = &v
	}
	if v, ok := settingsLookup(getenv, "server_dependencies"); ok {
		list, err := settingsStringList(v)
		if err != nil {
			return nil, err
		}
		s.ServerDependencies = list
	}
	if v, ok := settingsLookup(getenv, "include_tags"); ok {
		set, err := settingsStringSet(v)
		if err != nil {
			return nil, err
		}
		s.IncludeTags = set
	}
	if v, ok := settingsLookup(getenv, "exclude_tags"); ok {
		set, err := settingsStringSet(v)
		if err != nil {
			return nil, err
		}
		s.ExcludeTags = set
	}
	if v, ok := settingsLookup(getenv, "event_queue_max_size"); ok {
		n, err := settingsInt(v)
		if err != nil {
			return nil, err
		}
		s.EventQueueMaxSize = n
	}
	return s, nil
}

// settingsLookup tries the FASTMCP_ prefix then the deprecated FASTMCP_SERVER_ prefix,
// accepting an all-uppercase or all-lowercase spelling (Pydantic is case-insensitive).
func settingsLookup(getenv func(string) (string, bool), name string) (string, bool) {
	for _, prefix := range []string{"FASTMCP_", "FASTMCP_SERVER_"} {
		key := prefix + strings.ToUpper(name)
		if v, ok := getenv(key); ok {
			return v, true
		}
		if v, ok := getenv(strings.ToLower(key)); ok {
			return v, true
		}
	}
	return "", false
}

func defaultFastmcpHome(getenv func(string) (string, bool)) string {
	home, ok := getenv("HOME")
	if !ok || home == "" {
		if h, err := os.UserHomeDir(); err == nil {
			home = h
		}
	}
	return utilities.PyJoin(home, ".fastmcp")
}

func settingsBool(v string) (bool, error) {
	switch tmvo.PyLower(v) {
	case "false", "f", "n", "no", "off", "0":
		return false, nil
	case "true", "t", "y", "yes", "on", "1":
		return true, nil
	}
	return false, &tmvo.ValueError{Msg: "Input should be a valid boolean, unable to interpret input"}
}

func settingsInt(v string) (int, error) {
	n, ok := tmvo.PyParseInt(v)
	if !ok || !n.IsInt64() {
		return 0, &tmvo.ValueError{Msg: "Input should be a valid integer, unable to parse string as an integer"}
	}
	return int(n.Int64()), nil
}

func settingsFloat(v string) (float64, error) {
	t := strings.TrimFunc(v, tmvo.PyIsSpace)
	switch tmvo.PyLower(t) {
	case "inf", "+inf", "infinity", "+infinity":
		return math.Inf(1), nil
	case "-inf", "-infinity":
		return math.Inf(-1), nil
	case "nan", "+nan", "-nan":
		return math.NaN(), nil
	}
	f, err := strconv.ParseFloat(strings.ReplaceAll(t, "_", ""), 64)
	if err != nil {
		return 0, &tmvo.ValueError{Msg: "Input should be a valid number, unable to parse string as a number"}
	}
	return f, nil
}

func settingsStringList(v string) ([]string, error) {
	arr, err := settingsJSONArray(v)
	if err != nil {
		return nil, err
	}
	out := make([]string, 0, len(arr))
	for _, x := range arr {
		s, ok := x.(string)
		if !ok {
			return nil, &tmvo.ValueError{Msg: "Input should be a valid string"}
		}
		out = append(out, s)
	}
	return out, nil
}

func settingsStringSet(v string) (*entities.StringSet, error) {
	list, err := settingsStringList(v)
	if err != nil {
		return nil, err
	}
	set := &entities.StringSet{}
	for _, s := range list {
		set.Add(s)
	}
	return set, nil
}

func settingsJSONArray(v string) ([]any, error) {
	decoded, err := entities.DecodeJSON([]byte(v))
	if err != nil {
		return nil, &tmvo.ValueError{Msg: "Input should be a valid list"}
	}
	arr, ok := decoded.([]any)
	if !ok {
		return nil, &tmvo.ValueError{Msg: "Input should be a valid list"}
	}
	return arr, nil
}

// Settings is the process-wide settings instance, evaluated at startup like Python's
// module-level `settings = Settings()`.
var Settings = func() *SettingsConfig {
	s, err := LoadSettings(os.LookupEnv)
	if err != nil {
		panic(fmt.Sprintf("invalid fastmcp settings: %s", err))
	}
	return s
}()
