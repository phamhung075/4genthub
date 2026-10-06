// Package tools ports fastmcp/tools. This file ports a dependency-free part of
// tools/tool_transform.py: ArgTransform validation, the single-argument schema
// transform, the schema-precedence merge and the forwarding-transform builder.
// The parts that need the unported tools/tool.py (Tool/ParsedFunction),
// pydantic's TypeAdapter and Python's inspect.signature (FromTool, the custom
// transform_fn branch, _convert_to_content, forward()/forward_raw()) are not
// ported; see the report.
package tools

import (
	"context"
	"fmt"
	"sort"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// notSetType mirrors Python's Ellipsis (...) "no change" sentinel.
type notSetType struct{}

// NotSet is the Go spelling of Python's `...` used by ArgTransform.
var NotSet = notSetType{}

// ArgTransform mirrors tool_transform.ArgTransform. Use NewArgTransform so the
// unset fields hold NotSet (a Go zero value would mean Python None).
type ArgTransform struct {
	Name           any
	Description    any
	Default        any
	DefaultFactory any
	Type           any
	Hide           bool
	Required       any
	Examples       any
}

// NewArgTransform returns an ArgTransform with every optional field at NotSet.
func NewArgTransform() *ArgTransform {
	return &ArgTransform{
		Name:           NotSet,
		Description:    NotSet,
		Default:        NotSet,
		DefaultFactory: NotSet,
		Type:           NotSet,
		Required:       NotSet,
		Examples:       NotSet,
	}
}

// Validate ports ArgTransform.__post_init__.
func (t *ArgTransform) Validate() error {
	hasDefault := t.Default != NotSet
	hasFactory := t.DefaultFactory != NotSet

	if hasDefault && hasFactory {
		return &value_objects.ValueError{Msg: "Cannot specify both 'default' and 'default_factory' in ArgTransform. " +
			"Use either 'default' for a static value or 'default_factory' for a callable."}
	}
	if hasFactory && !t.Hide {
		return &value_objects.ValueError{Msg: "default_factory can only be used with hide=True. " +
			"Visible parameters must use static 'default' values since JSON schema " +
			"cannot represent dynamic factories."}
	}
	if t.Required == true && (hasDefault || hasFactory) {
		return &value_objects.ValueError{Msg: "Cannot specify 'required=True' with 'default' or 'default_factory'. " +
			"Required parameters cannot have defaults."}
	}
	if t.Hide && t.Required == true {
		return &value_objects.ValueError{Msg: "Cannot specify both 'hide=True' and 'required=True'. " +
			"Hidden parameters cannot be required since clients cannot provide them."}
	}
	if t.Required == false {
		return &value_objects.ValueError{Msg: "Cannot specify 'required=False'. Set a default value instead."}
	}
	return nil
}

// TransformParent is the minimal view of tools/tool.py::Tool that the transform
// builder needs.
type TransformParent interface {
	Parameters() *entities.OrderedMap[any]
	Run(ctx context.Context, arguments *entities.OrderedMap[any]) ([]any, error)
}

func asOrderedMap(v any) *entities.OrderedMap[any] {
	m, _ := v.(*entities.OrderedMap[any])
	return m
}

func asStringList(v any) []string {
	switch xs := v.(type) {
	case []string:
		return append([]string{}, xs...)
	case []any:
		out := make([]string, 0, len(xs))
		for _, x := range xs {
			s, ok := x.(string)
			if !ok {
				continue
			}
			out = append(out, s)
		}
		return out
	}
	return nil
}

func joinSorted(xs []string) string {
	cp := append([]string{}, xs...)
	sort.Strings(cp)
	return strings.Join(cp, ", ")
}

// ApplySingleTransform ports TransformedTool._apply_single_transform. It returns
// kept=false when the parameter is hidden/dropped. The Python `type` branch uses
// pydantic's TypeAdapter; here `transform.Type` must already be a JSON schema
// (*entities.OrderedMap[any]) because Go cannot introspect a type into a schema.
func ApplySingleTransform(oldName string, oldSchema *entities.OrderedMap[any], transform *ArgTransform, isRequired bool) (string, *entities.OrderedMap[any], bool, bool, error) {
	if transform.Hide {
		return "", nil, false, false, nil
	}

	newName := oldName
	if transform.Name != NotSet {
		if s, ok := transform.Name.(string); ok {
			newName = s
		}
	}

	newSchema := oldSchema.Copy()

	if transform.Description != NotSet {
		if transform.Description == nil {
			newSchema.Delete("description")
		} else {
			newSchema.Set("description", transform.Description)
		}
	}

	if transform.Required != NotSet {
		if transform.Required == true {
			isRequired = true
			newSchema.Delete("default")
		} else {
			isRequired = false
		}
	}

	if transform.Default != NotSet && transform.Required != true {
		newSchema.Set("default", transform.Default)
		isRequired = false
	}

	if transform.Type != NotSet {
		typeSchema := asOrderedMap(transform.Type)
		if typeSchema != nil {
			for _, k := range typeSchema.Keys() {
				v, _ := typeSchema.Get(k)
				newSchema.Set(k, v)
			}
		}
	}

	if transform.Examples != NotSet {
		newSchema.Set("examples", transform.Examples)
	}

	return newName, newSchema, isRequired, true, nil
}

// MergeSchemaWithPrecedence ports TransformedTool._merge_schema_with_precedence.
func MergeSchemaWithPrecedence(baseSchema, overrideSchema *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	mergedProps := entities.NewOrderedMap[any]()
	if p := asOrderedMap(mustGet(baseSchema, "properties")); p != nil {
		for _, k := range p.Keys() {
			v, _ := p.Get(k)
			mergedProps.Set(k, v)
		}
	}
	mergedRequired := asStringList(mustGet(baseSchema, "required"))

	overrideProps := asOrderedMap(mustGet(overrideSchema, "properties"))
	overrideRequired := asStringList(mustGet(overrideSchema, "required"))

	if overrideProps != nil {
		for _, name := range overrideProps.Keys() {
			schema, _ := overrideProps.Get(name)
			newParam := asOrderedMap(schema)
			if existing, ok := mergedProps.Get(name); ok {
				baseParam := asOrderedMap(existing)
				merged := entities.NewOrderedMap[any]()
				if baseParam != nil {
					for _, k := range baseParam.Keys() {
						v, _ := baseParam.Get(k)
						merged.Set(k, v)
					}
				}
				if newParam != nil {
					for _, k := range newParam.Keys() {
						v, _ := newParam.Get(k)
						merged.Set(k, v)
					}
				}
				mergedProps.Set(name, merged)
			} else if newParam != nil {
				mergedProps.Set(name, newParam.Copy())
			}
		}
	}

	finalRequired := entities.StringSet{}
	for _, name := range overrideRequired {
		finalRequired.Add(name)
	}
	for _, name := range mergedRequired {
		if overrideProps != nil && overrideProps.Has(name) {
			if schema := asOrderedMap(mustGet(mergedProps, name)); schema != nil && !schema.Has("default") {
				finalRequired.Add(name)
			}
		} else {
			finalRequired.Add(name)
		}
	}
	for _, name := range mergedProps.Keys() {
		if schema := asOrderedMap(mustGet(mergedProps, name)); schema != nil && schema.Has("default") {
			finalRequired.Remove(name)
		}
	}

	out := entities.NewOrderedMap[any]()
	out.Set("type", "object")
	out.Set("properties", mergedProps)
	required := make([]any, 0, finalRequired.Len())
	for _, name := range finalRequired.Items() {
		required = append(required, name)
	}
	out.Set("required", required)
	return out
}

func mustGet(m *entities.OrderedMap[any], k string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(k)
	return v
}

// CreateForwardingTransform ports TransformedTool._create_forwarding_transform:
// it builds the transformed JSON schema and the forwarder that validates the new
// argument names, maps them back and injects hidden defaults.
func CreateForwardingTransform(parent TransformParent, transformArgs *entities.OrderedMap[*ArgTransform]) (*entities.OrderedMap[any], func(context.Context, *entities.OrderedMap[any]) ([]any, error), error) {
	params := parent.Parameters()
	parentProps := asOrderedMap(mustGet(params, "properties"))
	parentRequired := map[string]bool{}
	for _, name := range asStringList(mustGet(params, "required")) {
		parentRequired[name] = true
	}

	newProps := entities.NewOrderedMap[any]()
	newRequired := entities.StringSet{}
	newToOld := entities.NewOrderedMap[string]()
	hiddenDefaults := entities.NewOrderedMap[*ArgTransform]()

	if parentProps != nil {
		for _, oldName := range parentProps.Keys() {
			oldSchemaAny, _ := parentProps.Get(oldName)
			oldSchema := asOrderedMap(oldSchemaAny)

			transform := NewArgTransform()
			if transformArgs != nil {
				if tr, ok := transformArgs.Get(oldName); ok {
					transform = tr
				}
			}

			if transform.Hide {
				hasUserDefault := transform.Default != NotSet || transform.DefaultFactory != NotSet
				if !hasUserDefault && parentRequired[oldName] {
					return nil, nil, &value_objects.ValueError{Msg: fmt.Sprintf(
						"Hidden parameter '%s' has no default value in parent tool "+
							"and no default or default_factory provided in ArgTransform. Either provide a default "+
							"or default_factory in ArgTransform or don't hide required parameters.", oldName)}
				}
				if hasUserDefault {
					hiddenDefaults.Set(oldName, transform)
				}
				continue
			}

			newName, newSchema, isRequired, kept, err := ApplySingleTransform(oldName, oldSchema, transform, parentRequired[oldName])
			if err != nil {
				return nil, nil, err
			}
			if !kept {
				continue
			}
			newProps.Set(newName, newSchema)
			newToOld.Set(newName, oldName)
			if isRequired {
				newRequired.Add(newName)
			}
		}
	}

	schema := entities.NewOrderedMap[any]()
	schema.Set("type", "object")
	schema.Set("properties", newProps)
	requiredList := make([]any, 0, newRequired.Len())
	for _, name := range newRequired.Items() {
		requiredList = append(requiredList, name)
	}
	schema.Set("required", requiredList)

	validArgs := map[string]bool{}
	for _, k := range newProps.Keys() {
		validArgs[k] = true
	}
	requiredNames := newRequired.Items()

	forward := func(ctx context.Context, kwargs *entities.OrderedMap[any]) ([]any, error) {
		var provided []string
		if kwargs != nil {
			provided = kwargs.Keys()
		}
		providedSet := map[string]bool{}
		for _, k := range provided {
			providedSet[k] = true
		}

		var unknown []string
		for _, k := range provided {
			if !validArgs[k] {
				unknown = append(unknown, k)
			}
		}
		if len(unknown) > 0 {
			return nil, &value_objects.TypeError{Msg: fmt.Sprintf("Got unexpected keyword argument(s): %s", joinSorted(unknown))}
		}

		var missing []string
		for _, k := range requiredNames {
			if !providedSet[k] {
				missing = append(missing, k)
			}
		}
		if len(missing) > 0 {
			return nil, &value_objects.TypeError{Msg: fmt.Sprintf("Missing required argument(s): %s", joinSorted(missing))}
		}

		parentArgs := entities.NewOrderedMap[any]()
		for _, newName := range provided {
			value, _ := kwargs.Get(newName)
			oldName, ok := newToOld.Get(newName)
			if !ok {
				oldName = newName
			}
			parentArgs.Set(oldName, value)
		}
		for _, oldName := range hiddenDefaults.Keys() {
			transform, _ := hiddenDefaults.Get(oldName)
			if transform.Default != NotSet {
				parentArgs.Set(oldName, transform.Default)
			} else if transform.DefaultFactory != NotSet {
				if factory, ok := transform.DefaultFactory.(func() any); ok {
					parentArgs.Set(oldName, factory())
				}
			}
		}

		return parent.Run(ctx, parentArgs)
	}

	return schema, forward, nil
}
