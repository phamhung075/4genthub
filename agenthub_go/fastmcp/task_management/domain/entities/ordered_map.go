package entities

// OrderedMap is a string-keyed map that iterates in insertion order, like a
// Python dict. The zero value is ready to use.
type OrderedMap[V any] struct {
	keys []string
	m    map[string]V
}

func NewOrderedMap[V any]() *OrderedMap[V] { return &OrderedMap[V]{m: map[string]V{}} }

func (o *OrderedMap[V]) Set(k string, v V) {
	if o.m == nil {
		o.m = map[string]V{}
	}
	if _, ok := o.m[k]; !ok {
		o.keys = append(o.keys, k)
	}
	o.m[k] = v
}

func (o *OrderedMap[V]) Get(k string) (V, bool) { v, ok := o.m[k]; return v, ok }
func (o *OrderedMap[V]) Has(k string) bool      { _, ok := o.m[k]; return ok }
func (o *OrderedMap[V]) Len() int               { return len(o.keys) }

// Keys returns a copy of the keys in insertion order.
func (o *OrderedMap[V]) Keys() []string { return append([]string{}, o.keys...) }

func (o *OrderedMap[V]) Delete(k string) {
	if _, ok := o.m[k]; !ok {
		return
	}
	delete(o.m, k)
	for i, key := range o.keys {
		if key == k {
			o.keys = append(o.keys[:i], o.keys[i+1:]...)
			break
		}
	}
}

// Values returns the values in insertion order.
func (o *OrderedMap[V]) Values() []V {
	out := make([]V, 0, len(o.keys))
	for _, k := range o.keys {
		out = append(out, o.m[k])
	}
	return out
}

// Copy returns a shallow copy (dict.copy()).
func (o *OrderedMap[V]) Copy() *OrderedMap[V] {
	c := NewOrderedMap[V]()
	for _, k := range o.keys {
		c.Set(k, o.m[k])
	}
	return c
}

// StringSet is a set that keeps insertion order (Python set order is unspecified).
type StringSet struct{ items []string }

func (s *StringSet) Add(v string) {
	if !s.Has(v) {
		s.items = append(s.items, v)
	}
}

func (s *StringSet) Has(v string) bool { return indexOf(s.items, v) >= 0 }
func (s *StringSet) Len() int          { return len(s.items) }
func (s *StringSet) Items() []string   { return append([]string{}, s.items...) }

func (s *StringSet) Remove(v string) {
	if i := indexOf(s.items, v); i >= 0 {
		s.items = append(s.items[:i], s.items[i+1:]...)
	}
}

// KeysAny and GetAny let value_objects (which cannot import entities) iterate any
// OrderedMap in insertion order through value_objects.OrderedAny.
func (o *OrderedMap[V]) KeysAny() []string { return o.Keys() }
func (o *OrderedMap[V]) GetAny(k string) any {
	v, _ := o.Get(k)
	return v
}
