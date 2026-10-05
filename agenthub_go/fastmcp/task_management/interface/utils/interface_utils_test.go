package utils

import (
	"errors"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestParseDictParameterPythonBehaviour(t *testing.T) {
	p := JSONParameterParser{}

	// None -> nil
	if got, err := p.ParseDictParameter(nil, "data"); err != nil || got != nil {
		t.Fatalf("None: got %v, %v", got, err)
	}

	// dict passthrough
	in := entities.NewOrderedMap[any]()
	in.Set("a", 1)
	out, err := p.ParseDictParameter(in, "data")
	if err != nil || out != in {
		t.Fatalf("dict: got %v, %v", out, err)
	}

	// JSON object keeps insertion order
	out, err = p.ParseDictParameter(`{"b": 2, "a": {"x": 1}}`, "data")
	if err != nil {
		t.Fatalf("json object: %v", err)
	}
	if strings.Join(out.Keys(), ",") != "b,a" {
		t.Fatalf("keys: %v", out.Keys())
	}

	// JSON array -> error, type name "list"
	_, err = p.ParseDictParameter(`[1, 2]`, "data")
	if err == nil || err.Error() != "Parameter 'data' JSON must be an object, not list" {
		t.Fatalf("array err: %v", err)
	}

	// invalid JSON -> ValueError message with example
	_, err = p.ParseDictParameter(`{bad`, "data")
	if err == nil || !strings.HasPrefix(err.Error(), "Invalid JSON string in 'data' parameter: ") ||
		!strings.Contains(err.Error(), "Valid formats: data={'key': 'value'} or data='{\"key\": \"value\"}'") {
		t.Fatalf("invalid err: %v", err)
	}

	// other type -> error
	_, err = p.ParseDictParameter(5, "data")
	if err == nil || err.Error() != "Parameter 'data' must be a dictionary object or JSON string, not int" {
		t.Fatalf("int err: %v", err)
	}
}

func TestGetDictParametersForTool(t *testing.T) {
	if got := GetDictParametersForTool("manage_context"); strings.Join(got, ",") != "data,delegate_data,filters,data_metadata" {
		t.Fatalf("manage_context: %v", got)
	}
	if got := GetDictParametersForTool("unknown"); strings.Join(got, ",") != "data,metadata,config" {
		t.Fatalf("default: %v", got)
	}
}

func TestCreateErrorResponseKeyOrder(t *testing.T) {
	d := (JSONParameterParser{}).CreateErrorResponse("data", "boom", "manage_task")
	want := "error,error_code,parameter,suggestions,examples"
	if strings.Join(d.Keys(), ",") != want {
		t.Fatalf("keys: %v", d.Keys())
	}
	sugg := d.GetAny("suggestions").([]any)
	if sugg[1] != "Or use a JSON string: data='{\"key\": \"value\", \"nested\": {\"item\": 123}}'" {
		t.Fatalf("suggestion: %v", sugg[1])
	}
}

func TestHandleErrorValueErrorAndKeyError(t *testing.T) {
	h := UserFriendlyErrorHandler{}
	d := h.HandleError(&value_objects.ValueError{Msg: "Invalid labels format"}, "create", nil)
	if d.GetAny("error_code") != string(ErrorCodeInvalidParameterFormat) {
		t.Fatalf("value error code: %v", d.GetAny("error_code"))
	}

	d = h.HandleError(&KeyError{Key: "git_branch_id"}, "create", nil)
	if d.GetAny("error") != "Required parameter 'git_branch_id' is missing." {
		t.Fatalf("key error: %v", d.GetAny("error"))
	}
}

func TestHandleErrorTaskNotFoundFromContext(t *testing.T) {
	ctx := entities.NewOrderedMap[any]()
	ctx.Set("task_id", "abc")
	d := (UserFriendlyErrorHandler{}).HandleError(errors.New("task not found"), "get", ctx)
	if d.GetAny("error") != "Task 'abc' was not found." || d.GetAny("error_code") != string(ErrorCodeTaskNotFound) {
		t.Fatalf("got %v", d)
	}
}

func TestFlexibleSchemaGenerator(t *testing.T) {
	gen := FlexibleSchemaGenerator{}

	orig := entities.NewOrderedMap[any]()
	orig.Set("type", "string")
	orig.Set("description", "Insights discovered during work")

	out := gen.CreateFlexibleSchemaForParameter("insights_found", orig)
	if strings.Join(out.Keys(), ",") != "anyOf,description" {
		t.Fatalf("keys: %v", out.Keys())
	}
	anyOf := out.GetAny("anyOf").([]any)
	if len(anyOf) != 4 {
		t.Fatalf("anyOf len: %d", len(anyOf))
	}
	if anyOf[0].(*entities.OrderedMap[any]).GetAny("type") != "array" {
		t.Fatalf("option 0: %v", anyOf[0])
	}
	if out.GetAny("description") != "Insights discovered during work. Accepts: array of strings, JSON string array, comma-separated string, or single string." {
		t.Fatalf("description: %v", out.GetAny("description"))
	}

	// Non-flexible parameter returns the original pointer.
	other := entities.NewOrderedMap[any]()
	if gen.CreateFlexibleSchemaForParameter("title", other) != other {
		t.Fatal("non-flexible param must be returned unchanged")
	}
}

func TestApplyFlexibleSchemasToToolSchema(t *testing.T) {
	gen := FlexibleSchemaGenerator{}
	props := entities.NewOrderedMap[any]()
	labelSchema := entities.NewOrderedMap[any]()
	labelSchema.Set("type", "string")
	props.Set("labels", labelSchema)
	props.Set("title", labelSchema)
	schema := entities.NewOrderedMap[any]()
	schema.Set("properties", props)

	out := gen.ApplyFlexibleSchemasToToolSchema(schema)
	outProps := out.GetAny("properties").(*entities.OrderedMap[any])
	if !outProps.GetAny("labels").(*entities.OrderedMap[any]).Has("anyOf") {
		t.Fatal("labels should become flexible")
	}
	if outProps.GetAny("title") != labelSchema {
		t.Fatal("title should be unchanged")
	}
}
