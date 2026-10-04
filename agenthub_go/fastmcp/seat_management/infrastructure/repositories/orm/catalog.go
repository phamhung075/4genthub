package orm

import (
	"context"
	"sync"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
)

// DBCatalog adapts a ModuleRepository for one tenant to resolver.Catalog. The resolver
// interface returns only bool, so the first database error is captured and exposed through
// Err.
type DBCatalog struct {
	modules domainrepo.ModuleRepository
	userID  string

	mu  sync.Mutex
	err error
}

var _ resolver.Catalog = (*DBCatalog)(nil)

// NewDBCatalog builds the catalog view of one user's modules.
func NewDBCatalog(modules domainrepo.ModuleRepository, userID string) *DBCatalog {
	return &DBCatalog{modules: modules, userID: userID}
}

// Get returns one module version, or false when it is absent or the lookup failed.
func (c *DBCatalog) Get(slug, version string) (resolver.ModuleVersion, bool) {
	mv, err := c.modules.GetVersion(context.Background(), c.userID, slug, version)
	if err != nil {
		c.record(err)
		return resolver.ModuleVersion{}, false
	}
	if mv == nil {
		return resolver.ModuleVersion{}, false
	}
	return resolver.ModuleVersion{Slug: mv.Slug, Version: mv.Version, Kind: mv.Kind, Content: mv.Content}, true
}

// Err returns the first database error observed, or nil.
func (c *DBCatalog) Err() error {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.err
}

func (c *DBCatalog) record(err error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.err == nil && err != nil {
		c.err = err
	}
}
