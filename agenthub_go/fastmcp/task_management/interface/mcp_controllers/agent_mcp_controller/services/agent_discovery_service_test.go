package services

// Expectations taken from Python
// task_management/interface/mcp_controllers/agent_mcp_controller/services/agent_discovery_service.py

import (
	"strings"
	"testing"
)

func TestGetAvailableAgentsFiltersAgentDirectories(t *testing.T) {
	s := NewAgentDiscoveryService()

	got := s.GetAvailableAgents()

	if got == nil {
		t.Fatal("expected a non-nil slice (Python returns an empty list)")
	}
	for _, name := range got {
		if !strings.HasSuffix(name, "_agent") {
			t.Errorf("entry %q does not end with _agent", name)
		}
	}
}
