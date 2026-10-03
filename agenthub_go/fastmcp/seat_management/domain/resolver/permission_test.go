package resolver

import (
	"strings"
	"testing"
)

func TestCheckPermissionPolicy(t *testing.T) {
	for _, policy := range []string{"locked", "standard", "open", "yolo", "none"} {
		if err := CheckPermissionPolicy(policy); err != nil {
			t.Errorf("CheckPermissionPolicy(%q) = %v", policy, err)
		}
	}
	for _, policy := range []string{"", "Yolo", "bypass", "builtin:yolo", "full_bypass"} {
		err := CheckPermissionPolicy(policy)
		if err == nil {
			t.Errorf("CheckPermissionPolicy(%q) = nil, want an error", policy)
			continue
		}
		if !strings.Contains(err.Error(), "yolo") || !strings.Contains(err.Error(), "standard") {
			t.Errorf("CheckPermissionPolicy(%q) = %q, want the supported policies named", policy, err)
		}
	}
}

func TestDefaultPermissionPolicyIsConservative(t *testing.T) {
	if DefaultPermissionPolicy == "yolo" {
		t.Fatalf("DefaultPermissionPolicy = %q, want a conservative policy, never yolo", DefaultPermissionPolicy)
	}
	if err := CheckPermissionPolicy(DefaultPermissionPolicy); err != nil {
		t.Fatalf("CheckPermissionPolicy(DefaultPermissionPolicy = %q) = %v, want nil", DefaultPermissionPolicy, err)
	}
}
