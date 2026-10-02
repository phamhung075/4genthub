package resources

import (
	"fmt"
	"regexp"
	"strings"

	"agenthub/fastmcp/utilities"
)

// MCPResourceTemplate mirrors mcp.types.ResourceTemplate.
type MCPResourceTemplate struct {
	URITemplate string
	Name        string
	Description *string
	MimeType    *string
}

// buildRegex ports build_regex. It splits the template on {name} placeholders,
// {name*} matches anything (.+), {name} matches a path segment ([^/]+).
func buildRegex(template string) *regexp.Regexp {
	parts := splitBracePlaceholders(template)
	pattern := ""
	for _, part := range parts {
		if strings.HasPrefix(part, "{") && strings.HasSuffix(part, "}") {
			name := part[1 : len(part)-1]
			if strings.HasSuffix(name, "*") {
				name = name[:len(name)-1]
				pattern += fmt.Sprintf("(?P<%s>.+)", name)
			} else {
				pattern += fmt.Sprintf("(?P<%s>[^/]+)", name)
			}
		} else {
			pattern += regexp.QuoteMeta(part)
		}
	}
	return regexp.MustCompile("^" + pattern + "$")
}

// splitBracePlaceholders mirrors re.split(r"(\{[^}]+\})", template): the
// capturing group keeps the placeholders as their own elements.
func splitBracePlaceholders(template string) []string {
	var parts []string
	rest := template
	for {
		start := strings.Index(rest, "{")
		if start < 0 {
			break
		}
		end := strings.Index(rest[start:], "}")
		if end < 0 {
			break
		}
		end += start
		if end == start+1 {
			break
		}
		parts = append(parts, rest[:start], rest[start:end+1])
		rest = rest[end+1:]
	}
	parts = append(parts, rest)
	return parts
}

// pyUnquote mirrors urllib.parse.unquote for the byte sequences this code sees:
// %XX is decoded (UTF-8 aware), invalid sequences are left untouched.
func pyUnquote(s string) string {
	var b strings.Builder
	for i := 0; i < len(s); {
		if s[i] == '%' && i+2 < len(s) && isHex(s[i+1]) && isHex(s[i+2]) {
			b.WriteByte(hexVal(s[i+1])<<4 | hexVal(s[i+2]))
			i += 3
			continue
		}
		b.WriteByte(s[i])
		i++
	}
	return b.String()
}

func isHex(c byte) bool {
	return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')
}

func hexVal(c byte) byte {
	switch {
	case c >= '0' && c <= '9':
		return c - '0'
	case c >= 'a' && c <= 'f':
		return c - 'a' + 10
	default:
		return c - 'A' + 10
	}
}

// matchURITemplate ports match_uri_template: a map of template parameter names
// to URL-unquoted values, or nil when the URI does not match.
func matchURITemplate(uri, uriTemplate string) map[string]string {
	re := buildRegex(uriTemplate)
	m := re.FindStringSubmatch(uri)
	if m == nil {
		return nil
	}
	out := map[string]string{}
	for i, name := range re.SubexpNames() {
		if i == 0 || name == "" {
			continue
		}
		out[name] = pyUnquote(m[i])
	}
	return out
}

// ResourceTemplate mirrors resources.template.ResourceTemplate.
type ResourceTemplate struct {
	*utilities.FastMCPComponent
	URITemplate string
	MimeType    string
	Parameters  map[string]any
}

// NewResourceTemplate builds a template with the Python field defaults.
func NewResourceTemplate(uriTemplate string, name string, description *string, mimeType string, parameters map[string]any, tags []string, enabled *bool, key *string) *ResourceTemplate {
	if mimeType == "" {
		mimeType = "text/plain"
	}
	if parameters == nil {
		parameters = map[string]any{}
	}
	return &ResourceTemplate{
		FastMCPComponent: utilities.NewFastMCPComponent(name, description, tags, enabled, key),
		URITemplate:      uriTemplate,
		MimeType:         mimeType,
		Parameters:       parameters,
	}
}

// Matches ports ResourceTemplate.matches.
func (t *ResourceTemplate) Matches(uri string) map[string]any {
	params := matchURITemplate(uri, t.URITemplate)
	if params == nil {
		return nil
	}
	out := make(map[string]any, len(params))
	for k, v := range params {
		out[k] = v
	}
	return out
}

// ToMCPTemplate ports to_mcp_template.
func (t *ResourceTemplate) ToMCPTemplate() *MCPResourceTemplate {
	mime := t.MimeType
	return &MCPResourceTemplate{
		URITemplate: t.URITemplate,
		Name:        t.Name,
		Description: t.Description,
		MimeType:    &mime,
	}
}

// Key ports the overridden key property (self._key or self.uri_template). The
// private key is not observable across packages, so the URI template is used.
func (t *ResourceTemplate) Key() string {
	if t.URITemplate != "" {
		return t.URITemplate
	}
	return t.FastMCPComponent.Key()
}
