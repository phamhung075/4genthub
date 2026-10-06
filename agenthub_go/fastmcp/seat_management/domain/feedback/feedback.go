// Package feedback holds the seat friction channel's vocabulary: the layer a report says its
// friction is in.
//
// The layer list is the single source of truth for three things that must not drift apart: the
// CHECK constraint on seat_feedback.layer, the route's validation of a submitted layer, and the
// order the read side groups by. TestSeatFeedbackLayerCheckMatchesDomain
// (infrastructure/database) checks the DDL copy against this list, the same way
// TestSeatPermissionPolicyCheckMatchesResolver checks the seats CHECK against resolver.
package feedback

import "fmt"

// Layer is the layer of the platform a seat says its friction is in. It is a closed set: an
// unknown layer is refused rather than stored, because the read side groups by it and a
// free-text layer would fragment that grouping into near-duplicates.
type Layer string

const (
	// LayerRuntime is the agent runtime and its harness running the seat: permission rules,
	// prompts, tool availability, the runtime CLI itself.
	LayerRuntime Layer = "runtime"
	// LayerOpenRig is the rig client and supervisor: rig CLI verbs, the daemon, seat
	// lifecycle, terminals.
	LayerOpenRig Layer = "openrig"
	// LayerCloud is the platform API and MCP surface: routes, auth, snapshots, sync.
	LayerCloud Layer = "cloud"
	// LayerSeatContext is what a seat was launched with: role text, skills, overlays, blocks.
	LayerSeatContext Layer = "seat-context"
	// LayerWorkspace is the repository and its tooling that the seat works in: tests, builds,
	// editors, the working tree.
	LayerWorkspace Layer = "workspace"
	// LayerOther is the escape hatch, and it is load-bearing: it is what stops a seat inventing
	// a layer name when the friction does not fit one of the five above. It is not a bucket to
	// prefer over naming the real layer.
	LayerOther Layer = "other"
)

// Layers is the closed set, in the order the read side groups by. The order is the grouping
// order the API answer renders, so it is part of the contract, not a display detail.
var Layers = []Layer{
	LayerRuntime,
	LayerOpenRig,
	LayerCloud,
	LayerSeatContext,
	LayerWorkspace,
	LayerOther,
}

// Valid reports whether l is one of Layers.
func (l Layer) Valid() bool {
	for _, known := range Layers {
		if l == known {
			return true
		}
	}
	return false
}

// ParseLayer validates a submitted layer. The error names the whole accepted set, because a
// caller that got the vocabulary wrong needs the vocabulary, not a boolean.
func ParseLayer(raw string) (Layer, error) {
	layer := Layer(raw)
	if !layer.Valid() {
		return "", fmt.Errorf("layer %q is not one of %s", raw, List())
	}
	return layer, nil
}

// List is the accepted set as one comma-separated string, for error text.
func List() string {
	out := ""
	for i, layer := range Layers {
		if i > 0 {
			out += ", "
		}
		out += string(layer)
	}
	return out
}
