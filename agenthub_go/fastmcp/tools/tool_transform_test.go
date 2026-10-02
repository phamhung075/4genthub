package tools

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// Expectations below are read from agenthub_main/src/fastmcp/tools/tool_transform.py.

func TestArgTransformValidation(t *testing.T) {
	cases := []struct {
		name string
		tr   *ArgTransform
		want string
	}{
		{
			name: "default and factory",
			tr:   &ArgTransform{Default: 1, DefaultFactory: func() any { return 1 }, Hide: true, Name: NotSet, Description: NotSet, Type: NotSet, Required: NotSet, Examples: NotSet},
			want: "Cannot specify both 'default' and 'default_factory' in ArgTransform. Use either 'default' for a static value or 'default_factory' for a callable.",
		},
		{
			name: "factory not hidden",
			tr:   &ArgTransform{DefaultFactory: func() any { return 1 }, Name: NotSet, Description: NotSet, Default: NotSet, Type: NotSet, Required: NotSet, Examples: NotSet},
			want: "default_factory can only be used with hide=True. Visible parameters must use static 'default' values since JSON schema cannot represent dynamic factories.",
		},
		{
			name: "required with default",
			tr:   &ArgTransform{Required: true, Default: 1, Name: NotSet, Description: NotSet, DefaultFactory: NotSet, Type: NotSet, Examples: NotSet},
			want: "Cannot specify 'required=True' with 'default' or 'default_factory'. Required parameters cannot have defaults.",
		},
		{
			name: "hide and required",
			tr:   &ArgTransform{Hide: true, Required: true, Name: NotSet, Description: NotSet, Default: NotSet, DefaultFactory: NotSet, Type: NotSet, Examples: NotSet},
			want: "Cannot specify both 'hide=True' and 'required=True'. Hidden parameters cannot be required since clients cannot provide them.",
		},
		{
			name: "required false",
			tr:   &ArgTransform{Required: false, Name: NotSet, Description: NotSet, Default: NotSet, DefaultFactory: NotSet, Type: NotSet, Examples: NotSet},
			want: "Cannot specify 'required=False'. Set a default value instead.",
		},
		{name: "ok", tr: NewArgTransform()},
	}
	for _, tc := range cases {
		err := tc.tr.Validate()
		if tc.want == "" {
			if err != nil {
				t.Fatalf("%s: unexpected error %v", tc.name, err)
			}
			continue
		}
		if err == nil || err.Error() != tc.want {
			t.Fatalf("%s: got %v want %q", tc.name, err, tc.want)
		}
	}
}

func TestApplySingleTransformRenameAndRequired(t *testing.T) {
	old := entities.NewOrderedMap[any]()
	old.Set("type", "string")
	old.Set("description", "old")
	old.Set("default", "d")

	tr := NewArgTransform()
	tr.Name = "newname"
	tr.Required = true
	name, schema, required, kept, err := ApplySingleTransform("old", old, tr, false)
	if err != nil || !kept {
		t.Fatalf("kept=%v err=%v", kept, err)
	}
	if name != "newname" || !required {
		t.Fatalf("name=%q required=%v", name, required)
	}
	if schema.Has("default") {
		t.Fatalf("required=True must remove default: %v", schema.Keys())
	}
	if d, _ := schema.Get("description"); d != "old" {
		t.Fatalf("description = %v", d)
	}
}

func TestApplySingleTransformHideDrops(t *testing.T) {
	old := entities.NewOrderedMap[any]()
	old.Set("type", "string")
	tr := NewArgTransform()
	tr.Hide = true
	_, _, _, kept, err := ApplySingleTransform("old", old, tr, false)
	if err != nil || kept {
		t.Fatalf("kept=%v err=%v", kept, err)
	}
}

