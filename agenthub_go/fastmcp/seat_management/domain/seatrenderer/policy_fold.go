package seatrenderer

import (
	"fmt"
	"strings"

	"agenthub/fastmcp/seat_management/domain/resolver"
	"gopkg.in/yaml.v3"
)

// PolicySet is the fold of every policy block a seat resolves: one parse feeding BOTH emissions -
// the document the runtime reads and the words the seat reads - so the two cannot drift.
type PolicySet struct {
	Role             string
	StartupTimeoutMs *int // nil when no block spoke about it; it must NOT become a literal 0
	BashRules        []PolicyRule
	ToolRules        []PolicyRule
}

// FoldPolicies folds a seat's policy blocks in resolution order.
//
// THE ASYMMETRY IS THE DESIGN, and it is a security decision rather than a merge detail:
//
//   - DENY LISTS UNION. Adding a deny anywhere can only make a seat safer, and a union has no winner
//     to argue about. A rule repeated with the SAME sibling folds silently; the same match declared
//     with a DIFFERENT sibling REFUSES the fold, because two sanctioned alternatives for one
//     refusal is exactly the ambiguity that makes a seat guess.
//   - SCALARS MUST AGREE. A block that does not speak about a scalar does not veto it (nil is
//     "silent", not "zero"); two blocks that both speak must say the same thing, and a disagreement
//     REFUSES the render. Silent last-writer-wins on a security-relevant scalar is how a second
//     source of truth starts.
func FoldPolicies(modules []resolver.ResolvedModule) (*PolicySet, error) {
	set := &PolicySet{}
	seenBash := map[string]PolicyRule{}
	seenTools := map[string]PolicyRule{}
	for _, m := range modules {
		if m.Kind != resolver.KindPolicy {
			continue
		}
		block, err := ParsePolicyModule(m.Content)
		if err != nil {
			return nil, fmt.Errorf("policy module %q: %w", m.Slug, err)
		}
		if set.Role == "" {
			set.Role = block.Role
		} else if set.Role != block.Role {
			return nil, fmt.Errorf(
				"policy module %q declares role %q but %q was already declared: a seat has one role, and a silent winner would word the limits from an arbitrary block",
				m.Slug, block.Role, set.Role,
			)
		}
		if block.StartupTimeoutMs != nil {
			if set.StartupTimeoutMs != nil && *set.StartupTimeoutMs != *block.StartupTimeoutMs {
				return nil, fmt.Errorf(
					"policy module %q sets mcp.startupTimeoutMs %d but %d was already set: the render refuses to pick a winner for a runtime setting",
					m.Slug, *block.StartupTimeoutMs, *set.StartupTimeoutMs,
				)
			}
			set.StartupTimeoutMs = block.StartupTimeoutMs
		}
		var err2 error
		if set.BashRules, err2 = foldRules(m.Slug, "bash", block.BashRules, seenBash, set.BashRules); err2 != nil {
			return nil, err2
		}
		if set.ToolRules, err2 = foldRules(m.Slug, "tools", block.ToolRules, seenTools, set.ToolRules); err2 != nil {
			return nil, err2
		}
	}
	return set, nil
}

// foldRules unions one rule list. The same match declared twice folds only when the two declarations
// AGREE, and the agreement is checked on the APPROVAL first and the sibling second: one match cannot
// be both refused and allowed (a seat would then have to guess which the runtime applied), and one
// refusal cannot have two sanctioned alternatives.
//
// The union is sound for a deny and needs its reason restated for an allow, because the two are not
// symmetric: adding a deny anywhere can only make a seat safer, while an allowance GRANTS something,
// so the union's safety comes from elsewhere - a seat cannot compose itself, so every block in its
// stack was put there by whoever owns the room. The collision rule above is what keeps that honest.
func foldRules(
	slug, section string,
	rules []PolicyRule,
	seen map[string]PolicyRule,
	out []PolicyRule,
) ([]PolicyRule, error) {
	for _, rule := range rules {
		if earlier, ok := seen[rule.Match]; ok {
			if earlier.Approval != rule.Approval {
				return nil, fmt.Errorf(
					"policy module %q declares %s %q as %q, but an earlier block declared it as %q: one match cannot be both refused and allowed",
					slug, section, rule.Match, rule.Approval, earlier.Approval,
				)
			}
			if rule.Approval == "deny" && earlier.Sibling != rule.Sibling {
				return nil, fmt.Errorf(
					"policy module %q declares %s %q with a different sibling than an earlier block: one refusal cannot have two sanctioned alternatives",
					slug, section, rule.Match,
				)
			}
			continue
		}
		seen[rule.Match] = rule
		out = append(out, rule)
	}
	return out, nil
}

