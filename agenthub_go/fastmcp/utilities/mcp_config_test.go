package utilities

import (
	"errors"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestInferTransportTypeFromURL(t *testing.T) {
	cases := []struct {
		url  string
		want string
	}{
		{"http://example.com/sse", TransportSSE},
		{"http://example.com/sse/", TransportSSE},
		{"http://example.com/sse?x=1", TransportSSE},
		{"http://example.com/sse&x=1", TransportSSE},
		{"https://example.com/v1/sse/endpoint", TransportSSE},
		{"http://example.com/messages", TransportStreamableHTTP},
		{"http://example.com/sses", TransportStreamableHTTP},
		{"http://example.com", TransportStreamableHTTP},
	}
	for _, c := range cases {
		got, err := InferTransportTypeFromURL(c.url)
		if err != nil {
			t.Fatalf("%s: %v", c.url, err)
		}
		if got != c.want {
			t.Fatalf("%s = %q, want %q", c.url, got, c.want)
		}
	}
}

func TestInferTransportTypeFromURLInvalid(t *testing.T) {
	_, err := InferTransportTypeFromURL("ftp://example.com")
	var verr *value_objects.ValueError
	if !errors.As(err, &verr) || verr.Msg != "Invalid URL: ftp://example.com" {
		t.Fatalf("err = %v", err)
	}
}

func TestMCPConfigFromDictStdio(t *testing.T) {
	raw, err := entities.DecodeJSON([]byte(`{"mcpServers":{"srv":{"command":"python","args":["-m","x"],"env":{"A":"1"}}}}`))
	if err != nil {
		t.Fatal(err)
	}
	cfg, err := MCPConfigFromDict(raw.(*entities.OrderedMap[any]))
	if err != nil {
		t.Fatalf("MCPConfigFromDict: %v", err)
	}
	entry, _ := cfg.MCPServers.Get("srv")
	stdio, ok := entry.(*StdioMCPServer)
	if !ok {
		t.Fatalf("entry = %T, want *StdioMCPServer", entry)
	}
	if stdio.Command != "python" || stdio.Transport != "stdio" || len(stdio.Args) != 2 || stdio.Args[0] != "-m" {
		t.Fatalf("stdio = %+v", stdio)
	}
	if v, _ := stdio.Env.Get("A"); v != "1" {
		t.Fatalf("env = %v", stdio.Env)
	}
}

func TestMCPConfigFromDictRemoteWithoutWrapper(t *testing.T) {
	raw, err := entities.DecodeJSON([]byte(`{"srv":{"url":"http://x/sse","transport":"sse","headers":{"H":"v"},"auth":"oauth"}}`))
	if err != nil {
		t.Fatal(err)
	}
	cfg, err := MCPConfigFromDict(raw.(*entities.OrderedMap[any]))
	if err != nil {
		t.Fatalf("MCPConfigFromDict: %v", err)
	}
	entry, _ := cfg.MCPServers.Get("srv")
	remote, ok := entry.(*RemoteMCPServer)
	if !ok {
		t.Fatalf("entry = %T, want *RemoteMCPServer", entry)
	}
	if remote.URL != "http://x/sse" || remote.Transport == nil || *remote.Transport != "sse" || remote.Auth != "oauth" {
		t.Fatalf("remote = %+v", remote)
	}
}

func TestMCPConfigFromDictRejectsAmbiguousAndUnknownKeys(t *testing.T) {
	for _, s := range []string{
		`{"srv":{"command":"x","url":"http://x"}}`,
		`{"srv":{"command":"x","bogus":1}}`,
		`{"srv":{"url":"http://x","transport":"bogus"}}`,
	} {
		raw, err := entities.DecodeJSON([]byte(s))
		if err != nil {
			t.Fatal(err)
		}
		if _, err := MCPConfigFromDict(raw.(*entities.OrderedMap[any])); err == nil {
			t.Fatalf("%s: expected an error", s)
		}
	}
}
