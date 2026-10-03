package resolver

import (
	"fmt"
	"strings"
)

// Runtimes a seat can run on: the ones the seat renderer can render. This is the one list;
// validation in the API, rigspec and the seed library, and the renderer, all read it.
const (
	RuntimeClaudeCode = "claude-code"
	RuntimeCodex      = "codex"
	RuntimeAgy        = "agy"
)

// CheckRuntime returns an error naming the supported runtimes unless runtime is one of them.
func CheckRuntime(runtime string) error {
	switch runtime {
	case RuntimeClaudeCode, RuntimeCodex, RuntimeAgy:
		return nil
	}
	supported := []string{RuntimeClaudeCode, RuntimeCodex, RuntimeAgy}
	return fmt.Errorf("unsupported runtime %q: supported runtimes are %s", runtime, strings.Join(supported, ", "))
}
