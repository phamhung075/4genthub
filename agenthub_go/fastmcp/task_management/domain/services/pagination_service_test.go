package services

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestPagination(t *testing.T) {
	r, err := CreatePaginationResult([]string{"a"}, 25, value_objects.NewPaginationRequest(2, 10, nil))
	if err != nil || r.TotalPages != 3 || !r.HasNext || !r.HasPrevious {
		t.Fatalf("%+v %v", r, err)
	}
	r, _ = CreatePaginationResult([]string{}, 0, value_objects.NewPaginationRequest(1, 10, nil))
	if r.TotalPages != 0 || r.HasNext || r.HasPrevious {
		t.Fatalf("%+v", r)
	}
	if _, err := CreatePaginationResult([]string{}, 5, value_objects.PaginationRequest{Page: 1}); err == nil {
		t.Fatal("expected zero division")
	}
	if floorDiv(-1, 10) != -1 {
		t.Fatal("floorDiv")
	}
	for _, c := range []struct {
		p    value_objects.PaginationRequest
		want string
	}{
		{value_objects.PaginationRequest{Page: 0, PageSize: 5}, "Page must be >= 1, got 0"},
		{value_objects.PaginationRequest{Page: 1, PageSize: 0}, "Page size must be > 0, got 0"},
		{value_objects.PaginationRequest{Page: 1, PageSize: 101}, "Page size must be <= 100, got 101"},
	} {
		if err := ValidatePaginationRequest(c.p); err == nil || err.Error() != c.want {
			t.Fatalf("%v", err)
		}
	}
	if CalculateOffset(value_objects.PaginationRequest{Page: 3, PageSize: 10}) != 20 {
		t.Fatal("offset")
	}
}

func TestEventDispatcher(t *testing.T) {
	d := NewEventDispatcher()
	var got []string
	h := EventHandler{"h", func(x any) { got = append(got, x.(string)) }}
	bad := EventHandler{"bad", func(any) { panic("boom") }}
	d.RegisterHandler("e", bad)
	d.RegisterHandler("e", h)
	d.RegisterHandler("e", h)
	if d.GetHandlerCount("e") != 2 {
		t.Fatal("dedupe")
	}
	d.Dispatch("e", "x")
	if len(got) != 1 {
		t.Fatal("panic handler must not stop others")
	}
	d.UnregisterHandler("e", bad)
	d.ClearHandlers("")
	if d.GetHandlerCount("e") != 0 {
		t.Fatal("clear")
	}
}
