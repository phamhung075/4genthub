package facades

// The read's resolution of the 4-31 hex ADDRESS form.
//
// WHY. TestTaskReadRouteHandsAPrefixToItsResolver in fastmcp/server/httpapp proves the read ROUTE does
// not refuse a prefix and hands it on unchanged; it cannot prove the resolution itself, and a
// regression in readableTaskID would leave it green. This test is that proof: it drives the reader
// over a repository fake and asserts what it returns for one match, several and none.

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

const (
	prefixTaskUUID    = "403d16ca-89df-4ccf-88f3-b0084dbac309"
	prefixTaskUUIDTwo = "403d16ca-1111-4222-8333-444455556666"
	readAddress       = "403d16ca"
)

// prefixTaskRepo answers the one query this reader makes and counts it. The embedded port is nil: any
// other call panics, which is how the test knows the reader resolved the address and did not fall
// through to a second read.
type prefixTaskRepo struct {
	FacadeTaskRepository
	rows    []*entities.Task
	calls   int
	filters map[string]any
}

func (r *prefixTaskRepo) FindByCriteria(_ context.Context, filters map[string]any, _ repositories.ListQuery) ([]*entities.Task, error) {
	r.calls++
	r.filters = filters
	return r.rows, nil
}

func prefixTask(t *testing.T, id string) *entities.Task {
	t.Helper()
	value, err := value_objects.NewTaskId(id)
	if err != nil {
		t.Fatalf("NewTaskId(%q): %v", id, err)
	}
	return &entities.Task{ID: &value}
}

func TestReadableTaskIDResolvesTheAddressFormToTheOneRowThatStartsWithIt(t *testing.T) {
	repo := &prefixTaskRepo{rows: []*entities.Task{prefixTask(t, prefixTaskUUID)}}
	f := &TaskApplicationFacade{taskRepository: repo}

	got, err := f.readableTaskID(context.Background(), readAddress)
	if err != nil {
		t.Fatalf("readableTaskID(%q): %v", readAddress, err)
	}
	if got != prefixTaskUUID {
		t.Fatalf("readableTaskID(%q) = %q, want %q", readAddress, got, prefixTaskUUID)
	}
	if repo.calls != 1 {
		t.Fatalf("the reader made %d prefix queries, want 1", repo.calls)
	}
	if got, want := repo.filters["id_prefix"], readAddress; got != want {
		t.Fatalf("the reader queried id_prefix %v, want %v", got, want)
	}
}

func TestReadableTaskIDRefusesAnAmbiguousAddressByNamingBothRows(t *testing.T) {
	repo := &prefixTaskRepo{rows: []*entities.Task{prefixTask(t, prefixTaskUUID), prefixTask(t, prefixTaskUUIDTwo)}}
	f := &TaskApplicationFacade{taskRepository: repo}

	got, err := f.readableTaskID(context.Background(), readAddress)
	if err == nil {
		t.Fatalf("an ambiguous address resolved to %q, want a refusal", got)
	}
	for _, want := range []string{"ambiguous", prefixTaskUUID, prefixTaskUUIDTwo} {
		if !strings.Contains(err.Error(), want) {
			t.Fatalf("the refusal does not name %q: %v", want, err)
		}
	}
}

func TestReadableTaskIDLeavesACallerErrorToTheCallersOwnAnswer(t *testing.T) {
	// No match: the reader hands the caller's own spelling back so the not-found it already has stands.
	repo := &prefixTaskRepo{}
	f := &TaskApplicationFacade{taskRepository: repo}
	if got, err := f.readableTaskID(context.Background(), readAddress); err != nil || got != readAddress {
		t.Fatalf("readableTaskID(%q) = %q, %v; want the input unchanged and no error", readAddress, got, err)
	}
}

func TestReadableTaskIDDoesNotQueryForAValueThatIsNotAnAddress(t *testing.T) {
	// A test-style name is a TaskId NewTaskId accepts but no address: reading it must not reach the
	// prefix query at all, so the nil embedded port stays unreachable and calls stays 0.
	repo := &prefixTaskRepo{}
	f := &TaskApplicationFacade{taskRepository: repo}
	for _, raw := range []string{"my-test-1", "403d16ca-89df-4ccf-88f3-b0084dbac309", "{abc}"} {
		got, err := f.readableTaskID(context.Background(), raw)
		if err != nil || got != raw {
			t.Fatalf("readableTaskID(%q) = %q, %v; want unchanged and no error", raw, got, err)
		}
	}
	if repo.calls != 0 {
		t.Fatalf("the reader ran %d prefix queries for non-address values, want 0", repo.calls)
	}
}