// RenderPolicyConfig is the document the CLIENT installs as `<agent dir>/config.yml`, in the shape the
// runtime reads. It carries ONLY what the fold decided: an absent startup setting emits NO key rather
// than a literal 0, because a 0 the blocks never asked for is a different fact from a 0 they did.
//
// The siblings are NOT emitted here: they are words for the seat, and they go to the limits text. One
// parse, two emissions, each carrying what its reader needs.
func RenderPolicyConfig(set *PolicySet) (string, error) {
	doc := map[string]any{}
	if set.StartupTimeoutMs != nil {
		doc["mcp"] = map[string]any{"startupTimeoutMs": *set.StartupTimeoutMs}
	}
	if len(set.BashRules) > 0 {
		patterns := make([]map[string]any, 0, len(set.BashRules))
		for _, rule := range set.BashRules {
			patterns = append(patterns, map[string]any{"match": rule.Match, "approval": rule.Approval})
		}
		// allowCompoundCommands is what makes a pattern match each command of `a && b` rather than the
		// whole line, which is the behaviour the deny list assumes.
		doc["bash"] = map[string]any{"allowCompoundCommands": true, "patterns": patterns}
	}
	if len(set.ToolRules) > 0 {
		approval := map[string]any{}
		for _, rule := range set.ToolRules {
			approval[rule.Match] = rule.Approval
		}
		doc["tools"] = map[string]any{"approval": approval}
	}
	encoded, err := yaml.Marshal(doc)
	if err != nil {
		return "", fmt.Errorf("encode the policy config: %w", err)
	}
	return string(encoded), nil
}

// RenderPolicyLimits is the OTHER emission: the seat's limits in words, from the same fold that
// produced the config document. Each refusal names its sibling, so the words and the rules agree by
// construction rather than by a reader checking them.
func RenderPolicyLimits(set *PolicySet) string {
	var b strings.Builder
	fmt.Fprintf(&b, "## Your limits as seat (%s)\n\n", set.Role)
	b.WriteString("Your tool calls are checked against a policy. A refused call returns `Tool ... is blocked by tool policy`. That is a rule, not a fault. **Do not retry it, rephrase it, or reach the same effect another way** (a script, `eval`, a file write). Do the allowed alternative, or ask the lead.\n")
	if allowed := rulesWith(set.BashRules, "allow"); len(allowed) > 0 {
		b.WriteString("\n### Allowed in every approval mode\n\nThese are exempted by the seat's own policy, so they do not prompt even on a seat that asks for everything else.\n\n")
		for _, rule := range allowed {
			fmt.Fprintf(&b, "- `%s`\n", rule.Match)
		}
	}
	if denied := rulesWith(set.BashRules, "deny"); len(denied) > 0 {
		b.WriteString("\n### Refused shell commands\n\nMatched inside a compound command too (`a && b`), each part separately.\n\n")
		for _, rule := range denied {
			fmt.Fprintf(&b, "- `%s` — instead: %s\n", rule.Match, rule.Sibling)
		}
	}
	if denied := rulesWith(set.ToolRules, "deny"); len(denied) > 0 {
		b.WriteString("\n### Refused tools\n\n")
		for _, rule := range denied {
			fmt.Fprintf(&b, "- `%s` — instead: %s\n", rule.Match, rule.Sibling)
		}
	}
	return b.String()
}

// rulesWith selects the rules of one approval. The words emission needs the split because an
// allowance listed under a "Refused" heading would tell a seat the opposite of what its policy says,
// and the seat reads this text rather than the config document.
func rulesWith(rules []PolicyRule, approval string) []PolicyRule {
	out := make([]PolicyRule, 0, len(rules))
	for _, rule := range rules {
		if rule.Approval == approval {
			out = append(out, rule)
		}
	}
	return out
}
