// Package modulecontent states what a module's content must be for its kind, by running the very
// parse the seat renderer will run.
//
// A module version is immutable: re-publishing the same version with different content is a
// conflict, so the publish is the LAST moment a content no seat can render can be refused, and
// every later discovery is a report about something unrepairable. Before this package the shape
// was only discovered at render time — a seat-scoped overlay naming an unrenderable module
// version answered 200 and the failure appeared on the seat's next read, arbitrarily far from the
// writer.
//
// The rules live with the parsers that own them, and every one of the three parsed kinds delegates
// rather than restates: skillblock.Parse for a skill block, mcpblock.Parse for a server object, and
// seatrenderer.ParseToolSettings — the very call mergeToolModules makes — for a tool module. This
// package is the one place that maps a kind to its rule, so a kind added later has to state its
// rule instead of inheriting a silent default.
package modulecontent

import (
	"errors"
	"fmt"

	"agenthub/fastmcp/seat_management/domain/mcpblock"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/seatrenderer"
	"agenthub/fastmcp/seat_management/domain/skillblock"
)

// ErrNoRule is what Validate returns for a module kind no rule covers. It is wrapped, so a caller
// can test it with errors.Is. Validate refuses such a kind rather than letting the content
// through: a permissive default would recreate, for the next kind somebody adds, the very defect
// this package exists to close.
var ErrNoRule = errors.New("no content rule for this module kind")

// Validate reports whether content is what kind's renderer can read. A skill is a skill block, an
// mcp module is one server object, a tool module is the settings object the runtime's fragment
// merges; instruction, document and memory render as text and accept any content. The caller
// writes the returned error to the publisher; it names the kind and the rule that failed.
func Validate(kind resolver.ModuleKind, content string) error {
	switch kind {
	case resolver.KindSkill:
		if _, err := skillblock.Parse(content); err != nil {
			return fmt.Errorf("skill content: %w", err)
		}
	case resolver.KindMCP:
		if _, err := mcpblock.Parse(content); err != nil {
			return fmt.Errorf("mcp content: %w", err)
		}
	case resolver.KindTool:
		if _, err := seatrenderer.ParseToolSettings(content); err != nil {
			return fmt.Errorf("tool content: %w", err)
		}
	case resolver.KindPolicy:
		if _, err := seatrenderer.ParsePolicyModule(content); err != nil {
			return fmt.Errorf("policy content: %w", err)
		}
	case resolver.KindInstruction, resolver.KindDocument, resolver.KindMemory:
		// Rendered verbatim into the seat's guidance, so any text renders. The publish route
		// already refuses an empty content, which is the only shape rule these kinds have.
	default:
		return fmt.Errorf("%w: %q", ErrNoRule, kind)
	}
	return nil
}
