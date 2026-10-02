package factories

import "sync"

// factoriesMu guards the class-level singleton state (`_instance` / `_initialized`) of
// every factory in this package. Python relies on the GIL for that.
var factoriesMu sync.Mutex
