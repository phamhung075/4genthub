package value_objects

import (
	"fmt"
	"math"
	"reflect"
	"strconv"
	"strings"
)

// ProgressPercentage is an immutable percentage between 0 and 100 inclusive.
type ProgressPercentage struct{ Value int }

// NewProgressPercentage validates the 0-100 range.
func NewProgressPercentage(value int) (ProgressPercentage, error) {
	if value < 0 || value > 100 {
		return ProgressPercentage{}, valueErrorf("Progress percentage must be between 0 and 100, got %d", value)
	}
	return ProgressPercentage{value}, nil
}

// ProgressPercentageFromAny converts int, bool, float, or numeric string input,
// mirroring Python int(value) truncation, then validates the range.
func ProgressPercentageFromAny(value any) (ProgressPercentage, error) {
	if value == nil {
		return ProgressPercentage{}, valueErrorf("Progress percentage cannot be None")
	}
	if i, ok := value.(int); ok {
		return NewProgressPercentage(i)
	}
	i, ok := toInt(value)
	if !ok {
		return ProgressPercentage{}, typeErrorf("Cannot convert %s to progress percentage: %v", pyTypeName(value), value)
	}
	return NewProgressPercentage(i)
}

func toInt(value any) (int, bool) {
	switch v := value.(type) {
	case bool:
		if v {
			return 1, true
		}
		return 0, true
	case int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64:
		return int(reflect.ValueOf(v).Convert(reflect.TypeOf(int64(0))).Int()), true
	case float32:
		return floatToInt(float64(v))
	case float64:
		return floatToInt(v)
	case string:
		i, err := strconv.Atoi(strings.ReplaceAll(strings.TrimSpace(v), "_", ""))
		return i, err == nil
	}
	return 0, false
}

func floatToInt(f float64) (int, bool) {
	if math.IsNaN(f) || math.IsInf(f, 0) {
		return 0, false
	}
	return int(math.Trunc(f)), true
}

func pyTypeName(v any) string {
	switch v.(type) {
	case string:
		return "str"
	case float32, float64:
		return "float"
	case bool:
		return "bool"
	case []any:
		return "list"
	case map[string]any:
		return "dict"
	}
	return fmt.Sprintf("%T", v)
}

func (p ProgressPercentage) ToInt() int { return p.Value }

func (p ProgressPercentage) String() string { return fmt.Sprintf("%d%%", p.Value) }

// GoString mirrors Python's __repr__.
func (p ProgressPercentage) GoString() string {
	return fmt.Sprintf("ProgressPercentage(value=%d)", p.Value)
}

func (p ProgressPercentage) Equals(o ProgressPercentage) bool { return p.Value == o.Value }
func (p ProgressPercentage) EqualsInt(o int) bool             { return p.Value == o }
func (p ProgressPercentage) Lt(o ProgressPercentage) bool     { return p.Value < o.Value }
func (p ProgressPercentage) Le(o ProgressPercentage) bool     { return p.Value <= o.Value }
func (p ProgressPercentage) Gt(o ProgressPercentage) bool     { return p.Value > o.Value }
func (p ProgressPercentage) Ge(o ProgressPercentage) bool     { return p.Value >= o.Value }

func (p ProgressPercentage) IsComplete() bool   { return p.Value == 100 }
func (p ProgressPercentage) IsNotStarted() bool { return p.Value == 0 }
func (p ProgressPercentage) IsInProgress() bool { return p.Value > 0 && p.Value < 100 }
