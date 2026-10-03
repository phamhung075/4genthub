package resolver

import "fmt"

// PermissionPolicies are the permission_policy names OpenRig records in a RigSpec (the
// bare names of `rig policy list`); the spec field itself takes builtin:<name> or none.
// yolo is the only one that changes the launch posture (full bypass); the others keep the
// harness floor and are translated into native config by OpenRig's permission skill.
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
