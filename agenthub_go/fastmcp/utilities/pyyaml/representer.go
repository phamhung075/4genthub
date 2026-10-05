package pyyaml

import (
	"fmt"
	"math"
	"math/big"
	"sort"
	"strconv"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
)

// Representer (representer.py). Only the Python types that can come out of
// entities.DecodeJSON (and their immediate containers) are handled: None, bool, str,
// int (int64 / *big.Int), float, list and dict. Anchors/aliases cannot occur for a
// freshly decoded JSON tree, so every node is emitted once with no anchor.

type representer struct {
	sortKeys bool
}

func (r *representer) representData(data any) (node, error) {
	switch v := data.(type) {
	case nil:
		return &scalarNode{tag: nullTag, value: "null"}, nil
	case bool:
		value := "false"
		if v {
			value = "true"
		}
		return &scalarNode{tag: boolTag, value: value}, nil
	case string:
		return &scalarNode{tag: defaultScalarTag, value: v}, nil
	case int64:
		return &scalarNode{tag: intTag, value: strconv.FormatInt(v, 10)}, nil
	case *big.Int:
		return &scalarNode{tag: intTag, value: v.String()}, nil
	case float64:
		return &scalarNode{tag: floatTag, value: representFloat(v)}, nil
	case []any:
		return r.representSequence(v)
	case *entities.OrderedMap[any]:
		return r.representMapping(v)
	}
	return nil, fmt.Errorf("cannot represent an object: %T", data)
}

func (r *representer) representSequence(seq []any) (node, error) {
	items := make([]node, len(seq))
	for i, item := range seq {
		n, err := r.representData(item)
		if err != nil {
			return nil, err
		}
		items[i] = n
	}
	return &sequenceNode{tag: defaultSequenceTag, value: items}, nil
}

func (r *representer) representMapping(m *entities.OrderedMap[any]) (node, error) {
	keys := m.Keys()
	if r.sortKeys {
		// sorted(mapping): keys are unique strings, so this is a plain string sort.
		sort.Strings(keys)
	}
	pairs := make([]nodePair, 0, len(keys))
	for _, k := range keys {
		val, _ := m.Get(k)
		kn, err := r.representData(k)
		if err != nil {
			return nil, err
		}
		vn, err := r.representData(val)
		if err != nil {
			return nil, err
		}
		pairs = append(pairs, nodePair{key: kn, value: vn})
	}
	return &mappingNode{tag: defaultMappingTag, value: pairs}, nil
}

// representFloat mirrors SafeRepresenter.represent_float: repr(value).lower(), with
// ".0" inserted before "e" when there is no decimal point, and the .inf/-.inf/.nan forms.
func representFloat(f float64) string {
	switch {
	case math.IsNaN(f):
		return ".nan"
	case math.IsInf(f, 1):
		return ".inf"
	case math.IsInf(f, -1):
		return "-.inf"
	}
	value := yamlFloatRepr(f)
	if !strings.Contains(value, ".") && strings.Contains(value, "e") {
		value = strings.Replace(value, "e", ".0e", 1)
	}
	return value
}

// yamlFloatRepr is Python's repr(float): shortest round-tripping digits, scientific
// notation when the decimal exponent is < -4 or >= 16.
func yamlFloatRepr(f float64) string {
	e := strconv.FormatFloat(f, 'e', -1, 64)
	exp, _ := strconv.Atoi(e[strings.IndexByte(e, 'e')+1:])
	if exp >= -4 && exp < 16 {
		s := strconv.FormatFloat(f, 'f', -1, 64)
		if !strings.Contains(s, ".") {
			s += ".0"
		}
		return s
	}
	return e
}
