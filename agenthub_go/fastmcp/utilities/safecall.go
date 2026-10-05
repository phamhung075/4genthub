package utilities

// SafeCall runs fn and reports whether it panicked. It is the counterpart of Python's
// `except Exception` around one unit of background work: the failure is swallowed (Python
// logs it) so a panic in one iteration cannot take the whole process down. It returns the
// recovered value, or nil when fn completed.
func SafeCall(fn func()) (recovered any) {
	defer func() { recovered = recover() }()
	fn()
	return nil
}
