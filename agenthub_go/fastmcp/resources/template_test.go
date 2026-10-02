package resources

import "testing"

func TestMatchURITemplate(t *testing.T) {
	cases := []struct {
		uri      string
		template string
		want     map[string]string
	}{
		{"weather://paris/current", "weather://{city}/current", map[string]string{"city": "paris"}},
		{"weather://new%20york/current", "weather://{city}/current", map[string]string{"city": "new york"}},
		{"weather://a/b/current", "weather://{city}/current", nil},
		{"res://a/b/c", "res://{path*}", map[string]string{"path": "a/b/c"}},
		{"res://x", "res://{path*}", map[string]string{"path": "x"}},
		{"user://1", "user://{id}", map[string]string{"id": "1"}},
		{"nomatch", "res://{id}", nil},
	}
	for _, c := range cases {
		got := matchURITemplate(c.uri, c.template)
		if len(got) != len(c.want) {
			t.Fatalf("matchURITemplate(%q, %q) = %v, want %v", c.uri, c.template, got, c.want)
		}
		for k, v := range c.want {
			if got[k] != v {
				t.Fatalf("matchURITemplate(%q, %q)[%q] = %q, want %q", c.uri, c.template, k, got[k], v)
			}
		}
	}
}

func TestResourceTemplateKey(t *testing.T) {
	tpl := NewResourceTemplate("weather://{city}/current", "", nil, "", nil, nil, nil, nil)
	if tpl.Key() != "weather://{city}/current" {
		t.Fatalf("Key() = %q", tpl.Key())
	}
	if tpl.MimeType != "text/plain" {
		t.Fatalf("MimeType = %q", tpl.MimeType)
	}
	if tpl.Matches("weather://rome/current")["city"] != "rome" {
		t.Fatalf("Matches failed")
	}
}
