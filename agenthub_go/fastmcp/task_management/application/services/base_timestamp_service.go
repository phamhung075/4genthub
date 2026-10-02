package services

import (
	"context"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
)

// BaseTimestampService ports application/services/base_timestamp_service.py.
//
// Python's ABC + Generic becomes a Go generic struct. The three abstract
// methods (_validate_business_rules, _get_entity_type_name,
// _create_entity_from_data) are function fields supplied at construction, and
// the two overridable hooks (_validate_deletion_allowed, _can_cleanup_entity)
// are optional function fields. Errors mirror the Python exception types.

// TimestampEntity is the subset of BaseTimestampEntity used by the service.
type TimestampEntity interface {
	Touch(reason string) error
	GetEntityID() string
}

// BaseTimestampRepository is the minimal repository contract the service needs
// (the Go infrastructure BaseTimestampRepository is a concrete generic struct
// and lacks GetByID, so the application layer declares this interface).
type BaseTimestampRepository[T TimestampEntity] interface {
	Save(ctx context.Context, entity T) (T, error)
	GetByID(ctx context.Context, entityID string) (T, bool, error)
	Delete(ctx context.Context, entity T) error
	TouchEntity(ctx context.Context, entityID, reason string) (T, error)
	FindByTimestampRange(ctx context.Context, start, end time.Time, timestampField string) ([]T, error)
	FindStaleEntities(ctx context.Context, maxStalenessHours int) ([]T, error)
	GetTimestampStats(ctx context.Context) (*entities.OrderedMap[any], error)
}

// BaseTimestampService is the generic application service.
type BaseTimestampService[T TimestampEntity] struct {
	repository BaseTimestampRepository[T]

	// Abstract methods, overridden by concrete service constructors.
	ValidateBusinessRules func(entity T) error
	GetEntityTypeName     func() string
	CreateEntityFromData  func(entityData map[string]any) (T, error)

	// Overridable hooks (defaults mirror Python).
	ValidateDeletionAllowed func(entity T) error
	CanCleanupEntity        func(entity T) bool
}

// NewBaseTimestampService builds the base service. Concrete services set the
// abstract function fields after construction.
func NewBaseTimestampService[T TimestampEntity](repository BaseTimestampRepository[T]) *BaseTimestampService[T] {
	return &BaseTimestampService[T]{repository: repository}
}

func (s *BaseTimestampService[T]) entityType() string {
	if s.GetEntityTypeName != nil {
		return s.GetEntityTypeName()
	}
	return ""
}

func (s *BaseTimestampService[T]) validateBusinessRules(entity T) error {
	if s.ValidateBusinessRules != nil {
		return s.ValidateBusinessRules(entity)
	}
	return nil
}

func (s *BaseTimestampService[T]) validateDeletionAllowed(entity T) error {
	if s.ValidateDeletionAllowed != nil {
		return s.ValidateDeletionAllowed(entity)
	}
	return nil
}

func (s *BaseTimestampService[T]) canCleanupEntity(entity T) bool {
	if s.CanCleanupEntity != nil {
		return s.CanCleanupEntity(entity)
	}
	return true
}

func (s *BaseTimestampService[T]) entityID(entity T) string { return entity.GetEntityID() }

// CreateEntity creates a new entity with automatic timestamp management.
func (s *BaseTimestampService[T]) CreateEntity(ctx context.Context, entityData map[string]any, validationCallback func(entity T) error) (T, error) {
	var zero T

	entity, err := s.CreateEntityFromData(entityData)
	if err != nil {
		var zeroDB T
		return zeroDB, exceptions.NewDatabaseException("Failed to create "+s.entityType()+": "+err.Error(), "create", strings.ToLower(s.entityType()))
	}

	if err := s.validateBusinessRules(entity); err != nil {
		return zero, err
	}
	if validationCallback != nil {
		if err := validationCallback(entity); err != nil {
			return zero, err
		}
	}

	saved, err := s.repository.Save(ctx, entity)
	if err != nil {
		return zero, exceptions.NewDatabaseException("Failed to create "+s.entityType()+": "+err.Error(), "create", strings.ToLower(s.entityType()))
	}
	_ = s.entityID(saved)
	return saved, nil
}

// UpdateEntity updates an entity with automatic timestamp management.
func (s *BaseTimestampService[T]) UpdateEntity(ctx context.Context, entityID string, updates map[string]any, touchReason *string) (T, error) {
	var zero T

	entity, found, err := s.repository.GetByID(ctx, entityID)
	if err != nil {
		return zero, exceptions.NewDatabaseException("Failed to update "+s.entityType()+": "+err.Error(), "update", strings.ToLower(s.entityType()))
	}
	if !found {
		return zero, exceptions.NewResourceNotFoundException(s.entityType(), entityID, s.entityType()+" with id "+entityID+" not found")
	}

	if err := s.ApplyUpdatesToEntity(entity, updates); err != nil {
		return zero, err
	}
	if err := s.validateBusinessRules(entity); err != nil {
		return zero, err
	}

	reason := ""
	if touchReason != nil {
		reason = *touchReason
	} else {
		reason = strings.ToLower(s.entityType()) + "_updated"
	}
	if err := entity.Touch(reason); err != nil {
		return zero, err
	}

	updated, err := s.repository.Save(ctx, entity)
	if err != nil {
		return zero, exceptions.NewDatabaseException("Failed to update "+s.entityType()+": "+err.Error(), "update", strings.ToLower(s.entityType()))
	}
	return updated, nil
}

