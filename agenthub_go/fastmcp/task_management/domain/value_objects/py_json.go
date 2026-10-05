package value_objects

import (
	"fmt"
	"math"
	"math/big"
	"reflect"
	"sort"
	"strconv"
	"strings"
)

// OrderedAny is implemented by entities.OrderedMap: a Python dict whose insertion order
// is observable.
type OrderedAny interface {
	KeysAny() []string
	GetAny(key string) any
}

// PyJSONDumps mirrors json.dumps(v, indent=indent) (default separators, ensure_ascii).
// indent < 0 means indent=None (single line, ", " and ": " separators). Dicts given as
// map[string]any are written with sorted keys (their Python insertion order is unknown);
// use an OrderedAny for order-sensitive output. Unsupported types return a TypeError text.
func PyJSONDumps(v any, indent int) (string, error) {
	return pyJSONDumps(v, indent, nil)
}

// PyJSONDumpsDefaultStr is json.dumps(v, indent=indent, default=str): values of
// unsupported types are written as the JSON string of PyStr(value).
func PyJSONDumpsDefaultStr(v any, indent int) string {
	s, _ := pyJSONDumps(v, indent, func(x any) string { return PyStr(x) })
	return s
}

func pyJSONDumps(v any, indent int, def func(any) string) (string, error) {
	var b strings.Builder
	if err := pyJSONWrite(&b, v, indent, 0, def); err != nil {
		return "", err
	}
	return b.String(), nil
}

func pyJSONNewline(b *strings.Builder, indent, level int) {
	b.WriteByte('\n')
	b.WriteString(strings.Repeat(" ", indent*level))
}

func pyJSONWrite(b *strings.Builder, v any, indent, level int, def func(any) string) error {
	if v == nil {
		b.WriteString("null")
		return nil
	}
	if o, ok := v.(OrderedAny); ok {
		// A typed-nil pointer (e.g. a nil *OrderedMap stored in an interface) is Python None.
		if rv := reflect.ValueOf(v); rv.Kind() == reflect.Pointer && rv.IsNil() {
			b.WriteString("null")
			return nil
		}
		keys := o.KeysAny()
		return pyJSONObject(b, keys, func(k string) any { return o.GetAny(k) }, indent, level, def)
	}
	if bi, ok := v.(*big.Int); ok {
		b.WriteString(bi.String())
		return nil
	}
	rv := reflect.ValueOf(v)
	switch rv.Kind() {
	case reflect.String:
		b.WriteString(pyJSONString(rv.String()))
	case reflect.Bool:
		b.WriteString(strconv.FormatBool(rv.Bool()))
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		b.WriteString(strconv.FormatInt(rv.Int(), 10))
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		b.WriteString(strconv.FormatUint(rv.Uint(), 10))
	case reflect.Float32, reflect.Float64:
		f := rv.Float()
		switch {
		case math.IsNaN(f):
			b.WriteString("NaN")
		case math.IsInf(f, 1):
			b.WriteString("Infinity")
		case math.IsInf(f, -1):
			b.WriteString("-Infinity")
		default:
			b.WriteString(pyFloatRepr(f))
		}
	case reflect.Slice, reflect.Array:
		if rv.Len() == 0 {
			b.WriteString("[]")
			return nil
		}
		b.WriteByte('[')
		for i := 0; i < rv.Len(); i++ {
			if i > 0 {
				b.WriteString(pyJSONItemSep(indent))
			}
			if indent >= 0 {
				pyJSONNewline(b, indent, level+1)
			}
			if err := pyJSONWrite(b, rv.Index(i).Interface(), indent, level+1, def); err != nil {
				return err
			}
		}
		if indent >= 0 {
			pyJSONNewline(b, indent, level)
		}
		b.WriteByte(']')
	case reflect.Map:
		if rv.Type().Key().Kind() != reflect.String {
			return fmt.Errorf("keys must be str, int, float, bool or None, not %s", rv.Type().Key())
		}
		keys := make([]string, 0, rv.Len())
		for _, k := range rv.MapKeys() {
			keys = append(keys, k.String())
		}
		sort.Strings(keys)
		return pyJSONObject(b, keys, func(k string) any { return rv.MapIndex(reflect.ValueOf(k).Convert(rv.Type().Key())).Interface() }, indent, level, def)
	case reflect.Pointer, reflect.Interface:
		if rv.IsNil() {
			b.WriteString("null")
			return nil
		}
		return pyJSONWrite(b, rv.Elem().Interface(), indent, level, def)
	default:
		if def != nil {
			b.WriteString(pyJSONString(def(v)))
			return nil
		}
		return fmt.Errorf("Object of type %s is not JSON serializable", rv.Type().Name())
	}
	return nil
}

// pyJSONCompact is the indent sentinel for separators=(",", ":").
const pyJSONCompact = -2

// PyJSONDumpsCompact mirrors json.dumps(v, separators=(",", ":")) (ensure_ascii).
func PyJSONDumpsCompact(v any) (string, error) { return pyJSONDumps(v, pyJSONCompact, nil) }

func pyJSONItemSep(indent int) string {
	if indent >= 0 || indent == pyJSONCompact {
		return ","
	}
	return ", "
}

func pyJSONObject(b *strings.Builder, keys []string, get func(string) any, indent, level int, def func(any) string) error {
	if len(keys) == 0 {
		b.WriteString("{}")
		return nil
	}
	b.WriteByte('{')
	for i, k := range keys {
		if i > 0 {
			b.WriteString(pyJSONItemSep(indent))
		}
		if indent >= 0 {
			pyJSONNewline(b, indent, level+1)
		}
		b.WriteString(pyJSONString(k))
		if indent == pyJSONCompact {
			b.WriteString(":")
		} else {
			b.WriteString(": ")
		}
		if err := pyJSONWrite(b, get(k), indent, level+1, def); err != nil {
			return err
		}
	}
	if indent >= 0 {
		pyJSONNewline(b, indent, level)
	}
	b.WriteByte('}')
	return nil
}

// pyJSONString is json's py_encode_basestring_ascii: escapes non-ASCII as \uXXXX
// (surrogate pairs above the BMP), control characters, quote and backslash.
func pyJSONString(s string) string {
	var b strings.Builder
	b.WriteByte('"')
	for _, r := range s {
		switch {
		case r == '"':
			b.WriteString(`\"`)
		case r == '\\':
			b.WriteString(`\\`)
		case r == '\n':
			b.WriteString(`\n`)
		case r == '\r':
			b.WriteString(`\r`)
		case r == '\t':
			b.WriteString(`\t`)
		case r == '\b':
			b.WriteString(`\b`)
		case r == '\f':
			b.WriteString(`\f`)
		case r < 0x20 || (r >= 0x7f && r <= 0xffff):
			fmt.Fprintf(&b, `\u%04x`, r)
		case r > 0xffff:
			r -= 0x10000
			fmt.Fprintf(&b, `\u%04x\u%04x`, 0xd800+(r>>10), 0xdc00+(r&0x3ff))
		default:
			b.WriteRune(r)
		}
	}
	b.WriteByte('"')
	return b.String()
}
