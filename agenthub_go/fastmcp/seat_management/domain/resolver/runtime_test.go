package resolver

import (
	"strings"
	"testing"
)

func TestCheckRuntime(t *testing.T) {
	for _, runtime := range []string{"claude-code", "codex", "agy", "omp"} {
		if err := CheckRuntime(runtime); err != nil {
			t.Errorf("CheckRuntime(%q) = %v", runtime, err)
		}
	}
	// "pi" stays here deliberately: OpenRig supports it, but the renderer and this list do not
	// until an omp-style decision is made for it.
	for _, runtime := range []string{"pi", "gemini", "", "Codex"} {
		err := CheckRuntime(runtime)
		if err == nil {
			t.Errorf("CheckRuntime(%q) = nil, want an error", runtime)
			continue
		}
		if !strings.Contains(err.Error(), "claude-code") || !strings.Contains(err.Error(), "codex") || !strings.Contains(err.Error(), "agy") || !strings.Contains(err.Error(), "omp") {
			t.Errorf("CheckRuntime(%q) = %q, want the supported runtimes named", runtime, err)
		}
	}
}
