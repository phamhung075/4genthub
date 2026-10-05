package context

import (
	"reflect"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestContextResponseToDict(t *testing.T) {
	data := entities.NewOrderedMap[any]()
	data.Set("a", 1)
	r := NewContextResponseSuccess(nil, data, nil)
	if r.Message != "Operation successful" {
		t.Fatalf("message = %q", r.Message)
	}
	m := r.ToDict()
	if !reflect.DeepEqual(m.Keys(), []string{"success", "message", "data"}) {
		t.Fatalf("keys = %v", m.Keys())
	}
	if v, _ := m.Get("data"); v != data {
		t.Fatalf("data = %v", v)
	}
}

func TestContextResponseError(t *testing.T) {
	r := NewContextResponseError("bad", nil)
	if r.Message != "Operation failed" || r.Error == nil || *r.Error != "bad" {
		t.Fatalf("r = %+v", r)
	}
	m := r.ToDict()
	if !reflect.DeepEqual(m.Keys(), []string{"success", "message", "error"}) {
		t.Fatalf("keys = %v", m.Keys())
	}
}

func TestGetPropertyResponse(t *testing.T) {
	r := NewGetPropertyResponseSuccess(7, nil)
	if r.Message != "Property retrieved successfully" {
		t.Fatalf("message = %q", r.Message)
	}
	m := r.ToDict()
	if !reflect.DeepEqual(m.Keys(), []string{"success", "message", "value"}) {
		t.Fatalf("keys = %v", m.Keys())
	}
	if v, _ := m.Get("value"); v != 7 {
		t.Fatalf("value = %v", v)
	}
}

func TestListContextsResponse(t *testing.T) {
	r := NewListContextsResponseSuccess([]*entities.TaskContext{}, nil)
	if r.Message != "Contexts retrieved successfully" {
		t.Fatalf("message = %q", r.Message)
	}
	m := r.ToDict()
	if !reflect.DeepEqual(m.Keys(), []string{"success", "message", "contexts"}) {
		t.Fatalf("keys = %v", m.Keys())
	}
	contexts, _ := m.Get("contexts")
	if lst, ok := contexts.([]any); !ok || len(lst) != 0 {
		t.Fatalf("contexts = %#v", contexts)
	}
}
