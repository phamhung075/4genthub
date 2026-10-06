package seatrenderer

import (
	"encoding/json"
	"fmt"
	"strings"
)

// A `policy` block declares a seat's limits as data: the role, the runtime settings the limits need,
// and the rules the runtime enforces. This parse lives with the renderer because the renderer is what
// CONSUMES it - `modulecontent.Validate` delegates here, so a policy no seat can render is refused at
// publish AND at seed time, by the same function.
//
// WHY A KIND OF ITS OWN, rather than a fatter `tool`: `tool` already means "a Claude settings
// fragment", and overloading it would make one kind carry two parse rules and two refusals. A kind
// states its own rule in the one place that maps kinds to rules, and the gate added for the seeder
// then covers the new kind by construction rather than by remembering.

// PolicyRule is one enforcement entry: a pattern the runtime refuses and the SANCTIONED ALTERNATIVE
// a seat should take instead.
//
// THE SIBLING IS NOT OPTIONAL, and that is the reviewer's rule enforced where rules are declared: a
// denial with a named sibling is a rule, a denial without one is a trap - it tells a seat what it may
// not do and leaves it to guess what it may. Requiring it at PARSE time means no block can be
// published or seeded carrying a trap, rather than a later report about one.
type PolicyRule struct {
	Match    string `json:"match"`
	Approval string `json:"approval"`
	Sibling  string `json:"sibling"`
}

// PolicyModule is a parsed policy block.
type PolicyModule struct {
	Role             string
	StartupTimeoutMs *int // nil when the block does not set it
	BashDeny         []PolicyRule
	ToolDeny         []PolicyRule
}

// policyJSON mirrors the block shape. Pointers distinguish "absent" from "set to the zero value",
// because an absent startup setting is a different fact from a setting of 0.
type policyJSON struct {
	Role string `json:"role"`
	MCP  *struct {
		StartupTimeoutMs *int `json:"startupTimeoutMs"`
	} `json:"mcp"`
	Bash *struct {
		Patterns []PolicyRule `json:"patterns"`
	} `json:"bash"`
	Tools *struct {
		Patterns []PolicyRule `json:"patterns"`
	} `json:"tools"`
}

// ParsePolicyModule reads a policy block, naming the rule that failed. Every refusal says which rule
// failed and what the rule is, because the caller writes it to a publisher who cannot see this code.
func ParsePolicyModule(content string) (*PolicyModule, error) {
	var raw policyJSON
	if err := json.Unmarshal([]byte(content), &raw); err != nil {
		return nil, fmt.Errorf("content is not a JSON object: %w", err)
	}
	if strings.TrimSpace(raw.Role) == "" {
		return nil, fmt.Errorf("role is required: the limits text is worded from it")
	}
	out := &PolicyModule{Role: strings.TrimSpace(raw.Role)}
	if raw.MCP != nil {
		if raw.MCP.StartupTimeoutMs != nil && *raw.MCP.StartupTimeoutMs < 0 {
			return nil, fmt.Errorf("mcp.startupTimeoutMs must not be negative, got %d", *raw.MCP.StartupTimeoutMs)
		}
		out.StartupTimeoutMs = raw.MCP.StartupTimeoutMs
	}
	if raw.Bash != nil {
		rules, err := parsePolicyRules("bash", raw.Bash.Patterns)
		if err != nil {
			return nil, err
		}
		out.BashDeny = rules
	}
	if raw.Tools != nil {
		rules, err := parsePolicyRules("tools", raw.Tools.Patterns)
		if err != nil {
			return nil, err
		}
		out.ToolDeny = rules
	}
	return out, nil
}

// parsePolicyRules validates one rule list: every entry must name what it refuses, must be a denial
// (the only approval this kind expresses today, refused by name rather than ignored), and must carry
// the sibling that makes it a rule rather than a trap.
func parsePolicyRules(section string, rules []PolicyRule) ([]PolicyRule, error) {
	out := make([]PolicyRule, 0, len(rules))
	for i, rule := range rules {
		if strings.TrimSpace(rule.Match) == "" {
			return nil, fmt.Errorf("%s.patterns[%d]: match is required", section, i)
		}
		if rule.Approval != "deny" {
			return nil, fmt.Errorf(
				"%s.patterns[%d] (%s): approval %q is not one this kind expresses; only \"deny\" is, and an unknown approval would silently not apply",
				section, i, rule.Match, rule.Approval,
			)
		}
		if strings.TrimSpace(rule.Sibling) == "" {
			return nil, fmt.Errorf(
				"%s.patterns[%d] (%s): a denial needs its sibling - the sanctioned way to do the legitimate thing it looks like - or it is a trap rather than a rule",
				section, i, rule.Match,
			)
		}
		out = append(out, PolicyRule{
			Match:    strings.TrimSpace(rule.Match),
			Approval: rule.Approval,
			Sibling:  strings.TrimSpace(rule.Sibling),
		})
	}
	return out, nil
}
