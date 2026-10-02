// Package exceptions ports task_management/domain/exceptions.
//
// Python exception classes map to Go structs that embed their parent and expose
// it through Unwrap, so errors.As(err, &parentPtr) mirrors isinstance checks.
package exceptions

// DomainException is the base class for all domain exceptions.
type DomainException struct{ Msg string }

func (e *DomainException) Error() string { return e.Msg }
