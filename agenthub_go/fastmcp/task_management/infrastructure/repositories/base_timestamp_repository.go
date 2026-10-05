package repositories

// Base Timestamp Repository (Python repositories/base_timestamp_repository.py): timestamp-aware
// generic CRUD over a generated row struct, extending BaseORMRepository. The SQLAlchemy
// Session/query API is replaced by the ORMRepository helpers plus explicit SQL for the
// timestamp-range, staleness and statistics queries.

import (
	"context"
	"errors"
	"fmt"
	"reflect"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// BaseTimestampRepository is BaseTimestampRepository[ModelType].
type BaseTimestampRepository[M any] struct {
	*ORMRepository[M]
}

// NewBaseTimestampRepository builds the repository for the table named tableName.
func NewBaseTimestampRepository[M any](tableName string, sessions *database.SessionManager) (*BaseTimestampRepository[M], error) {
	base, err := NewORMRepository[M](tableName, sessions)
	if err != nil {
		return nil, err
	}
	return &BaseTimestampRepository[M]{ORMRepository: base}, nil
}

// pkFieldValue returns the primary-key attribute value of entity (hasID is false when the
// primary key is unset, mirroring `entity.id is None`).
func (r *BaseTimestampRepository[M]) pkFieldValue(entity *M) (any, bool) {
	pos, ok := r.byAttr[r.pkAttr]
	if !ok {
		return nil, false
	}
	idx := r.fieldIdx[pos]
	field := reflect.ValueOf(entity).Elem().Field(idx)
	v := field.Interface()
	return v, !baseTimestampRepoIsZero(v)
}

// entityKwargs turns every column of the row into a Python-attribute-keyed value map.
func (r *BaseTimestampRepository[M]) entityKwargs(entity *M) Kwargs {
	row := reflect.ValueOf(entity).Elem()
	kw := NewKwargs()
	for pos, c := range r.Table.Columns {
		kw.Set(c.Attr, row.Field(r.fieldIdx[pos]).Interface())
	}
	return kw
}

// applyAttrs is `setattr(entity, key, value)` for the known columns.
func (r *BaseTimestampRepository[M]) applyAttrs(entity *M, kwargs Kwargs) {
	if kwargs == nil {
		return
	}
	row := reflect.ValueOf(entity).Elem()
	for _, attr := range kwargs.Keys() {
		pos, ok := r.byAttr[attr]
		if !ok {
			continue
		}
		field := row.Field(r.fieldIdx[pos])
		v, _ := kwargs.Get(attr)
		baseTimestampRepoAssign(field, v)
	}
}

// Save handles both new entities (INSERT) and existing entities (UPDATE); timestamps are managed
// by the entity/row timestamp hooks. flush is accepted for signature parity (Go executes the
// statement immediately).
func (r *BaseTimestampRepository[M]) Save(ctx context.Context, entity *M, flush bool) (*M, error) {
	id, hasID := r.pkFieldValue(entity)
	if !hasID {
		out, err := r.Create(ctx, r.entityKwargs(entity))
		if err != nil {
			return nil, baseTimestampRepoError(r.Table.Model, "save", err)
		}
		baseTimestampRepoPublishDomainEvents(entity)
		return out, nil
	}
	if ts, ok := any(entity).(database.Timestamped); ok {
		ts.Touch()
	}
	out, err := r.ORMRepository.Update(ctx, id, r.entityKwargs(entity))
	if err != nil {
		return nil, baseTimestampRepoError(r.Table.Model, "save", err)
	}
	if out == nil {
		// SQLAlchemy merge inserts an entity whose primary key is absent from the table.
		out, err = r.Create(ctx, r.entityKwargs(entity))
		if err != nil {
			return nil, baseTimestampRepoError(r.Table.Model, "save", err)
		}
	}
	baseTimestampRepoPublishDomainEvents(entity)
	return out, nil
}

// Update applies the changes, touches the entity and saves it.
func (r *BaseTimestampRepository[M]) Update(ctx context.Context, entity *M, kwargs Kwargs) (*M, error) {
	r.applyAttrs(entity, kwargs)
	if ts, ok := any(entity).(database.Timestamped); ok {
		ts.Touch()
	}
	return r.Save(ctx, entity, true)
}

// Delete removes the entity and publishes its collected domain events.
func (r *BaseTimestampRepository[M]) Delete(ctx context.Context, entity *M) error {
	id, _ := r.pkFieldValue(entity)
	if _, err := r.ORMRepository.Delete(ctx, id); err != nil {
		return baseTimestampRepoError(r.Table.Model, "delete", err)
	}
	baseTimestampRepoPublishDomainEvents(entity)
	return nil
}

// FindByTimestampRange returns the entities whose timestamp field is between start and end
// (inclusive).
func (r *BaseTimestampRepository[M]) FindByTimestampRange(ctx context.Context, startTime, endTime time.Time, timestampField string) ([]*M, error) {
	if timestampField != "created_at" && timestampField != "updated_at" {
		return nil, exceptions.NewValidationException("Invalid timestamp field: "+timestampField, "", nil)
	}
	var out []*M
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		suffix := fmt.Sprintf(" WHERE %s BETWEEN $1 AND $2", quoteIdent(timestampField))
		rows, err := r.selectRows(ctx, s, suffix, startTime.UTC(), endTime.UTC())
		out = rows
		return err
	})
	if err != nil {
		return nil, baseTimestampRepoError(r.Table.Model, "find", err)
	}
	return out, nil
}

