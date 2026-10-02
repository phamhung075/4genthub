package repositories

// Clean timestamp repository mixin (Python repositories/clean_timestamp_repository_mixin.py):
// helpers that keep the timestamp semantics of BaseTimestampEntity-derived entities consistent
// when they are persisted. The abstract _perform_save / _perform_bulk_save methods become the
// CleanTimestampRepositoryImpl interface supplied by the concrete repository.

import (
	"reflect"
	"time"
)

// CleanTimestampEntity is the entity surface the mixin uses: BaseTimestampEntity.touch.
type CleanTimestampEntity interface {
	Touch(reason string) error
}

// CleanTimestampRepositoryImpl is the concrete persistence the mixin delegates to
// (Python's abstract _perform_save / _perform_bulk_save).
type CleanTimestampRepositoryImpl[T CleanTimestampEntity] interface {
	PerformSave(entity T) (T, error)
	PerformBulkSave(entities []T) ([]T, error)
}

// CleanTimestampRepository encapsulates clean timestamp persistence patterns.
type CleanTimestampRepository[T CleanTimestampEntity] struct {
	Impl CleanTimestampRepositoryImpl[T]
}

// SaveWithCleanTimestamp persists one entity with automatic timestamp management.
func (r *CleanTimestampRepository[T]) SaveWithCleanTimestamp(entity T, reason string) (T, error) {
	if err := entity.Touch(reason); err != nil {
		var zero T
		return zero, err
	}
	return r.Impl.PerformSave(entity)
}

// SaveBulkWithConsistentTimestamp persists several entities with one consistent timestamp.
func (r *CleanTimestampRepository[T]) SaveBulkWithConsistentTimestamp(entities []T, reason string) ([]T, error) {
	if len(entities) == 0 {
		return []T{}, nil
	}
	consistentTimestamp := time.Now().UTC()
	for _, entity := range entities {
		// touch captures the domain events, then the consistent timestamp overrides updated_at.
		if err := entity.Touch(reason); err != nil {
			return nil, err
		}
		cleanTimestampSetUpdatedAt(entity, &consistentTimestamp)
	}
	return r.Impl.PerformBulkSave(entities)
}

// cleanTimestampSetUpdatedAt is `entity.updated_at = <ts>`. Go entities expose UpdatedAt as a
// promoted field without a setter, so it is assigned reflectively.
func cleanTimestampSetUpdatedAt(entity any, ts *time.Time) {
	v := reflect.ValueOf(entity)
	for v.Kind() == reflect.Pointer {
		if v.IsNil() {
			return
		}
		v = v.Elem()
	}
	if v.Kind() != reflect.Struct {
		return
	}
	field := v.FieldByName("UpdatedAt")
	if field.IsValid() && field.CanSet() && field.Type() == reflect.TypeOf((*time.Time)(nil)) {
		field.Set(reflect.ValueOf(ts))
	}
}
