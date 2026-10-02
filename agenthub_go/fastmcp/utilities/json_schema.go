package utilities

import (
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
)

// jsonSchema is the Python dict shape these functions operate on: ordered string-keyed
// maps (nested), []any lists and scalars.
type jsonSchema = entities.OrderedMap[any]

// jsDeepCopy mirrors copy.deepcopy for JSON-like schema values.
func jsDeepCopy(v any) any {
	switch x := v.(type) {
	case *jsonSchema:
		out := entities.NewOrderedMap[any]()
		for _, k := range x.Keys() {
			val, _ := x.Get(k)
			out.Set(k, jsDeepCopy(val))
		}
		return out
	case []any:
		out := make([]any, len(x))
		for i, e := range x {
			out[i] = jsDeepCopy(e)
		}
		return out
	default:
		return v
	}
}

// pruneParam mirrors _prune_param. Note the Python quirk: props.pop runs before the
// "nothing to do" check, so a property whose value is None is removed from properties
// but not from required.
func pruneParam(schema *jsonSchema, param string) *jsonSchema {
	var props *jsonSchema
	if pv, ok := schema.Get("properties"); ok {
		if m, isMap := pv.(*jsonSchema); isMap {
			props = m
		}
	}
	if props == nil {
		return schema
	}
	removed, found := props.Get(param)
	if found {
		props.Delete(param)
	}
	if !found || removed == nil {
		return schema
	}
	if rv, ok := schema.Get("required"); ok {
		if list, isList := rv.([]any); isList {
			for i, e := range list {
				if s, isStr := e.(string); isStr && s == param {
					list = append(list[:i], list[i+1:]...)
					if len(list) == 0 {
						schema.Delete("required")
					} else {
						schema.Set("required", list)
					}
					break
				}
			}
		}
	}
	return schema
}

// pruneUnusedDefs mirrors _prune_unused_defs.
func pruneUnusedDefs(schema *jsonSchema) (*jsonSchema, error) {
	defsVal, ok := schema.Get("$defs")
	if !ok || defsVal == nil {
		return schema, nil
	}
	defs, isMap := defsVal.(*jsonSchema)
	if !isMap {
		return schema, nil
	}

	rootDefs := map[string]bool{}
	referencedBy := map[string][]string{}

	var walk func(node any, currentDef *string, skipDefs bool)
	walk = func(node any, currentDef *string, skipDefs bool) {
		switch n := node.(type) {
		case *jsonSchema:
			if ref, ok := n.Get("$ref"); ok {
				if rs, isStr := ref.(string); isStr && strings.HasPrefix(rs, "#/$defs/") {
					defName := rs[strings.LastIndex(rs, "/")+1:]
					if currentDef != nil {
						referencedBy[defName] = append(referencedBy[defName], *currentDef)
					} else {
						rootDefs[defName] = true
					}
				}
			}
			for _, k := range n.Keys() {
				if skipDefs && k == "$defs" {
					continue
				}
				v, _ := n.Get(k)
				// Python does not propagate skip_defs/current_def into recursive calls.
				walk(v, currentDef, false)
			}
		case []any:
			for _, v := range n {
				walk(v, nil, false)
			}
		}
	}

	walk(schema, nil, true)

	for _, defName := range defs.Keys() {
		value, _ := defs.Get(defName)
		cd := defName
		walk(value, &cd, false)
	}

	// Python recurses without a guard, so a cycle of defs unreachable from the root raises
	// RecursionError before any root def is found; re-entering a def on the current path is
	// that same condition (and would otherwise be a fatal Go stack overflow).
	onPath := map[string]bool{}
	var defIsReferenced func(string) (bool, error)
	defIsReferenced = func(name string) (bool, error) {
		if rootDefs[name] {
			return true, nil
		}
		if onPath[name] {
			return false, &RecursionError{Msg: "maximum recursion depth exceeded"}
		}
		onPath[name] = true
		defer delete(onPath, name)
		for _, reference := range referencedBy[name] {
			ok, err := defIsReferenced(reference)
			if err != nil {
				return false, err
			}
			if ok {
				return true, nil
			}
		}
		return false, nil
	}

	for _, defName := range defs.Keys() {
		referenced, err := defIsReferenced(defName)
		if err != nil {
			return nil, err
		}
		if !referenced {
			defs.Delete(defName)
		}
	}
	if defs.Len() == 0 {
		schema.Delete("$defs")
	}
	return schema, nil
}

// RecursionError mirrors Python's RecursionError.
type RecursionError struct{ Msg string }

func (e *RecursionError) Error() string { return e.Msg }

// walkAndPrune mirrors _walk_and_prune.
func walkAndPrune(schema *jsonSchema, pruneTitles, pruneAdditionalProperties bool) *jsonSchema {
	var walk func(node any)
	walk = func(node any) {
		switch n := node.(type) {
		case *jsonSchema:
			if pruneTitles {
				n.Delete("title")
			}
			if pruneAdditionalProperties {
				if v, ok := n.Get("additionalProperties"); ok {
					if b, isBool := v.(bool); isBool && !b {
						n.Delete("additionalProperties")
					}
				}
			}
			for _, k := range n.Keys() {
				v, _ := n.Get(k)
				walk(v)
			}
		case []any:
			for _, v := range n {
				walk(v)
			}
		}
	}
	walk(schema)
	return schema
}

// pruneAdditionalProperties mirrors _prune_additional_properties.
func pruneAdditionalProperties(schema *jsonSchema) *jsonSchema {
	if v, ok := schema.Get("additionalProperties"); ok {
		if b, isBool := v.(bool); isBool && !b {
			schema.Delete("additionalProperties")
		}
	}
	return schema
}

// CompressSchema mirrors compress_schema. The Python defaults are prune_defs=True,
// prune_additional_properties=True, prune_titles=False; callers pass them explicitly.
func CompressSchema(schema *jsonSchema, pruneParams []string, pruneDefs, pruneAdditionalProperties, pruneTitles bool) (*jsonSchema, error) {
	copied := jsDeepCopy(schema)
	out, _ := copied.(*jsonSchema)
	for _, param := range pruneParams {
		out = pruneParam(out, param)
	}
	if pruneTitles || pruneAdditionalProperties {
		out = walkAndPrune(out, pruneTitles, pruneAdditionalProperties)
	}
	if pruneDefs {
		return pruneUnusedDefs(out)
	}
	return out, nil
}
