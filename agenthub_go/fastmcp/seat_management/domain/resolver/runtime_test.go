package resolver

import (
	"strings"
	"testing"
)

func TestCheckRuntime(t *testing.T) {
	for _, runtime := range []string{"claude-code", "codex", "agy"} {
		if err := CheckRuntime(runtime); err != nil {
			t.Errorf("CheckRuntime(%q) = %v", runtime, err)
		}
	}
	for _, runtime := range []string{"pi", "omp", "gemini", "", "Codex"} {
		err := CheckRuntime(runtime)
		if err == nil {
			t.Errorf("CheckRuntime(%q) = nil, want an error", runtime)
			continue
		}
		if !strings.Contains(err.Error(), "claude-code") || !strings.Contains(err.Error(), "codex") || !strings.Contains(err.Error(), "agy") {
			t.Errorf("CheckRuntime(%q) = %q, want the supported runtimes named", runtime, err)
		}
	}
}