func TestMergeSchemaWithPrecedence(t *testing.T) {
	base := entities.NewOrderedMap[any]()
	base.Set("type", "object")
	baseProps := entities.NewOrderedMap[any]()
	a := entities.NewOrderedMap[any]()
	a.Set("type", "string")
	baseProps.Set("a", a)
	b := entities.NewOrderedMap[any]()
	b.Set("type", "integer")
	b.Set("default", 5)
	baseProps.Set("b", b)
	base.Set("properties", baseProps)
	base.Set("required", []any{"a", "b"})

	override := entities.NewOrderedMap[any]()
	override.Set("type", "object")
	overrideProps := entities.NewOrderedMap[any]()
	oa := entities.NewOrderedMap[any]()
	oa.Set("description", "A")
	overrideProps.Set("a", oa)
	c := entities.NewOrderedMap[any]()
	c.Set("type", "boolean")
	overrideProps.Set("c", c)
	override.Set("properties", overrideProps)
	override.Set("required", []any{"c"})

	merged := MergeSchemaWithPrecedence(base, override)
	props := asOrderedMap(mustGet(merged, "properties"))
	if props.Keys()[0] != "a" || props.Keys()[1] != "b" || props.Keys()[2] != "c" {
		t.Fatalf("property order = %v", props.Keys())
	}
	ma := asOrderedMap(mustGet(props, "a"))
	if v, _ := ma.Get("type"); v != "string" {
		t.Fatalf("a.type = %v", v)
	}
	if v, _ := ma.Get("description"); v != "A" {
		t.Fatalf("a.description = %v", v)
	}
	req := map[string]bool{}
	for _, r := range asStringList(mustGet(merged, "required")) {
		req[r] = true
	}
	if !req["a"] || !req["c"] || req["b"] {
		t.Fatalf("required = %v (b has a default so it must be optional)", req)
	}
}

type fakeParent struct {
	params *entities.OrderedMap[any]
	got    *entities.OrderedMap[any]
}

func (f *fakeParent) Parameters() *entities.OrderedMap[any] { return f.params }
func (f *fakeParent) Run(_ context.Context, args *entities.OrderedMap[any]) ([]any, error) {
	f.got = args
	return []any{"ok"}, nil
}

func newFakeParent() *fakeParent {
	props := entities.NewOrderedMap[any]()
	x := entities.NewOrderedMap[any]()
	x.Set("type", "string")
	props.Set("x", x)
	y := entities.NewOrderedMap[any]()
	y.Set("type", "integer")
	y.Set("default", 3)
	props.Set("y", y)
	params := entities.NewOrderedMap[any]()
	params.Set("type", "object")
	params.Set("properties", props)
	params.Set("required", []any{"x"})
	return &fakeParent{params: params}
}

func TestCreateForwardingTransformRenameAndHiddenDefault(t *testing.T) {
	parent := newFakeParent()
	trs := entities.NewOrderedMap[*ArgTransform]()
	rx := NewArgTransform()
	rx.Name = "a"
	trs.Set("x", rx)
	ry := NewArgTransform()
	ry.Hide = true
	ry.Default = 42
	trs.Set("y", ry)

	schema, forward, err := CreateForwardingTransform(parent, trs)
	if err != nil {
		t.Fatal(err)
	}
	props := asOrderedMap(mustGet(schema, "properties"))
	if props.Keys()[0] != "a" || props.Len() != 1 {
		t.Fatalf("transformed properties = %v", props.Keys())
	}
	req := asStringList(mustGet(schema, "required"))
	if len(req) != 1 || req[0] != "a" {
		t.Fatalf("required = %v", req)
	}

	kwargs := entities.NewOrderedMap[any]()
	kwargs.Set("a", "hi")
	if _, err := forward(context.Background(), kwargs); err != nil {
		t.Fatal(err)
	}
	if v, _ := parent.got.Get("x"); v != "hi" {
		t.Fatalf("parent x = %v", v)
	}
	if v, _ := parent.got.Get("y"); v != 42 {
		t.Fatalf("parent y = %v", v)
	}
}

func TestCreateForwardingTransformErrors(t *testing.T) {
	parent := newFakeParent()
	trs := entities.NewOrderedMap[*ArgTransform]()
	rx := NewArgTransform()
	rx.Name = "a"
	trs.Set("x", rx)
	_, forward, err := CreateForwardingTransform(parent, trs)
	if err != nil {
		t.Fatal(err)
	}

	unknown := entities.NewOrderedMap[any]()
	unknown.Set("z", 1)
	if _, err := forward(context.Background(), unknown); err == nil || err.Error() != "Got unexpected keyword argument(s): z" {
		t.Fatalf("unknown err = %v", err)
	}

	if _, err := forward(context.Background(), entities.NewOrderedMap[any]()); err == nil || err.Error() != "Missing required argument(s): a" {
		t.Fatalf("missing err = %v", err)
	}
}

func TestCreateForwardingTransformHiddenRequiredWithoutDefault(t *testing.T) {
	parent := newFakeParent()
	trs := entities.NewOrderedMap[*ArgTransform]()
	ry := NewArgTransform()
	ry.Hide = true
	trs.Set("x", ry)
	_, _, err := CreateForwardingTransform(parent, trs)
	want := "Hidden parameter 'x' has no default value in parent tool " +
		"and no default or default_factory provided in ArgTransform. Either provide a default " +
		"or default_factory in ArgTransform or don't hide required parameters."
	if err == nil || err.Error() != want {
		t.Fatalf("err = %v want %q", err, want)
	}
}
