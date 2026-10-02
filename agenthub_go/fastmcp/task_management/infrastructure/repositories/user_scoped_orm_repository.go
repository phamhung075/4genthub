package repositories

// User-Scoped ORM Repository (Python repositories/user_scoped_orm_repository.py): the ORM
// repository combined with user-based data isolation. Audit logging (log_access) is dropped.

import (
	"context"
	"fmt"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// UserScopedORMRepository is UserScopedORMRepository[M].
type UserScopedORMRepository[M any] struct {
	*ORMRepository[M]
	UserScope
}

// NewUserScopedORMRepository builds the repository for tableName scoped to userID (nil = system mode).
func NewUserScopedORMRepository[M any](tableName string, sessions *database.SessionManager, userID *string) (*UserScopedORMRepository[M], error) {
	base, err := NewORMRepository[M](tableName, sessions)
	if err != nil {
		return nil, err
	}
	return &UserScopedORMRepository[M]{ORMRepository: base, UserScope: NewUserScope(userID)}, nil
}

// scoped merges the user filter with the extra filters (user filter first).
func (r *UserScopedORMRepository[M]) scoped(extra Kwargs) Kwargs {
	out := r.GetUserFilter()
	if extra != nil {
		for _, k := range extra.Keys() {
			v, _ := extra.Get(k)
			out.Set(k, v)
		}
	}
	return out
}

// GetByID gets a model by ID within the user's data.
func (r *UserScopedORMRepository[M]) GetByID(ctx context.Context, id any) (*M, error) {
	return r.FindOneBy(ctx, NewKwargs(r.pkAttr, id))
}

// GetAll gets all models of the user (offset then limit when truthy).
func (r *UserScopedORMRepository[M]) GetAll(ctx context.Context, limit, offset *int) ([]*M, error) {
	var out []*M
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(r.GetUserFilter(), 1)
		if err != nil {
			return err
		}
		if limit != nil && *limit != 0 {
			w += fmt.Sprintf(" LIMIT %d", *limit)
		}
		if offset != nil && *offset != 0 {
			w += fmt.Sprintf(" OFFSET %d", *offset)
		}
		rows, err := r.selectRows(ctx, s, w, args...)
		out = rows
		return err
	})
	return out, err
}

// Create injects the user id (an error in system mode) and creates the record.
func (r *UserScopedORMRepository[M]) Create(ctx context.Context, kwargs Kwargs) (*M, error) {
	kwargs, err := r.SetUserID(kwargs)
	if err != nil {
		return nil, err
	}
	return r.ORMRepository.Create(ctx, kwargs)
}

// ownerOf reads the user id of a loaded row (rows without user_id are not owned by anyone).
type userIDGetter interface{ GetUserID() string }

func (r *UserScopedORMRepository[M]) checkOwnership(row *M) error {
	if g, ok := any(row).(userIDGetter); ok {
		return r.EnsureUserOwnership(g)
	}
	return nil
}

// Update updates a model of the user; user_id cannot be changed.
func (r *UserScopedORMRepository[M]) Update(ctx context.Context, id any, kwargs Kwargs) (*M, error) {
	var out *M
	err := r.Transaction(ctx, func(ctx context.Context) error {
		cur, err := r.GetByID(ctx, id)
		if err != nil || cur == nil {
			return err
		}
		if err := r.checkOwnership(cur); err != nil {
			return err
		}
		clean := entities.NewOrderedMap[any]()
		for _, k := range kwargs.Keys() {
			if k == "user_id" {
				continue
			}
			v, _ := kwargs.Get(k)
			clean.Set(k, v)
		}
		out, err = r.ORMRepository.Update(ctx, id, clean)
		return err
	})
	return out, err
}

// Delete deletes a model of the user.
func (r *UserScopedORMRepository[M]) Delete(ctx context.Context, id any) (bool, error) {
	deleted := false
	err := r.Transaction(ctx, func(ctx context.Context) error {
		cur, err := r.GetByID(ctx, id)
		if err != nil || cur == nil {
			return err
		}
		if err := r.checkOwnership(cur); err != nil {
			return err
		}
		deleted, err = r.ORMRepository.Delete(ctx, id)
		return err
	})
	return deleted, err
}

// FindBy finds models by filters within the user's data.
func (r *UserScopedORMRepository[M]) FindBy(ctx context.Context, filters Kwargs) ([]*M, error) {
	return r.ORMRepository.FindBy(ctx, r.scoped(filters))
}

