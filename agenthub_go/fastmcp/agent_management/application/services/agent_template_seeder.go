package services

import (
	"context"
	"fmt"
	"os"

	"agenthub/fastmcp/agent_management/domain/repositories"
)

// SeedAgentTemplates stores every agent-library template through the repository.
// It is idempotent by slug: an existing template keeps its id and is overwritten with
// the library content, so the YAML library stays the single source of truth. It fails
// when any agent directory cannot be loaded instead of silently seeding a partial set.
func SeedAgentTemplates(ctx context.Context, loader *YAMLAgentTemplateLoader, repo repositories.AgentTemplateRepository) (int, error) {
	entries, err := os.ReadDir(loader.AgentsPath)
	if err != nil {
		return 0, fmt.Errorf("read agents dir: %w", err)
	}
	expected := 0
	for _, entry := range entries {
		if entry.IsDir() {
			expected++
		}
	}

	templates := loader.LoadAllAgents()
	if len(templates) != expected {
		return 0, fmt.Errorf("loaded %d of %d agent directories in %s", len(templates), expected, loader.AgentsPath)
	}

	for _, template := range templates {
		existing, err := repo.FindBySlug(ctx, template.Slug)
		if err != nil {
			return 0, fmt.Errorf("find %s: %w", template.Slug, err)
		}
		if existing != nil {
			template.ID = existing.ID
		}
		if _, err := repo.Save(ctx, template); err != nil {
			return 0, fmt.Errorf("save %s: %w", template.Slug, err)
		}
	}
	return len(templates), nil
}
