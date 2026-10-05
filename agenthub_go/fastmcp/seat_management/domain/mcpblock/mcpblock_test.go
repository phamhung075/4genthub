package mcpblock

import (
	"encoding/json"
	"reflect"
	"strings"
	"testing"
)

const platformBlock = `{
  "name": "agenthub_http",
  "type": "http",
  "url": "${AGENTHUB_MCP_URL}",
  "headers": {"Accept": "application/json, text/event-stream", "Authorization": "Bearer ${AGENTHUB_TOKEN}"}
}`

func TestParseHTTP(t *testing.T) {
	server, err := Parse(platformBlock)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	if server.Name != "agenthub_http" || server.Type != TypeHTTP || server.URL != PlatformURLPlaceholder {
		t.Fatalf("server = %+v", server)
	}
	if server.Headers["Authorization"] != "Bearer ${AGENTHUB_TOKEN}" {
		t.Fatalf("headers = %v", server.Headers)
	}
	resolved := server.WithPlatformURL("https://api.example.test/mcp")
	if resolved.URL != "https://api.example.test/mcp" {
		t.Fatalf("resolved url = %q", resolved.URL)
	}
	if resolved.Headers["Authorization"] != "Bearer ${AGENTHUB_TOKEN}" {
		t.Fatalf("substitution touched a client-expanded reference: %v", resolved.Headers)
	}
	fragment := resolved.Fragment()
	want := map[string]any{
		"type": "http",
		"url":  "https://api.example.test/mcp",
		"headers": map[string]string{
			"Accept":        "application/json, text/event-stream",
			"Authorization": "Bearer ${AGENTHUB_TOKEN}",
		},
	}
	if !reflect.DeepEqual(fragment, want) {
		t.Fatalf("fragment = %v", fragment)
	}
}

func TestParseStdio(t *testing.T) {
	server, err := Parse(`{"name":"sequential-thinking","type":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-sequential-thinking"],"env":{"EXA_API_KEY":"${EXA_API_KEY}"}}`)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	if server.Command != "npx" || len(server.Args) != 2 || server.Env["EXA_API_KEY"] != "${EXA_API_KEY}" {
		t.Fatalf("server = %+v", server)
	}
	fragment := server.Fragment()
	if fragment["url"] != nil || fragment["command"] != "npx" || fragment["type"] != TypeStdio {
		t.Fatalf("fragment = %v", fragment)
	}
}

func TestParseErrors(t *testing.T) {
	cases := map[string]struct{ content, want string }{
		"not json":       {`not json`, "not one JSON value"},
		"two values":     {`{"name":"a","type":"http","url":"http://x"} {"name":"b"}`, "not one JSON value"},
		"not an object":  {`123`, "not a server object"},
		"unknown field":  {`{"name":"a","type":"http","url":"http://x","alwaysAllow":["t"]}`, "unknown field"},
		"no name":        {`{"type":"http","url":"http://x"}`, "field name is required"},
		"blank name":     {`{"name":"  ","type":"http","url":"http://x"}`, "field name is required"},
		"no type":        {`{"name":"a"}`, `field type must be "http" or "stdio"`},
		"bad type":       {`{"name":"a","type":"sse","url":"http://x"}`, `field type must be "http" or "stdio"`},
		"http no url":    {`{"name":"a","type":"http"}`, "field url is required"},
		"http command":   {`{"name":"a","type":"http","url":"http://x","command":"npx"}`, "not command, args or env"},
		"http env":       {`{"name":"a","type":"http","url":"http://x","env":{"A":"1"}}`, "not command, args or env"},
		"http bad url":   {`{"name":"a","type":"http","url":"ftp://x"}`, "url must be http(s)"},
		"stdio no cmd":   {`{"name":"a","type":"stdio"}`, "field command is required"},
		"stdio url":      {`{"name":"a","type":"stdio","command":"npx","url":"http://x"}`, "not url or headers"},
		"stdio headers":  {`{"name":"a","type":"stdio","command":"npx","headers":{"A":"1"}}`, "not url or headers"},
		"literal bearer": {`{"name":"a","type":"http","url":"http://x","headers":{"Authorization":"Bearer tok_0123456789abcdefghij"}}`, "credential-shaped"},
		"jwt":            {`{"name":"a","type":"http","url":"http://x","headers":{"Authorization":"eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefghijklmnop"}}`, "credential-shaped"},
		"api key":        {`{"name":"a","type":"http","url":"http://x","headers":{"X-Key":"sk-abcdefghijklmnopqrstuvwx"}}`, "credential-shaped"},
		"private key":    {`{"name":"a","type":"stdio","command":"sh","args":["-----BEGIN RSA PRIVATE KEY-----"]}`, "credential-shaped"},
		"url credential": {`{"name":"a","type":"http","url":"https://user:hunter2@example.test/mcp"}`, "credential-shaped"},
	}
	for name, c := range cases {
		if _, err := Parse(c.content); err == nil || !strings.Contains(err.Error(), c.want) {
			t.Errorf("%s: err = %v, want %q", name, err, c.want)
		}
	}
}

// A value that names an environment variable is not a secret: that is the whole point of the
// ${VAR} convention, so the scanner must not flag it.
func TestParseAcceptsEnvReferences(t *testing.T) {
	for name, content := range map[string]string{
		"token":   `{"name":"a","type":"http","url":"${AGENTHUB_MCP_URL}","headers":{"Authorization":"Bearer ${AGENTHUB_TOKEN}"}}`,
		"api key": `{"name":"a","type":"stdio","command":"npx","env":{"EXA_API_KEY":"${EXA_API_KEY}"}}`,
		"secret":  `{"name":"a","type":"stdio","command":"npx","env":{"AUTH_SECRET":"${AUTH_SECRET}"}}`,
	} {
		if _, err := Parse(content); err != nil {
			t.Errorf("%s: Parse(%s) = %v, want nil", name, content, err)
		}
	}
}

func TestCheckURLAcceptsClientExpandedReference(t *testing.T) {
	if err := CheckURL("${MY_SERVER_URL}"); err != nil {
		t.Fatalf("CheckURL(expanded ref) = %v, want nil", err)
	}
	if err := CheckURL("https://example.test/mcp"); err != nil {
		t.Fatalf("CheckURL(https) = %v, want nil", err)
	}
	if err := CheckURL(""); err != nil {
		t.Fatalf("CheckURL(empty) = %v, want nil", err)
	}
	if err := CheckURL("http://example.test/mcp"); err != nil {
		t.Fatalf("CheckURL(http) = %v, want nil", err)
	}
	if err := CheckURL("ftp://example.test"); err == nil {
		t.Fatal("CheckURL(ftp) = nil, want an error")
	}
}

func TestFragmentJSONShape(t *testing.T) {
	server, err := Parse(platformBlock)
	if err != nil {
		t.Fatal(err)
	}
	server = server.WithPlatformURL("https://api.example.test/mcp")
	encoded, err := json.Marshal(server.Fragment())
	if err != nil {
		t.Fatal(err)
	}
	want := `{"headers":{"Accept":"application/json, text/event-stream","Authorization":"Bearer ${AGENTHUB_TOKEN}"},"type":"http","url":"https://api.example.test/mcp"}`
	if string(encoded) != want {
		t.Fatalf("fragment = %s\nwant      %s", encoded, want)
	}
}