// FindStaleEntities returns the entities not updated within maxStalenessHours.
func (r *BaseTimestampRepository[M]) FindStaleEntities(ctx context.Context, maxStalenessHours int) ([]*M, error) {
	cutoff := time.Now().UTC().Add(-time.Duration(maxStalenessHours) * time.Hour)
	var out []*M
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := r.selectRows(ctx, s, ` WHERE "updated_at" < $1`, cutoff)
		out = rows
		return err
	})
	if err != nil {
		return nil, baseTimestampRepoError(r.Table.Model, "find", err)
	}
	return out, nil
}

// TouchEntity touches the entity with the given id and saves it.
func (r *BaseTimestampRepository[M]) TouchEntity(ctx context.Context, entityID string, reason string) (*M, error) {
	row, err := r.ORMRepository.GetByID(ctx, entityID)
	if err != nil {
		return nil, err
	}
	if row == nil {
		return nil, exceptions.NewResourceNotFoundException(r.Table.Model, entityID,
			fmt.Sprintf("%s with id %s not found", r.Table.Model, entityID))
	}
	if ts, ok := any(row).(database.Timestamped); ok {
		ts.Touch()
	}
	return r.Save(ctx, row, true)
}

// GetTimestampStats returns count / oldest / newest statistics for the table.
func (r *BaseTimestampRepository[M]) GetTimestampStats(ctx context.Context) (*entities.OrderedMap[any], error) {
	stats := entities.NewOrderedMap[any]()
	var count int64
	var oldestCreated, newestCreated, oldestUpdated, newestUpdated *time.Time
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		q := fmt.Sprintf(`SELECT count(*), min("created_at"), max("created_at"), min("updated_at"), max("updated_at") FROM %s`, quoteIdent(r.Table.Name))
		return s.QueryRowContext(ctx, q).Scan(&count, &oldestCreated, &newestCreated, &oldestUpdated, &newestUpdated)
	})
	if err != nil {
		return nil, baseTimestampRepoError(r.Table.Model, "get", err)
	}
	stats.Set("entity_type", r.Table.Model)
	stats.Set("total_count", int(count))
	stats.Set("oldest_created", baseTimestampRepoISO(oldestCreated))
	stats.Set("newest_created", baseTimestampRepoISO(newestCreated))
	stats.Set("oldest_updated", baseTimestampRepoISO(oldestUpdated))
	stats.Set("newest_updated", baseTimestampRepoISO(newestUpdated))
	return stats, nil
}

// ---- helpers -------------------------------------------------------------------

type baseTimestampEventHolder interface {
	GetDomainEvents() []events.Event
	ClearDomainEvents()
}

func baseTimestampRepoPublishDomainEvents[M any](entity *M) {
	if holder, ok := any(entity).(baseTimestampEventHolder); ok {
		_ = holder.GetDomainEvents()
		holder.ClearDomainEvents()
	}
}

func baseTimestampRepoISO(t *time.Time) any {
	if t == nil {
		return nil
	}
	return value_objects.IsoFormat(t.UTC())
}

func baseTimestampRepoIsZero(v any) bool {
	rv := reflect.ValueOf(v)
	for rv.IsValid() && rv.Kind() == reflect.Pointer {
		if rv.IsNil() {
			return true
		}
		rv = rv.Elem()
	}
	if !rv.IsValid() {
		return true
	}
	switch rv.Kind() {
	case reflect.String:
		return rv.Len() == 0
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return rv.Int() == 0
	}
	return rv.IsZero()
}

func baseTimestampRepoAssign(field reflect.Value, v any) {
	if !field.CanSet() || v == nil {
		return
	}
	nv := reflect.ValueOf(v)
	switch {
	case nv.Type().AssignableTo(field.Type()):
		field.Set(nv)
	case nv.Type().ConvertibleTo(field.Type()) && field.Kind() != reflect.Pointer:
		field.Set(nv.Convert(field.Type()))
	}
}

func baseTimestampRepoError(model, action string, err error) error {
	var integrity *exceptions.DatabaseIntegrityException
	if database.IsSQLAlchemyError(err) || errors.As(err, &integrity) {
		return exceptions.NewDatabaseException("Failed to "+action+" "+model+": "+err.Error(), action, "")
	}
	if action == "save" {
		return exceptions.NewDatabaseException("Unexpected error saving entity: "+err.Error(), action, "")
	}
	return exceptions.NewDatabaseException("Failed to "+action+" "+model+": "+err.Error(), action, "")
}
