package utils

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestCreateResponseKeyOrderAndShapes(t *testing.T) {
	t.Setenv("ENABLE_RESPONSE_OPTIMIZATION", "false")
	f := NewMCPResponseFormatter()
	data := om("id", "abc")
	res := f.CreateSuccessResponse("create", data, nil, nil, nil, nil)
	want := []string{"status", "success", "operation", "operation_id", "timestamp", "confirmation", "data"}
	for i, k := range want {
		if res.Keys()[i] != k {
			t.Fatalf("key %d = %q want %q", i, res.Keys()[i], k)
		}
	}
	if v, _ := res.Get("status"); v != "success" {
		t.Errorf("status=%#v", v)
	}
	if v, _ := res.Get("success"); v != true {
		t.Errorf("success=%#v", v)
	}
	conf, _ := res.Get("confirmation")
	c := conf.(*entities.OrderedMap[any])
	if c.Keys()[0] != "operation_completed" || c.Keys()[1] != "data_persisted" || c.Keys()[2] != "partial_failures" || c.Keys()[3] != "operation_details" {
		t.Fatalf("confirmation keys=%v", c.Keys())
	}
	if v, _ := c.Get("data_persisted"); v != true {
		t.Errorf("data_persisted=%#v", v)
	}
	od, _ := c.Get("operation_details")
	details := od.(*entities.OrderedMap[any])
	if details.Keys()[0] != "operation" || details.Keys()[1] != "operation_id" || details.Keys()[2] != "timestamp" {
		t.Fatalf("details keys=%v", details.Keys())
	}
	if v, _ := res.Get("operation_id"); v != valueOf(t, details, "operation_id") {
		t.Errorf("operation_id mismatch")
	}
	if v, _ := res.Get("timestamp"); v != valueOf(t, details, "timestamp") {
		t.Errorf("timestamp mismatch")
	}
}

func valueOf(t *testing.T, m *entities.OrderedMap[any], k string) any {
	t.Helper()
	v, _ := m.Get(k)
	return v
}

func TestCreateErrorResponseShape(t *testing.T) {
	t.Setenv("ENABLE_RESPONSE_OPTIMIZATION", "false")
	f := NewMCPResponseFormatter()
	res := f.CreateErrorResponse("delete", "boom", "UNKNOWN_ERROR", nil)
	want := []string{"status", "success", "operation", "operation_id", "timestamp", "confirmation", "error"}
	for i, k := range want {
		if res.Keys()[i] != k {
			t.Fatalf("key %d = %q", i, res.Keys()[i])
		}
	}
	if v, _ := res.Get("success"); v != false {
		t.Errorf("success=%#v", v)
	}
	conf, _ := res.Get("confirmation")
	c := conf.(*entities.OrderedMap[any])
	if v, _ := c.Get("operation_completed"); v != false {
		t.Errorf("operation_completed=%#v", v)
	}
	if v, _ := c.Get("data_persisted"); v != false {
		t.Errorf("data_persisted=%#v", v)
	}
	errAny, _ := res.Get("error")
	e := errAny.(*entities.OrderedMap[any])
	if e.Keys()[0] != "message" || e.Keys()[1] != "code" || e.Keys()[2] != "operation" || e.Keys()[3] != "timestamp" {
		t.Fatalf("error keys=%v", e.Keys())
	}
	if v, _ := e.Get("code"); v != "UNKNOWN_ERROR" {
		t.Errorf("code=%#v", v)
	}
}

func TestVerifySuccessAndHasPartialFailures(t *testing.T) {
	t.Setenv("ENABLE_RESPONSE_OPTIMIZATION", "false")
	f := NewMCPResponseFormatter()
	res := f.CreateSuccessResponse("get", om("id", "1"), nil, nil, nil, nil)
	if !VerifyResponseSuccess(res) {
		t.Errorf("VerifyResponseSuccess=false")
	}
	if HasResponsePartialFailures(res) {
		t.Errorf("HasPartialFailures=true")
	}
	if ExtractResponseData(res) == nil {
		t.Errorf("ExtractResponseData nil")
	}
	partial := f.CreatePartialSuccessResponse("update", om("id", "1"), []*entities.OrderedMap[any]{om("field", "x")}, nil, nil, nil, nil)
	if !HasResponsePartialFailures(partial) {
		t.Errorf("partial not detected")
	}
	if VerifyResponseSuccess(partial) {
		t.Errorf("partial verified as success")
	}
	if v, _ := partial.Get("status"); v != "partial_success" {
		t.Errorf("status=%#v", v)
	}
}

func TestFormatSuccessMovesOperationFields(t *testing.T) {
	t.Setenv("ENABLE_RESPONSE_OPTIMIZATION", "false")
	f := NewMCPResponseFormatter()
	raw := om("success", true, "created", true, "count", 2, "context_id", "c1", "other", "v")
	out := f.FormatSuccess(raw, "create", nil, nil, nil)
	metaAny, _ := out.Get("metadata")
	meta := metaAny.(*entities.OrderedMap[any])
	opAny, _ := meta.Get("operation_details")
	op := opAny.(*entities.OrderedMap[any])
	if !op.Has("created") || !op.Has("count") || !op.Has("context_id") {
		t.Errorf("operation_details=%v", op.Keys())
	}
	dataAny, _ := out.Get("data")
	data := dataAny.(*entities.OrderedMap[any])
	if v, _ := data.Get("other"); v != "v" {
		t.Errorf("data other=%#v", v)
	}
	if data.Has("success") {
		t.Errorf("success leaked into data")
	}
}

func TestFormatContextResponseUpdate(t *testing.T) {
	t.Setenv("ENABLE_RESPONSE_OPTIMIZATION", "false")
	f := NewMCPResponseFormatter()
	ctx := om("id", "ctx1", "name", "n")
	raw := om("success", true, "context", ctx, "level", "branch", "propagated", true, "context_id", "c9")
	out := f.FormatContextResponse(raw, "update", true, nil, nil)
	dataAny, _ := out.Get("data")
	data := dataAny.(*entities.OrderedMap[any])
	want := []string{"id", "updated_data", "level", "propagated"}
	for i, k := range want {
		if data.Keys()[i] != k {
			t.Fatalf("data key %d=%q want %q", i, data.Keys()[i], k)
		}
	}
	if v, _ := data.Get("id"); v != "c9" {
		t.Errorf("id=%#v", v)
	}
	meta, _ := out.Get("metadata")
	m := meta.(*entities.OrderedMap[any])
	coAny, _ := m.Get("context_operation")
	co := coAny.(*entities.OrderedMap[any])
	if co.Has("level") {
		t.Errorf("update metadata should not contain level: %v", co.Keys())
	}
	if v, _ := co.Get("operation_type"); v != "update" {
		t.Errorf("operation_type=%#v", v)
	}
}
