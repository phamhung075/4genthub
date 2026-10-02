package utilities

import (
	"sort"
	"strings"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// FastMCPComponent mirrors utilities.components.FastMCPComponent: the base model for
// FastMCP tools, prompts, resources and resource templates. Tags are a Python set, so
// they are deduplicated and stored sorted (set order is unspecified in Python).
type FastMCPComponent struct {
	Name        string
	Description *string
	Tags        []string
	Enabled     bool
	key         *string
}

// NewFastMCPComponent builds a component. enabled nil is Python's True default; tags nil
// is the empty set; description/key nil are Python None.
func NewFastMCPComponent(name string, description *string, tags []string, enabled *bool, key *string) *FastMCPComponent {
	c := &FastMCPComponent{Name: name, Description: description, key: key, Enabled: true}
	if enabled != nil {
		c.Enabled = *enabled
	}
	c.Tags = normalizeTags(tags)
	return c
}

// normalizeTags is set(tags): unique and sorted.
func normalizeTags(tags []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(tags))
	for _, t := range tags {
		if !seen[t] {
			seen[t] = true
			out = append(out, t)
		}
	}
	sort.Strings(out)
	return out
}

// Key mirrors the key property: the private key if truthy, else the name.
func (c *FastMCPComponent) Key() string {
	if c.key != nil && *c.key != "" {
		return *c.key
	}
	return c.Name
}

// WithKey mirrors with_key: a copy with the private key replaced.
func (c *FastMCPComponent) WithKey(key string) *FastMCPComponent {
	clone := *c
	clone.Tags = append([]string{}, c.Tags...)
	k := key
	clone.key = &k
	return &clone
}

// Equals mirrors __eq__: same class and equal model_dump (private key excluded).
func (c *FastMCPComponent) Equals(other *FastMCPComponent) bool {
	if other == nil {
		return false
	}
	if c.Name != other.Name || c.Enabled != other.Enabled {
		return false
	}
	if !equalOptionalString(c.Description, other.Description) {
		return false
	}
	if len(c.Tags) != len(other.Tags) {
		return false
	}
	for i := range c.Tags {
		if c.Tags[i] != other.Tags[i] {
			return false
		}
	}
	return true
}

func equalOptionalString(a, b *string) bool {
	if a == nil || b == nil {
		return a == nil && b == nil
	}
	return *a == *b
}

// Repr mirrors __repr__.
func (c *FastMCPComponent) Repr() string {
	return "FastMCPComponent(name=" + value_objects.PyRepr(c.Name) +
		", description=" + value_objects.PyRepr(ptrOrNil(c.Description)) +
		", tags=" + pySetRepr(c.Tags) +
		", enabled=" + value_objects.PyRepr(c.Enabled) + ")"
}

func ptrOrNil(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

// pySetRepr renders a Python set literal (element order is unspecified in Python).
func pySetRepr(items []string) string {
	if len(items) == 0 {
		return "set()"
	}
	parts := make([]string, len(items))
	for i, s := range items {
		parts[i] = value_objects.PyRepr(s)
	}
	return "{" + strings.Join(parts, ", ") + "}"
}

// Enable sets enabled to True.
func (c *FastMCPComponent) Enable() { c.Enabled = true }

// Disable sets enabled to False.
func (c *FastMCPComponent) Disable() { c.Enabled = false }