// FindOneBy finds one model by filters within the user's data.
func (r *UserScopedORMRepository[M]) FindOneBy(ctx context.Context, filters Kwargs) (*M, error) {
	return r.ORMRepository.FindOneBy(ctx, r.scoped(filters))
}

// Count counts models within the user's data.
func (r *UserScopedORMRepository[M]) Count(ctx context.Context, filters Kwargs) (int, error) {
	return r.ORMRepository.Count(ctx, r.scoped(filters))
}

// Exists reports whether a model exists within the user's data.
func (r *UserScopedORMRepository[M]) Exists(ctx context.Context, filters Kwargs) (bool, error) {
	n, err := r.Count(ctx, filters)
	return n > 0, err
}

// BulkCreate injects the user id into every record and creates them.
func (r *UserScopedORMRepository[M]) BulkCreate(ctx context.Context, records []Kwargs) ([]*M, error) {
	for i, rec := range records {
		rec, err := r.SetUserID(rec)
		if err != nil {
			return nil, err
		}
		records[i] = rec
	}
	return r.ORMRepository.BulkCreate(ctx, records)
}

func (r *UserScopedORMRepository[M]) idsCondition(ids []any, argStart int) (string, []any, error) {
	pk := r.Table.Columns[r.byAttr[r.pkAttr]]
	var holders []string
	var args []any
	for _, id := range ids {
		bv, err := bind(pk, id)
		if err != nil {
			return "", nil, err
		}
		args = append(args, bv)
		holders = append(holders, fmt.Sprintf("$%d", argStart+len(args)-1))
	}
	if len(holders) == 0 {
		return "false", nil, nil
	}
	return r.pkColumn() + " IN (" + strings.Join(holders, ", ") + ")", args, nil
}

// BulkUpdate updates the given ids of the user and returns the affected count; user_id is ignored.
func (r *UserScopedORMRepository[M]) BulkUpdate(ctx context.Context, ids []any, updates Kwargs) (int, error) {
	count := 0
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var sets []string
		var args []any
		for _, attr := range updates.Keys() {
			if attr == "user_id" {
				continue
			}
			pos, ok := r.byAttr[attr]
			if !ok {
				return &ValueError{Msg: fmt.Sprintf("Entity namespace for %q has no property %q", r.Table.Name, attr)}
			}
			v, _ := updates.Get(attr)
			c := r.Table.Columns[pos]
			bv, err := bind(c, v)
			if err != nil {
				return err
			}
			args = append(args, bv)
			sets = append(sets, fmt.Sprintf("%s = $%d", quoteIdent(c.Name), len(args)))
		}
		w, wargs, err := r.where(r.GetUserFilter(), len(args)+1)
		if err != nil {
			return err
		}
		args = append(args, wargs...)
		cond, idArgs, err := r.idsCondition(ids, len(args)+1)
		if err != nil {
			return err
		}
		args = append(args, idArgs...)
		if w == "" {
			w = " WHERE " + cond
		} else {
			w += " AND " + cond
		}
		if len(sets) == 0 {
			return nil
		}
		res, err := s.ExecContext(ctx, fmt.Sprintf("UPDATE %s SET %s%s", quoteIdent(r.Table.Name), strings.Join(sets, ", "), w), args...)
		if err != nil {
			return err
		}
		n, _ := res.RowsAffected()
		count = int(n)
		return nil
	})
	return count, err
}

// BulkDelete deletes the given ids of the user and returns the count that existed.
func (r *UserScopedORMRepository[M]) BulkDelete(ctx context.Context, ids []any) (int, error) {
	count := 0
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(r.GetUserFilter(), 1)
		if err != nil {
			return err
		}
		cond, idArgs, err := r.idsCondition(ids, len(args)+1)
		if err != nil {
			return err
		}
		args = append(args, idArgs...)
		if w == "" {
			w = " WHERE " + cond
		} else {
			w += " AND " + cond
		}
		if err := s.QueryRowContext(ctx, fmt.Sprintf("SELECT count(*) FROM %s%s", quoteIdent(r.Table.Name), w), args...).Scan(&count); err != nil {
			return err
		}
		_, err = s.ExecContext(ctx, fmt.Sprintf("DELETE FROM %s%s", quoteIdent(r.Table.Name), w), args...)
		return err
	})
	return count, err
}
