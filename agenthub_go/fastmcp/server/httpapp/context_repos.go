package httpapp

import (
	"context"
	"fmt"
	"sort"

	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// ctxRepo adapts one typed context repository to services.UnifiedContextRepository, which
// Python duck-types over entity objects.
type ctxRepo[E any] struct {
	get    func(ctx context.Context, id string) (*E, error)
	create func(ctx context.Context, e *E) (*E, error)
	update func(ctx context.Context, id string, e *E) (*E, error)
	del    func(ctx context.Context, id string) (bool, error)
	list   func(ctx context.Context, filters infrarepos.Kwargs) ([]*E, error)
}

func (r ctxRepo[E]) Get(ctx context.Context, id string) (any, error) {
	e, err := r.get(ctx, id)
	if e == nil || err != nil {
		return nil, err
	}
	return e, nil
}

func (r ctxRepo[E]) Create(ctx context.Context, entity any) (any, error) {
	e, ok := entity.(*E)
	if !ok {
		return nil, fmt.Errorf("unexpected context entity type %T", entity)
	}
	out, err := r.create(ctx, e)
	if out == nil || err != nil {
		return nil, err
	}
	return out, nil
}

func (r ctxRepo[E]) Update(ctx context.Context, id string, entity any) (any, error) {
	e, ok := entity.(*E)
	if !ok {
		return nil, fmt.Errorf("unexpected context entity type %T", entity)
	}
	out, err := r.update(ctx, id, e)
	if out == nil || err != nil {
		return nil, err
	}
	return out, nil
}

func (r ctxRepo[E]) Delete(ctx context.Context, id string) (bool, error) { return r.del(ctx, id) }

func (r ctxRepo[E]) List(ctx context.Context, filters map[string]any) ([]any, error) {
	kw := infrarepos.NewKwargs()
	keys := make([]string, 0, len(filters))
	for k := range filters {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		kw.Set(k, filters[k])
	}
	items, err := r.list(ctx, kw)
	if err != nil {
		return nil, err
	}
	out := make([]any, 0, len(items))
	for _, i := range items {
		out = append(out, i)
	}
	return out, nil
}

// unifiedContextRepositories is factories.UnifiedContextRepositoryBuilder.
func unifiedContextRepositories(sessions *database.SessionManager, userID *string) (global, project, branch, task services.UnifiedContextRepository, err error) {
	g, err := infrarepos.NewGlobalContextRepository(sessions, userID)
	if err != nil {
		return
	}
	p, err := infrarepos.NewProjectContextRepository(sessions, userID)
	if err != nil {
		return
	}
	b, err := infrarepos.NewBranchContextRepository(sessions, userID)
	if err != nil {
		return
	}
	t, err := infrarepos.NewTaskContextRepository(sessions, userID)
	if err != nil {
		return
	}
	global = ctxRepo[entities.GlobalContext]{g.Get, g.Create, g.Update, g.Delete, g.List}
	project = ctxRepo[entities.ProjectContext]{p.Get, p.Create, p.Update, p.Delete, p.List}
	branch = ctxRepo[entities.BranchContext]{b.Get, b.Create, b.Update, b.Delete, b.List}
	task = ctxRepo[entities.TaskContextUnified]{t.Get, t.Create, t.Update, t.Delete, t.List}
	return
}
