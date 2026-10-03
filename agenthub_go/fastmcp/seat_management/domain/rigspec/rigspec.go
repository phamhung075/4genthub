// Package rigspec renders one company room as an OpenRig RigSpec v0.2 document:
// the room becomes a pod, its seats become members, and its allowed links become
// pod-local edges.
package rigspec

import (
	"bytes"
	"fmt"
	"regexp"
	"sort"

	"gopkg.in/yaml.v3"
)

// Seat is one room seat as it appears in the rig spec.
type Seat struct {
	Key     string
	Runtime string
	Model   string
}

// Edge is one allowed seat link; From and To are seat keys in the same room.
type Edge struct {
	Kind string
	From string
	To   string
}

// agentRefPrefix points at the agent specs the OpenRig client materializes beside
// the rig file. local: refs resolve relative to the rig spec's directory (rig root).
const agentRefPrefix = "local:agents/"

var (
	namePattern    = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9_-]*$`)
	validRuntimes  = map[string]bool{"claude-code": true, "codex": true}
	validEdgeKinds = map[string]bool{
		"delegates_to":      true,
		"spawned_by":        true,
		"can_observe":       true,
		"collaborates_with": true,
		"escalates_to":      true,
	}
	permissionPolicies = []string{"locked", "standard", "open", "yolo", "none"}
	edgeKindList       = []string{"delegates_to", "spawned_by", "can_observe", "collaborates_with", "escalates_to"}
)

type quotedString string

func (q quotedString) MarshalYAML() (any, error) {
	return &yaml.Node{Kind: yaml.ScalarNode, Tag: "!!str", Style: yaml.DoubleQuotedStyle, Value: string(q)}, nil
}

type rigYAML struct {
	Version          quotedString `yaml:"version"`
	Name             string       `yaml:"name"`
	PermissionPolicy string       `yaml:"permission_policy,omitempty"`
	Pods             []podYAML    `yaml:"pods"`
	Edges            []edgeYAML   `yaml:"edges"`
}

type podYAML struct {
	ID      string       `yaml:"id"`
	Label   string       `yaml:"label"`
	Members []memberYAML `yaml:"members"`
	Edges   []edgeYAML   `yaml:"edges"`
}

type memberYAML struct {
	ID       string `yaml:"id"`
	AgentRef string `yaml:"agent_ref"`
	Profile  string `yaml:"profile"`
	Runtime  string `yaml:"runtime"`
	Model    string `yaml:"model,omitempty"`
	Cwd      string `yaml:"cwd"`
}

type edgeYAML struct {
	Kind string `yaml:"kind"`
	From string `yaml:"from"`
	To   string `yaml:"to"`
}

// ValidatePermissionPolicy accepts "" (no policy line) or one of locked, standard, open, yolo, none.
func ValidatePermissionPolicy(policy string) error {
	if policy == "" {
		return nil
	}
	for _, valid := range permissionPolicies {
		if policy == valid {
			return nil
		}
	}
	return fmt.Errorf("rigspec: permission policy %q must be one of %v", policy, permissionPolicies)
}

// permissionPolicyValue is the rig-level value: builtin:<name>, or the literal none.
func permissionPolicyValue(policy string) string {
	if policy == "" || policy == "none" {
		return policy
	}
	return "builtin:" + policy
}

// RenderRoom renders one room as a deterministic OpenRig RigSpec v0.2 document.
// Seats are sorted by key, edges by (kind, from, to); the output is identical for
// any input order. A non-empty permissionPolicy adds a rig-level permission_policy
// line between name and pods.
func RenderRoom(roomSlug, roomName, permissionPolicy string, seats []Seat, edges []Edge) (string, error) {
	if err := validateName("room slug", roomSlug); err != nil {
		return "", err
	}
	if err := ValidatePermissionPolicy(permissionPolicy); err != nil {
		return "", err
	}
	if roomName == "" {
		return "", fmt.Errorf("rigspec: room name is required")
	}
	if len(seats) == 0 {
		return "", fmt.Errorf("rigspec: room %q has no seats", roomSlug)
	}

	sortedSeats := append([]Seat(nil), seats...)
	sort.Slice(sortedSeats, func(i, j int) bool { return sortedSeats[i].Key < sortedSeats[j].Key })

	members := make([]memberYAML, 0, len(sortedSeats))
	keys := make(map[string]bool, len(sortedSeats))
	for i, seat := range sortedSeats {
		if err := validateName(fmt.Sprintf("seats[%d] key", i), seat.Key); err != nil {
			return "", err
		}
		if keys[seat.Key] {
			return "", fmt.Errorf("rigspec: duplicate seat key %q", seat.Key)
		}
		keys[seat.Key] = true
		if !validRuntimes[seat.Runtime] {
			return "", fmt.Errorf("rigspec: seat %q runtime %q must be \"claude-code\" or \"codex\"", seat.Key, seat.Runtime)
		}
		members = append(members, memberYAML{
			ID:       seat.Key,
			AgentRef: agentRefPrefix + seat.Key,
			Profile:  "default",
			Runtime:  seat.Runtime,
			Model:    seat.Model,
			Cwd:      ".",
		})
	}

	sortedEdges := append([]Edge(nil), edges...)
	sort.Slice(sortedEdges, func(i, j int) bool {
		a, b := sortedEdges[i], sortedEdges[j]
		if a.Kind != b.Kind {
			return a.Kind < b.Kind
		}
		if a.From != b.From {
			return a.From < b.From
		}
		return a.To < b.To
	})

	podEdges := make([]edgeYAML, 0, len(sortedEdges))
	for i, edge := range sortedEdges {
		if !validEdgeKinds[edge.Kind] {
			return "", fmt.Errorf("rigspec: edges[%d] kind %q must be one of %v", i, edge.Kind, edgeKindList)
		}
		if !keys[edge.From] {
			return "", fmt.Errorf("rigspec: edges[%d] from %q is not a seat in the room", i, edge.From)
		}
		if !keys[edge.To] {
			return "", fmt.Errorf("rigspec: edges[%d] to %q is not a seat in the room", i, edge.To)
		}
		if edge.From == edge.To {
			return "", fmt.Errorf("rigspec: edges[%d] from and to are the same seat %q", i, edge.From)
		}
		podEdges = append(podEdges, edgeYAML{Kind: edge.Kind, From: edge.From, To: edge.To})
	}

	doc := rigYAML{
		Version:          quotedString("0.2"),
		Name:             roomSlug,
		PermissionPolicy: permissionPolicyValue(permissionPolicy),
		Pods: []podYAML{{
			ID:      roomSlug,
			Label:   roomName,
			Members: members,
			Edges:   podEdges,
		}},
		Edges: []edgeYAML{},
	}

	var buf bytes.Buffer
	enc := yaml.NewEncoder(&buf)
	enc.SetIndent(2)
	if err := enc.Encode(doc); err != nil {
		return "", fmt.Errorf("encode rig.yaml: %w", err)
	}
	if err := enc.Close(); err != nil {
		return "", fmt.Errorf("close rig.yaml encoder: %w", err)
	}
	return buf.String(), nil
}

func validateName(field, value string) error {
	if !namePattern.MatchString(value) {
		return fmt.Errorf("rigspec: %s %q must match %s", field, value, namePattern)
	}
	return nil
}
