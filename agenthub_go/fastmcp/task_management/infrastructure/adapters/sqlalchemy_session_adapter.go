// sqlalchemy_session_adapter.go ports task_management/infrastructure/adapters/sqlalchemy_session_adapter.py.
package adapters

import (
	"database/sql"
	"sync"

	"agenthub/fastmcp/task_management/domain/interfaces"
)

// SQLAlchemyQuery is the adapter implementation of interfaces.IQuery.
type SQLAlchemyQuery struct {
	modelClass any
	criterion  []any
	filterBy   map[string]any
	orderBy    []any
	limitVal   *int
	offsetVal  *int
	items      []any
}

func NewSQLAlchemyQuery(modelClass any) *SQLAlchemyQuery {
	return &SQLAlchemyQuery{
		modelClass: modelClass,
		filterBy:   make(map[string]any),
		items:      make([]any, 0),
	}
}

func (q *SQLAlchemyQuery) Filter(criterion ...any) interfaces.IQuery {
	newQ := *q
	newQ.criterion = append(append([]any(nil), q.criterion...), criterion...)
	return &newQ
}

func (q *SQLAlchemyQuery) FilterBy(kwargs map[string]any) interfaces.IQuery {
	newQ := *q
	newQ.filterBy = make(map[string]any, len(q.filterBy)+len(kwargs))
	for k, v := range q.filterBy {
		newQ.filterBy[k] = v
	}
	for k, v := range kwargs {
		newQ.filterBy[k] = v
	}
	return &newQ
}

func (q *SQLAlchemyQuery) First() (any, error) {
	if len(q.items) > 0 {
		return q.items[0], nil
	}
	return nil, nil
}

func (q *SQLAlchemyQuery) All() ([]any, error) {
	res := make([]any, len(q.items))
	copy(res, q.items)
	return res, nil
}

func (q *SQLAlchemyQuery) Count() (int, error) {
	return len(q.items), nil
}

func (q *SQLAlchemyQuery) OrderBy(criterion ...any) interfaces.IQuery {
	newQ := *q
	newQ.orderBy = append(append([]any(nil), q.orderBy...), criterion...)
	return &newQ
}

func (q *SQLAlchemyQuery) Limit(limit int) interfaces.IQuery {
	newQ := *q
	newQ.limitVal = &limit
	return &newQ
}

func (q *SQLAlchemyQuery) Offset(offset int) interfaces.IQuery {
	newQ := *q
	newQ.offsetVal = &offset
	return &newQ
}

// SQLAlchemySessionAdapter adapts database session operations to interfaces.IDatabaseSession.
type SQLAlchemySessionAdapter struct {
	db     *sql.DB
	tx     *sql.Tx
	closed bool
	mu     sync.Mutex
}

func NewSQLAlchemySessionAdapter(db *sql.DB) *SQLAlchemySessionAdapter {
	return &SQLAlchemySessionAdapter{db: db}
}

func (s *SQLAlchemySessionAdapter) Query(modelClass any) interfaces.IQuery {
	return NewSQLAlchemyQuery(modelClass)
}

func (s *SQLAlchemySessionAdapter) Add(instance any) error {
	return nil
}

func (s *SQLAlchemySessionAdapter) Delete(instance any) error {
	return nil
}

func (s *SQLAlchemySessionAdapter) Commit() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.tx != nil {
		err := s.tx.Commit()
		s.tx = nil
		return err
	}
	return nil
}

func (s *SQLAlchemySessionAdapter) Rollback() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.tx != nil {
		err := s.tx.Rollback()
		s.tx = nil
		return err
	}
	return nil
}

func (s *SQLAlchemySessionAdapter) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.closed = true
	if s.tx != nil {
		_ = s.tx.Rollback()
		s.tx = nil
	}
	return nil
}

func (s *SQLAlchemySessionAdapter) Flush() error {
	return nil
}

// SQLAlchemySessionFactory is interfaces.IDatabaseSessionFactory.
type SQLAlchemySessionFactory struct {
	db *sql.DB
}

func NewSQLAlchemySessionFactory() *SQLAlchemySessionFactory {
	return &SQLAlchemySessionFactory{}
}

func (f *SQLAlchemySessionFactory) CreateSession() (interfaces.IDatabaseSession, func() error, error) {
	sess := NewSQLAlchemySessionAdapter(f.db)
	closeFn := func() error {
		return sess.Close()
	}
	return sess, closeFn, nil
}

func (f *SQLAlchemySessionFactory) GetSession() (interfaces.IDatabaseSession, error) {
	return NewSQLAlchemySessionAdapter(f.db), nil
}
