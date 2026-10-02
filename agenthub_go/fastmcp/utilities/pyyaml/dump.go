package pyyaml

// Dump is yaml.dump(value, sort_keys=sortKeys, default_flow_style=False) (PyYAML 6, default
// Dumper). value is limited to the shapes produced by entities.DecodeJSON: nil, bool,
// string, int64, *big.Int, float64, []any and *entities.OrderedMap[any].
func Dump(value any, sortKeys bool) (string, error) {
	rep := &representer{sortKeys: sortKeys}
	root, err := rep.representData(value)
	if err != nil {
		return "", err
	}

	e := newEmitter()
	s := newSerializer(e)
	// Serializer.open() -> open(); Representer.represent() -> serialize(); close().
	e.emit(streamStartEvent{})
	s.serialize(root)
	e.emit(streamEndEvent{})
	return e.buf.String(), nil
}
