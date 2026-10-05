package services

// Agent Discovery Service (Python agent_discovery_service.py).

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

// AgentDiscoveryService ports AgentDiscoveryService.
type AgentDiscoveryService struct{}

// NewAgentDiscoveryService constructs a discovery service.
func NewAgentDiscoveryService() *AgentDiscoveryService {
	return &AgentDiscoveryService{}
}

// GetAvailableAgents ports get_available_agents(): it lists directory entries
// ending in "_agent" under ../../../agent-library/agents relative to this
// module (Python __file__ -> runtime.Caller).
func (s *AgentDiscoveryService) GetAvailableAgents() []string {
	availableAgents := []string{}

	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		return availableAgents
	}
	agentDir := filepath.Join(filepath.Dir(thisFile), "../../../agent-library/agents")

	absAgentDir, err := filepath.Abs(agentDir)
	if err != nil {
		return availableAgents
	}

	info, err := os.Stat(absAgentDir)
	if err != nil || !info.IsDir() {
		return availableAgents
	}

	f, err := os.Open(absAgentDir)
	if err != nil {
		return availableAgents
	}
	defer f.Close()

	entries, err := f.Readdirnames(-1)
	if err != nil {
		return availableAgents
	}
	for _, entry := range entries {
		if !strings.HasSuffix(entry, "_agent") {
			continue
		}
		if fi, err := os.Stat(filepath.Join(absAgentDir, entry)); err == nil && fi.IsDir() {
			availableAgents = append(availableAgents, entry)
		}
	}

	return availableAgents
}
