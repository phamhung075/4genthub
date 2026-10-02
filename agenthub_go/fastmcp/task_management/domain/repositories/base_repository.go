// Package repositories ports task_management/domain/repositories: persistence
// contracts of the domain layer. Every method takes a context.Context and
// returns an error in addition to the Python return value.
package repositories

import (
	"context"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// BaseRepository provides standardized operations for all domain repositories.
type BaseRepository[T any] interface {
	// FindByCriteria finds entities by multiple criteria with optional pagination.
	FindByCriteria(ctx context.Context, filters map[string]any, pagination *value_objects.PaginationRequest) (value_objects.PaginationResult[T], error)
	// FindAll finds all entities with optional pagination.
	FindAll(ctx context.Context, pagination *value_objects.PaginationRequest) (value_objects.PaginationResult[T], error)
	// Count returns the total number of entities.
	Count(ctx context.Context) (int, error)
	// CountByCriteria counts entities matching the criteria.
	CountByCriteria(ctx context.Context, filters map[string]any) (int, error)
	// Exists checks whether an entity exists by its identifier.
	Exists(ctx context.Context, entityID any) (bool, error)
	// BulkSave saves multiple entities in a single operation.
	BulkSave(ctx context.Context, entities []T) ([]T, error)
	// BulkDelete deletes entities by identifier and returns the number deleted.
	BulkDelete(ctx context.Context, entityIDs []any) (int, error)
}
