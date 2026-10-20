package resolver

import "fmt"

// PermissionPolicies are the permission_policy names recorded in a seat spec (the
// bare names of `4genteam policy render`); the spec field itself takes builtin:<name> or none.
// yolo is the only one that changes the launch posture (full bypass); the others keep the
// harness floor and are translated into native config by the client's permission skill.
var PermissionPolicies = []string{"locked", "standard", "open", "yolo", "none"}

// DefaultPermissionPolicy is the policy of a seat that does not name one: conservative, never
// yolo.
const DefaultPermissionPolicy = "standard"

// CheckPermissionPolicy returns an error naming the accepted policies unless policy is one of
// them.
func CheckPermissionPolicy(policy string) error {
	for _, valid := range PermissionPolicies {
		if policy == valid {
			return nil
		}
	}
	return fmt.Errorf("unsupported permission policy %q: supported policies are %v", policy, PermissionPolicies)
}