// GetEntity returns the entity and whether it was found.
func (s *BaseTimestampService[T]) GetEntity(ctx context.Context, entityID string) (T, bool, error) {
	entity, found, err := s.repository.GetByID(ctx, entityID)
	if err != nil {
		var zero T
		return zero, false, exceptions.NewDatabaseException("Failed to retrieve "+s.entityType()+": "+err.Error(), "read", strings.ToLower(s.entityType()))
	}
	return entity, found, nil
}

// DeleteEntity deletes by id, raising when it does not exist.
func (s *BaseTimestampService[T]) DeleteEntity(ctx context.Context, entityID string) error {
	entity, found, err := s.repository.GetByID(ctx, entityID)
	if err != nil {
		return exceptions.NewDatabaseException("Failed to delete "+s.entityType()+": "+err.Error(), "delete", strings.ToLower(s.entityType()))
	}
	if !found {
		return exceptions.NewResourceNotFoundException(s.entityType(), entityID, s.entityType()+" with id "+entityID+" not found")
	}
	if err := s.validateDeletionAllowed(entity); err != nil {
		return err
	}
	if err := s.repository.Delete(ctx, entity); err != nil {
		return exceptions.NewDatabaseException("Failed to delete "+s.entityType()+": "+err.Error(), "delete", strings.ToLower(s.entityType()))
	}
	return nil
}

// TouchEntity updates only the entity timestamp.
func (s *BaseTimestampService[T]) TouchEntity(ctx context.Context, entityID, reason string) (T, error) {
	return s.repository.TouchEntity(ctx, entityID, reason)
}

// FindEntitiesByTimestampRange finds entities within a timestamp range.
func (s *BaseTimestampService[T]) FindEntitiesByTimestampRange(ctx context.Context, startTime, endTime time.Time, timestampField string) ([]T, error) {
	if startTime.After(endTime) {
		return nil, exceptions.NewValidationException("Start time must be before end time", "start_time", startTime)
	}
	return s.repository.FindByTimestampRange(ctx, startTime, endTime, timestampField)
}

// FindStaleEntities finds entities not updated recently.
func (s *BaseTimestampService[T]) FindStaleEntities(ctx context.Context, maxStalenessHours int) ([]T, error) {
	if maxStalenessHours < 1 {
		return nil, exceptions.NewValidationException("Max staleness must be at least 1 hour", "max_staleness_hours", maxStalenessHours)
	}
	return s.repository.FindStaleEntities(ctx, maxStalenessHours)
}

// GetTimestampStatistics returns repository timestamp stats.
func (s *BaseTimestampService[T]) GetTimestampStatistics(ctx context.Context) (*entities.OrderedMap[any], error) {
	return s.repository.GetTimestampStats(ctx)
}

// CleanupStaleEntities deletes (or dry-runs) very stale entities.
func (s *BaseTimestampService[T]) CleanupStaleEntities(ctx context.Context, maxStalenessDays int, dryRun bool) (*entities.OrderedMap[any], error) {
	if maxStalenessDays < 1 {
		return nil, exceptions.NewValidationException("Max staleness must be at least 1 day", "max_staleness_days", maxStalenessDays)
	}

	staleEntities, err := s.FindStaleEntities(ctx, maxStalenessDays*24)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Cleanup failed: "+err.Error(), "cleanup", strings.ToLower(s.entityType()))
	}

	result := entities.NewOrderedMap[any]()
	if dryRun {
		ids := make([]any, 0, len(staleEntities))
		for _, e := range staleEntities {
			ids = append(ids, s.entityID(e))
		}
		result.Set("dry_run", true)
		result.Set("entities_to_delete", len(staleEntities))
		result.Set("entity_ids", ids)
		return result, nil
	}

	deletedCount := 0
	errorsList := []string{}
	for _, entity := range staleEntities {
		if s.canCleanupEntity(entity) {
			if err := s.repository.Delete(ctx, entity); err != nil {
				errorsList = append(errorsList, "Failed to delete "+s.entityID(entity)+": "+err.Error())
				continue
			}
			deletedCount++
		}
	}

	result.Set("dry_run", false)
	result.Set("entities_deleted", deletedCount)
	result.Set("entities_failed", len(errorsList))
	result.Set("errors", errorsList)
	return result, nil
}

// ApplyUpdatesToEntity is the default update logic: set known map keys. The Go
// entities do not expose arbitrary attribute reflection, so this records the
// updates on the entity only when it implements the optional setter interface;
// otherwise the Python "attribute not found" warning branch is taken.
func (s *BaseTimestampService[T]) ApplyUpdatesToEntity(entity T, updates map[string]any) error {
	if setter, ok := any(entity).(interface {
		ApplyUpdate(key string, value any) (bool, error)
	}); ok {
		for key, value := range updates {
			if _, err := setter.ApplyUpdate(key, value); err != nil {
				return err
			}
		}
	}
	return nil
}
