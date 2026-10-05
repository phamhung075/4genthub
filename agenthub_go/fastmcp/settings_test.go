package fastmcp_test

import (
	"testing"

	"agenthub/fastmcp"
)

func envFn(env map[string]string) func(string) (string, bool) {
	return func(k string) (string, bool) { v, ok := env[k]; return v, ok }
}

func TestSettingsDefaults(t *testing.T) {
	s, err := fastmcp.LoadSettings(func(string) (string, bool) { return "", false })
	if err != nil {
		t.Fatal(err)
	}
	if s.LogLevel != fastmcp.LogLevelInfo {
		t.Fatalf("LogLevel = %q", s.LogLevel)
	}
	if !s.EnableRichTracebacks || !s.DeprecationWarnings || !s.ClientRaiseFirstExceptiongroupError {
		t.Fatalf("bool defaults wrong: %+v", s)
	}
	if s.ResourcePrefixFormat != "path" {
		t.Fatalf("ResourcePrefixFormat = %q", s.ResourcePrefixFormat)
	}
	if s.Host != "127.0.0.1" || s.Port != 8000 {
		t.Fatalf("host/port = %q/%d", s.Host, s.Port)
	}
	if s.SSEPath != "/sse/" || s.MessagePath != "/messages/" || s.StreamableHTTPPath != "/mcp/" {
		t.Fatalf("paths wrong: %+v", s)
	}
	if s.TestMode || s.Debug || s.MaskErrorDetails || s.JSONResponse || s.StatelessHTTP ||
		s.EnableAsyncEventQueue || s.ToolAttemptParseJSONArgs {
		t.Fatalf("bool defaults wrong: %+v", s)
	}
	if s.ClientInitTimeout != nil || s.DefaultAuthProvider != nil || s.IncludeTags != nil || s.ExcludeTags != nil {
		t.Fatalf("optional defaults should be nil: %+v", s)
	}
	if s.ServerDependencies == nil || len(s.ServerDependencies) != 0 {
		t.Fatalf("ServerDependencies = %#v", s.ServerDependencies)
	}
	if s.EventQueueMaxSize != 10000 {
		t.Fatalf("EventQueueMaxSize = %d", s.EventQueueMaxSize)
	}
	if len(s.Home) < len(".fastmcp") || s.Home[len(s.Home)-len(".fastmcp"):] != ".fastmcp" {
		t.Fatalf("Home = %q", s.Home)
	}
}

func TestSettingsEnvOverrides(t *testing.T) {
	s, err := fastmcp.LoadSettings(envFn(map[string]string{
		"FASTMCP_PORT":                                    "9000",
		"FASTMCP_SERVER_HOST":                             "0.0.0.0",
		"FASTMCP_TEST_MODE":                               "true",
		"FASTMCP_LOG_LEVEL":                               "DEBUG",
		"FASTMCP_RESOURCE_PREFIX_FORMAT":                  "protocol",
		"FASTMCP_CLIENT_INIT_TIMEOUT":                     "1.5",
		"FASTMCP_DEFAULT_AUTH_PROVIDER":                   "bearer_env",
		"FASTMCP_SERVER_DEPENDENCIES":                     `["x","y"]`,
		"FASTMCP_INCLUDE_TAGS":                            `["a","b"]`,
		"FASTMCP_EVENT_QUEUE_MAX_SIZE":                    "500",
		"FASTMCP_ENABLE_RICH_TRACEBACKS":                  "false",
		"FASTMCP_ENABLE_ASYNC_EVENT_QUEUE":                "yes",
		"FASTMCP_CLIENT_RAISE_FIRST_EXCEPTIONGROUP_ERROR": "on",
	}))
	if err != nil {
		t.Fatal(err)
	}
	if s.Port != 9000 {
		t.Fatalf("Port = %d", s.Port)
	}
	if s.Host != "0.0.0.0" {
		t.Fatalf("Host = %q", s.Host)
	}
	if !s.TestMode || s.EnableRichTracebacks || !s.EnableAsyncEventQueue || !s.ClientRaiseFirstExceptiongroupError {
		t.Fatalf("bools wrong: %+v", s)
	}
	if s.LogLevel != fastmcp.LogLevelDebug {
		t.Fatalf("LogLevel = %q", s.LogLevel)
	}
	if s.ResourcePrefixFormat != "protocol" {
		t.Fatalf("ResourcePrefixFormat = %q", s.ResourcePrefixFormat)
	}
	if s.ClientInitTimeout == nil || *s.ClientInitTimeout != 1.5 {
		t.Fatalf("ClientInitTimeout = %v", s.ClientInitTimeout)
	}
	if s.DefaultAuthProvider == nil || *s.DefaultAuthProvider != "bearer_env" {
		t.Fatalf("DefaultAuthProvider = %v", s.DefaultAuthProvider)
	}
	if len(s.ServerDependencies) != 2 || s.ServerDependencies[0] != "x" {
		t.Fatalf("ServerDependencies = %v", s.ServerDependencies)
	}
	if s.IncludeTags == nil || s.IncludeTags.Len() != 2 || !s.IncludeTags.Has("a") || !s.IncludeTags.Has("b") {
		t.Fatalf("IncludeTags = %v", s.IncludeTags)
	}
	if s.EventQueueMaxSize != 500 {
		t.Fatalf("EventQueueMaxSize = %d", s.EventQueueMaxSize)
	}
}

