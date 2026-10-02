package interfaces

// IDatabaseSession is the database session contract (SQLAlchemy-style unit of work).
type IDatabaseSession interface {
	Query(modelClass any) IQuery
	Add(instance any) error
	Delete(instance any) error
	Commit() error
	Rollback() error
	Close() error
	Flush() error
}

// IQuery is the chainable query contract.
type IQuery interface {
	Filter(criterion ...any) IQuery
	FilterBy(kwargs map[string]any) IQuery
	First() (any, error)
	All() ([]any, error)
	Count() (int, error)
	OrderBy(criterion ...any) IQuery
	Limit(limit int) IQuery
	Offset(offset int) IQuery
}

// IDatabaseSessionFactory creates database sessions.
type IDatabaseSessionFactory interface {
	// CreateSession opens a session scoped to the returned close function
	// (Python's @contextmanager: the session is committed/closed on exit).
	CreateSession() (session IDatabaseSession, closeFn func() error, err error)
	GetSession() (IDatabaseSession, error)
}
