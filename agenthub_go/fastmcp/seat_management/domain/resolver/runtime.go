package resolver

import (
	"fmt"
	"strings"
)

// Runtimes a seat can run on: the ones the seat renderer can render. This is the one list;
// validation in the API, rigspec and the seed library, and the renderer, all read it.
//
// omp (Oh My Pi) is the runtime that carries a non-Anthropic provider: OpenRig passes a seat its
// provider key only when the model is written "provider/id", for example "deepseek/deepseek-flash"
// (OpenRig docs/reference/rig-spec.md, Oh My Pi). Like codex and agy it receives no Claude
// fragment, so it renders guidance and skills only.
const (
	RuntimeClaudeCode = "claude-code"
	RuntimeCodex      = "codex"
	RuntimeAgy        = "agy"
	RuntimeOmp        = "omp"
)

// CheckRuntime returns an error naming the supported runtimes unless runtime is one of them.
func CheckRuntime(runtime string) error {
	switch runtime {
	case RuntimeClaudeCode, RuntimeCodex, RuntimeAgy, RuntimeOmp:
		return nil
	}
	supported := []string{RuntimeClaudeCode, RuntimeCodex, RuntimeAgy, RuntimeOmp}
	return fmt.Errorf("unsupported runtime %q: supported runtimes are %s", runtime, strings.Join(supported, ", "))
}