func TestSettingsPrefixPrecedenceAndCase(t *testing.T) {
	// FASTMCP_ wins over the deprecated FASTMCP_SERVER_.
	s, err := fastmcp.LoadSettings(envFn(map[string]string{
		"FASTMCP_PORT":        "9000",
		"FASTMCP_SERVER_PORT": "9100",
	}))
	if err != nil {
		t.Fatal(err)
	}
	if s.Port != 9000 {
		t.Fatalf("Port = %d", s.Port)
	}

	// The deprecated prefix is used when the primary one is absent.
	s, err = fastmcp.LoadSettings(envFn(map[string]string{"FASTMCP_SERVER_PORT": "9100"}))
	if err != nil {
		t.Fatal(err)
	}
	if s.Port != 9100 {
		t.Fatalf("Port = %d", s.Port)
	}

	// Pydantic's env source is case-insensitive.
	s, err = fastmcp.LoadSettings(envFn(map[string]string{"fastmcp_port": "9200"}))
	if err != nil {
		t.Fatal(err)
	}
	if s.Port != 9200 {
		t.Fatalf("Port = %d", s.Port)
	}
}

func TestSettingsInvalidValues(t *testing.T) {
	cases := []struct {
		name string
		env  map[string]string
		msg  string
	}{
		{"bool", map[string]string{"FASTMCP_TEST_MODE": "maybe"}, "Input should be a valid boolean, unable to interpret input"},
		{"int", map[string]string{"FASTMCP_PORT": "abc"}, "Input should be a valid integer, unable to parse string as an integer"},
		{"log-level", map[string]string{"FASTMCP_LOG_LEVEL": "info"}, "Input should be 'DEBUG', 'INFO', 'WARNING', 'ERROR' or 'CRITICAL'"},
		{"resource-prefix", map[string]string{"FASTMCP_RESOURCE_PREFIX_FORMAT": "other"}, "Input should be 'protocol' or 'path'"},
		{"auth-provider", map[string]string{"FASTMCP_DEFAULT_AUTH_PROVIDER": "other"}, "Input should be 'bearer_env'"},
		{"list-json", map[string]string{"FASTMCP_SERVER_DEPENDENCIES": "not-json"}, "Input should be a valid list"},
		{"list-elem", map[string]string{"FASTMCP_SERVER_DEPENDENCIES": `[1]`}, "Input should be a valid string"},
		{"timeout", map[string]string{"FASTMCP_CLIENT_INIT_TIMEOUT": "abc"}, "Input should be a valid number, unable to parse string as a number"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := fastmcp.LoadSettings(envFn(tc.env))
			if err == nil || err.Error() != tc.msg {
				t.Fatalf("err = %v, want %q", err, tc.msg)
			}
		})
	}
}

func TestSettingsFloatSpecialValues(t *testing.T) {
	s, err := fastmcp.LoadSettings(envFn(map[string]string{"FASTMCP_CLIENT_INIT_TIMEOUT": "inf"}))
	if err != nil {
		t.Fatal(err)
	}
	if s.ClientInitTimeout == nil || !isInf(*s.ClientInitTimeout) {
		t.Fatalf("ClientInitTimeout = %v", s.ClientInitTimeout)
	}
}

func isInf(f float64) bool { return f > 1e308 }
