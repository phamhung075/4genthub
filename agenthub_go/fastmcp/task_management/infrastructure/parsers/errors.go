package parsers

import "math/big"

// AttributeError mirrors Python's AttributeError.
type AttributeError struct{ Msg string }

func (e *AttributeError) Error() string { return e.Msg }

// UnicodeDecodeError mirrors Python's UnicodeDecodeError (a ValueError subclass).
type UnicodeDecodeError struct{ Msg string }

func (e *UnicodeDecodeError) Error() string { return e.Msg }

// pyTypeName is type(v).__name__ for a decoded JSON value.
func pyTypeName(v any) string {
	switch v.(type) {
	case nil:
		return "NoneType"
	case bool:
		return "bool"
	case string:
		return "str"
	case int64, int, *big.Int:
		return "int"
	case float64:
		return "float"
	case []any:
		return "list"
	}
	return "dict"
}
