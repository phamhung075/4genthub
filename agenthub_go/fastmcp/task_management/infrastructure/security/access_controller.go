// Package security ports task_management/infrastructure/security.
package security

import "errors"

// SecurityLevel is the simplified set of security levels.
type SecurityLevel string

const (
	SecurityLevelPublic       SecurityLevel = "public"
	SecurityLevelInternal     SecurityLevel = "internal"
	SecurityLevelConfidential SecurityLevel = "confidential"
)

// AccessController is the security access control service. PYTHON DEFECT (preserved):
// its constructor references SecurityLevel.PROTECTED and SecurityLevel.RESTRICTED, which
// the simplified enum no longer defines, so `AccessController()` always raises
// AttributeError and no instance (hence none of its methods) is reachable. Nothing in the
// codebase constructs it.
type AccessController struct{}

// NewAccessController always fails like the Python constructor.
func NewAccessController() (*AccessController, error) {
	return nil, errors.New("type object 'SecurityLevel' has no attribute 'PROTECTED'")
}
